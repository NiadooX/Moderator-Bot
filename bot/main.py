from aiogram import Bot, Dispatcher
from aiogram.enums.parse_mode import ParseMode
from private_handlers import router1
from group_handlers import router2
import asyncio
from aiogram.types.chat_administrator_rights import ChatAdministratorRights
import logging
from start_set import get_settings


async def main():
    print('[INFO] Бот успешно запущен')
    bot = Bot(token=get_settings()['Telegram Bot']['token'], parse_mode=ParseMode.HTML)
    dp = Dispatcher()
    dp.include_routers(router1, router2)
    await bot.delete_webhook(drop_pending_updates=True)
    logging.basicConfig(filename='logs/errors_logs.log', filemode='w', format='%(asctime)s %(levelname)s %(message)s', level=logging.ERROR)
    logging.error('Errors of bot')
    await dp.start_polling(bot, allowed_updates=['message', 'callback_query', 'my_chat_member', 'chat_member'])


asyncio.run(main())
