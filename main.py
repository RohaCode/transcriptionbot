import asyncio
import logging
import os
import sys

from utils import logging_config

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.bot import bot, dp
from middlewares.block_middleware import BlockMiddleware
from middlewares.rate_limit_middleware import RateLimitMiddleware

dp.update.outer_middleware(BlockMiddleware())
dp.message.outer_middleware(RateLimitMiddleware())
dp.callback_query.outer_middleware(RateLimitMiddleware())

from handlers.start_handler import router as start_router
from handlers.transcription_handler import router as transcription_router
from handlers.main_menu_handlers import router as main_menu_router
from handlers.history_handler import router as history_router
from handlers.help_handler import router as help_router
from handlers.balance_handler import router as balance_router
from handlers.admin_handler import router as admin_router
from database.database import init_db
from utils.error_handler import setup_error_handlers



# Подключение роутеров: более специфичные обработчики должны идти раньше
dp.include_router(start_router)
dp.include_router(history_router)
dp.include_router(help_router)
dp.include_router(balance_router)
dp.include_router(admin_router)
dp.include_router(transcription_router)

# Главное меню и обработка остальных сообщений должны быть в конце
dp.include_router(main_menu_router)


async def main():
    # Создаем папку для данных, если она не существует
    os.makedirs("data", exist_ok=True)
    
    # Инициализация базы данных
    await init_db()
    
    # Настройка обработки ошибок
    setup_error_handlers(bot)
    
    # Запуск бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
    except Exception as e:
        print(f"Критическая ошибка при запуске бота: {e}")
        # Отправляем уведомление админу (если уже инициализирован)
        try:
            from utils.error_handler import notify_admin_about_error
            import asyncio
            # Get the current running event loop
            loop = asyncio.get_event_loop()
            # Schedule the coroutine to be run in the existing event loop
            loop.call_soon_threadsafe(lambda: asyncio.create_task(notify_admin_about_error(bot, str(e), None)))
        except Exception as notify_e:
            print(f"Не удалось отправить критическое уведомление администратору при запуске: {notify_e}")