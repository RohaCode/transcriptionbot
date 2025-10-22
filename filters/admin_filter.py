from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union

from config.settings import settings
from utils.language import get_text, get_user_language_from_db
from keyboards.main_menu import get_main_keyboard
from database.database import get_async_db


class AdminFilter(Filter):
    async def __call__(self, obj: Union[Message, CallbackQuery]) -> bool:
        user_id = obj.from_user.id

        if user_id in settings.admin_ids:
            return True
        
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, user_id)
            
        if isinstance(obj, Message):
            await obj.answer(
                get_text("admin_access_denied", lang),
                reply_markup=get_main_keyboard(lang)
            )
        elif isinstance(obj, CallbackQuery):
            await obj.answer(get_text("admin_access_denied", lang), show_alert=True)
            
        return False