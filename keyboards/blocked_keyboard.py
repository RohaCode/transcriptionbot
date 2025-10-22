from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.language import get_text
from config.settings import settings

def get_blocked_keyboard(lang: str) -> InlineKeyboardMarkup:
    # Создает и возвращает Inline-клавиатуру для заблокированного пользователя с кнопкой связи с администратором.
    builder = InlineKeyboardBuilder()
    
    admin_id = settings.admin_ids.split(',')[0].strip()
    if admin_id:
        builder.row(InlineKeyboardButton(
            text=get_text("faq_admin_link_text", lang),
            url=f"tg://user?id={admin_id}"
        ))
    
    return builder.as_markup()