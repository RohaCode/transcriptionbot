from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.client.session.aiohttp import AiohttpSession

from config.settings import settings

# Увеличиваем таймаут сессии для скачивания больших файлов
session = AiohttpSession(timeout=300)

# Инициализация бота
bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    ),
    session=session
)

# Инициализация диспетчера
dp = Dispatcher()