from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Optional

from database.models import User
from utils.language import get_text

def create_admin_user_list_keyboard(users: List[User], page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для списка пользователей в админ-панели.
    builder = InlineKeyboardBuilder()

    for user in users:
        status_icon = "🟢" if user.is_active else "🔴" # Зеленый для активных, красный для заблокированных
        admin_icon = "👑" if user.is_admin else "👤"
        username_display = user.username or user.first_name or f"ID: {user.telegram_id}"
        button_text = f"{status_icon}{admin_icon} {username_display} | {user.balance:.1f} min"
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"admin_users:view:{user.id}:{page}"))

    # Кнопки пагинации
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="⏪", callback_data=f"admin_users:page:{page - 1}"))
    
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1} / {total_pages}", callback_data="ignore"))

    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton(text="⏩", callback_data=f"admin_users:page:{page + 1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    # Кнопка возврата в главное меню админки
    builder.row(InlineKeyboardButton(text=get_text("kb_back_to_admin_menu", lang), callback_data="admin_users:main_menu"))

    return builder.as_markup()

def create_admin_user_view_keyboard(user: User, page: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для детального просмотра пользователя в админ-панели.
    builder = InlineKeyboardBuilder()
    
    block_unblock_text = get_text("admin_btn_unblock_user", lang) if not user.is_active else get_text("admin_btn_block_user", lang)
    builder.row(
        InlineKeyboardButton(text=block_unblock_text, callback_data=f"admin_users:toggle_block:{user.id}:{page}"),
        InlineKeyboardButton(text=get_text("admin_btn_add_minutes", lang), callback_data=f"admin_users:add_minutes_prompt:{user.id}:{page}")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("kb_back_to_list", lang), callback_data=f"admin_users:page:{page}")
    )
    return builder.as_markup()

def create_admin_add_minutes_confirm_keyboard(user_id: int, page: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для подтверждения добавления минут. На данный момент содержит только кнопку отмены, так как ввод минут будет через FSM.
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("kb_cancel", lang), callback_data=f"admin_users:view:{user_id}:{page}")
    )
    return builder.as_markup()