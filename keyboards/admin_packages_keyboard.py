from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from database.models import Package
from utils.language import get_text

def create_packages_for_delete_keyboard(packages: List[Package], lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру со списком пакетов для удаления.
    builder = InlineKeyboardBuilder()

    for package in packages:
        button_text = f"🗑️ {package.name} ({package.minutes_count} мин)"
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"pkg_delete_confirm:{package.id}"))

    builder.row(InlineKeyboardButton(text=get_text("kb_back_to_settings_menu", lang), callback_data="admin_settings:manage_packages"))
    
    return builder.as_markup()

def create_delete_confirmation_keyboard(package_id: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для подтверждения удаления пакета.
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("kb_confirm_delete", lang), callback_data=f"pkg_delete_execute:{package_id}"),
        InlineKeyboardButton(text=get_text("kb_cancel_delete", lang), callback_data="admin_packages:delete")
    )
    return builder.as_markup()