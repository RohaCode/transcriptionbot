from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.fsm.context import FSMContext
import math
import io
import logging

from database.database import get_async_db
from database.crud import (
    get_user_by_telegram_id, 
    get_transcriptions_by_user_id, 
    count_transcriptions_by_user_id,
    get_transcription_by_id,
    delete_transcription_by_id
)
from keyboards.history_keyboard import (
    create_history_list_keyboard, 
    create_transcription_view_keyboard,
    create_confirm_delete_keyboard
)
from keyboards.main_menu import get_main_keyboard
from utils.language import get_text, get_user_language_from_db
from handlers.transcription_handler import TranscriptionState
from utils.error_handler import log_exceptions
from core.bot import bot
from utils.error_handler import notify_admin_about_error

router = Router()
logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 5

@log_exceptions
async def show_history_page(message: Message, user_id: int, page: int = 0):
    # Отправляет или редактирует сообщение, отображая страницу истории.
    try:
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, user_id)
            user = await get_user_by_telegram_id(db, user_id)
            if not user:
                await message.answer(get_text("user_not_found_start", lang))
                return

            total_items = await count_transcriptions_by_user_id(db, user.id)
            if total_items == 0:
                text = get_text("history_empty", lang)
                if isinstance(message, CallbackQuery):
                    await message.message.edit_text(text, reply_markup=None)
                else:
                    await message.answer(text)
                return

            total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
            page = max(0, min(page, total_pages - 1))

            transcriptions = await get_transcriptions_by_user_id(db, user.id, skip=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
            
            text = get_text("history_header", lang)
            keyboard = create_history_list_keyboard(transcriptions, page, total_pages, lang)
            
            if isinstance(message, CallbackQuery):
                await message.message.edit_text(text, reply_markup=keyboard)
            else:
                await message.answer(text, reply_markup=keyboard)
    except Exception as e:
        logger.exception(f"Ошибка при отображении истории для пользователя {user_id}: {e}")
        await notify_admin_about_error(bot, str(e), user_id)
        # Отправляем пользователю сообщение об ошибке
        if isinstance(message, CallbackQuery):
            await message.answer("Произошла ошибка при отображении истории. Пожалуйста, попробуйте позже.", show_alert=True)
        else:
            async with get_async_db() as db:
                lang = await get_user_language_from_db(db, user_id)
                await message.answer(get_text("general_error", lang) or "Произошла ошибка при отображении истории. Пожалуйста, попробуйте позже.")

@router.message(F.text.in_(["📋 История", "📋 History"]))
@log_exceptions
async def history_start_handler(message: Message, state: FSMContext):
    try:
        current_state = await state.get_state()
        # If user was in any state, cancel it first.
        if current_state is not None:
            async with get_async_db() as db:
                lang = await get_user_language_from_db(db, message.from_user.id)
                await state.clear()
                # Use a generic cancellation message or check the state to be more specific
                await message.answer(get_text("transcription_canceled", lang), reply_markup=get_main_keyboard(lang))
        
        # Proceed to show the history page
        await show_history_page(message, message.from_user.id, page=0)
    except Exception as e:
        logger.exception(f"Ошибка в обработчике истории для пользователя {message.from_user.id}: {e}")
        await notify_admin_about_error(bot, str(e), message.from_user.id)
        await message.answer("Произошла ошибка при открытии истории. Пожалуйста, попробуйте позже.")

@router.callback_query(F.data.startswith("history:"))
@log_exceptions
async def history_callback_handler(callback: CallbackQuery):
    try:
        prefix, action, *params = callback.data.split(':')
        user_id = callback.from_user.id
        
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, user_id)

            if prefix != 'history':
                return

            if action == "page":
                page = int(params[0])
                await show_history_page(callback, user_id, page=page)

            elif action == "view":
                transcription_id, page = int(params[0]), int(params[1])
                transcription = await get_transcription_by_id(db, transcription_id)
                if not transcription:
                    await callback.answer(get_text("transcription_not_found", lang), show_alert=True)
                    return
                
                # Проверяем, принадлежит ли транскрипция пользователю, используя user_id из транскрипции
                # и сравнивая с telegram_id пользователя
                user = await get_user_by_telegram_id(db, user_id)
                if not user or transcription.user_id != user.id:
                    await callback.answer(get_text("transcription_not_found", lang), show_alert=True)
                    return
                
                text = transcription.result_text or get_text("text_missing", lang)
                keyboard = create_transcription_view_keyboard(transcription_id, page, lang)
                await callback.message.edit_text(text, reply_markup=keyboard)

            elif action == "download":
                transcription_id = int(params[0])
                transcription = await get_transcription_by_id(db, transcription_id)
                if not transcription:
                    await callback.answer(get_text("transcription_not_found", lang), show_alert=True)
                    return

                # Проверяем, принадлежит ли транскрипция пользователю, используя user_id из транскрипции
                # и сравнивая с telegram_id пользователя
                user = await get_user_by_telegram_id(db, user_id)
                if not user or transcription.user_id != user.id:
                    await callback.answer(get_text("transcription_not_found", lang), show_alert=True)
                    return

                file_content = transcription.result_text or ""
                file_name = f"{transcription.file_name.split('.')[0]}_result.txt"
                
                buffered_file = io.BytesIO(file_content.encode('utf-8'))
                text_file = BufferedInputFile(buffered_file.read(), filename=file_name)
                
                await callback.message.answer_document(text_file)

            elif action == "delete":
                transcription_id, page = int(params[0]), int(params[1])
                keyboard = create_confirm_delete_keyboard(transcription_id, page, lang)
                await callback.message.edit_text(get_text("delete_confirm", lang), reply_markup=keyboard)

            elif action == "confirm_delete":
                transcription_id, page = int(params[0]), int(params[1])
                success = await delete_transcription_by_id(db, transcription_id)
                if success:
                    await callback.answer(get_text("deleted_successfully", lang), show_alert=True)
                else:
                    await callback.answer(get_text("delete_error", lang), show_alert=True)
                
                await show_history_page(callback, user_id, page=page)
            
            elif action == "main_menu":
                await callback.message.delete()
                await callback.message.answer(
                    get_text("main_menu", lang),
                    reply_markup=get_main_keyboard(lang)
                )

            await callback.answer()
    except Exception as e:
        logger.exception(f"Ошибка в callback-обработчике истории для пользователя {callback.from_user.id}: {e}")
        await notify_admin_about_error(bot, str(e), callback.from_user.id)
        await callback.answer("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.", show_alert=True)