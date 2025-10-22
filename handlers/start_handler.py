from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
import logging

from database.database import get_async_db
from database.crud import create_user
from keyboards.main_menu import get_main_keyboard
from utils.language import detect_language_by_tg_code, get_text
from utils.error_handler import log_exceptions, notify_admin_about_error
from core.bot import bot

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
@log_exceptions
async def command_start_handler(message: Message, state: FSMContext):
    # Обработчик команды /start
    try:
        await state.clear()

        async with get_async_db() as db:
            user = await create_user(
                db=db,
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                language_code=message.from_user.language_code
            )
        
        user_language = detect_language_by_tg_code(user.language_code or 'ru')
        
        welcome_text = get_text('start_message', user_language).format(username=user.first_name or user.username)
        welcome_text += "\n\n" + get_text('start_guide_message', user_language)
        
        await message.answer(
            text=welcome_text,
            reply_markup=get_main_keyboard(user_language)
        )
    except Exception as e:
        logger.exception(f"Ошибка в обработчике команды /start для пользователя {message.from_user.id}: {e}")
        # Уведомить администратора о критической ошибке
        await notify_admin_about_error(bot, str(e), message.from_user.id)
        await message.answer(get_text("start_command_error", user_language))