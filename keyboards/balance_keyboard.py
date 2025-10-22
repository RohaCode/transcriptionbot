from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from database.models import Package
from utils.language import get_text

def create_balance_keyboard(packages: List[Package], page: int, total_pages: int, lang: str, payment_token_set: bool) -> InlineKeyboardMarkup:
    # Создает клавиатуру для раздела Баланс.
    builder = InlineKeyboardBuilder()

    # Кнопки пакетов
    for package in packages:
        button_text = get_text("package_button_format", lang).format(
            name=package.name,
            minutes=package.minutes_count,
            price=int(package.price)
        )
        if payment_token_set:
            builder.row(InlineKeyboardButton(text=button_text, callback_data=f"buy:{package.id}:{page}")) # Добавляем page для возврата
        else:
            # Make button inactive if payment token is not set
            builder.row(InlineKeyboardButton(text=f"🚫 {button_text}", callback_data="ignore")) # Add a visual cue

    # Кнопки пагинации
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="<<", callback_data=f"balance:page:{page - 1}"))
    
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1} / {total_pages}", callback_data="ignore"))

    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton(text=">>", callback_data=f"balance:page:{page + 1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text=get_text("kb_main_menu", lang), callback_data="balance:main_menu"))

    return builder.as_markup()

def create_payment_confirmation_keyboard(package_id: int, page: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для подтверждения платежа.
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("kb_pay", lang), callback_data=f"payment:confirm:{package_id}"),
        InlineKeyboardButton(text=get_text("kb_cancel_delete", lang), callback_data=f"balance:page:{page}") # kb_cancel_delete это "Отмена"
    )
    return builder.as_markup()