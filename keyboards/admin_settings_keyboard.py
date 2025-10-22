from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.language import get_text

def get_admin_settings_keyboard(lang: str) -> InlineKeyboardMarkup:
    # Создает и возвращает Inline-клавиатуру для раздела настроек админ-панели.
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_settings_api_key", lang), callback_data="admin_settings:api_key"))
    builder.row(InlineKeyboardButton(text=get_text("admin_settings_cost_per_minute", lang), callback_data="admin_settings:cost_per_minute"))
    builder.row(InlineKeyboardButton(text=get_text("admin_settings_manage_packages", lang), callback_data="admin_settings:manage_packages"))
    builder.row(InlineKeyboardButton(text=get_text("admin_settings_audio_duration", lang), callback_data="admin_settings:audio_duration"))

    builder.row(InlineKeyboardButton(text=get_text("kb_back_to_admin_menu", lang), callback_data="admin_settings:main_menu"))
    return builder.as_markup()

def get_admin_packages_keyboard(lang: str) -> InlineKeyboardMarkup:
    # Создает и возвращает Inline-клавиатуру для управления пакетами.
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("admin_packages_add", lang), callback_data="admin_packages:add"))
    builder.row(InlineKeyboardButton(text=get_text("admin_packages_edit", lang), callback_data="admin_packages:edit"))
    builder.row(InlineKeyboardButton(text=get_text("admin_packages_delete", lang), callback_data="admin_packages:delete"))
    builder.row(InlineKeyboardButton(text=get_text("kb_back_to_settings_menu", lang), callback_data="admin_packages:back_to_settings"))
    return builder.as_markup()

def get_cancel_keyboard(lang: str) -> InlineKeyboardMarkup:
    # Создает и возвращает Inline-клавиатуру с кнопкой "Отмена".
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("kb_cancel", lang), callback_data="admin_settings:cancel_action"))
    return builder.as_markup()