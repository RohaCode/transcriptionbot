from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
import logging
import time
from database.database import get_async_db
from utils.language import get_text, get_user_language_from_db
from keyboards.main_menu import get_main_keyboard
import uuid
from config.settings import settings

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, time_limit: int = 1):
        self.users_last_request: Dict[int, float] = {} # Changed to a simple dict
        self.time_limit = time_limit # Store time_limit
        self.instance_id = str(uuid.uuid4())
        logger.debug(f"ThrottlingMiddleware initialized with time_limit: {self.time_limit}, Instance ID: {self.instance_id}")
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any],
    ) -> Any:

        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        # Skip rate limiting for admin users
        if user_id in settings.admin_ids:
            return await handler(event, data)

        current_time = time.time() # Get current time
        
        logger.debug(f"ThrottlingMiddleware: Instance ID: {self.instance_id}, User {user_id} - Checking. Last requests: {self.users_last_request}")
        
        if user_id in self.users_last_request:
            last_request_time = self.users_last_request[user_id]
            if (current_time - last_request_time) < self.time_limit:
                logger.debug(f"ThrottlingMiddleware: Instance ID: {self.instance_id}, User {user_id} - THROTTLED. Last request: {last_request_time:.2f}, Current: {current_time:.2f}, Diff: {(current_time - last_request_time):.2f}, Limit: {self.time_limit}")
                # If throttled, send message to user
                async with get_async_db() as db:
                    lang = await get_user_language_from_db(db, user_id)
                    error_text = get_text("rate_limit_exceeded", lang)
                    
                    try:
                        if isinstance(event, Message):
                            await event.answer(error_text, reply_markup=get_main_keyboard(lang))
                        elif isinstance(event, CallbackQuery):
                            await event.answer(error_text, show_alert=True)
                    except Exception as e:
                        logger.error(f"Error sending rate limit message to user {user_id}: {e}")
                return # Stop further processing
            else:
                # Request is allowed, but old entry needs to be updated
                logger.debug(f"ThrottlingMiddleware: Instance ID: {self.instance_id}, User {user_id} - Cache entry expired. Updating.")
                self.users_last_request[user_id] = current_time # Update last request time
        else:
            # User not in cache, add them
            self.users_last_request[user_id] = current_time # Add user to cache
            logger.debug(f"ThrottlingMiddleware: Instance ID: {self.instance_id}, User {user_id} - Added to cache. Current requests: {self.users_last_request}")

        return await handler(event, data)