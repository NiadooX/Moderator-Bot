from aiogram import BaseMiddleware
from aiogram import types
from datetime import datetime, timedelta
from aiogram.dispatcher.flags import get_flag
from misc import connect_to_db
import texts
import aiogram.exceptions
from banwords import filter_text
import asyncio


cache = {}


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, *, timeout=3):
        self.timeout = timeout

    async def __call__(self, handler, event, data):
        if get_flag(data, name='only_without_state'):
            if await data['state'].get_state() is not None:
                return

        if get_flag(data, name='use_throttle') or isinstance(event, types.CallbackQuery):
            bot = data['bot']

            if event.from_user.id not in cache.keys():
                cache[event.from_user.id] = datetime.now() + timedelta(seconds=self.timeout)
                try:
                    result = await handler(event, data)
                    return result
                except aiogram.exceptions.TelegramRetryAfter:
                    cache[event.from_user.id] = datetime.now() + timedelta(seconds=self.timeout + 5)
                    await asyncio.sleep(self.timeout + 5)
            else:
                if cache[event.from_user.id] > datetime.now():
                    try:
                        if not isinstance(event, types.Message) and not isinstance(event, types.CallbackQuery):
                            return
                        if isinstance(event, types.CallbackQuery):
                            try:
                                await event.answer(texts.DONT_FLOOD)
                            except aiogram.exceptions.TelegramRetryAfter:
                                await asyncio.sleep(6)
                    except aiogram.exceptions.TelegramRetryAfter:
                        await asyncio.sleep(6)
                    return

                else:
                    cache[event.from_user.id] = datetime.now() + timedelta(seconds=self.timeout)
                    try:
                        result = await handler(event, data)
                        return result
                    except aiogram.exceptions.TelegramRetryAfter:
                        cache[event.from_user.id] = datetime.now() + timedelta(seconds=self.timeout + 5)
                        await asyncio.sleep(self.timeout + 5)
        else:
            try:
                result = await handler(event, data)
                return result
            except aiogram.exceptions.TelegramRetryAfter:
                cache[event.from_user.id] = datetime.now() + timedelta(seconds=self.timeout+5)
                await asyncio.sleep(self.timeout + 5)


class CheckUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if get_flag(data, name='use_verify'):
            bot = data['bot']

            mydb = await connect_to_db()
            cursor = await mydb.cursor()

            check_user_sql = f"SELECT username FROM users WHERE id = '{event.from_user.id}';"
            await cursor.execute(check_user_sql)
            if await cursor.fetchone():
                return await handler(event, data)
            else:
                await bot.send_message(event.from_user.id, texts.NON_REGISTR_ERROR)
        else:
            return await handler(event, data)


chat_administrators_cache = {}


class CheckBotRights(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if get_flag(data, name='check_bot_rights'):

            bot = data['bot']

            if isinstance(event, types.CallbackQuery):
                chat_type = event.message.chat.type
                chat_id = event.message.chat.id
            elif isinstance(event, types.Message):
                chat_type = event.chat.type
                chat_id = event.chat.id
            elif isinstance(event, types.ChatMemberUpdated):
                chat_type = event.chat.type
                chat_id = event.chat.id
            else:
                return

            if chat_type in ['group', 'supergroup']:
                group_id = data['event_chat'].id
            else:
                mydb = await connect_to_db()
                cursor = await mydb.cursor()

                get_now_chat_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {event.from_user.id};"
                await cursor.execute(get_now_chat_sql)
                r = await cursor.fetchone()
                if r is None:
                    return
                group_id = r[0]

            if chat_administrators_cache.get(chat_id) is None or chat_administrators_cache[chat_id][1] < datetime.now():
                tmp = await bot.get_chat_administrators(group_id)
                administrators = [i.user.id for i in tmp]
                administrators_without_bots = [i.user.id for i in tmp if not i.user.is_bot]
                chat_administrators_cache[chat_id] = (administrators, datetime.now() + timedelta(seconds=10), administrators_without_bots)
            else:
                if chat_administrators_cache[chat_id] == group_id:
                    administrators = chat_administrators_cache[chat_id][0]
                    administrators_without_bots = chat_administrators_cache[chat_id][2]
                else:
                    tmp = await bot.get_chat_administrators(group_id)
                    administrators = [i.user.id for i in tmp]
                    administrators_without_bots = [i.user.id for i in tmp if not i.user.is_bot]
                    chat_administrators_cache[chat_id] = (administrators, datetime.now() + timedelta(seconds=10), administrators_without_bots)

            me = await bot.get_me()
            if me.id in administrators:
                return await handler(event, data)
            else:
                try:
                    await bot.send_message(event.chat.id, texts.BOT_NOT_ADMIN)
                except aiogram.exceptions.TelegramBadRequest:
                    await bot.send_message(event.from_user.id, texts.BOT_NOT_ADMIN)
                return
        else:
            return await handler(event, data)


class OnlyGroupActionsMiddlware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if not isinstance(event, types.Message):
            return await handler(event, data)
        chat_type = data['event_chat'].type
        try:
            if data['command'].command in ['ban', 'unban', 'mute', 'unmute']:
                if chat_type in ['group', 'supergroup']:
                    return await handler(event, data)
                else:
                    return
            else:
                return await handler(event, data)
        except KeyError:
            return await handler(event, data)


class CheckActionNormal(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data['bot']
        bot_id = (await bot.get_me()).id
        if get_flag(data, name='check_action_normal'):
            try:
                to_user = event.reply_to_message.from_user.id
                from_user = event.from_user.id
            except:
                return

            if (to_user != bot_id) and (from_user != to_user):
                return await handler(event, data)
            else:
                try:
                    await bot.send_message(event.chat.id, texts.BAD_ACTION, reply_to_message_id=event.message_id)
                except:
                    return
        else:
            return await handler(event, data)


class FilterTextMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        bot = data['bot']
        if event.chat.type in ['group', 'supergroup']:
            try:
                mydb = await connect_to_db()
                cursor = await mydb.cursor()

                if isinstance(event, types.CallbackQuery):
                    chat_type = event.message.chat.type
                    chat_id = event.message.chat.id
                elif isinstance(event, types.Message):
                    chat_type = event.chat.type
                    chat_id = event.chat.id
                elif isinstance(event, types.ChatMemberUpdated):
                    chat_type = event.chat.type
                    chat_id = event.chat.id
                else:
                    return

                if chat_type in ['group', 'supergroup']:
                    group_id = data['event_chat'].id
                else:
                    return

                if chat_administrators_cache.get(chat_id) is None or chat_administrators_cache[chat_id][1] < datetime.now():
                    tmp = await bot.get_chat_administrators(group_id)
                    administrators = [i.user.id for i in tmp]
                    administrators_without_bots = [i.user.id for i in tmp if not i.user.is_bot]
                    chat_administrators_cache[chat_id] = (administrators, datetime.now() + timedelta(seconds=10), administrators_without_bots)
                else:
                    administrators = chat_administrators_cache[chat_id][0]
                    administrators_without_bots = chat_administrators_cache[chat_id][2]

                get_banwords_list_sql = f"SELECT banwords_list FROM users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id WHERE owner_id = {administrators_without_bots[0]} AND ugs.group_id = uga.group_id;"
                await cursor.execute(get_banwords_list_sql)

                r = await cursor.fetchone()
                banwords_list = [i.replace("'", '').replace('"', '').strip() for i in r[0].lstrip('[').rstrip(']').split(', ')]
                if not await filter_text(event.text, banwords_list):
                    await bot.delete_message(chat_id=event.chat.id, message_id=event.message_id)
                    await bot.send_message(event.chat.id, texts.MESSAGE_HAVE_BANWORD)
                    return
                else:
                    return await handler(event, data)
            except:
                return await handler(event, data)
        else:
            return await handler(event, data)


class CheckChosenGroupPrivate(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if get_flag(data, 'check_chosen_group_private'):
            print('Im working')
            mydb = await connect_to_db()
            cursor = await mydb.cursor()

            user_id = event.from_user.id
            check_chosen_group_sql = f"SELECT bot_groups.id FROM bot_groups INNER JOIN users_groups_actions ON bot_groups.owner_id = users_groups_actions.user_id WHERE owner_id = {user_id};"
            await cursor.execute(check_chosen_group_sql)
            if not await cursor.fetchone():
                return
            return await handler(event, data)
        else:
            return await handler(event, data)

