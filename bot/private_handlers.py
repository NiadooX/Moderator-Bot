import aiogram.enums
from aiogram import Bot, Router, F
from middlewares import ThrottlingMiddleware, CheckUserMiddleware, CheckBotRights, FilterTextMiddleware, CheckChosenGroupPrivate
from aiogram.filters.command import Command
from aiogram import types
from aiogram.filters import ChatMemberUpdatedFilter, IS_MEMBER, IS_NOT_MEMBER, LEFT, RESTRICTED, KICKED
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import texts
from misc import connect_to_db, concat_dicts
from datetime import datetime
import keyboards
import re
import aiogram.exceptions
from aiogram.types.chat_permissions import ChatPermissions


router1 = Router()
router1.message.middleware(ThrottlingMiddleware(timeout=0.3))
router1.callback_query.middleware(ThrottlingMiddleware(timeout=0.5))
router1.message.middleware(CheckUserMiddleware())
router1.message.middleware(CheckBotRights())
router1.message.middleware(CheckChosenGroupPrivate())
router1.callback_query.middleware(CheckChosenGroupPrivate())
USE_BOT_RIGHTS_CHECK = {'check_bot_rights': True}
USE_THROTTLE = {'use_throttle': True}
USE_USER_CHECK = {'use_verify': True}
USE_THROTTLE_AND_USER_CHECK = {'use_throttle': True, 'use_verify': True}
ONLY_WITHOUT_STATE = {'only_without_state': True}
ONLY_WITHOUT_STATE_AND_USE_THROTTLE = concat_dicts(ONLY_WITHOUT_STATE, USE_THROTTLE)
ONLY_WITHOUT_STATE_AND_USE_THROTTLE_AND_USER_CHECK = concat_dicts(ONLY_WITHOUT_STATE_AND_USE_THROTTLE, USE_USER_CHECK)
USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK = concat_dicts(concat_dicts(USE_THROTTLE, USE_USER_CHECK), USE_BOT_RIGHTS_CHECK)
CHECK_CHOSEN_GROUP = {'check_chosen_group_private': True}


class BotStates(StatesGroup):
    in_profile_info = State()
    in_user_groups_info = State()
    choosing_group_action = State()
    banning_user_action = State()
    unbanning_user_action = State()
    muting_user_action = State()
    unmuting_user_action = State()
    creating_invite_link = State()
    in_group_settings = State()
    writing_a_bad_words_to_replace = State()
    writing_a_bad_words_to_add = State()


@router1.message(Command('start'), flags=ONLY_WITHOUT_STATE_AND_USE_THROTTLE)
async def start_command_handler(message: types.Message):
    if message.chat.type == 'private':
        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        check_user_sql = f"SELECT username FROM users WHERE id = '{message.from_user.id}';"
        await cursor.execute(check_user_sql)
        r = await cursor.fetchone()
        if r is None:
            create_user_sql = f"""INSERT INTO users (id, username, date_registration, has_active_groups) VALUES ({message.from_user.id}, '{message.from_user.username}', '{datetime.now().strftime("%d.%m.%Y %X")}', False);"""
            await cursor.execute(create_user_sql)
            await mydb.commit()
            await message.answer(texts.REGISTR_SUCCESS)
            await message.answer(texts.START_MESSAGE_PRIVATE, reply_markup=await keyboards.main_keyboard())
        else:
            await message.answer(texts.NOW_REGISTR_ERROR)
    else:
        return


@router1.message(F.text == texts.MY_PROFILE_BUTTON_TEXT, flags=USE_THROTTLE_AND_USER_CHECK)
async def my_profile_handler(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.in_profile_info)

    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    user_link = f'<a href="tg://user?id={message.from_user.id}">{message.from_user.full_name}</a>'

    check_date_registr_sql = f"SELECT date_registration FROM users WHERE id = '{message.from_user.id}';"
    await cursor.execute(check_date_registr_sql)
    date_registration = await cursor.fetchone()

    check_user_groups = f"SELECT title, type, bot_groups.id FROM bot_groups INNER JOIN users ON bot_groups.owner_id = users.id WHERE users.id = '{message.from_user.id}';"
    await cursor.execute(check_user_groups)

    r = await cursor.fetchall()
    groups_types_dict = {'group': 'Группа', 'supergroup': 'Супергруппа'}
    if r:
        user_groups = '\n        ' + ', \n        '.join([f'{r.index(i) + 1}. <b>{groups_types_dict[i[1]]} "{i[0]}" (id {str(i[2])})</b>' for i in r])
    else:
        user_groups = texts.USER_DONT_HAVE_ACTIVE_GROUPS

    await message.answer(f'<b>{texts.MY_PROFILE_TITLE}</b>\n    {texts.MY_PROFILE_USER_LINK}: <b>{user_link}</b>\n    {texts.MY_PROFILE_DATE_REGISTRATION}: <b>{date_registration[0]}</b>\n    {texts.MY_PROFILE_USER_GROUPS}: {user_groups}', reply_markup=await keyboards.back_keyboard())


@router1.message(F.text == texts.MY_GROUPS_BUTTON_TEXT, flags=USE_THROTTLE_AND_USER_CHECK)
async def my_groups_handler(message: types.Message, state: FSMContext):
    await state.set_state(BotStates.in_user_groups_info)

    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    check_user_groups = f"SELECT title, type, bot_groups.id FROM bot_groups INNER JOIN users ON bot_groups.owner_id = users.id WHERE users.id = '{message.from_user.id}';"
    await cursor.execute(check_user_groups)
    r = await cursor.fetchall()
    groups_types_dict = {'group': 'Группа', 'supergroup': 'Супергруппа'}
    if r:
        user_groups = '\n    ' + ', \n    '.join([f'{r.index(i) + 1}. <b>{groups_types_dict[i[1]]} "{i[0]}" (id {str(i[2])})</b>' for i in r])
        await message.answer(texts.USER_GROUPS_MAIN_TEXT_TEMP1 + ': ' + user_groups + '\n\n' + texts.USER_GROUPS_MAIN_TEXT_TEMP2, reply_markup=await keyboards.user_groups_keyboard(**{str(i[2]): i[0] for i in r}))
    else:
        await message.answer(texts.USER_DONT_HAVE_ACTIVE_GROUPS)


@router1.callback_query(BotStates.in_user_groups_info, F.func(lambda x: 'chose_group' in x.data.lower()), flags=USE_THROTTLE_AND_USER_CHECK)
async def chose_group_handler(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    await state.set_state(BotStates.choosing_group_action)
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    mydb = await connect_to_db()
    cursor = await mydb.cursor()
    group_id = call.data.split()[1]
    group_name = call.data.split()[2]

    check_chosen_group_sql = f"SELECT id FROM bot_groups WHERE owner_id = {call.from_user.id} AND id = {group_id};"
    await cursor.execute(check_chosen_group_sql)
    if not await cursor.fetchone():
        return

    temp_sql = f"SELECT users.id FROM users INNER JOIN users_groups_actions ON users.id = users_groups_actions.user_id WHERE users.id = {call.from_user.id};"
    await cursor.execute(temp_sql)
    r1 = await cursor.fetchall()

    if not r1:
        temp_sql2 = f"INSERT INTO users_groups_actions (user_id, group_id) VALUES ({call.from_user.id}, {group_id})"
        await cursor.execute(temp_sql2)
        await mydb.commit()
    else:
        update_action_sql = f"UPDATE users_groups_actions SET group_id = {group_id} WHERE user_id = {call.from_user.id}"
        await cursor.execute(update_action_sql)
        await mydb.commit()

    await bot.send_message(call.from_user.id, f'{texts.CHOSE_GROUP_ANSWER} "{group_name}"')

    await bot.send_message(call.from_user.id, texts.CHOOSING_ACTION_GROUP_QUESTION, reply_markup=await keyboards.user_group_settings())


@router1.message(F.text == texts.BAN_USER_BUTTON_TEXT, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def ban_user_temp_handler(message: types.Message, state: FSMContext):
    r = await state.get_state()
    if r in texts.BOT_PRIVATE_USER_GROUPS_STATES_NAMES:
        await state.set_state(BotStates.banning_user_action)
        await message.answer(texts.WRITE_A_USER_FOR_BAN)


@router1.message(F.text == texts.UNBAN_USER_BUTTON_TEXT, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def unban_user_temp_handler(message: types.Message, state: FSMContext):
    r = await state.get_state()
    if r in texts.BOT_PRIVATE_USER_GROUPS_STATES_NAMES:
        await state.set_state(BotStates.unbanning_user_action)
        await message.answer(texts.WRITE_A_USER_FOR_UNBAN)


@router1.message(BotStates.banning_user_action, F.forward_from, F.text, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK))
async def ban_user_handler(message: types.Message, bot: Bot, state: FSMContext):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()
    get_info_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id};"
    await cursor.execute(get_info_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    group_id = r[0]

    t = await bot.get_chat_member(chat_id=group_id, user_id=message.forward_from.id)

    if (t.status is aiogram.enums.ChatMemberStatus.MEMBER) or (t.status is aiogram.enums.ChatMemberStatus.RESTRICTED):
        await bot.ban_chat_member(chat_id=group_id, user_id=message.forward_from.id)
        await message.answer(texts.BAN_USER_SUCCESSFUL)
    else:
        await message.answer(texts.BAN_USER_FAILED)
    await state.set_state(BotStates.choosing_group_action)


@router1.message(BotStates.banning_user_action, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS), flags=USE_THROTTLE_AND_USER_CHECK)
async def ban_user_decline_handler(message: types.Message, state: FSMContext):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_group_id_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id}"
    await cursor.execute(get_group_id_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    group_id = r[0]

    if message.forward_from is None and message.forward_sender_name:
        await message.answer(texts.WRITE_A_USER_FOR_BAN_DECLINE_VAR2)
        return
    await message.answer(texts.WRITE_A_USER_FOR_BAN_DECLINE_VAR1)


@router1.message(BotStates.unbanning_user_action, F.forward_from, F.text, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK))
async def unban_user_handler(message: types.Message, bot: Bot, state: FSMContext):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()
    get_info_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id}"
    await cursor.execute(get_info_sql)
    r = await cursor.fetchone()
    group_id = r[0]

    t = await bot.get_chat_member(chat_id=group_id, user_id=message.forward_from.id)

    if (t.status is aiogram.enums.ChatMemberStatus.LEFT) or (t.status is aiogram.enums.ChatMemberStatus.KICKED):
        await bot.unban_chat_member(chat_id=group_id, user_id=message.forward_from.id)
        await message.answer(texts.UNBAN_USER_SUCCESSFUL)
    else:
        await message.answer(texts.UNBAN_USER_FAILED)
    await state.set_state(BotStates.choosing_group_action)


@router1.message(BotStates.unbanning_user_action, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS), flags=USE_THROTTLE_AND_USER_CHECK)
async def unban_user_decline_handler(message: types.Message):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_group_id_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id};"
    await cursor.execute(get_group_id_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    group_id = r[0]

    if message.forward_from is None and message.forward_sender_name:
        await message.answer(texts.WRITE_A_USER_FOR_UNBAN_DECLINE_VAR2)
        return
    await message.answer(texts.WRITE_A_USER_FOR_UNBAN_DECLINE_VAR1)


@router1.message(F.text == texts.MUTE_USER_BUTTON_TEXT, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def mute_user_temp_handler(message: types.Message, state: FSMContext):
    r = await state.get_state()
    if r in texts.BOT_PRIVATE_USER_GROUPS_STATES_NAMES:
        await state.set_state(BotStates.muting_user_action)
        await message.answer(texts.WRITE_A_USER_FOR_MUTE)


@router1.message(F.text, F.forward_from, BotStates.muting_user_action, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def mute_user_handler(message: types.Message, state: FSMContext, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_group_id_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id};"
    await cursor.execute(get_group_id_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    group_id = r[0]

    new_user_rights = ChatPermissions(can_send_messages=False)
    try:
        await bot.restrict_chat_member(chat_id=group_id, user_id=message.forward_from.id, permissions=new_user_rights)
    except aiogram.exceptions.TelegramBadRequest or aiogram.exceptions.TelegramRetryAfter:
        await message.answer(texts.FAILED_MUTE)
        return

    await message.answer(texts.USER_WAS_MUTED_SUCCESSFUL)
    await state.set_state(BotStates.choosing_group_action)


@router1.message(F.text, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS), BotStates.muting_user_action, flags=USE_THROTTLE_AND_USER_CHECK)
async def mute_user_decline_handler(message: types.Message):
    if message.forward_from is None and message.forward_sender_name:
        await message.answer(texts.WRITE_A_USER_FOR_MUTE_DECLINE_VAR2)
        return
    await message.answer(texts.WRITE_A_USER_FOR_MUTE_DECLINE_VAR1)


@router1.message(F.text == texts.UNMUTE_USER_BUTTON_TEXT, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def unmute_user_temp_handler(message: types.Message, state: FSMContext):
    r = await state.get_state()
    if r in texts.BOT_PRIVATE_USER_GROUPS_STATES_NAMES:
        await state.set_state(BotStates.unmuting_user_action)
        await message.answer(texts.WRITE_A_USER_FOR_UNMUTE)


@router1.message(F.text, F.forward_from, BotStates.unmuting_user_action, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def unmute_user_handler(message: types.Message, state: FSMContext, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_group_id_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id};"
    await cursor.execute(get_group_id_sql)
    r = await cursor.fetchone()
    group_id = r[0]

    new_user_rights = ChatPermissions(can_send_messages=True)
    try:
        await bot.restrict_chat_member(chat_id=group_id, user_id=message.forward_from.id, permissions=new_user_rights)
    except aiogram.exceptions.TelegramBadRequest or aiogram.exceptions.TelegramRetryAfter:
        await message.answer(texts.FAILED_UNMUTE)
        return

    await message.answer(texts.USER_WAS_UNMUTED_SUCCESSFUL)
    await state.set_state(BotStates.choosing_group_action)


@router1.message(F.text, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS), BotStates.unmuting_user_action, flags=USE_THROTTLE_AND_USER_CHECK)
async def unmute_user_decline_handler(message: types.Message, state: FSMContext):
    if message.forward_from is None and message.forward_sender_name:
        await message.answer(texts.WRITE_A_USER_FOR_UNMUTE_DECLINE_VAR2)
        return
    await message.answer(texts.WRITE_A_USER_FOR_UNMUTE_DECLINE_VAR1)


@router1.message(F.text == texts.CREATE_INVITE_LINK_BUTTON_TEXT, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def create_invite_link_temp_handler(message: types.Message, state: FSMContext):
    r = await state.get_state()
    if r in texts.BOT_PRIVATE_USER_GROUPS_STATES_NAMES:
        await state.set_state(BotStates.creating_invite_link)
        await message.answer(texts.WRITE_A_NUMBER_OF_INVITE_LINK)


@router1.message(BotStates.creating_invite_link, F.func(lambda x: re.fullmatch(r'[-\d]?\d+', x.text)), flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK))
async def create_invite_link_handler(message: types.Message, bot: Bot, state: FSMContext):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()
    get_info_sql = f"SELECT group_id FROM users_groups_actions WHERE user_id = {message.from_user.id}"
    await cursor.execute(get_info_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    group_id = r[0]

    member_limit = int(message.text)
    if member_limit > 99999:
        member_limit = 99999
        await message.answer(texts.LINK_NUMBER_MORE_MAX)
    elif member_limit < 1:
        member_limit = 1
        await message.answer(texts.LINK_NUMBER_LESS_MIN)

    invite_link = await bot.create_chat_invite_link(chat_id=group_id, member_limit=member_limit)

    await message.answer(f'{texts.LINK_CREATED_SUCCESSFUL}:  {invite_link.invite_link} (кол-во переходов {str(invite_link.member_limit)})')
    await state.set_state(BotStates.choosing_group_action)


@router1.message(BotStates.creating_invite_link, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS))
async def create_invite_link_decline_handler(message: types.Message):
    await message.answer(texts.LINK_CREATING_FAILED)


@router1.message(F.text == texts.GROUP_SETTINGS_BUTTON_TEXT, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def group_settings_handler(message: types.Message, state: FSMContext):
    r = await state.get_state()
    if r in texts.BOT_PRIVATE_USER_GROUPS_STATES_NAMES:
        mydb = await connect_to_db()
        cursor = await mydb.cursor()

        get_data_sql = f"SELECT use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, banwords_list, use_banwords_filter FROM users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id WHERE owner_id = {message.from_user.id} AND ugs.group_id = uga.group_id;"
        await cursor.execute(get_data_sql)
        r = await cursor.fetchone()
        if r is None:
            return
        use_notify_for_ban_user = r[0]
        use_notify_for_unban_user = r[1]
        use_banwords_filter = r[2]

        await message.answer(texts.SET_GROUP_SETTINGS_ANSWER, reply_markup=await keyboards.set_group_settings_keyboard(use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, use_edit_banwords=bool(use_banwords_filter)))


@router1.callback_query(F.data.in_(['set notify_for_ban_user', 'set notify_for_unban_user', 'set banwords_filter']), flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def set_group_settings_handler(call: types.CallbackQuery, bot: Bot, state: FSMContext):
    await bot.delete_message(chat_id=call.from_user.id, message_id=call.message.message_id)

    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_data_sql = f"SELECT use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter FROM users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    use_notify_for_ban_user = r[0]
    use_notify_for_unban_user = r[1]
    use_banwords_filter = r[2]

    d = {True: 'выключено', False: 'включено'}

    if call.data == 'set notify_for_ban_user':
        set_notify_for_ban_user_sql = f"UPDATE users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id SET use_notify_for_ban_user = {not bool(use_notify_for_ban_user)} WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
        await cursor.execute(set_notify_for_ban_user_sql)
        await mydb.commit()

        await bot.send_message(call.from_user.id, f'{texts.SET_NOTIFY_FOR_BAN_SUCCESSFUL} {d[use_notify_for_ban_user]}!')
    elif call.data == 'set notify_for_unban_user':
        set_notify_for_unban_user_sql = f"UPDATE users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id SET use_notify_for_unban_user = {not bool(use_notify_for_unban_user)} WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
        await cursor.execute(set_notify_for_unban_user_sql)
        await mydb.commit()

        await bot.send_message(call.from_user.id, f'{texts.SET_NOTIFY_FOR_UNBAN_SUCCESSFUL} {d[use_notify_for_unban_user]}!')
    elif call.data == 'set banwords_filter':
        d = {True: 'выключен', False: 'включен'}

        set_banwords_filter_sql = f"UPDATE users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id SET use_banwords_filter = {not bool(use_banwords_filter)} WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
        await cursor.execute(set_banwords_filter_sql)
        await mydb.commit()

        await bot.send_message(call.from_user.id, f'{texts.SET_BANWORDS_FILTER_SUCCESSFUL} {d[use_banwords_filter]}!')

        if not use_banwords_filter:
            await bot.send_message(call.from_user.id, texts.CHOOSE_A_BANWORDS_LIST_ACTION, reply_markup=await keyboards.choose_a_banwords_list_action_keyboard())
        else:
            off_banwords_filter = f"UPDATE users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id SET use_banwords_filter = {not bool(use_banwords_filter)}, banwords_list = '[]' WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
            await cursor.execute(off_banwords_filter)
        await mydb.commit()


@router1.callback_query(F.data == 'edit banwords_list', flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def edit_banwords_list_temp_handler(call: types.CallbackQuery, bot: Bot):
    try:
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=texts.CHOOSE_A_BANWORDS_LIST_ACTION, reply_markup=await keyboards.choose_a_banwords_list_action_keyboard())
    except aiogram.exceptions.TelegramBadRequest:
        return


@router1.callback_query(F.data == 'replace banwords_list', flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def replace_banwords_list_temp_handler(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await bot.send_message(call.from_user.id, texts.WRITE_A_BANWORDS)
    await state.set_state(BotStates.writing_a_bad_words_to_replace)


@router1.message(F.text, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS), BotStates.writing_a_bad_words_to_replace, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def replace_banwords_list_handler(message: types.Message, state: FSMContext, bot: Bot):
    try:
        banwords = [i.strip().replace("'", '').replace('"', '') for i in message.text.strip().split(',') if i.strip().replace("'", '').replace('"', '')]
    except:
        return

    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    add_banwords_sql = f"""UPDATE users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id SET banwords_list = "{banwords}" WHERE owner_id = {message.from_user.id} AND ugs.group_id = uga.group_id;"""
    await cursor.execute(add_banwords_sql)

    await mydb.commit()

    await message.answer(texts.BANWORDS_WAS_SET_SUCCESSFUL)

    await state.set_state(BotStates.in_group_settings)


@router1.callback_query(F.data == 'add to banwords_list', flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def add_to_banwords_list_temp_handler(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    await bot.send_message(call.from_user.id, texts.WRITE_A_BANWORDS)
    await state.set_state(BotStates.writing_a_bad_words_to_add)


@router1.message(F.text, F.func(lambda x: x.text not in texts.BOT_PRIVATE_USER_GROUPS_BUTTONS), BotStates.writing_a_bad_words_to_add, flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def add_to_banwords_list_handler(message: types.Message, state: FSMContext, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_old_banwords_list_sql = f"SELECT banwords_list FROM users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id WHERE owner_id = {message.from_user.id} AND ugs.group_id = uga.group_id;"

    await cursor.execute(get_old_banwords_list_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    old_banwords = [i.strip("'").replace("'", '').replace('"', '') for i in r[0].lstrip('[').rstrip(']').split(', ') if i.strip("'").replace("'", '').replace('"', '')]

    try:
        banwords = old_banwords + [i.strip().replace("'", '').replace('"', '') for i in message.text.strip().split(',') if i.strip().replace("'", '').replace('"', '')]
    except:
        return

    add_banwords_sql = f"""UPDATE users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id SET banwords_list = "{banwords}" WHERE owner_id = {message.from_user.id} AND ugs.group_id = uga.group_id;"""
    await cursor.execute(add_banwords_sql)

    await mydb.commit()

    await message.answer(texts.BANWORDS_WAS_SET_SUCCESSFUL)

    await state.set_state(BotStates.in_group_settings)


@router1.callback_query(F.data == 'show banwords_list', flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK_AND_BOT_RIGHTS_CHECK))
async def show_banwords_list_handler(call: types.CallbackQuery, state: FSMContext, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_banwords_list_sql = f"SELECT banwords_list FROM users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
    await cursor.execute(get_banwords_list_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    banwords_list = [i.strip('').replace('"', '').replace("'", '') for i in r[0].lstrip('[').rstrip(']').split(',') if i.strip('').replace('"', '').replace("'", '') != '']

    await bot.send_message(call.from_user.id, f"""{texts.SHOW_BANWORDS_LIST_ANSWER}<b>{', '.join(banwords_list)}</b>""")

    await state.set_state(BotStates.in_group_settings)


@router1.message(F.text == texts.ABOUT_BOT_BUTTON_TEXT, flags=USE_THROTTLE_AND_USER_CHECK)
async def about_bot_handler(message: types.Message):
    await message.answer(texts.ABOUT_BOT_BUTTON_ANSWER, reply_markup=await keyboards.bot_author_keyboard())


@router1.message(Command('cancel'), flags=USE_THROTTLE_AND_USER_CHECK)
async def cancel_state_handler(message: types.Message, state: FSMContext):
    await state.clear()

    await message.answer(texts.WAS_CANCEL_TEXT, reply_markup=await keyboards.main_keyboard())


@router1.message(F.text == texts.BACK_BUTTON_TEXT, flags=USE_THROTTLE_AND_USER_CHECK)
async def back_handler(message: types.Message, state: FSMContext, bot: Bot):
    await state.clear()

    await message.answer(texts.BACK_BUTTON_ANSWER, reply_markup=await keyboards.main_keyboard())


@router1.callback_query(F.data == 'back to_group_settings', flags=concat_dicts(CHECK_CHOSEN_GROUP, USE_THROTTLE_AND_USER_CHECK))
async def back_to_group_settings_handler(call: types.CallbackQuery, bot: Bot):
    mydb = await connect_to_db()
    cursor = await mydb.cursor()

    get_data_sql = f"SELECT use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, banwords_list, use_banwords_filter FROM users_groups_settings ugs INNER JOIN users_groups_actions uga ON uga.user_id = ugs.owner_id WHERE owner_id = {call.from_user.id} AND ugs.group_id = uga.group_id;"
    await cursor.execute(get_data_sql)
    r = await cursor.fetchone()
    if r is None:
        return
    use_notify_for_ban_user = r[0]
    use_notify_for_unban_user = r[1]
    use_banwords_filter = r[2]

    try:
        if use_banwords_filter:
            await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=texts.SET_GROUP_SETTINGS_ANSWER, reply_markup=await keyboards.set_group_settings_keyboard(use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, True))
        else:
            await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text=texts.SET_GROUP_SETTINGS_ANSWER, reply_markup=await keyboards.set_group_settings_keyboard(use_notify_for_ban_user, use_notify_for_unban_user, use_banwords_filter, False))
    except aiogram.exceptions.TelegramBadRequest:
        return

