import re
from typing import Optional, Tuple
import logging

from utils.language import get_text, get_user_language_from_db

logger = logging.getLogger(__name__)

class InputValidationResult:
    # Результат валидации ввода
    def __init__(self, is_valid: bool, value: any = None, error_message: str = None):
        self.is_valid = is_valid
        self.value = value
        self.error_message = error_message


class InputValidator:
    # Класс для валидации пользовательского ввода
    
    @staticmethod
    def validate_number_input(input_str: str, lang: str, min_value: float = None, max_value: float = None) -> InputValidationResult:
        # Валидирует числовое значение
        try:
            value = float(input_str.strip().replace(",", "."))
            
            if min_value is not None and value < min_value:
                return InputValidationResult(False, None, get_text("validation_min_value", lang).format(min_value=min_value))
            
            if max_value is not None and value > max_value:
                return InputValidationResult(False, None, get_text("validation_max_value", lang).format(max_value=max_value))
            
            return InputValidationResult(True, value, None)
        except ValueError:
            return InputValidationResult(False, None, get_text("validation_invalid_number", lang))
    
    @staticmethod
    def validate_integer_input(input_str: str, lang: str, min_value: int = None, max_value: int = None) -> InputValidationResult:
        # Валидирует целочисленное значение
        try:
            value = int(input_str.strip())
            
            if min_value is not None and value < min_value:
                return InputValidationResult(False, None, get_text("validation_min_value", lang).format(min_value=min_value))
            
            if max_value is not None and value > max_value:
                return InputValidationResult(False, None, get_text("validation_max_value", lang).format(max_value=max_value))
            
            return InputValidationResult(True, value, None)
        except ValueError:
            return InputValidationResult(False, None, get_text("validation_invalid_integer", lang))
    
    @staticmethod
    def validate_percentage_input(input_str: str, lang: str) -> InputValidationResult:
        # Валидирует процентное значение (0-100)
        result = InputValidator.validate_number_input(input_str, lang, min_value=0, max_value=100)
        if result.is_valid:
            if not result.value.is_integer() and result.value != round(result.value, 2):
                return InputValidationResult(False, None, get_text("validation_percentage_precision", lang))
        return result
    
    @staticmethod
    def validate_text_input(input_str: str, lang: str, min_length: int = 1, max_length: int = 1000) -> InputValidationResult:
        # Валидирует текстовое значение
        if not input_str or not input_str.strip():
            return InputValidationResult(False, None, get_text("validation_field_empty", lang))
        
        text = input_str.strip()
        
        if len(text) < min_length:
            return InputValidationResult(False, None, get_text("validation_text_min_length", lang).format(min_length=min_length))
        
        if len(text) > max_length:
            return InputValidationResult(False, None, get_text("validation_text_max_length", lang).format(max_length=max_length))
        
        # Проверяем на наличие потенциально опасных символов или конструкций
        dangerous_patterns = [
            r'<script',  # HTML/JS скрипты
            r'javascript:',  # JavaScript URL
            r'vbscript:',  # VBScript
            r'on\w+\s*=',  # HTML события
        ]
        
        for pattern in dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"Обнаружена потенциально опасная строка: {text}")
                return InputValidationResult(False, None, get_text("validation_dangerous_characters", lang))
        
        return InputValidationResult(True, text, None)
    
    @staticmethod
    def validate_api_key(input_str: str, lang: str) -> InputValidationResult:
        # Валидирует API-ключ
        if not input_str or not input_str.strip():
            return InputValidationResult(False, None, get_text("validation_api_key_empty", lang))
        
        # Basic API key validation - should be alphanumeric with possible special chars like hyphens, underscores
        api_key = input_str.strip()
        
        if len(api_key) < 10:
            return InputValidationResult(False, None, get_text("validation_api_key_too_short", lang))
        
        if len(api_key) > 200:
            return InputValidationResult(False, None, get_text("validation_api_key_too_long", lang))
        
        # Проверяем, что ключ содержит только допустимые символы
        if not re.match(r'^[a-zA-Z0-9\-_=]+$', api_key):
            return InputValidationResult(False, None, get_text("validation_api_key_invalid_characters", lang))
        
        return InputValidationResult(True, api_key, None)
    

    @staticmethod
    def validate_audio_duration_input(input_str: str, lang: str) -> InputValidationResult:
        # Валидирует продолжительность аудио (в минутах)
        return InputValidator.validate_integer_input(input_str, lang, min_value=1, max_value=120)