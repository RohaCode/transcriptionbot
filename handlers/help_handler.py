from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

from utils.language import get_text, get_user_language_from_db
from keyboards.main_menu import get_main_keyboard
from config.settings import settings
from handlers.transcription_handler import TranscriptionState
from database.database import get_async_db

router = Router()


@router.message(F.text.in_(["❓ Помощь", "❓ Help"]))
async def help_handler(message: Message, state: FSMContext):
    # Обработчик для кнопки Помощь/Help. Отправляет текст FAQ и кнопки для связи с администратором и возврата в меню.
    current_state = await state.get_state()
    if current_state is not None:
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, message.from_user.id)
            await state.clear()
            await message.answer(get_text("transcription_canceled", lang), reply_markup=get_main_keyboard(lang))
            
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
    
    faq_text = get_text("faq_text", lang)
    
    builder = InlineKeyboardBuilder()
    
    # Кнопка связи с админом
    admin_id = settings.admin_ids[0] if settings.admin_ids else None
    if admin_id:
        builder.row(InlineKeyboardButton(
            text=get_text("faq_admin_link_text", lang),
            url=f"tg://user?id={admin_id}"
        ))
    
    # Кнопка возврата в меню
    builder.row(InlineKeyboardButton(
        text=get_text("kb_main_menu", lang),
        callback_data="help:main_menu"
    ))

    await message.answer(
        faq_text,
        reply_markup=builder.as_markup(),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

@router.callback_query(F.data == "help:main_menu")
async def back_to_main_menu_handler(callback: CallbackQuery):
    # Обрабатывает кнопку возврата в главное меню из раздела помощи.
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await callback.message.delete()
        await callback.message.answer(
            get_text("main_menu", lang),
            reply_markup=get_main_keyboard(lang)
        )
        await callback.answer()