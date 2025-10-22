from aiogram import Router
from aiogram.types import Message
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import StateFilter

from utils.language import get_text, get_user_language_from_db
from handlers.transcription_handler import TranscriptionState
from keyboards.main_menu import get_main_keyboard
from database.database import get_async_db

router = Router()


@router.message(F.text.in_(["🎤 Транскрибировать", "🎤 Transcribe"]))
async def handle_transcribe_button(message: Message, state: FSMContext):
    # Обработка нажатия кнопки 'Транскрибировать' в главном меню
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        
        # Устанавливаем состояние ожидания файла
        await state.set_state(TranscriptionState.waiting_for_file)
        
        # Отправляем сообщение с просьбой прислать файл и убираем клавиатуру
        text = get_text("send_audio_video", lang)
        
        await message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(F.text.in_(["Отмена", "Cancel"]))
async def handle_cancel_from_any_state(message: Message, state: FSMContext):
    # Обработка нажатия кнопки 'Отмена' из любого состояния
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        
        # Сбрасываем состояние
        await state.clear()
        
        # Отправляем сообщение об отмене и главное меню
        await message.answer(
            text=get_text("transcription_canceled", lang),
            reply_markup=get_main_keyboard(lang)
        )


@router.message()
async def handle_message_without_state(message: Message, state: FSMContext):
    # Обработка сообщений, когда пользователь не в состоянии ожидания файла
    current_state = await state.get_state()
    
    # Если пользователь не в состоянии ожидания файла, но присылает аудио/видео/документ/голосовое
    if current_state != TranscriptionState.waiting_for_file and (message.audio or message.video or message.document or message.voice):
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, message.from_user.id)
            text = get_text("this_does_not_work", lang)
            await message.answer(text, reply_markup=get_main_keyboard(lang)) # Added keyboard
    # Во всех остальных случаях отвечаем, что команда не распознана
    else:
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, message.from_user.id)
            text = get_text("unknown_command", lang)
            await message.answer(text, reply_markup=get_main_keyboard(lang)) # Added keyboard