import logging
import os
from datetime import datetime

# Убедимся, что директория logs существует
os.makedirs("logs", exist_ok=True)

# Настройка формата логов с контекстной информацией
log_format = (
    "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
)

# Настройка основного логгера
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler("logs/bot.log", encoding="utf-8", mode="a"),
        logging.StreamHandler(),  # Вывод в консоль
    ],
)

# Создание отдельного логгера для бота
logger = logging.getLogger(__name__)

# Explicitly set level for RateLimiter to ensure debug messages are shown
logging.getLogger("middlewares.rate_limit_middleware").setLevel(logging.INFO)


def setup_logger(name: str) -> logging.Logger:
    # Создает и настраивает логгер с заданным именем
    logger_instance = logging.getLogger(name)
    logger_instance.setLevel(logging.INFO)
    return logger_instance