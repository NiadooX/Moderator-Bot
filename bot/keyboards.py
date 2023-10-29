from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton, InlineKeyboardMarkup
import texts
from misc import async_range


async def main_keyboard():
    buttons = [[KeyboardButton(text=texts.MY_PROFILE_BUTTON_TEXT), KeyboardButton(text=texts.MY_GROUPS_BUTTON_TEXT)], [KeyboardButton(text=texts.ABOUT_BOT_BUTTON_TEXT)]]
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True, input_field_placeholder=texts.MAIN_PLACEHOLDER)
    return markup


async def back_keyboard():
    buttons = [[KeyboardButton(text=texts.BACK_BUTTON_TEXT)]]
    markup = ReplyKeyboardMarkup(keyboard=buttons, one_time_keyboard=True, resize_keyboard=True)
    return markup


async def user_groups_keyboard(**groups):
    builder = InlineKeyboardBuilder()
    for group_id, group_name in groups.items():
        builder.add(InlineKeyboardButton(text=group_name, callback_data=f'chose_group {group_id} {group_name}'))
    builder.adjust(2)
    return builder.as_markup()


async def user_group_settings():
    buttons = [[KeyboardButton(text=texts.BAN_USER_BUTTON_TEXT), KeyboardButton(text=texts.UNBAN_USER_BUTTON_TEXT)], [KeyboardButton(text=texts.MUTE_USER_BUTTON_TEXT), KeyboardButton(text=texts.UNMUTE_USER_BUTTON_TEXT)], [KeyboardButton(text=texts.GROUP_SETTINGS_BUTTON_TEXT)], [KeyboardButton(text=texts.CREATE_INVITE_LINK_BUTTON_TEXT)], [KeyboardButton(text=texts.BACK_BUTTON_TEXT)]]
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True, input_field_placeholder=texts.MAIN_PLACEHOLDER)
    return markup


async def bot_author_keyboard():
    buttons = [[InlineKeyboardButton(text='Гитхаб', url='https://github.com/NiadooX')]]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def sure_about_ban_user_keyboard():
    buttons = [[InlineKeyboardButton(text=texts.SURE, callback_data='sure_to_ban'), InlineKeyboardButton(text=texts.UNSURE, callback_data='unsure_to_ban')]]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def sure_about_unban_user_keyboard():
    buttons = [[InlineKeyboardButton(text=texts.SURE, callback_data='sure_to_unban'), InlineKeyboardButton(text=texts.UNSURE, callback_data='unsure_to_unban')]]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def set_group_settings_keyboard(use_notify_for_ban_user_: bool, use_notify_for_unban_user_: bool, use_banwords_filter_: bool, use_edit_banwords: bool):
    d = {True: 'Отключить', False: 'Включить'}
    if use_edit_banwords:
        buttons = [[InlineKeyboardButton(text=d[use_notify_for_ban_user_] + texts.SET_NOTIFY_FOR_BAN_USER_BUTTON_TEXT, callback_data='set notify_for_ban_user')], [InlineKeyboardButton(text=d[use_notify_for_unban_user_] + texts.SET_NOTIFY_FOR_UNBAN_USER_BUTTON_TEXT, callback_data='set notify_for_unban_user')], [InlineKeyboardButton(text=d[use_banwords_filter_] + texts.SET_BANWORDS_FILTER_BUTTON_TEXT, callback_data='set banwords_filter')], [InlineKeyboardButton(text=texts.EDIT_BANWORDS_BUTTON_TEXT, callback_data='edit banwords_list')]]
    else:
        buttons = [[InlineKeyboardButton(text=d[use_notify_for_ban_user_] + texts.SET_NOTIFY_FOR_BAN_USER_BUTTON_TEXT, callback_data='set notify_for_ban_user')], [InlineKeyboardButton(text=d[use_notify_for_unban_user_] + texts.SET_NOTIFY_FOR_UNBAN_USER_BUTTON_TEXT, callback_data='set notify_for_unban_user')], [InlineKeyboardButton(text=d[use_banwords_filter_] + texts.SET_BANWORDS_FILTER_BUTTON_TEXT, callback_data='set banwords_filter')]]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def choose_a_banwords_list_action_keyboard():
    buttons = [[InlineKeyboardButton(text=texts.CLEAR_BANWORDS_LIST_BUTTON_TEXT, callback_data='replace banwords_list')], [InlineKeyboardButton(text=texts.ADD_TO_BANWORDS_LIST_BUTTON_TEXT, callback_data='add to banwords_list')], [InlineKeyboardButton(text=texts.SHOW_BANWORDS_LIST_BUTTON_TEXT, callback_data='show banwords_list')], [InlineKeyboardButton(text=texts.BACK_BUTTON_TEXT, callback_data='back to_group_settings')]]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def tic_tac_toe_game_keyboard(positions: list):
    buttons = []
    async for j in async_range(len(positions)):
        temp = []
        async for c in async_range(len(positions[j])):
            temp.append(InlineKeyboardButton(text=positions[j][c], callback_data=f'set_pos {j} {c}'))
        buttons.append(temp)
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def tic_tac_toe_game_ready_keyboard(fighter1: str, fighter2: str, fighter1_ready: bool, fighter2_ready: bool):
    temp_dict = {True: texts.GAME1_READY, False: texts.GAME1_UNREADY}
    buttons = [[InlineKeyboardButton(text=f'{fighter1} {temp_dict[fighter1_ready]}', callback_data=f'{fighter1} game1_ready')], [InlineKeyboardButton(text=f'{fighter2} {temp_dict[fighter2_ready]}', callback_data=f'{fighter2} game1_ready')]]
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup


async def test_keyboard():
    buttons = [[InlineKeyboardButton(text='test', callback_data='test_bt')]*20]*50
    markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    return markup

