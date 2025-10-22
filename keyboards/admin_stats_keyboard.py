from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.language import get_text

def get_admin_stats_keyboard(lang: str) -> InlineKeyboardMarkup:
    # Создает и возвращает Inline-клавиатуру для раздела статистики админ-панели.
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("kb_back_to_admin_menu", lang), callback_data="admin_stats:main_menu"))
    return builder.as_markup()