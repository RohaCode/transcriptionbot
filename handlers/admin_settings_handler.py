from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import asyncio
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.admin_settings_keyboard import (
    get_admin_settings_keyboard,
    get_admin_packages_keyboard,
    get_cancel_keyboard,
)
from keyboards.admin_packages_keyboard import (
    create_packages_for_delete_keyboard,
    create_delete_confirmation_keyboard,
)
from keyboards.admin_keyboard import get_admin_main_keyboard
from filters.admin_filter import AdminFilter
from utils.language import get_text, get_user_language_from_db
from database.crud import (
    update_setting,
    get_all_packages,
    get_setting,
    delete_package_by_id,
    get_package_by_id,
    create_package,
)
from database.models import Setting
from database.database import get_async_db
from core.bot import bot
from utils.validation import InputValidator

router = Router()


class AdminSettingsStates(StatesGroup):
    waiting_for_api_key = State()
    waiting_for_cost_per_minute = State()
    waiting_for_package_action = State()
    waiting_for_audio_duration = State()

    # States for adding a package
    waiting_for_package_name = State()
    waiting_for_package_minutes = State()
    waiting_for_package_discount = State()
    waiting_for_package_confirmation = State()


class AdminEditPackageStates(StatesGroup):
    waiting_for_package_id_to_edit = State()
    waiting_for_new_package_name = State()
    waiting_for_new_package_minutes = State()
    waiting_for_new_package_discount = State()
    waiting_for_package_edit_confirmation = State()


async def show_admin_settings_page(
    message: Message | CallbackQuery, admin_telegram_id: int
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, admin_telegram_id)
        settings_text = get_text("admin_settings_header", lang)
        keyboard = get_admin_settings_keyboard(lang)

        if isinstance(message, CallbackQuery):
            if (
                message.message.text != settings_text
                or message.message.reply_markup != keyboard
            ):
                await message.message.edit_text(settings_text, reply_markup=keyboard)
        else:
            await message.answer(settings_text, reply_markup=keyboard)


@router.callback_query(F.data == "admin_settings:main_menu", AdminFilter())
async def admin_settings_main_menu_callback(callback: CallbackQuery):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await callback.message.delete()
        await callback.message.answer(
            get_text("admin_main_menu", lang),
            reply_markup=get_admin_main_keyboard(lang),
        )
    await callback.answer()


@router.callback_query(F.data == "admin_settings:cancel_action", AdminFilter())
async def admin_settings_cancel_action_callback(
    callback: CallbackQuery, state: FSMContext
):
    await state.clear()
    await show_admin_settings_page(callback, callback.from_user.id)
    await callback.answer()


# --- API Key Handlers ---
@router.callback_query(F.data == "admin_settings:api_key", AdminFilter())
async def admin_settings_api_key_callback(callback: CallbackQuery, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await state.update_data(prompt_message_id=callback.message.message_id)
        prompt_text = get_text("admin_settings_enter_api_key", lang)
        await callback.message.edit_text(
            prompt_text, reply_markup=get_cancel_keyboard(lang)
        )
        await state.set_state(AdminSettingsStates.waiting_for_api_key)
    await callback.answer()


@router.message(AdminSettingsStates.waiting_for_api_key, AdminFilter())
async def process_new_api_key(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_api_key(message.text, lang)

        if not validation_result.is_valid:
            await message.reply(validation_result.error_message)
            return

        await update_setting(db, key="api_key", value=validation_result.value)

        await message.delete()
        data = await state.get_data()
        prompt_message_id = data.get("prompt_message_id")
        await state.clear()

        confirmation_msg = await bot.send_message(
            chat_id=message.chat.id,
            text=get_text("admin_settings_api_key_updated", lang),
        )

        if prompt_message_id:
            await show_admin_settings_page(message, message.from_user.id)
            await bot.delete_message(
                chat_id=message.chat.id, message_id=prompt_message_id
            )

        await asyncio.sleep(3)
        await bot.delete_message(
            chat_id=message.chat.id, message_id=confirmation_msg.message_id
        )


# --- Cost Per Minute Handlers ---
@router.callback_query(F.data == "admin_settings:cost_per_minute", AdminFilter())
async def admin_settings_cost_per_minute_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await state.update_data(prompt_message_id=callback.message.message_id)

        current_value = await get_setting(db, "cost_per_minute")

        prompt_text = get_text("admin_settings_enter_cost_per_minute", lang).format(
            current_value=current_value
        )
        await callback.message.edit_text(
            prompt_text, reply_markup=get_cancel_keyboard(lang)
        )
        await state.set_state(AdminSettingsStates.waiting_for_cost_per_minute)
    await callback.answer()


@router.message(AdminSettingsStates.waiting_for_cost_per_minute, AdminFilter())
async def process_new_cost_per_minute(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)

        validation_result = InputValidator.validate_number_input(
            message.text, lang, min_value=0.01, max_value=1000
        )

        if not validation_result.is_valid:
            await message.reply(
                validation_result.error_message
                or get_text("admin_minutes_invalid_format", lang)
            )
            return

        await update_setting(
            db, key="cost_per_minute", value=str(validation_result.value)
        )

        all_packages = await get_all_packages(db)
        for package in all_packages:
            new_price = (
                validation_result.value
                * package.minutes_count
                * (1 - (package.discount or 0) / 100)
            )
            package.price = round(new_price, 2)
            db.add(package)
        await db.commit()

        await message.delete()
        data = await state.get_data()
        prompt_message_id = data.get("prompt_message_id")
        await state.clear()

        confirmation_msg = await bot.send_message(
            chat_id=message.chat.id,
            text=get_text("admin_settings_cost_per_minute_updated", lang),
        )

        if prompt_message_id:
            await show_admin_settings_page(message, message.from_user.id)
            await bot.delete_message(
                chat_id=message.chat.id, message_id=prompt_message_id
            )

        await asyncio.sleep(3)
        await bot.delete_message(
            chat_id=message.chat.id, message_id=confirmation_msg.message_id
        )


# --- Audio Duration Handlers ---
@router.callback_query(F.data == "admin_settings:audio_duration", AdminFilter())
async def admin_settings_audio_duration_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await state.update_data(prompt_message_id=callback.message.message_id)

        current_value = await get_setting(db, "max_audio_duration_minutes")

        prompt_text = get_text("admin_settings_enter_audio_duration", lang).format(
            current_value=current_value
        )
        await callback.message.edit_text(
            prompt_text, reply_markup=get_cancel_keyboard(lang)
        )
        await state.set_state(AdminSettingsStates.waiting_for_audio_duration)
    await callback.answer()


@router.message(AdminSettingsStates.waiting_for_audio_duration, AdminFilter())
async def process_new_audio_duration(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)

        validation_result = InputValidator.validate_audio_duration_input(
            message.text, lang
        )

        if not validation_result.is_valid:
            await message.reply(
                validation_result.error_message
                or get_text("admin_minutes_invalid_format", lang)
            )
            return

        await update_setting(
            db, key="max_audio_duration_minutes", value=str(validation_result.value)
        )

        await message.delete()
        data = await state.get_data()
        prompt_message_id = data.get("prompt_message_id")
        await state.clear()

        confirmation_msg = await bot.send_message(
            chat_id=message.chat.id,
            text=get_text("admin_settings_audio_duration_updated", lang),
        )

        if prompt_message_id:
            await show_admin_settings_page(message, message.from_user.id)
            await bot.delete_message(
                chat_id=message.chat.id, message_id=prompt_message_id
            )

        await asyncio.sleep(3)
        await bot.delete_message(
            chat_id=message.chat.id, message_id=confirmation_msg.message_id
        )


# --- Package Management Handlers ---
@router.callback_query(F.data == "admin_settings:manage_packages", AdminFilter())
async def admin_settings_manage_packages_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)

        packages = await get_all_packages(db)

        header = get_text("admin_packages_header", lang)

        if not packages:
            text = f"{header}\n\n{get_text('admin_packages_list_empty', lang)}"
        else:
            package_lines = []
            for pkg in packages:
                status_key = "status_active" if pkg.is_active else "status_inactive"
                status_text = get_text(status_key, lang)
                package_line = get_text("admin_package_item_format", lang).format(
                    name=pkg.name,
                    minutes=pkg.minutes_count,
                    price=pkg.price,
                    discount=pkg.discount,
                    status=status_text,
                )
                package_lines.append(package_line)

            text = f"{header}\n\n" + "\n".join(package_lines)

        await callback.message.edit_text(
            text, reply_markup=get_admin_packages_keyboard(lang), parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "admin_packages:back_to_settings", AdminFilter())
async def admin_packages_back_to_settings_callback(
    callback: CallbackQuery, state: FSMContext
):
    await state.clear()
    await show_admin_settings_page(callback, callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data == "admin_packages:delete", AdminFilter())
async def admin_packages_delete_callback(callback: CallbackQuery, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        packages = await get_all_packages(db)

        if not packages:
            await callback.answer(
                get_text("admin_packages_list_empty", lang), show_alert=True
            )
            return

        keyboard = create_packages_for_delete_keyboard(packages, lang)
        await callback.message.edit_text(
            text=get_text("admin_packages_delete", lang), reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pkg_delete_confirm:"), AdminFilter())
async def admin_packages_delete_confirm_callback(
    callback: CallbackQuery, state: FSMContext
):
    package_id = int(callback.data.split(":")[1])
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        package = await get_package_by_id(db, package_id)

        if not package:
            await callback.answer(get_text("package_not_found", lang), show_alert=True)
            return

        confirmation_text = get_text("admin_package_delete_confirm", lang).format(
            package_name=package.name
        )
        keyboard = create_delete_confirmation_keyboard(package_id, lang)

        await callback.message.edit_text(text=confirmation_text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("pkg_delete_execute:"), AdminFilter())
async def admin_packages_delete_execute_callback(
    callback: CallbackQuery, state: FSMContext
):
    package_id = int(callback.data.split(":")[1])
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        success = await delete_package_by_id(db, package_id)

        if success:
            await callback.answer(get_text("deleted_successfully", lang))
        else:
            await callback.answer(get_text("delete_error", lang), show_alert=True)

        # Refresh the delete list
        packages = await get_all_packages(db)

        keyboard = create_packages_for_delete_keyboard(packages, lang)
        await callback.message.edit_text(
            text=get_text("admin_packages_delete", lang), reply_markup=keyboard
        )


# --- Add Package Handlers ---
@router.callback_query(F.data == "admin_packages:add", AdminFilter())
async def admin_packages_add_callback(callback: CallbackQuery, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await state.update_data(prompt_message_id=callback.message.message_id)
        prompt_text = get_text("admin_package_enter_name", lang)
        await callback.message.edit_text(
            prompt_text, reply_markup=get_cancel_keyboard(lang)
        )
        await state.set_state(AdminSettingsStates.waiting_for_package_name)
    await callback.answer()


@router.message(AdminSettingsStates.waiting_for_package_name, AdminFilter())
async def process_package_name(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_text_input(
            message.text, lang, min_length=1, max_length=100
        )

        if not validation_result.is_valid:
            await message.reply(validation_result.error_message)
            return

        await state.update_data(package_name=validation_result.value)
        await message.delete()

        data = await state.get_data()
        prompt_message_id = data.get("prompt_message_id")
        if prompt_message_id:
            prompt_text = get_text("admin_package_enter_minutes", lang).format(
                package_name=validation_result.value
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=prompt_text,
                reply_markup=get_cancel_keyboard(lang),
            )
    await state.set_state(AdminSettingsStates.waiting_for_package_minutes)


@router.message(AdminSettingsStates.waiting_for_package_minutes, AdminFilter())
async def process_package_minutes(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_integer_input(
            message.text, lang, min_value=1, max_value=10000
        )

        if not validation_result.is_valid:
            await message.reply(
                validation_result.error_message
                or get_text("admin_minutes_invalid_format", lang)
            )
            return

        await state.update_data(minutes_count=validation_result.value)
        await message.delete()

        data = await state.get_data()
        package_name = data.get("package_name")
        prompt_message_id = data.get("prompt_message_id")
        if prompt_message_id:
            prompt_text = get_text("admin_package_enter_discount", lang).format(
                package_name=package_name
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=prompt_text,
                reply_markup=get_cancel_keyboard(lang),
            )
    await state.set_state(AdminSettingsStates.waiting_for_package_discount)


@router.message(AdminSettingsStates.waiting_for_package_discount, AdminFilter())
async def process_package_discount(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_percentage_input(message.text, lang)

        if not validation_result.is_valid:
            await message.reply(
                validation_result.error_message
                or get_text("admin_minutes_invalid_format", lang)
            )
            return

        await state.update_data(discount=validation_result.value)
        await message.delete()

        data = await state.get_data()
        package_name = data.get("package_name")
        minutes_count = data.get("minutes_count")
        discount = data.get("discount")
        prompt_message_id = data.get("prompt_message_id")

        cost_per_minute_str = await get_setting(db, "cost_per_minute")
        cost_per_minute = float(cost_per_minute_str)
        calculated_price = cost_per_minute * minutes_count * (1 - discount / 100)
        calculated_price = round(calculated_price, 2)

        await state.update_data(calculated_price=calculated_price)

        if prompt_message_id:
            confirmation_text = get_text("admin_package_confirm_creation", lang).format(
                name=package_name,
                minutes=minutes_count,
                discount=int(discount),
                price=calculated_price,
            )
            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(
                    text=get_text("yes", lang),
                    callback_data="admin_packages:add_confirm",
                ),
                InlineKeyboardButton(
                    text=get_text("no", lang), callback_data="admin_packages:add_cancel"
                ),
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=confirmation_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
            )
    await state.set_state(AdminSettingsStates.waiting_for_package_confirmation)


@router.callback_query(
    F.data == "admin_packages:add_confirm",
    AdminFilter(),
    AdminSettingsStates.waiting_for_package_confirmation,
)
async def admin_packages_add_confirm_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        data = await state.get_data()
        package_name = data.get("package_name")
        minutes_count = data.get("minutes_count")
        discount = data.get("discount")
        calculated_price = data.get("calculated_price")
        prompt_message_id = data.get("prompt_message_id")

        await create_package(
            db=db,
            name=package_name,
            minutes_count=minutes_count,
            price=calculated_price,
            discount=discount,
        )

        await state.clear()
        await callback.answer(
            get_text("admin_package_created_successfully", lang).format(
                package_name=package_name
            )
        )

        if prompt_message_id:
            await show_admin_settings_page(callback, callback.from_user.id)


@router.callback_query(
    F.data == "admin_packages:add_cancel",
    AdminFilter(),
    AdminSettingsStates.waiting_for_package_confirmation,
)
async def admin_packages_add_cancel_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await state.clear()
        await callback.answer(get_text("admin_package_creation_cancelled", lang))
    await show_admin_settings_page(callback, callback.from_user.id)


# --- Edit Package Handlers ---
@router.callback_query(F.data == "admin_packages:edit", AdminFilter())
async def admin_packages_edit_callback(callback: CallbackQuery, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        packages = await get_all_packages(db)

        if not packages:
            await callback.answer(
                get_text("admin_packages_list_empty", lang), show_alert=True
            )
            return

        builder = InlineKeyboardBuilder()
        for package in packages:
            builder.row(
                InlineKeyboardButton(
                    text=f"✏️ {package.name} ({package.minutes_count} мин)",
                    callback_data=f"pkg_edit_select:{package.id}",
                )
            )

        builder.row(
            InlineKeyboardButton(
                text=get_text("kb_back_to_settings_menu", lang),
                callback_data="admin_settings:manage_packages",
            )
        )

        await callback.message.edit_text(
            text=get_text("admin_packages_edit", lang), reply_markup=builder.as_markup()
        )
    await callback.answer()


@router.callback_query(F.data.startswith("pkg_edit_select:"), AdminFilter())
async def admin_packages_edit_select_callback(
    callback: CallbackQuery, state: FSMContext
):
    package_id = int(callback.data.split(":")[1])
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        package = await get_package_by_id(db, package_id)

        if not package:
            await callback.answer(get_text("package_not_found", lang), show_alert=True)
            return

        await state.update_data(editing_package_id=package_id)
        await state.update_data(prompt_message_id=callback.message.message_id)

        prompt_text = get_text("admin_package_enter_new_name", lang).format(
            current_name=package.name
        )
        await callback.message.edit_text(
            prompt_text, reply_markup=get_cancel_keyboard(lang)
        )
        await state.set_state(AdminEditPackageStates.waiting_for_new_package_name)
    await callback.answer()


@router.message(AdminEditPackageStates.waiting_for_new_package_name, AdminFilter())
async def process_package_new_name(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_text_input(
            message.text, lang, min_length=1, max_length=100
        )

        if not validation_result.is_valid:
            await message.reply(validation_result.error_message)
            return

        await state.update_data(new_package_name=validation_result.value)
        await message.delete()

        data = await state.get_data()
        prompt_message_id = data.get("prompt_message_id")
        if prompt_message_id:
            prompt_text = get_text("admin_package_enter_new_minutes", lang).format(
                new_name=validation_result.value
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=prompt_text,
                reply_markup=get_cancel_keyboard(lang),
            )
    await state.set_state(AdminEditPackageStates.waiting_for_new_package_minutes)


@router.message(AdminEditPackageStates.waiting_for_new_package_minutes, AdminFilter())
async def process_package_new_minutes(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_integer_input(
            message.text, lang, min_value=1, max_value=10000
        )

        if not validation_result.is_valid:
            await message.reply(
                validation_result.error_message
                or get_text("admin_minutes_invalid_format", lang)
            )
            return

        await state.update_data(new_minutes_count=validation_result.value)
        await message.delete()

        data = await state.get_data()
        new_name = data.get("new_package_name")
        prompt_message_id = data.get("prompt_message_id")
        if prompt_message_id:
            prompt_text = get_text("admin_package_enter_new_discount", lang).format(
                new_name=new_name
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=prompt_text,
                reply_markup=get_cancel_keyboard(lang),
            )
    await state.set_state(AdminEditPackageStates.waiting_for_new_package_discount)


@router.message(AdminEditPackageStates.waiting_for_new_package_discount, AdminFilter())
async def process_package_new_discount(message: Message, state: FSMContext):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, message.from_user.id)
        validation_result = InputValidator.validate_percentage_input(message.text, lang)

        if not validation_result.is_valid:
            await message.reply(
                validation_result.error_message
                or get_text("admin_minutes_invalid_format", lang)
            )
            return

        await state.update_data(new_discount=validation_result.value)
        await message.delete()

        data = await state.get_data()
        new_name = data.get("new_package_name")
        new_minutes = data.get("new_minutes_count")
        new_discount = data.get("new_discount")
        prompt_message_id = data.get("prompt_message_id")

        cost_per_minute_str = await get_setting(db, "cost_per_minute")
        cost_per_minute = float(cost_per_minute_str)
        calculated_price = cost_per_minute * new_minutes * (1 - new_discount / 100)
        calculated_price = round(calculated_price, 2)

        await state.update_data(new_calculated_price=calculated_price)

        if prompt_message_id:
            confirmation_text = get_text("admin_package_confirm_edit", lang).format(
                name=new_name,
                minutes=new_minutes,
                discount=int(new_discount),
                price=calculated_price,
            )
            keyboard = InlineKeyboardBuilder()
            keyboard.row(
                InlineKeyboardButton(
                    text=get_text("yes", lang),
                    callback_data="admin_packages:edit_confirm",
                ),
                InlineKeyboardButton(
                    text=get_text("no", lang),
                    callback_data="admin_packages:edit_cancel",
                ),
            )
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=prompt_message_id,
                text=confirmation_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML",
            )
    await state.set_state(AdminEditPackageStates.waiting_for_package_edit_confirmation)


@router.callback_query(
    F.data == "admin_packages:edit_confirm",
    AdminFilter(),
    AdminEditPackageStates.waiting_for_package_edit_confirmation,
)
async def admin_packages_edit_confirm_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        data = await state.get_data()
        editing_package_id = data.get("editing_package_id")
        new_name = data.get("new_package_name")
        new_minutes = data.get("new_minutes_count")
        new_discount = data.get("new_discount")
        new_calculated_price = data.get("new_calculated_price")
        prompt_message_id = data.get("prompt_message_id")

        package = await get_package_by_id(db, editing_package_id)
        if package:
            package.name = new_name
            package.minutes_count = new_minutes
            package.discount = new_discount
            package.price = new_calculated_price
            await db.commit()

        await state.clear()
        await callback.answer(
            get_text("admin_package_updated_successfully", lang).format(
                package_name=new_name
            )
        )

        if prompt_message_id:
            await show_admin_settings_page(callback, callback.from_user.id)


@router.callback_query(
    F.data == "admin_packages:edit_cancel",
    AdminFilter(),
    AdminEditPackageStates.waiting_for_package_edit_confirmation,
)
async def admin_packages_edit_cancel_callback(
    callback: CallbackQuery, state: FSMContext
):
    async with get_async_db() as db:
        lang = await get_user_language_from_db(db, callback.from_user.id)
        await state.clear()
        await callback.answer(get_text("admin_package_edit_cancelled", lang))
    await show_admin_settings_page(callback, callback.from_user.id)