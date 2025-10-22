from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils.language import get_text

def get_admin_main_keyboard(lang: str) -> ReplyKeyboardMarkup:
    # Создает и возвращает основную клавиатуру для админ-панели.
    keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text=get_text("admin_btn_users", lang)),
                    KeyboardButton(text=get_text("admin_btn_stats", lang))
                ],
                [
                    KeyboardButton(text=get_text("admin_btn_settings", lang))
                ]
            ],        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard