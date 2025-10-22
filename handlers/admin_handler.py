from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from filters.admin_filter import AdminFilter
from utils.language import get_text, get_user_language_from_db
from keyboards.admin_keyboard import get_admin_main_keyboard
from handlers.admin_user_handler import show_admin_users_page, router as admin_user_router
from handlers.admin_stats_handler import show_admin_stats_page, router as admin_stats_router
from handlers.admin_settings_handler import show_admin_settings_page, router as admin_settings_router
from database.database import get_async_db

router = Router()
router.include_router(admin_user_router)
router.include_router(admin_stats_router)
router.include_router(admin_settings_router)

@router.message(Command("admin"), AdminFilter())
async def admin_panel_handler(message: Message):
    # Обработчик команды /admin для администраторов.
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        welcome_text = get_text("admin_welcome", lang).format(username=message.from_user.first_name or message.from_user.username)
        await message.answer(
            text=welcome_text,
            reply_markup=get_admin_main_keyboard(lang)
        )

@router.message(F.text.in_(["👥 Пользователи", "👥 Users"]), AdminFilter())
async def admin_users_handler(message: Message):
    # Обработчик кнопки 'Пользователи' в админ-панели.
    await show_admin_users_page(message, message.from_user.id)

@router.message(F.text.in_(["📊 Статистика", "📊 Statistics"]), AdminFilter())
async def admin_stats_handler(message: Message):
    # Обработчик кнопки 'Статистика' в админ-панели.
    await show_admin_stats_page(message, message.from_user.id)

@router.message(F.text.in_(["⚙️ Настройки", "⚙️ Settings"]), AdminFilter())
async def admin_settings_handler(message: Message):
    # Обработчик кнопки 'Настройки' в админ-панели.
    await show_admin_settings_page(message, message.from_user.id)