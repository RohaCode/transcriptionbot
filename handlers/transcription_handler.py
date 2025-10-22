from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove
import os
import tempfile
import math
import logging

from core.bot import bot
from database.crud import (
    get_user_by_telegram_id, 
    deduct_minutes_from_balance,
    create_transcription,
    update_transcription_status_and_result,
    get_setting
)
from database.database import get_async_db
from utils.audio_processing import get_audio_duration_async, cleanup_temp_file_async, process_file_for_transcription_optimized, get_file_size, process_file_for_transcription_async
from services.transcription_service import transcribe_audio_file_with_progress
from utils.language import get_text, get_user_language_from_db
from config.settings import settings, transcription_semaphore
from keyboards.main_menu import get_main_keyboard
from utils.error_handler import log_exceptions, notify_admin_about_error

router = Router()
logger = logging.getLogger(__name__)

class TranscriptionState(StatesGroup):
    waiting_for_file = State()


@router.message(Command("transcribe"))
@log_exceptions
async def start_transcription_command(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        await state.set_state(TranscriptionState.waiting_for_file)
        text = get_text("send_audio_video", lang)
        await message.answer(text, reply_markup=ReplyKeyboardRemove())


from aiogram.exceptions import TelegramBadRequest


@router.message(TranscriptionState.waiting_for_file)
@log_exceptions
async def handle_file_for_transcription(message: Message, state: FSMContext):
    temp_file_path = None
    processed_audio_path = None
    db_transcription = None

    try:
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, message.from_user.id)
        if message.text and message.text.lower() == get_text("kb_cancel", lang).lower():
            return

        file = message.voice or message.audio or message.video or message.document
        if not file:
            await message.answer(get_text("send_audio_video", lang), reply_markup=get_main_keyboard(lang))
            await state.clear()
            return

        original_filename = file.file_name if hasattr(file, 'file_name') else get_text("default_voice_filename", lang)
        file_ext = os.path.splitext(original_filename)[1].lower()
        is_video = file_ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']

        if message.document and file_ext not in ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.mp4', '.avi', '.mov', '.mkv', '.webm']:
            await message.answer(get_text("unsupported_format", lang), reply_markup=get_main_keyboard(lang))
            await state.clear()
            return

        async with get_async_db() as db:
            max_duration_db = await get_setting(db, "max_audio_duration_minutes")
            if max_duration_db and max_duration_db.isdigit():
                max_audio_duration_minutes = int(max_duration_db)
            else:
                max_audio_duration_minutes = 10

        # File size check is now handled by catching the Telegram API error
        try:
            file_info = await bot.get_file(file.file_id)
        except TelegramBadRequest as e:
            if "file is too big" in str(e).lower():
                await message.answer(get_text("file_too_big", lang).format(max_size=20), reply_markup=get_main_keyboard(lang))
                await state.clear()
                return
            else:
                logger.error(f"TelegramBadRequest while getting file info: {e}")
                raise e

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_file_path = temp_file.name

        await bot.download_file(file_info.file_path, temp_file_path)
            
        progress_msg = await message.answer(get_text("processing", lang))
        
        # Используем семафор для ограничения одновременных обработок
        async with transcription_semaphore:
            # Для видео используем оптимизированную функцию, для аудио - стандартную
            if is_video:
                processed_audio_path, processing_error_message = await process_file_for_transcription_optimized(
                    temp_file_path, is_video
                )
            else:
                processed_audio_path, processing_error_message = await process_file_for_transcription_async(
                    temp_file_path, is_video
                )
        
        if not processed_audio_path:
            await message.answer(processing_error_message or get_text("transcription_error", lang), reply_markup=get_main_keyboard(lang))
            return


        duration_seconds = await get_audio_duration_async(processed_audio_path)
        
        if duration_seconds > max_audio_duration_minutes * 60:
            actual_duration_min = math.ceil(duration_seconds / 60)
            await message.answer(get_text("audio_too_long", lang).format(
                max_duration_min=max_audio_duration_minutes,
                actual_duration_min=actual_duration_min
            ), reply_markup=get_main_keyboard(lang))
            return

        cost_minutes = math.ceil(duration_seconds / 60)

        async with get_async_db() as db:
            user = await get_user_by_telegram_id(db, message.from_user.id)
            if not user:
                await message.answer(get_text("user_not_found_start", lang), reply_markup=get_main_keyboard(lang))
                return

            if user.balance <= 0:
                await message.answer(get_text("zero_balance", lang).format(username=(user.first_name or user.username)), reply_markup=get_main_keyboard(lang))
                return
            
            if user.balance < cost_minutes:
                await message.answer(get_text("insufficient_balance", lang).format(
                    cost_minutes=cost_minutes,
                    user_balance=int(user.balance)
                ), reply_markup=get_main_keyboard(lang))
                return

            db_transcription = await create_transcription(
                db=db,
                user_id=user.id,
                file_name=original_filename,
                file_path=processed_audio_path,
                duration=duration_seconds,
                language=user.language_code,
                cost=cost_minutes
            )

        transcription_text, transcription_error_message = await transcribe_audio_file_with_progress(
            db,
            processed_audio_path,
            user.language_code,
            bot,
            progress_msg,
            original_filename=original_filename
        )

        if transcription_text:
            async with get_async_db() as db:
                await update_transcription_status_and_result(
                    db=db,
                    transcription_id=db_transcription.id,
                    status='completed',
                    result_text=transcription_text
                )
                await deduct_minutes_from_balance(db, user.telegram_id, cost_minutes)
        else:
            async with get_async_db() as db:
                await update_transcription_status_and_result(
                    db=db,
                    transcription_id=db_transcription.id,
                    status='failed',
                    error_message=transcription_error_message
                )
            await message.answer(transcription_error_message or get_text("transcription_error", lang), reply_markup=get_main_keyboard(lang))

    except Exception as e:
        logger.exception(get_text("transcription_handler_error", lang).format(user_id=message.from_user.id))
        # Отправить уведомление админу о критической ошибке
        await notify_admin_about_error(bot, str(e), message.from_user.id)
        if db_transcription:
            async with get_async_db() as db:
                await update_transcription_status_and_result(
                    db=db,
                    transcription_id=db_transcription.id,
                    status='failed',
                    error_message=str(e)
                )
        # Получаем язык для сообщения об ошибке, если он не был установлен ранее
        if 'lang' not in locals():
            async with get_async_db() as db:
                lang = await get_user_language_from_db(db, message.from_user.id)
        await message.answer(get_text("transcription_error", lang), reply_markup=get_main_keyboard(lang))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            await cleanup_temp_file_async(temp_file_path)
        if processed_audio_path and os.path.exists(processed_audio_path):
            await cleanup_temp_file_async(processed_audio_path)
        await state.clear()