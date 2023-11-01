import aiogram.exceptions
from aiogram import Router, Bot, F
from aiogram import types
from aiogram.filters.command import Command
from aiogram.filters.chat_member_updated import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, KICKED, IS_ADMIN, LEFT, RESTRICTED, MEMBER
from middlewares import ThrottlingMiddleware, CheckBotRights, OnlyGroupActionsMiddlware, CheckActionNormal, FilterTextMiddleware
from misc import connect_to_db, time_to_cancel_user_ban, time_to_cancel_user_unban, async_range, CheckUserAction, CheckUserRights, concat_dicts, CheckCallbackNormal, time_to_ready_in_game1, CheckGame1, tic_tac_toe_fillers, async_list
import texts
from datetime import datetime, timedelta
import asyncio
import keyboards
import aiogram
from copy import deepcopy
from aiogram.types.chat_permissions import ChatPermissions
import random
import re
from banwords import async_items
import pymysql.err


router2 = Router()
router2.chat_member.middleware(CheckBotRights())
router2.message.middleware(CheckBotRights())
router2.callback_query.middleware(CheckBotRights())
router2.chat_member.middleware(OnlyGroupActionsMiddlware())
router2.message.middleware(OnlyGroupActionsMiddlware())
router2.message.middleware(CheckActionNormal())
router2.message.middleware(FilterTextMiddleware())
router2.message.middleware(ThrottlingMiddleware(timeout=0.5))
router2.callback_query.middleware(ThrottlingMiddleware(timeout=3))


USE_THROTTLE = {'use_throttle': True}
CHECK_BOT_RIGHT = {'check_bot_rights': True}
CHECK_ACTION_NORMAL = {'check_action_normal': True}
CHECK_BOT_RIGHT_AND_ACTION_NORMAL = concat_dicts(CHECK_BOT_RIGHT, CHECK_ACTION_NORMAL)
CHECK_BOT_RIGHT_AND_USE_THROTTLE = concat_dicts(CHECK_BOT_RIGHT, USE_THROTTLE)
CHECK_ACTION_NORMAL_AND_USE_THROTTLE = concat_dicts(CHECK_ACTION_NORMAL, USE_THROTTLE)
CHECK_BOT_RIGHT_AND_CHECK_ACTION_NORMAL_AND_USE_THROTTLE = concat_dicts(CHECK_BOT_RIGHT, concat_dicts(CHECK_ACTION_NORMAL, USE_THROTTLE))


chat_administrators_cache = {}
temp_tic_tac_toe = {'started': False}


@router2.my_chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER))
async def bot_group_start_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not event.chat.type in ['group', 'supergroup']:
        return
    mydb = await connect_to_db()
    cursor = await mydb.cursor()
    types_dict = {'group': 'группу', 'supergroup': 'супергруппу'}

    if chat_administrators_cache.get(event.chat.id) is None or chat_administrators_cache[event.chat.id][1] < datetime.now():
        administrators = [i.user.id for i in await bot.get_chat_administrators(event.chat.id)]
        chat_administrators_cache[event.chat.id] = (administrators, datetime.now() + timedelta(seconds=10))
    else:
        administrators = chat_administrators_cache[event.chat.id][0]

    to_insert = []
    group_id = event.chat.id
    group_title = event.chat.title
    group_type = event.chat.type
    date_now = datetime.now().strftime('%d.%m.%Y %X')
    my_id = (await bot.get_me()).id
    if administrators:
        for admin in administrators:
            if admin == my_id:
                continue
            check_group_sql = f"SELECT * FROM bot_groups WHERE id = {event.chat.id} AND owner_id = {admin}"
            await cursor.execute(check_group_sql)
            if await cursor.fetchone():
                to_insert.append(f"UPDATE bot_groups SET add_date = '{date_now}' WHERE id = {event.chat.id} AND owner_id = {admin}")
                continue

            check_admin_unique_sql = f"SELECT id FROM users WHERE id = {admin};"
            await cursor.execute(check_admin_unique_sql)
            if not await cursor.fetchone():
                to_insert.append(f"INSERT INTO users (id, date_registration, has_active_groups) VALUES ({admin}, '{date_now}', 1)")
            to_insert.append(f"INSERT INTO bot_groups (id, title, owner_id, type, add_date) VALUES ({group_id}, '{group_title}', {admin}, '{group_type}', '{date_now}')")
            to_insert.append(f"INSERT INTO users_groups_settings (group_id, owner_id, use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, banwords_list, muted_users_list) VALUES ({group_id}, {admin}, True, True, False, '[]', '[]')")
    else:
        await bot.send_message(event.chat.id, texts.NON_ADMINS_ERROR)
        await bot.leave_chat(event.chat.id)
        return

    insert_new_group_sql = f"START TRANSACTION; {'; '.join(to_insert)}" + '; COMMIT;'

    await cursor.execute(insert_new_group_sql)
    await bot.send_message(event.chat.id, texts.START_MESSAGE_GROUP_TEMP1 + types_dict[event.chat.type] + texts.START_MESSAGE_GROUP_TEMP2)


@router2.message(CheckUserRights(), Command('ban'), F.reply_to_message, F.func(lambda x: not x.from_user.is_bot), flags=CHECK_BOT_RIGHT_AND_CHECK_ACTION_NORMAL_AND_USE_THROTTLE)
async def ban_user_handler(message: types.Message, bot: Bot, command: aiogram.filters.CommandObject):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    question_message = await message.reply(texts.QUESTION_TO_ACTION_SENDED_TO_U)

    to_user_bot_check = {False: 'пользователя', True: 'бота'}
    to_user_bot_check2 = {False: 'Пользователь', True: 'Бот'}
    keyboard = await keyboards.sure_about_ban_user_keyboard()

    try:
        ban_days = int(command.args)
        if ban_days >= 366:
            ban_days = 0
    except:
        ban_days = 0

    """Func"""
    async def __ban_user():
        try:
            if ban_days == 0:
                await bot.ban_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id)
            else:
                await bot.ban_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id, until_date=timedelta(days=ban_days))
            await bot.send_message(message.from_user.id, f'{to_user_bot_check2[message.reply_to_message.from_user.is_bot]} "{message.reply_to_message.from_user.full_name}" {texts.USER_BAN_SUCCESSFUL}')

        except aiogram.exceptions.TelegramBadRequest:
            await bot.send_message(message.from_user.id, texts.USER_BAN_FAILED)
            await bot.edit_message_text(text=texts.USER_BAN_FAILED, chat_id=message.chat.id, message_id=question_message.message_id)
            return

        await bot.edit_message_text(text=f'{to_user_bot_check2[message.reply_to_message.from_user.is_bot]} "{message.reply_to_message.from_user.full_name}" {texts.USER_BAN_SUCCESSFUL}', chat_id=message.chat.id, message_id=question_message.message_id)

        await mydb.commit()


    get_use_notify_for_ban_user_sql = f"SELECT use_notify_for_ban_user FROM users_groups_settings WHERE owner_id = {message.from_user.id} AND group_id = {message.chat.id};"
    await cursor.execute(get_use_notify_for_ban_user_sql)
    r0 = await cursor.fetchone()
    if r0 is None:
        return
    use_notify_for_ban_user = bool(int(r0[0]))

    if not use_notify_for_ban_user:
        await __ban_user()
        return

    temp_check_sql = f"SELECT warn_message_id FROM users_moderations WHERE from_user = {message.from_user.id} AND group_id = {message.chat.id} AND to_user = {message.reply_to_message.from_user.id} AND ended is False AND action = 'ban';"
    await cursor.execute(temp_check_sql)
    r = await cursor.fetchone()
    if r:
        temp = await bot.send_message(message.from_user.id, f'{texts.ARE_U_SURE_ABOUT_BAN_USER_TEMP1} {to_user_bot_check[message.reply_to_message.from_user.is_bot]} {message.reply_to_message.from_user.full_name}? {to_user_bot_check2[message.reply_to_message.from_user.is_bot]} {texts.ARE_U_SURE_ABOUT_BAN_USER_TEMP2} {time_to_cancel_user_ban} секунд', reply_markup=keyboard)
        old_warn_message_id = r[0]
        try:
            await bot.delete_message(chat_id=temp.chat.id, message_id=old_warn_message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
        update_action_sql = f"""UPDATE users_moderations SET ban_days = {ban_days}, question_message_id = {question_message.message_id}, to_user_full_name = '{message.reply_to_message.from_user.full_name}', to_user = {message.reply_to_message.from_user.id}, action = 'ban', warn_message_id = {temp.message_id}, ended = False, from_bot = {message.from_user.is_bot}, to_bot = {message.reply_to_message.from_user.is_bot}, date = '{datetime.now().strftime('%d.%m.%Y %X')}' WHERE from_user = {message.from_user.id} AND group_id = {message.chat.id} AND to_user = {message.reply_to_message.from_user.id} AND ended is False AND action = 'ban';"""
        await cursor.execute(update_action_sql)
        await mydb.commit()
    else:
        temp = await bot.send_message(message.from_user.id, f'{texts.ARE_U_SURE_ABOUT_BAN_USER_TEMP1} {to_user_bot_check[message.reply_to_message.from_user.is_bot]} {message.reply_to_message.from_user.full_name}? {to_user_bot_check2[message.reply_to_message.from_user.is_bot]} {texts.ARE_U_SURE_ABOUT_BAN_USER_TEMP2} {time_to_cancel_user_ban} секунд', reply_markup=keyboard)
        insert_action_sql = f"""INSERT INTO users_moderations (group_id, warn_message_id, question_message_id, from_user, to_user, to_user_full_name, action, ban_days, ended, from_bot, to_bot, date) VALUES ({message.chat.id}, {temp.message_id}, {question_message.message_id}, {message.from_user.id}, {message.reply_to_message.from_user.id}, '{message.reply_to_message.from_user.full_name}', 'ban', {ban_days}, False, {message.from_user.is_bot}, {message.reply_to_message.from_user.is_bot}, '{datetime.now().strftime('%d.%m.%Y %X')}');"""
        await cursor.execute(insert_action_sql)
        await mydb.commit()

    warn_message = temp.text

    async for i in async_range(time_to_cancel_user_ban):
        try:
            await bot.edit_message_text(text=warn_message.replace(str(time_to_cancel_user_ban-i), str(time_to_cancel_user_ban-(i+1))), chat_id=temp.chat.id, message_id=temp.message_id, reply_markup=keyboard)
            await asyncio.sleep(1)
            warn_message = warn_message.replace(str(time_to_cancel_user_ban - i), str(time_to_cancel_user_ban - (i + 1)))
        except aiogram.exceptions.TelegramBadRequest:
            break
    if i == time_to_cancel_user_ban - 1:
        try:
            await bot.delete_message(chat_id=temp.chat.id, message_id=temp.message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
        end_action_sql = f"UPDATE users_moderations SET ended = True WHERE from_user = {message.from_user.id} AND group_id = {message.chat.id} AND to_user = {message.reply_to_message.from_user.id} AND ended is False AND action = 'ban';"
        await cursor.execute(end_action_sql)

        await __ban_user()
    await mydb.commit()


@router2.callback_query(CheckUserAction('ban'), F.data == 'sure_to_ban', CheckCallbackNormal(), flags=CHECK_BOT_RIGHT)
async def access_ban_handler(call: types.CallbackQuery, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    get_data_sql = f"SELECT group_id, to_user, to_bot, to_user_full_name, question_message_id, ban_days FROM users_moderations WHERE from_user = {call.from_user.id} AND ended is False AND warn_message_id = {call.message.message_id} AND action = 'ban';"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()
    if r:
        group_id = r[0]
    else:
        return

    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    user_to_ban = r[1]

    await bot.edit_message_text(text=f'{to_user_bot_check[r[2]]} "{r[3]}" {texts.USER_BAN_SUCCESSFUL}', chat_id=group_id, message_id=r[4])

    end_action_sql = f"UPDATE users_moderations SET ended = True WHERE from_user = {call.from_user.id} AND group_id = {group_id} AND to_user = {user_to_ban} AND ended is False AND action = 'ban';"
    await cursor.execute(end_action_sql)
    await mydb.commit()

    ban_days = r[5]
    try:
        if ban_days == 0:
            await bot.ban_chat_member(chat_id=group_id, user_id=r[1])
        else:
            await bot.ban_chat_member(chat_id=group_id, user_id=r[1], until_date=timedelta(days=ban_days))
        await bot.send_message(call.from_user.id, f'{to_user_bot_check[r[2]]} "{r[3]}" {texts.USER_BAN_SUCCESSFUL}')

    except aiogram.exceptions.TelegramBadRequest:
        await bot.send_message(call.from_user.id, texts.USER_BAN_FAILED)
        await bot.edit_message_text(text=texts.USER_BAN_FAILED, chat_id=group_id, message_id=r[4])


@router2.callback_query(CheckUserAction('ban'), F.data == 'unsure_to_ban', CheckCallbackNormal(), flags=CHECK_BOT_RIGHT)
async def cancel_ban_handler(call: types.CallbackQuery, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_data_sql = f"SELECT group_id, to_user, to_bot, to_user_full_name, question_message_id FROM users_moderations WHERE from_user = {call.from_user.id} AND ended is False AND warn_message_id = {call.message.message_id} AND action = 'ban';"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()
    if r:
        group_id = r[0]
    else:
        return

    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    await bot.edit_message_text(text=texts.ACTION_WAS_CANCELED, chat_id=group_id, message_id=r[4])

    await bot.send_message(call.from_user.id, texts.ACTION_WAS_CANCELED)
    end_action_sql = f"UPDATE users_moderations SET ended = True WHERE from_user = {call.from_user.id} AND group_id = {group_id} AND to_user = {r[1]} AND ended is False AND action = 'ban';"
    await cursor.execute(end_action_sql)
    await mydb.commit()


@router2.message(Command('ban'), F.reply_to_message, F.func(lambda x: not x.from_user.is_bot), flags=CHECK_BOT_RIGHT)
async def ban_user_failed_handler(message: types.Message):
    await message.reply(texts.BAN_USER_FAILED_GROUP)


@router2.message(CheckUserRights(), Command('unban'), F.reply_to_message, F.func(lambda x: not x.from_user.is_bot), flags=CHECK_BOT_RIGHT_AND_ACTION_NORMAL)
async def unban_user_handler(message: types.Message, bot: Bot):
    question_message = await message.reply(texts.QUESTION_TO_ACTION_SENDED_TO_U)

    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    to_user_bot_check = {False: 'пользователя', True: 'бота'}
    to_user_bot_check2 = {False: 'Пользователь', True: 'Бот'}
    keyboard = await keyboards.sure_about_unban_user_keyboard()


    """Func"""
    async def __unban_user():
        await bot.send_message(message.from_user.id, f'{to_user_bot_check2[message.reply_to_message.from_user.is_bot]} "{message.reply_to_message.from_user.full_name}" {texts.USER_UNBAN_SUCCESSFUL}')
        end_action_sql = f"UPDATE users_moderations SET ended = True WHERE from_user = {message.from_user.id} AND group_id = {message.chat.id} AND to_user = {message.reply_to_message.from_user.id} AND ended is False AND action = 'unban';"
        await cursor.execute(end_action_sql)
        await bot.edit_message_text(text=f'{to_user_bot_check2[message.reply_to_message.from_user.is_bot]} "{message.reply_to_message.from_user.full_name}" {texts.USER_UNBAN_SUCCESSFUL}', chat_id=message.chat.id, message_id=question_message.message_id)

        await bot.unban_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id, only_if_banned=True)

        await mydb.commit()


    get_use_notify_for_unban_user_sql = f"SELECT use_notify_for_unban_user FROM users_groups_settings WHERE owner_id = {message.from_user.id} AND group_id = {message.chat.id};"
    await cursor.execute(get_use_notify_for_unban_user_sql)
    r0 = await cursor.fetchone()
    if r0 is None:
        return
    use_notify_for_unban_user = bool(int(r0[0]))

    if not use_notify_for_unban_user:
        await __unban_user()
        return

    temp_check_sql = f"SELECT warn_message_id FROM users_moderations WHERE from_user = {message.from_user.id} AND group_id = {message.chat.id} AND to_user = {message.reply_to_message.from_user.id} AND ended is False AND action = 'unban';"
    await cursor.execute(temp_check_sql)
    r = await cursor.fetchone()
    if r:
        temp = await bot.send_message(message.from_user.id, f'{texts.ARE_U_SURE_ABOUT_UNBAN_USER_TEMP1} {to_user_bot_check[message.reply_to_message.from_user.is_bot]} {message.reply_to_message.from_user.full_name}? {to_user_bot_check2[message.reply_to_message.from_user.is_bot]} {texts.ARE_U_SURE_ABOUT_UNBAN_USER_TEMP2} {time_to_cancel_user_ban} секунд', reply_markup=keyboard)
        old_warn_message_id = r[0]
        try:
            await bot.delete_message(chat_id=temp.chat.id, message_id=old_warn_message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
        update_action_sql = f"""UPDATE users_moderations SET question_message_id = {question_message.message_id}, to_user_full_name = '{message.reply_to_message.from_user.full_name}', to_user = {message.reply_to_message.from_user.id}, action = 'unban', warn_message_id = {temp.message_id}, ended = False, from_bot = {message.from_user.is_bot}, to_bot = {message.reply_to_message.from_user.is_bot}, date = '{datetime.now().strftime('%d.%m.%Y %X')}' WHERE from_user = {message.from_user.id} AND group_id = {message.chat.id} AND to_user = {message.reply_to_message.from_user.id} AND ended is False AND action = 'unban';"""
        await cursor.execute(update_action_sql)
        await mydb.commit()
    else:
        temp = await bot.send_message(message.from_user.id, f'{texts.ARE_U_SURE_ABOUT_UNBAN_USER_TEMP1} {to_user_bot_check[message.reply_to_message.from_user.is_bot]} {message.reply_to_message.from_user.full_name}? {to_user_bot_check2[message.reply_to_message.from_user.is_bot]} {texts.ARE_U_SURE_ABOUT_UNBAN_USER_TEMP2} {time_to_cancel_user_ban} секунд', reply_markup=keyboard)
        insert_action_sql = f"""INSERT INTO users_moderations (group_id, warn_message_id, question_message_id, from_user, to_user, to_user_full_name, action, ended, from_bot, to_bot, date) VALUES ({message.chat.id}, {temp.message_id}, {question_message.message_id}, {message.from_user.id}, {message.reply_to_message.from_user.id}, '{message.reply_to_message.from_user.full_name}', 'unban', False, {message.from_user.is_bot}, {message.reply_to_message.from_user.is_bot}, '{datetime.now().strftime('%d.%m.%Y %X')}');"""
        await cursor.execute(insert_action_sql)
        await mydb.commit()

    warn_message = temp.text

    async for i in async_range(time_to_cancel_user_unban):
        try:
            await bot.edit_message_text(text=warn_message.replace(str(time_to_cancel_user_unban - i), str(time_to_cancel_user_unban - (i + 1))), chat_id=temp.chat.id, message_id=temp.message_id, reply_markup=keyboard)
            await asyncio.sleep(1)
            warn_message = warn_message.replace(str(time_to_cancel_user_unban - i), str(time_to_cancel_user_unban - (i + 1)))
        except aiogram.exceptions.TelegramBadRequest:
            break
    if i == time_to_cancel_user_unban - 1:
        try:
            await bot.delete_message(chat_id=temp.chat.id, message_id=temp.message_id)
        except aiogram.exceptions.TelegramBadRequest:
            pass
        to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
        await __unban_user()


@router2.callback_query(CheckUserAction('unban'), F.data == 'sure_to_unban', CheckCallbackNormal(), flags=CHECK_BOT_RIGHT)
async def access_unban_handler(call: types.CallbackQuery, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    get_data_sql = f"SELECT group_id, to_user, to_bot, to_user_full_name, question_message_id FROM users_moderations WHERE from_user = {call.from_user.id} AND ended is False AND warn_message_id = {call.message.message_id} AND action = 'unban';"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()

    if r:
        group_id = r[0]
    else:
        return

    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    user_to_unban = r[1]
    await bot.send_message(call.from_user.id, f'{to_user_bot_check[r[2]]} "{r[3]}" {texts.USER_UNBAN_SUCCESSFUL}')
    await bot.edit_message_text(text=f'{to_user_bot_check[r[2]]} "{r[3]}" {texts.USER_UNBAN_SUCCESSFUL}', chat_id=group_id, message_id=r[4])
    end_action_sql = f"UPDATE users_moderations SET ended = True WHERE from_user = {call.from_user.id} AND group_id = {group_id} AND to_user = {user_to_unban} AND ended is False AND action = 'unban';"
    await cursor.execute(end_action_sql)
    await mydb.commit()

    await bot.unban_chat_member(chat_id=group_id, user_id=r[1], only_if_banned=True)


@router2.callback_query(CheckUserAction('unban'), F.data == 'unsure_to_unban', CheckCallbackNormal(), flags=CHECK_BOT_RIGHT_AND_USE_THROTTLE)
async def cancel_unban_handler(call: types.CallbackQuery, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_data_sql = f"SELECT group_id, to_user, to_bot, to_user_full_name, question_message_id FROM users_moderations WHERE from_user = {call.from_user.id} AND ended is False AND warn_message_id = {call.message.message_id} AND action = 'unban';"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()
    if r:
        group_id = r[0]
    else:
        return

    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    await bot.edit_message_text(text=texts.ACTION_WAS_CANCELED, chat_id=group_id, message_id=r[4])

    await bot.send_message(call.from_user.id, texts.ACTION_WAS_CANCELED)

    end_action_sql = f"UPDATE users_moderations SET ended = True WHERE from_user = {call.from_user.id} AND group_id = {group_id} AND to_user = {r[1]} AND ended is False AND action = 'unban';"
    await cursor.execute(end_action_sql)
    await mydb.commit()


@router2.message(Command('unban'), F.func(lambda x: not x.from_user.is_bot), flags=CHECK_BOT_RIGHT_AND_USE_THROTTLE)
async def unban_user_failed_handler(message: types.Message):
    await message.reply(texts.UNBAN_USER_FAILED_GROUP)


@router2.message(Command('mute'), F.reply_to_message, flags=CHECK_BOT_RIGHT_AND_ACTION_NORMAL)
async def mute_temp_handler(message: types.Message, bot: Bot):
    if message.chat.type == 'supergroup':
        new_user_rights = ChatPermissions(can_send_messages=False, can_invite_users=False)
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id, permissions=new_user_rights)
    else:
        await message.answer(texts.MUTE_OR_UNMUTE_FAILED_GROUP)
        return

    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    from_user_bot_check = {False: 'пользователем', True: 'ботом'}
    await message.answer(f'{to_user_bot_check[message.reply_to_message.from_user.is_bot]} {message.reply_to_message.from_user.full_name} {texts.USER_WAS_MUTED_TEMP1} {from_user_bot_check[message.from_user.is_bot]} {message.from_user.full_name}\n{texts.USER_WAS_MUTED_TEMP2}')


@router2.message(Command('unmute'), F.reply_to_message, flags=CHECK_BOT_RIGHT_AND_ACTION_NORMAL)
async def umnute_temp_handler(message: types.Message, bot: Bot):
    if message.chat.type == 'supergroup':
        new_user_rights = ChatPermissions(can_send_messages=True, can_invite_users=True)
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=message.reply_to_message.from_user.id, permissions=new_user_rights)
    else:
        await message.answer(texts.MUTE_OR_UNMUTE_FAILED_GROUP)
        return

    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    from_user_bot_check = {False: 'пользователем', True: 'ботом'}
    await message.answer(f'{to_user_bot_check[message.reply_to_message.from_user.is_bot]} {message.reply_to_message.from_user.full_name} {texts.USER_WAS_UNMUTED} {from_user_bot_check[message.from_user.is_bot]} {message.from_user.full_name}')


@router2.message(Command('random'), flags=CHECK_BOT_RIGHT_AND_USE_THROTTLE)
async def random_num_handler(message: types.Message, command: types.BotCommand):
    args_ = command.args
    if not args_ or len(args_.split()) == 1:
        from_number = 1
        to_number = 100
    else:
        args_ = args_.split()
        try:
            from_number = int(args_[0])
            to_number = int(args_[1]) if from_number <= int(args_[1]) else int(args_[0])
        except:
            await message.answer(texts.INVALID_RANDOM_NUM)
            return
    await message.answer(f'{message.from_user.first_name}, {texts.UR_RANDOM_NUMBER} {random.randint(from_number, to_number)}')


@router2.message(Command('tic_tac_toe', 'game1'), F.func(lambda x: x.command not in texts.BOT_GROUP_COMMANDS_TEXTS if isinstance(x, types.BotCommand) else True), CheckGame1(), flags=CHECK_BOT_RIGHT_AND_USE_THROTTLE)
async def tic_tac_toe_game_temp_handler(message: types.Message, command: types.BotCommand, bot: Bot):
    if re.fullmatch(r'@\w+ @\w+', str(command.args)):
        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        get_check_unique_sql = f"SELECT id FROM tic_tac_toe_game WHERE group_id = {message.chat.id} AND user_start_message_id = {message.message_id};"
        await cursor.execute(get_check_unique_sql)
        r_temp = await cursor.fetchone()
        if r_temp is None:
            fighters = command.args.strip().split()
            fighter1 = fighters[0].lower()
            fighter2 = fighters[1].lower()

            bot_username = f'@{(await bot.get_me()).username}'.lower()
            if not (fighter1 != fighter2 and (fighter1 != bot_username and fighter2 != bot_username)):
                await message.answer(texts.INVALID_FIGHTERS_GAME1)
                return
            if not f'@{message.from_user.username.lower()}' in fighters:
                await message.answer(texts.ANOTHER_FIGHTERS_GAME1)
                return

            insert_fighters_sql = f"INSERT INTO tic_tac_toe_game (group_id, user_start_message_id, fighter1_username, fighter1_ready, fighter2_username, fighter2_ready, ended) VALUES ({message.chat.id}, {message.message_id}, '{fighter1}', False, '{fighter2}', False, False);"
            await cursor.execute(insert_fighters_sql)
            await mydb.commit()

            temp = await message.answer(f'{fighter1}, {fighter2}{texts.GAME1_READY_VERIFICATION} {time_to_ready_in_game1} секунд!', reply_markup=await keyboards.tic_tac_toe_game_ready_keyboard(fighter1=fighter1, fighter2=fighter2, fighter1_ready=False, fighter2_ready=False))

            add_last_ready_message_id_sql = f"UPDATE tic_tac_toe_game SET last_ready_message_id = {temp.message_id} WHERE group_id = {message.chat.id} AND fighter1_username = '{fighter1}' AND fighter2_username = '{fighter2}' AND ended is False;"
            await cursor.execute(add_last_ready_message_id_sql)
            await mydb.commit()

            warn_message = temp.text

            async for i in async_range(time_to_ready_in_game1):
                try:
                    get_fighters_ready_sql = f"SELECT fighter1_ready, fighter2_ready FROM tic_tac_toe_game WHERE group_id = {message.chat.id} AND fighter1_username = '{fighter1}' AND fighter2_username = '{fighter2}' AND ended is False;"
                    await mydb.commit()
                    await cursor.execute(get_fighters_ready_sql)
                    r = await cursor.fetchone()
                    fighter1_ready, fighter2_ready = bool(r[0]), bool(r[1])

                    await bot.edit_message_text(text=warn_message.replace(str(time_to_ready_in_game1 - i), str(time_to_ready_in_game1 - (i + 1))), chat_id=temp.chat.id, message_id=temp.message_id, reply_markup=await keyboards.tic_tac_toe_game_ready_keyboard(fighter1=fighter1, fighter1_ready=fighter1_ready, fighter2=fighter2, fighter2_ready=fighter2_ready))
                    await asyncio.sleep(1)
                    warn_message = warn_message.replace(str(time_to_ready_in_game1 - i), str(time_to_ready_in_game1 - (i + 1)))
                except aiogram.exceptions.TelegramBadRequest:
                    await bot.edit_message_text(text=warn_message.replace(str(time_to_ready_in_game1 - i), '0', chat_id=temp.chat.id, message_id=temp.message_id, reply_markup=await keyboards.tic_tac_toe_game_ready_keyboard(fighter1=fighter1, fighter1_ready=fighter1_ready, fighter2=fighter2, fighter2_ready=fighter2_ready)))
                    break

            await bot.delete_message(chat_id=message.chat.id, message_id=temp.message_id)

            if fighter1_ready and fighter2_ready:
                first_picker = random.choice([fighter1, fighter2])

                if first_picker == fighter2:
                    f2_temp = fighter1
                else:
                    f2_temp = fighter2

                main_game_message = await message.answer(f'{texts.GAME1_STARTED}\nКрестики - {first_picker}, нолики - {f2_temp}\nХодит {first_picker}', reply_markup=await keyboards.tic_tac_toe_game_keyboard([[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]))

                update_main_game_message_id_sql = f"UPDATE tic_tac_toe_game SET main_game_message_id = {main_game_message.message_id} WHERE group_id = {message.chat.id} AND fighter1_username = '{fighter1}' AND fighter2_username = '{fighter2}' AND ended is False;"
                await cursor.execute(update_main_game_message_id_sql)
                await mydb.commit()

                get_first_picker_pos_sql = f"SELECT CASE WHEN fighter1_username = '{first_picker}' THEN 'fighter1' WHEN fighter2_username = '{first_picker}' THEN 'fighter2' ELSE NULL END FROM tic_tac_toe_game WHERE group_id = {message.chat.id} AND ended is False;"
                await cursor.execute(get_first_picker_pos_sql)
                first_picker_pos = (await cursor.fetchone())[0]

                get_data_sql = f"SELECT id, {first_picker_pos}_id FROM tic_tac_toe_game WHERE group_id = {message.chat.id} AND fighter1_username = '{fighter1}' AND fighter2_username = '{fighter2}' AND ended is False;"
                await cursor.execute(get_data_sql)
                r2 = await cursor.fetchone()
                game_session_id, first_picker_id = r2[0], r2[1]

                insert_game_session_sql = f"""INSERT INTO tic_tac_toe_temp (game_id, current_picker_id, current_filler, map_positions, fillers) VALUES ({game_session_id}, {first_picker_id}, '{tic_tac_toe_fillers.split()[0]}', "[[' ', ' ', ' '], [' ', ' ', ' '], [' ', ' ', ' ']]", '{tic_tac_toe_fillers}');"""
                await cursor.execute(insert_game_session_sql)
                await mydb.commit()
            else:
                end_the_game_sql = f"UPDATE tic_tac_toe_game SET ended = True WHERE group_id = {message.chat.id} AND ended is False;"
                await cursor.execute(end_the_game_sql)
                await mydb.commit()

                await message.answer(texts.GAME1_USERS_READY_TIMEOUT_FAILED)
                return
    else:
        await message.answer(texts.GAME1_DECLINE_START)


@router2.message(Command('tic_tac_toe', 'game1'))
async def tic_tac_toe_game_decline_handler(message: types.Message):
    await message.answer(texts.GAME1_DECLINE_START)


@router2.callback_query(F.func(lambda x: 'game1_ready' in x.data), flags=CHECK_BOT_RIGHT)
async def tic_tac_toe_game_ready_handler(call: types.CallbackQuery, bot: Bot):
    if call.from_user.username.lower() == call.data.rstrip('game1_ready').lstrip('@').strip().lower():
        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        call_buttons_texts = [i[0].text for i in call.message.reply_markup.inline_keyboard]
        fighter1 = call_buttons_texts[0].strip().rstrip(texts.GAME1_READY).rstrip(texts.GAME1_UNREADY).lstrip('@').lower()
        fighter2 = call_buttons_texts[1].strip().rstrip(texts.GAME1_READY).rstrip(texts.GAME1_UNREADY).lstrip('@').lower()

        get_last_ready_message_id_sql = f"SELECT last_ready_message_id FROM tic_tac_toe_game WHERE group_id = {call.message.chat.id} AND fighter1_username = '@{fighter1}' AND fighter2_username = '@{fighter2}' AND ended is False;"
        await cursor.execute(get_last_ready_message_id_sql)
        r = await cursor.fetchone()
        if r is not None and r[0] == call.message.message_id:
            get_fighter_pos_sql = f"SELECT CASE WHEN fighter1_username = '@{call.from_user.username}' THEN 'fighter1' WHEN fighter2_username = '@{call.from_user.username}' THEN 'fighter2' ELSE NULL END FROM tic_tac_toe_game WHERE group_id = {call.message.chat.id} AND ended is False;"
            await cursor.execute(get_fighter_pos_sql)
            fighter_pos = (await cursor.fetchone())[0]
            update_tic_tac_toe_game_sql = f"UPDATE tic_tac_toe_game SET {fighter_pos}_id = {call.from_user.id}, {fighter_pos}_ready = True WHERE group_id = {call.message.chat.id} AND fighter1_username = '@{fighter1}' AND fighter2_username = '@{fighter2}' AND ended is False;"
            await cursor.execute(update_tic_tac_toe_game_sql)
            await mydb.commit()

            temp_tic_tac_toe['started'] = True
        else:
            return


@router2.message(Command('cancel_tic_tac_toe', 'cancel_game1'), flags=CHECK_BOT_RIGHT)
async def cancel_tic_tac_toe_game_handler(message: types.Message, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_last_ready_message_id_sql = f"SELECT last_ready_message_id FROM tic_tac_toe_game WHERE group_id = {message.chat.id} AND ended is False;"
    await cursor.execute(get_last_ready_message_id_sql)
    r = await cursor.fetchone()
    if r is None:
        await message.answer(texts.GAMES_WAS_SUCCESSFUL_CANCELLED_GAME1)
        return
    last_ready_message_id = r[0]

    cancel_all_games_sql = f"UPDATE tic_tac_toe_game SET ended = True WHERE group_id = {message.chat.id} AND ended is False;"
    await cursor.execute(cancel_all_games_sql)
    await mydb.commit()

    try:
        await bot.delete_message(chat_id=message.chat.id, message_id=last_ready_message_id)
    except:
        pass

    await message.answer(texts.GAMES_WAS_SUCCESSFUL_CANCELLED_GAME1)


@router2.callback_query(F.func(lambda x: 'set_pos' in x.data), flags=CHECK_BOT_RIGHT)
async def pick_tic_tac_toe_handler(call: types.CallbackQuery, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_data_sql = f"SELECT id, main_game_message_id, fighter1_id, fighter2_id, fighter1_username, fighter2_username FROM tic_tac_toe_game WHERE group_id = {call.message.chat.id} AND ended is False;"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    game_session_id, main_game_message_id, fighter1_id, fighter2_id, fighter1_username, fighter2_username = r[0], r[1], r[2], r[3], r[4], r[5]

    if call.message.message_id == main_game_message_id and temp_tic_tac_toe['started']:
        get_current_picker_id_sql = f"SELECT current_picker_id, current_filler, map_positions, fillers FROM tic_tac_toe_temp WHERE game_id = {game_session_id};"
        await cursor.execute(get_current_picker_id_sql)
        r2 = await cursor.fetchone()
        expr = compile(r2[2], '<string>', 'eval')
        current_picker_id, current_filler, map_positions, fillers = r2[0], r2[1],  eval(expr), r2[3]

        if current_picker_id == call.from_user.id:
            temp = call.data.lstrip('set_pos ').split()
            index1, index2 = int(temp[0]), int(temp[1])

            if map_positions[index1][index2] == ' ':
                if call.from_user.id == fighter1_id:
                    next_picker_id = fighter2_id
                    next_picker_username = fighter2_username
                elif call.from_user.id == fighter2_id:
                    next_picker_id = fighter1_id
                    next_picker_username = fighter1_username
                else:
                    return

                next_filler = fillers.split()[0] if fillers.split().index(current_filler) == 1 else fillers.split()[1]

                new_map_positions = deepcopy(map_positions)
                new_map_positions[index1][index2] = current_filler

                tmp_fillers = fillers.split()
                tic_tac_toe_end_if_has_winner = (new_map_positions[0].count(tmp_fillers[0]) == 3 or new_map_positions[0].count(tmp_fillers[1]) == 3) or (new_map_positions[1].count(tmp_fillers[0]) == 3 or new_map_positions[1].count(tmp_fillers[1]) == 3) or (new_map_positions[2].count(tmp_fillers[0]) == 3 or new_map_positions[2].count(tmp_fillers[1]) == 3) or ((new_map_positions[0][0] == new_map_positions[1][1] == new_map_positions[2][2]) and (new_map_positions[0][0] != ' ' and new_map_positions[1][1] != ' ' and new_map_positions[2][2] != ' ')) or ((new_map_positions[0][2] == new_map_positions[1][1] == new_map_positions[2][0]) and (new_map_positions[0][2] != ' ' and new_map_positions[1][1] != ' ' and new_map_positions[2][0] != ' ')) or ((new_map_positions[0][0] == new_map_positions[1][0] == new_map_positions[2][0]) and (new_map_positions[0][0] != ' ' and new_map_positions[1][0] != ' ' and new_map_positions[2][0] != ' ')) or ((new_map_positions[0][1] == new_map_positions[1][1] == new_map_positions[2][1]) and (new_map_positions[0][1] != ' ' and new_map_positions[1][1] != ' ' and new_map_positions[2][1] != ' ')) or ((new_map_positions[0][2] == new_map_positions[1][2] == new_map_positions[2][2]) and (new_map_positions[0][2] != ' ' and new_map_positions[1][2] != ' ' and new_map_positions[2][2] != ' '))
                new_map_positions_copy = deepcopy(new_map_positions)
                new_map_positions_copy = list(map(lambda x: x[0] != ' ' and x[1] != ' ' and x[2] != ' ', new_map_positions_copy))
                tic_tac_toe_end_if_without_winners = all(new_map_positions_copy)

                if tic_tac_toe_end_if_has_winner:
                    await bot.edit_message_text(text=f'{texts.GAME1_ENDED}\nПобедитель - @{call.from_user.username.lower()}', chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=await keyboards.tic_tac_toe_game_keyboard(new_map_positions))
                    end_tic_tac_toe_game_sql = f"UPDATE tic_tac_toe_game SET ended = True, winner_username = '@{call.from_user.username.lower()}', winner_id = {call.from_user.id} WHERE group_id = {call.message.chat.id} AND ended is False;"
                    await cursor.execute(end_tic_tac_toe_game_sql)
                    await mydb.commit()
                    return
                if tic_tac_toe_end_if_without_winners:
                    await bot.edit_message_text(text=f'{texts.GAME1_ENDED}\nПобедителей нет', chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=await keyboards.tic_tac_toe_game_keyboard(new_map_positions))
                    end_tic_tac_toe_game_sql = f"UPDATE tic_tac_toe_game SET ended = True, winner_username = '0', winner_id = 0 WHERE group_id = {call.message.chat.id} AND ended is False;"
                    await cursor.execute(end_tic_tac_toe_game_sql)
                    await mydb.commit()
                    return

                update_tic_tac_toe_temp_sql = f"""UPDATE tic_tac_toe_temp tttt INNER JOIN tic_tac_toe_game tttg ON tttg.id = tttt.game_id SET current_picker_id = {next_picker_id}, current_filler = '{next_filler}', map_positions = "{str(new_map_positions)}" WHERE group_id = {call.message.chat.id} AND ended is False;"""
                await cursor.execute(update_tic_tac_toe_temp_sql)
                await mydb.commit()

                await bot.edit_message_text(text=re.sub(pattern=r'Ходит @\w+\b', repl=f'Ходит {next_picker_username}', string=call.message.text), chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=await keyboards.tic_tac_toe_game_keyboard(new_map_positions))


@router2.message(Command('tic_tac_toe_wins', 'game1_wins'), flags=CHECK_BOT_RIGHT_AND_USE_THROTTLE)
async def user_wins_handler(message: types.Message):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_user_wins = f"SELECT COUNT(*) FROM tic_tac_toe_game WHERE winner_id = {message.from_user.id} GROUP BY winner_id;"
    await cursor.execute(get_user_wins)
    r = await cursor.fetchone()
    if r is None:
        await message.answer(texts.USER_WINS_IN_GAME1_ANSWER_FAILED)
        return

    await message.answer(f'{texts.USER_WINS_IN_GAME1_ANSWER}<b>{r[0]}</b>')


@router2.message(Command('tic_tac_toe_leaderboard', 'game1_leaderboard'), flags=CHECK_BOT_RIGHT_AND_USE_THROTTLE)
async def tic_tac_toe_leaderboard(message: types.Message):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_top_users = f"SELECT winner_username, COUNT(*) FROM tic_tac_toe_game GROUP BY winner_username;"
    await cursor.execute(get_top_users)
    r = await cursor.fetchall()
    if r is None:
        await message.answer(texts.GAME1_LEADERBOARD_ANSWER_FAILED)
        return
    leaderboard = list(enumerate(sorted([i for i in r if i[0] not in (None, '0')], key=lambda x: int(x[1]), reverse=True), start=1))

    if len(leaderboard) < 10:
        count = len(leaderboard)
    else:
        count = 10

    await message.answer(f'Топ {count} {texts.GAME1_LEADERBOARD_ANSWER}\n    ' + '\n    '.join([f"<b>{i[0]}. {i[1][0].lstrip('@')} - {i[1][1]}</b>" for i in leaderboard]))


@router2.message(Command('help'))
async def help_handler(message: types.Message, bot: Bot):
    result_text = ''
    async for key, value in async_items(texts.BOT_GROUP_COMMANDS):
        result_text += f'<b>{key}</b>: {value}\n\n'
    await message.answer(result_text)


@router2.chat_member(ChatMemberUpdatedFilter(IS_NOT_MEMBER >> IS_MEMBER), flags=CHECK_BOT_RIGHT)
async def new_user_start_message_handler(event: types.ChatMemberUpdated, bot: Bot):
    types_dict = {'group': 'группу', 'supergroup': 'супергруппу'}
    await bot.send_message(event.chat.id, f'{texts.USER_START_MESSAGE_GROUP} {types_dict[event.chat.type]}, {event.old_chat_member.user.full_name}!')


@router2.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> KICKED), flags=CHECK_BOT_RIGHT)
async def kick_user_message_handler(event: types.ChatMemberUpdated, bot: Bot):
    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    from_user_bot_check = {False: 'пользователем', True: 'ботом'}
    await bot.send_message(event.chat.id, f'{to_user_bot_check[event.old_chat_member.user.is_bot]} {event.old_chat_member.user.full_name} {texts.USER_KICKED} {from_user_bot_check[event.from_user.is_bot]} {event.from_user.full_name}')


@router2.chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> (LEFT | -RESTRICTED)), flags=CHECK_BOT_RIGHT)
async def leave_user_message_handler(event: types.ChatMemberUpdated, bot: Bot):
    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    chat_type_dict = {'group': 'группы', 'supergroup': 'супергруппы'}
    await bot.send_message(event.chat.id, f'{to_user_bot_check[event.from_user.is_bot]} {event.from_user.full_name} {texts.USER_LEAVED} {chat_type_dict[event.chat.type]}')


@router2.chat_member(ChatMemberUpdatedFilter((MEMBER | +RESTRICTED) >> IS_ADMIN))
async def user_to_admin_handler(event: types.ChatMemberUpdated, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    date = datetime.now().strftime("%d.%m.%Y %X")
    get_user_exists_sql = f"SELECT id FROM users WHERE id = {event.new_chat_member.user.id};"

    await cursor.execute(get_user_exists_sql)
    if not (await cursor.fetchone()):
        insert_new_admin_sql = f"""START TRANSACTION; INSERT INTO users (id, username, date_registration, has_active_groups) VALUES ({event.new_chat_member.user.id}, '{event.new_chat_member.user.username}', '{date}', 0); INSERT INTO bot_groups (id, title, owner_id, type, add_date) VALUES ({event.chat.id}, '{event.chat.title}', {event.new_chat_member.user.id}, '{event.chat.type}', '{date}'); COMMIT;"""
    else:
        get_group_exists_sql = f"SELECT id FROM bot_groups WHERE owner_id = {event.new_chat_member.user.id};"
        await cursor.execute(get_group_exists_sql)
        if not (await cursor.fetchone()):
            insert_new_admin_sql = f"""START TRANSACTION; UPDATE users SET has_active_groups = 1 WHERE id = {event.new_chat_member.user.id}; INSERT INTO bot_groups (id, title, owner_id, type, add_date) VALUES ({event.chat.id}, '{event.chat.title}', {event.new_chat_member.user.id}, '{event.chat.type}', '{date}'); COMMIT;"""
        else:
            insert_new_admin_sql = f"""START TRANSACTION; UPDATE users SET has_active_groups = 1 WHERE id = {event.new_chat_member.user.id}; UPDATE bot_groups SET add_date = '{date}' WHERE id = {event.new_chat_member.user.id}; COMMIT;"""
    await cursor.execute(insert_new_admin_sql)

    get_another_admin_data_sql = f"SELECT owner_id, use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, banwords_list FROM users_groups_settings WHERE group_id = {event.chat.id};"
    await cursor.execute(get_another_admin_data_sql)
    r = await cursor.fetchone()
    if r and r[0]:
        try:
            insert_user_group_settings_sql = f"INSERT INTO users_groups_settings (group_id, owner_id, use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, banwords_list) VALUES ({event.chat.id}, {event.new_chat_member.user.id}, {r[1]}, {r[2]}, {r[3]}, '{r[4]}');"
            await cursor.execute(insert_user_group_settings_sql)
        except pymysql.IntegrityError:
            update_user_group_settings_sql = f"UPDATE users_groups_settings SET use_notify_for_ban_user = {r[1]}, use_notify_for_unban_user = {r[2]}, use_banwords_filter = {r[3]}, banwords_list = {r[4]};"
            await cursor.execute(update_user_group_settings_sql)
    else:
        insert_user_group_settings_sql = f"INSERT INTO users_groups_settings (group_id, owner_id, use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, banwords_list) VALUES ({event.chat.id}, {event.new_chat_member.user.id}, True, True, False, '[]');"
        await cursor.execute(insert_user_group_settings_sql)
    await mydb.commit()

    to_user_bot_check = {False: 'Пользователь', True: 'Бот'}
    from_user_bot_check = {False: 'пользователем', True: 'ботом'}
    await bot.send_message(event.chat.id, f'{to_user_bot_check[event.new_chat_member.user.is_bot]} {event.new_chat_member.user.full_name} {texts.USER_TO_ADMIN} {from_user_bot_check[event.from_user.is_bot]} {event.from_user.full_name}')


@router2.my_chat_member(ChatMemberUpdatedFilter(IS_MEMBER >> IS_NOT_MEMBER))
async def bot_kick_handler(event: types.ChatMemberUpdated, bot: Bot):
    if not event.chat.type in ['group', 'supergroup']:
        return
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    delete_group_sql = f"START TRANSACTION; DELETE FROM bot_groups WHERE id = {event.chat.id}; DELETE FROM users_groups_settings WHERE group_id = {event.chat.id}; DELETE FROM users_groups_actions WHERE group_id = {event.chat.id}; COMMIT;"
    await cursor.execute(delete_group_sql)


"""Handler for use filter text"""
@router2.message()
async def user_sended_message_handler(message: types.Message):
    pass

