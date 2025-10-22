from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import math

from database.database import get_async_db
from database.crud import (
    get_all_users,
    count_all_users,
    get_user_by_id,
    update_user_is_active_status,
    update_user_balance,
    get_user_total_transcriptions_count
)
from keyboards.admin_user_keyboard import (
    create_admin_user_list_keyboard,
    create_admin_user_view_keyboard,
    create_admin_add_minutes_confirm_keyboard
)
from keyboards.admin_keyboard import get_admin_main_keyboard
from filters.admin_filter import AdminFilter
from utils.language import get_text, get_user_language_from_db

router = Router()

ITEMS_PER_PAGE = 5

class AdminUserStates(StatesGroup):
    add_minutes = State()

async def show_admin_users_page(message: Message | CallbackQuery, admin_telegram_id: int, page: int = 0):
    # Отправляет или редактирует сообщение, отображая страницу со списком пользователей.
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, admin_telegram_id)
        total_items = await count_all_users(db)
        if total_items == 0:
            text = get_text("admin_users_empty", lang)
            if isinstance(message, CallbackQuery):
                await message.message.edit_text(text, reply_markup=None)
            else:
                await message.answer(text)
            return

        total_pages = math.ceil(total_items / ITEMS_PER_PAGE)
        page = max(0, min(page, total_pages - 1))

        users = await get_all_users(db, skip=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
        
        text = get_text("admin_users_header", lang)
        keyboard = create_admin_user_list_keyboard(users, page, total_pages, lang)
        
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(text, reply_markup=keyboard)
        else:
            await message.answer(text, reply_markup=keyboard)

async def show_admin_user_details(callback: CallbackQuery, user_id: int, page: int, lang: str):
    async with get_async_db() as db:
        user = await get_user_by_id(db, user_id)
        if not user:
            await callback.answer(get_text("user_not_found", lang), show_alert=True)
            return
        
        transcription_count = await get_user_total_transcriptions_count(db, user.id)

        user_info_text = get_text("admin_user_details", lang).format(
            user_id=user.id,
            telegram_id=user.telegram_id,
            username=user.username if user.username else get_text("not_available", lang),
            first_name=user.first_name if user.first_name else get_text("not_available", lang),
            last_name=user.last_name if user.last_name else get_text("not_available", lang),
            balance=f"{user.balance:.1f}",
            is_active=get_text("yes", lang) if user.is_active else get_text("no", lang),
            is_admin=get_text("yes", lang) if user.is_admin else get_text("no", lang),
            created_at=user.created_at.strftime("%d.%m.%Y %H:%M"),
            transcription_count=transcription_count
        )
        keyboard = create_admin_user_view_keyboard(user, page, lang)
        await callback.message.edit_text(user_info_text, reply_markup=keyboard)

@router.callback_query(F.data.startswith("admin_users:"), AdminFilter())
async def admin_users_callback_handler(callback: CallbackQuery, state: FSMContext):
    prefix, action, *params = callback.data.split(':')
    admin_telegram_id = callback.from_user.id
    
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, admin_telegram_id)

        if prefix != 'admin_users':
            return

        if action == "page":
            page = int(params[0])
            await show_admin_users_page(callback, admin_telegram_id, page=page)

        elif action == "view":
            user_id, page = int(params[0]), int(params[1])
            await show_admin_user_details(callback, user_id, page, lang)

        elif action == "toggle_block":
            user_id, page = int(params[0]), int(params[1])
            user = await get_user_by_id(db, user_id)
            if user:
                new_status = not user.is_active
                updated_user = await update_user_is_active_status(db, user_id, new_status)
                if updated_user:
                    status_message = get_text("admin_user_blocked", lang) if not new_status else get_text("admin_user_unblocked", lang)
                    await callback.answer(status_message, show_alert=True)
                else:
                    await callback.answer(get_text("admin_user_status_error", lang), show_alert=True)
            else:
                await callback.answer(get_text("user_not_found", lang), show_alert=True)
            await show_admin_user_details(callback, user_id, page, lang) # Обновляем текущий вид пользователя

        elif action == "add_minutes_prompt":
            await callback.answer() # Acknowledge the callback immediately
            user_id, page = int(params[0]), int(params[1])
            await state.update_data(admin_user_id=user_id, admin_page=page, prompt_message_id=callback.message.message_id)
            await state.set_state(AdminUserStates.add_minutes)
            keyboard = create_admin_add_minutes_confirm_keyboard(user_id, page, lang)
            await callback.message.edit_text(get_text("admin_enter_minutes_amount", lang), reply_markup=keyboard)

        elif action == "main_menu":
            await callback.message.delete()
            await callback.message.answer(
                get_text("admin_main_menu", lang),
                reply_markup=get_admin_main_keyboard(lang)
            )

    await callback.answer()

@router.message(AdminUserStates.add_minutes)
async def process_add_minutes(message: Message, state: FSMContext):
    admin_telegram_id = message.from_user.id
    data = await state.get_data()
    user_id = data.get("admin_user_id")
    page = data.get("admin_page")
    prompt_message_id = data.get("prompt_message_id")

    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, admin_telegram_id)

        if not user_id:
            await message.answer(get_text("admin_error_no_user_selected", lang))
            await state.clear()
            return

        try:
            minutes_to_add = float(message.text)
            if minutes_to_add <= 0:
                await message.answer(get_text("admin_minutes_positive_error", lang))
                return

            user = await get_user_by_id(db, user_id)
            if user:
                new_balance = user.balance + minutes_to_add
                updated_user = await update_user_balance(db, user_id, new_balance)
                if updated_user:
                    await message.answer(get_text("admin_minutes_added_success", lang).format(minutes=minutes_to_add, username=user.username or user.first_name or f"ID: {user.telegram_id}", new_balance=f"{new_balance:.1f}"))
                    if prompt_message_id:
                        await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
                else:
                    await message.answer(get_text("admin_minutes_add_error", lang))
            else:
                await message.answer(get_text("user_not_found", lang))
        except ValueError:
            await message.answer(get_text("admin_minutes_invalid_format", lang))
        finally:
            await state.clear()
            # Возвращаемся в главное меню админки после добавления минут
            await message.answer(
                get_text("admin_main_menu", lang),
                reply_markup=get_admin_main_keyboard(lang)
            )