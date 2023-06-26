import asyncio
from config import BOT_TOKEN
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.fsm.storage.memory import MemoryStorage
import handlers


storage = MemoryStorage()


async def set_main_menu(bot: Bot):
    main_menu_commands = [BotCommand(command='/start', description='Начать с начала')]
    await bot.set_my_commands(main_menu_commands)


async def main():
    bot = Bot(BOT_TOKEN)
    dp = Dispatcher(storage=storage)
    dp.include_router(handlers.router)
    dp.startup.register(set_main_menu)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
