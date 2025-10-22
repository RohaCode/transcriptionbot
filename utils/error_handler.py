import logging
import traceback
from functools import wraps
from typing import Callable, Any, Optional
from aiogram import Bot
from aiogram.types import Message
from config.settings import settings

logger = logging.getLogger(__name__)

# Инициализация админского ID из настроек
admin_tg_id: Optional[int] = None
if settings.admin_ids and isinstance(settings.admin_ids, list) and len(settings.admin_ids) > 0:
    admin_tg_id = settings.admin_ids[0]


def setup_error_handlers(bot: Bot):
    # Устанавливает глобальный обработчик необработанных исключений
    def exception_handler(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow Ctrl+C to exit gracefully
            raise exc_value
        logger.critical("Необработанное исключение", 
                       exc_info=(exc_type, exc_value, exc_traceback))
        
        # Отправить сообщение админу, если ID админа определен
        if admin_tg_id:
            error_msg = f"Критическая ошибка в боте:\n{exc_type.__name__}: {exc_value}\n\n{traceback.format_tb(exc_traceback)}"
            try:
                import asyncio
                # Get the current running event loop
                loop = asyncio.get_event_loop()
                # Schedule the coroutine to be run in the existing event loop
                loop.call_soon_threadsafe(lambda: asyncio.create_task(bot.send_message(admin_tg_id, error_msg)))
            except Exception as e:
                logger.error(f"Не удалось отправить критическое уведомление администратору: {e}")
    
    import sys
    sys.excepthook = exception_handler


def log_exceptions(func: Callable) -> Callable:
    # Декоратор для логирования исключений в асинхронных функциях
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Ошибка в функции {func.__name__}: {str(e)}")
            raise
    return wrapper


def handle_exceptions(default_return=None):
    # Декоратор для обработки и логирования исключений с возможностью возврата значения по умолчанию
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.exception(f"Ошибка в функции {func.__name__}: {str(e)}")
                return default_return
        return wrapper
    return decorator


async def notify_admin_about_error(bot: Bot, error_message: str, user_id: int = None):
    # Отправляет уведомление администратору о критической ошибке
    if admin_tg_id:
        try:
            full_message = f"Критическая ошибка в боте:\n{error_message}"
            if user_id:
                full_message += f"\n\nОшибка произошла у пользователя с ID: {user_id}"
            
            await bot.send_message(
                chat_id=admin_tg_id,
                text=full_message
            )
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение администратору: {e}")