from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List

from database.models import Transcription
from utils.language import get_text


def create_history_list_keyboard(transcriptions: List[Transcription], page: int, total_pages: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для списка истории, где каждая запись - кнопка.
    builder = InlineKeyboardBuilder()

    for t in transcriptions:
        # Показываем первые 40 символов имени файла
        file_name_snippet = (t.file_name[:35] + '...') if len(t.file_name) > 38 else t.file_name
        status_icon = "✅" if t.status == 'completed' else ("❌" if t.status == 'failed' else "⏳")
        button_text = f"{status_icon} {t.created_at.strftime('%d.%m.%y')} - {file_name_snippet}"
        builder.row(InlineKeyboardButton(text=button_text, callback_data=f"history:view:{t.id}:{page}"))

    # Кнопки пагинации
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton(text="<<", callback_data=f"history:page:{page - 1}"))
    
    if total_pages > 1:
        pagination_row.append(InlineKeyboardButton(text=f"{page + 1} / {total_pages}", callback_data="ignore"))

    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton(text=">>", callback_data=f"history:page:{page + 1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    # Кнопка возврата в главное меню
    builder.row(InlineKeyboardButton(text=get_text("kb_main_menu", lang), callback_data="history:main_menu"))

    return builder.as_markup()

def create_transcription_view_keyboard(transcription_id: int, page: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для детального просмотра транскрипции.
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("kb_delete", lang), callback_data=f"history:delete:{transcription_id}:{page}"),
        InlineKeyboardButton(text=get_text("kb_download", lang), callback_data=f"history:download:{transcription_id}")
    )
    builder.row(
        InlineKeyboardButton(text=get_text("kb_back_to_list", lang), callback_data=f"history:page:{page}")
    )
    return builder.as_markup()

def create_confirm_delete_keyboard(transcription_id: int, page: int, lang: str) -> InlineKeyboardMarkup:
    # Создает клавиатуру для подтверждения удаления.
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("kb_confirm_delete", lang), callback_data=f"history:confirm_delete:{transcription_id}:{page}"),
        InlineKeyboardButton(text=get_text("kb_cancel_delete", lang), callback_data=f"history:view:{transcription_id}:{page}") # Возврат к просмотру
    )
    return builder.as_markup()