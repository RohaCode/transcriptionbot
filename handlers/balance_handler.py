from aiogram import Router, F, Bot
from aiogram.types import (
    Message, 
    CallbackQuery, 
    LabeledPrice, 
    PreCheckoutQuery, 
    SuccessfulPayment
)
from aiogram.enums import ContentType
from aiogram.fsm.context import FSMContext
import math
import logging

from database.database import get_async_db
from database.crud import (
    get_user_by_telegram_id,
    count_transcriptions_by_user_id,
    get_active_packages,
    count_active_packages,
    get_package_by_id,
    add_minutes_to_balance,
    create_payment
)
from keyboards.balance_keyboard import create_balance_keyboard, create_payment_confirmation_keyboard
from keyboards.main_menu import get_main_keyboard
from utils.language import get_text, get_user_language_from_db
from config.settings import settings
from core.bot import bot
from handlers.transcription_handler import TranscriptionState
from utils.error_handler import notify_admin_about_error

router = Router()
logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 4

async def show_balance_page(message: Message, user_id: int, page: int = 0):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, user_id)
        user = await get_user_by_telegram_id(db, user_id)
        if not user:
            await message.answer(get_text("user_not_found_start", lang))
            return

        transcription_count = await count_transcriptions_by_user_id(db, user.id)
        
        user_info = get_text("profile_info", lang).format(
            username=(user.first_name or user.username),
            balance=int(user.balance),
            count=transcription_count
        )

        total_packages = await count_active_packages(db)
        total_pages = math.ceil(total_packages / ITEMS_PER_PAGE)
        page = max(0, min(page, total_pages - 1))
        packages = await get_active_packages(db, skip=page * ITEMS_PER_PAGE, limit=ITEMS_PER_PAGE)
        payment_token_set = bool(settings.payment_token) # Determine if token is set
        keyboard = create_balance_keyboard(packages, page, total_pages, lang, payment_token_set) # Pass the status
        
        if isinstance(message, CallbackQuery):
            await message.message.edit_text(user_info, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await message.answer(user_info, reply_markup=keyboard, parse_mode="Markdown")

@router.message(F.text.in_(["👤 Профиль", "👤 Profile"]))
async def balance_start_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, message.from_user.id)
            await state.clear()
            await message.answer(get_text("transcription_canceled", lang), reply_markup=get_main_keyboard(lang))
            
    await show_balance_page(message, message.from_user.id, page=0)

@router.callback_query(F.data.startswith("balance:"))
async def balance_menu_callback_handler(callback: CallbackQuery):
    _, action, *params = callback.data.split(':')
    user_id = callback.from_user.id

    if action == "page":
        page = int(params[0])
        await show_balance_page(callback, user_id, page=page)
    
    elif action == "main_menu":
        async with get_async_db() as db:
            lang = await get_user_language_from_db(db, user_id)
            await callback.message.delete()
            await callback.message.answer(
                get_text("main_menu", lang),
                reply_markup=get_main_keyboard(lang)
            )
    await callback.answer()

@router.callback_query(F.data.startswith("buy:"))
async def buy_callback_handler(callback: CallbackQuery):
    _, package_id, page = callback.data.split(':')
    user_id = callback.from_user.id

    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, user_id)
        package = await get_package_by_id(db, int(package_id))
        if not package:
            await callback.answer(get_text("package_not_found", lang), show_alert=True)
            return

        confirmation_text = get_text("payment_confirmation", lang).format(
            package_name=package.name,
            minutes_count=package.minutes_count,
            price=int(package.price)
        )
        keyboard = create_payment_confirmation_keyboard(int(package_id), int(page), lang)
        await callback.message.edit_text(confirmation_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()

@router.callback_query(F.data.startswith("payment:confirm"))
async def confirm_payment_handler(callback: CallbackQuery):
    _, _, package_id = callback.data.split(':')
    user_id = callback.from_user.id

    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, user_id)
        package = await get_package_by_id(db, int(package_id))
        if not package:
            await callback.answer(get_text("package_not_found", lang), show_alert=True)
            return

        # Удаляем предыдущее сообщение с кнопками подтверждения
        await callback.message.delete()

        await bot.send_invoice(
            chat_id=user_id,
            title=get_text("invoice_title", lang).format(package_name=package.name),
            description=get_text("invoice_description", lang).format(minutes_count=package.minutes_count),
            payload=f"package_purchase:{package.id}",
            provider_token=settings.payment_token,
            currency="RUB",
            prices=[
                LabeledPrice(
                    label=get_text("price_label", lang).format(minutes_count=package.minutes_count), 
                    amount=int(package.price * 100)
                )
            ]
        )
        await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment_handler(message: Message):
    payload = message.successful_payment.invoice_payload
    user_id = message.from_user.id

    try:
        prefix, package_id_str = payload.split(':')
        if prefix == "package_purchase":
            package_id = int(package_id_str)
            async with get_async_db() as db:
                lang = await get_user_language_from_db(db, user_id)
                package = await get_package_by_id(db, package_id)
                if package:
                    await add_minutes_to_balance(db, user_id, package.minutes_count)
                    
                    # Создаем запись о платеже
                    await create_payment(
                        db,
                        user_id=user_id,
                        package_id=package.id,
                        minutes_count=package.minutes_count,
                        amount=message.successful_payment.total_amount / 100, # Telegram отправляет сумму в копейках/центах
                        currency=message.successful_payment.currency,
                        payment_system="telegram_payments", # Или "yookassa" если интегрировано
                        payment_id=message.successful_payment.telegram_payment_charge_id,
                        status="success"
                    )

                    await bot.send_message(
                        user_id,
                        get_text("payment_successful", lang).format(minutes_count=package.minutes_count)
                    )
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка обработки payload: {e}")
        await notify_admin_about_error(bot, f"Ошибка обработки payload платежа: {e}", user_id)