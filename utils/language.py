import os
from typing import Dict

import os
import json
from typing import Dict

# Словарь для хранения загруженных переводов
TEXTS: Dict[str, Dict[str, str]] = {}

LOCALE_DIR = os.path.join(os.path.dirname(__file__), "..", "locales")


def load_translations():
    global TEXTS
    TEXTS = {}
    for filename in os.listdir(LOCALE_DIR):
        if filename.endswith(".json"):
            lang_code = os.path.splitext(filename)[0]
            filepath = os.path.join(LOCALE_DIR, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    TEXTS[lang_code] = json.load(f)
            except Exception as e:
                print(f"Ошибка при загрузке переводов для {lang_code}: {e}")


# Загружаем переводы при импорте модуля
load_translations()

# Словарь соответствия языковых кодов Telegram
TG_LANG_CODES = {"ru": ["ru", "ru-RU"], "en": ["en", "en-US", "en-GB"]}


async def get_user_language_from_db(db, user_id: int) -> str:
    # Асинхронное получение языка пользователя из базы данных
    from database.crud import get_user_by_telegram_id

    user = await get_user_by_telegram_id(db, user_id)
    return user.language_code if user and user.language_code else "ru"


def get_text(key: str, language_code: str = "ru") -> str:
    # Получение текста по ключу и языку
    if language_code in TEXTS:
        return TEXTS[language_code].get(key, key)
    else:
        # Если язык не найден, используем русский по умолчанию
        return TEXTS["ru"].get(key, key)


def detect_language_by_tg_code(tg_language_code: str) -> str:
    # Определение языка на основе языкового кода Telegram
    for lang, codes in TG_LANG_CODES.items():
        if tg_language_code in codes:
            return lang
    # Если код языка не найден, возвращаем 'ru' по умолчанию
    return "ru"
