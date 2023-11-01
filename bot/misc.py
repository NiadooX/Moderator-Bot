from aiogram import types
import aiogram.types
import aiomysql
from start_set import get_settings
from aiogram.filters import BaseFilter
import texts
from datetime import datetime, timedelta
import aiogram.exceptions


time_to_cancel_user_ban = 10
time_to_cancel_user_unban = 10
time_to_ready_in_game1 = 10
time_to_start_game1 = 4
tic_tac_toe_fillers = '❌ ⭕'
mysql_settings = get_settings()['MySQL']


async def async_range(range_: int):
    for i in range(range_):
        yield i


async def async_list(list_: list):
    for i in list_:
        yield i


async def connect_to_db():
    mydb = await aiomysql.connect(host=mysql_settings['host'], port=int(mysql_settings['port']), user=mysql_settings['user'], password=mysql_settings['password'], db=mysql_settings['db_name'])
    return mydb


def concat_dicts(a: dict, b: dict):
    return dict(list(a.items()) + list(b.items()))


class CheckUserAction(BaseFilter):
    def __init__(self, action_name: str):
        self.action = action_name

    async def __call__(self, message: types.Message):
        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        if self.action == 'ban':
            check_user_ban_action_sql = f"SELECT warn_message_id FROM users_moderations WHERE from_user = {message.from_user.id} AND ended is False AND action = 'ban';"
            await cursor.execute(check_user_ban_action_sql)
            r = await cursor.fetchone()
            return bool(r)
        elif self.action == 'unban':
            check_user_unban_action_sql = f"SELECT warn_message_id FROM users_moderations WHERE from_user = {message.from_user.id} AND ended is False AND action = 'unban';"
            await cursor.execute(check_user_unban_action_sql)
            r = await cursor.fetchone()
            return bool(r)


chat_administrators_cache = {}


class CheckUserRights(BaseFilter):
    async def __call__(self, event, bot: aiogram.Bot):
        if isinstance(event, types.CallbackQuery):
            chat_type = event.message.chat.type
        elif isinstance(event, types.Message):
            chat_type = event.chat.type
        else:
            return

        if chat_type in ['group', 'supergroup']:
            if chat_administrators_cache.get(event.chat.id) is None or chat_administrators_cache[event.chat.id][1] < datetime.now():
                try:
                    administrators = [i.user.id for i in await bot.get_chat_administrators(event.chat.id)]
                except aiogram.exceptions.TelegramForbiddenError:
                    return
                chat_administrators_cache[event.chat.id] = (administrators, datetime.now() + timedelta(seconds=10))
            else:
                administrators = chat_administrators_cache[event.chat.id][0]
            return event.from_user.id in administrators
        return False


class CheckCallbackNormal(BaseFilter):
    async def __call__(self, call: types.CallbackQuery):
        call_warn_message_id = call.message.message_id

        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        get_active_warn_messages_id_sql = f"SELECT warn_message_id FROM users_moderations WHERE from_user = {call.from_user.id} AND ended is False;"
        await cursor.execute(get_active_warn_messages_id_sql)
        r = await cursor.fetchall()
        get_active_warn_messages_id_list = [i[0] for i in r]

        return call_warn_message_id in get_active_warn_messages_id_list


class CheckGame1(BaseFilter):
    async def __call__(self, event, bot: aiogram.Bot):
        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        if isinstance(event, types.Message):
            chat_id = event.chat.id
        elif isinstance(event, types.CallbackQuery):
            chat_id = event.message.chat.id
        else:
            return

        check_have_a_games_game1_sql = f"SELECT id FROM tic_tac_toe_game WHERE group_id = {chat_id} AND ended is False;"
        await cursor.execute(check_have_a_games_game1_sql)
        r = await cursor.fetchone()
        if r is not None:
            await bot.send_message(chat_id, texts.GAME1_ALREADY_EXISTS)

        return r is None


async def get_admins(chat_id: int, chat_administrators_cache: dict, bot: aiogram.Bot):
    if chat_administrators_cache.get(chat_id) is None or chat_administrators_cache[chat_id][1] < datetime.now():
        tmp = await bot.get_chat_administrators(chat_id)
        administrators = [i.user.id for i in tmp]
        administrators_without_bots = [i.user.id for i in tmp if not i.user.is_bot]
        chat_administrators_cache[chat_id] = (administrators, datetime.now() + timedelta(seconds=10), administrators_without_bots)
    else:
        administrators = chat_administrators_cache[chat_id][0]
        administrators_without_bots = chat_administrators_cache[chat_id][2]

    return administrators, administrators_without_bots

