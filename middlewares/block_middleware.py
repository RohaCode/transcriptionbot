from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update
from aiogram.exceptions import TelegramBadRequest
from typing import Callable, Dict, Any, Awaitable
import logging # Added

from database.database import get_async_db
from database.crud import get_user_by_telegram_id
from config.settings import settings
from utils.language import get_text, get_user_language_from_db
from keyboards.blocked_keyboard import get_blocked_keyboard

logger = logging.getLogger(__name__) # Added

class BlockMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        logger.debug(f"BlockMiddleware: __call__ entered for update: {event.update_id}") # ADDED
        user_id = None
        if event.message:
            user_id = event.message.from_user.id
        elif event.callback_query:
            user_id = event.callback_query.from_user.id
        
        logger.debug(f"BlockMiddleware: Processing user_id: {user_id}") # ADDED

        if user_id is None:
            logger.debug("BlockMiddleware: user_id is None, passing to next handler.") # ADDED
            return await handler(event, data)

        # Проверяем, является ли пользователь администратором
        admin_ids = settings.admin_ids
        if user_id in admin_ids:
            logger.debug(f"BlockMiddleware: User {user_id} is admin, passing to next handler.") # ADDED
            return await handler(event, data)

        async with get_async_db() as db:
            user = await get_user_by_telegram_id(db, user_id)
            
            # Если пользователя нет в БД, пропускаем (он будет создан при /start)
            if not user:
                logger.debug(f"BlockMiddleware: User {user_id} not in DB, passing to next handler.") # ADDED
                return await handler(event, data)

            # Если пользователь заблокирован (is_active = False), останавливаем обработку
            if not user.is_active:
                logger.debug(f"BlockMiddleware: User {user_id} is BLOCKED. Stopping processing.") # ADDED
                lang = user.language_code if user.language_code else 'ru'
                blocked_message = get_text("user_blocked_message", lang)
                blocked_keyboard = get_blocked_keyboard(lang)
                
                if event.message:
                    await event.message.answer(blocked_message, reply_markup=blocked_keyboard)
                elif event.callback_query:
                    try:
                        await event.callback_query.message.edit_text(blocked_message, reply_markup=blocked_keyboard)
                    except TelegramBadRequest: # Сообщение слишком старое для редактирования
                        await event.callback_query.message.answer(blocked_message, reply_markup=blocked_keyboard)
                    await event.callback_query.answer()
                return # Останавливаем дальнейшую обработку
        # Если пользователь не заблокирован, продолжаем обработку
        logger.debug(f"BlockMiddleware: User {user_id} is ACTIVE. Passing to next handler.") # ADDED
        return await handler(event, data)