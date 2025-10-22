from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

from utils.language import get_text

def get_main_keyboard(language_code: str = 'ru'):
    # Создает и возвращает основную клавиатуру для бота
    # Определяем текст кнопок в зависимости от языка
    if language_code == 'ru':
        transcribe_text = "🎤 Транскрибировать"
        history_text = "📋 История"
        profile_text = "👤 Профиль"
        help_text = "❓ Помощь"
    else:  # по умолчанию английский
        transcribe_text = "🎤 Transcribe"
        history_text = "📋 History"
        profile_text = "👤 Profile"
        help_text = "❓ Help"
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=transcribe_text),
                KeyboardButton(text=history_text)
            ],
            [
                KeyboardButton(text=profile_text),
                KeyboardButton(text=help_text)
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )
    return keyboard