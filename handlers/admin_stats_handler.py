from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database.database import get_async_db
from database.crud import (
    count_all_users,
    count_total_transcriptions,
    count_total_payments,
    count_active_users,
    count_blocked_users,
    get_total_payments_amount
)
from keyboards.admin_stats_keyboard import get_admin_stats_keyboard
from keyboards.admin_keyboard import get_admin_main_keyboard
from filters.admin_filter import AdminFilter
from utils.language import get_text, get_user_language_from_db

router = Router()

async def show_admin_stats_page(message: Message | CallbackQuery, admin_telegram_id: int):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, admin_telegram_id)
        total_users = await count_all_users(db)
        total_transcriptions = await count_total_transcriptions(db)
        total_payments = await count_total_payments(db)
        total_payments_amount = await get_total_payments_amount(db)
        active_users = await count_active_users(db)
        blocked_users = await count_blocked_users(db)

        stats_text = get_text("admin_stats_header", lang).format(
            total_users=total_users,
            total_transcriptions=total_transcriptions,
            total_payments=total_payments,
            total_payments_amount=f"{total_payments_amount:.2f}",
            active_users=active_users,
            blocked_users=blocked_users
        )
        keyboard = get_admin_stats_keyboard(lang)

        if isinstance(message, CallbackQuery):
            await message.message.edit_text(stats_text, reply_markup=keyboard)
        else:
            await message.answer(stats_text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_stats:main_menu", AdminFilter())
async def admin_stats_main_menu_callback(callback: CallbackQuery):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await callback.message.delete()
        await callback.message.answer(
            get_text("admin_main_menu", lang),
            reply_markup=get_admin_main_keyboard(lang)
        )
        await callback.answer()