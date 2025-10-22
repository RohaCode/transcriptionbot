import os
import aiohttp
import json
import logging
from typing import Optional, Tuple
from aiogram import Bot
from aiogram.types import Message, BufferedInputFile
import asyncio
import io
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from database.crud import get_setting
from utils.error_handler import log_exceptions
from database.database import get_async_db
from keyboards.main_menu import get_main_keyboard
from utils.language import get_text

# Получаем логгер
logger = logging.getLogger(__name__)


async def _notify_admins(bot: Bot, message_key: str, language: str = "ru", **kwargs):
    """Sends a message to all configured admin IDs."""
    admin_message = get_text(message_key, language).format(**kwargs)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(chat_id=admin_id, text=admin_message)
        except Exception as e:
            logger.error(f"Failed to send admin notification to {admin_id}: {e}")


@log_exceptions
async def transcribe_audio_file_with_progress(
    db: AsyncSession,
    file_path: str,
    language: str = "ru",
    bot: Bot = None,
    progress_message: Message = None,
    original_filename: str = "audio.wav",
    target_format: str = "text",
) -> Tuple[Optional[str], Optional[str]]:
    # Отправка аудиофайла на транскрипцию через Speechmatics API с отображением прогресса.
    # Возвращает кортеж: (текст транскрипции, сообщение об ошибке) или (None, сообщение об ошибке).
    try:
        api_key = await get_setting(db, "api_key")
        if not api_key:
            error_msg = get_text("transcription_error", language)
            logger.error(error_msg)
            return None, error_msg

        headers = {"Authorization": f"Bearer {api_key}"}
        config = {
            "type": "transcription",
            "transcription_config": {"language": language},
        }

        # Асинхронная отправка файла на транскрипцию
        async with aiohttp.ClientSession() as session:
            with open(file_path, "rb") as audio_file:
                data = aiohttp.FormData()
                data.add_field(
                    "data_file",
                    audio_file,
                    filename=os.path.basename(file_path),
                    content_type="audio/wav",
                )
                data.add_field(
                    "config", json.dumps(config), content_type="application/json"
                )

                async with session.post(
                    settings.speechmatics_api_url, headers=headers, data=data
                ) as response:
                    response_status = response.status
                    response_text = await response.text()

                    logger.info(f"Speechmatics POST response status: {response_status}")
                    if response_status in [401, 403, 429, 500]:
                        admin_message_key = "admin_api_key_invalid" if response_status in [401, 403] else (
                            "admin_rate_limited_notification" if response_status == 429 else "admin_internal_server_error_notification"
                        )
                        user_message_key = "user_transcription_failed_generic" if response_status in [401, 403] else (
                            "user_rate_limited_generic" if response_status == 429 else "user_internal_server_error_generic"
                        )
                        await _notify_admins(bot, admin_message_key, language)
                        user_error_msg = get_text(user_message_key, language)
                        logger.error(f"Speechmatics API error ({response_status}). Admin notified. User: {progress_message.from_user.id}")
                        return None, user_error_msg
                    elif response_status not in [200, 201]:
                        error_msg = f"Ошибка при отправке файла на транскрипцию: {response_status}, {response_text}"
                        logger.error(error_msg)
                        return None, error_msg

                    response_json = await response.json()
                    job_id = response_json.get("id")
                    if not job_id:
                        error_msg = (
                            "Не удалось получить ID задачи из ответа Speechmatics."
                        )
                        logger.error(error_msg)
                        return None, error_msg

        logger.info(f"Transcription job created with ID: {job_id}")

        plain_text, error_msg = await wait_for_transcription_with_progress(
            db, job_id, api_key, bot, progress_message, original_filename, language
        )

        return plain_text, error_msg

    except aiohttp.ClientError as e:
        error_msg = f"Ошибка сети при транскрипции аудио: {e}"
        logger.exception(error_msg)
        return None, error_msg
    except json.JSONDecodeError as e:
        error_msg = f"Ошибка при обработке JSON-ответа от Speechmatics: {e}"
        logger.exception(error_msg)
        return None, error_msg
    except Exception as e:
        error_msg = f"Неизвестная ошибка при транскрипции аудио: {e}"
        logger.exception(error_msg)
        return None, error_msg
    finally:
        pass


@log_exceptions
async def wait_for_transcription_with_progress(
    db: AsyncSession,
    job_id: str,
    api_key: str,
    bot: Bot,
    progress_message: Message,
    original_filename: str,
    language: str = "ru",
) -> Tuple[Optional[str], Optional[str]]:
    # Ожидание завершения транскрипции с обновлением прогресса.
    # Возвращает кортеж: (текст транскрипции, сообщение об ошибке) или (None, сообщение об ошибке).
    try:
        headers = {"Authorization": f"Bearer {api_key}"}
        result_url = f"{settings.speechmatics_api_url.rstrip('/')}/{job_id}/transcript"

        max_wait_time = settings.speechmatics_max_wait_time_seconds
        wait_interval = 5
        elapsed_time = 0

        async with aiohttp.ClientSession() as session:
            while elapsed_time < max_wait_time:
                try:
                    async with session.get(result_url, headers=headers) as response:
                        response_status = response.status
                        response_text = await response.text()

                        if response_status == 200:
                            logger.info(
                                f"Speechmatics GET response status for job {job_id}: 200 - Transcription ready."
                            )
                            result_data = await response.json()

                            plain_text = " ".join(
                                item.get("alternatives", [{}])[0].get("content", "")
                                for item in result_data.get("results", [])
                            ).strip()

                            if not plain_text:
                                if bot and progress_message:
                                    from utils.language import get_user_language_from_db
                                    lang = await get_user_language_from_db(db, progress_message.from_user.id)
                                    no_text_message = get_text("transcription_no_text_found", lang)
                                    main_keyboard = get_main_keyboard(lang) # Get keyboard here

                                    try:
                                        await bot.delete_message( # Delete the progress message
                                            chat_id=progress_message.chat.id,
                                            message_id=progress_message.message_id,
                                        )
                                    except Exception as e:
                                        logger.warning(f"Не удалось удалить сообщение о прогрессе: {e}")

                                    await bot.send_message( # Send new message with error and keyboard
                                        chat_id=progress_message.chat.id,
                                        text=no_text_message,
                                        reply_markup=main_keyboard,
                                    )
                                logger.warning(f"No text found in transcription for job {job_id}. User: {progress_message.from_user.id}")
                                return None, None # Return None for error_message to indicate user message was sent

                            if bot and progress_message:
                                from utils.language import (
                                    get_text,
                                    get_user_language_from_db,
                                )

                                lang = await get_user_language_from_db(
                                    db, progress_message.from_user.id
                                )
                                success_text = get_text("transcription_complete", lang)
                                main_keyboard = get_main_keyboard(lang)

                                # Создаем текстовый файл в памяти
                                file_content = plain_text or " "
                                file_name = f"{os.path.splitext(original_filename)[0]}_result.txt"

                                buffered_file = io.BytesIO(file_content.encode("utf-8"))
                                text_file = BufferedInputFile(
                                    buffered_file.read(), filename=file_name
                                )

                                # Пытаемся удалить сообщение "Обработка..."
                                try:
                                    await bot.delete_message(
                                        chat_id=progress_message.chat.id,
                                        message_id=progress_message.message_id,
                                    )
                                except Exception as e:
                                    logger.warning(
                                        f"Не удалось удалить сообщение о прогрессе: {e}"
                                    )

                                # Отправляем результат в виде документа
                                await bot.send_document(
                                    chat_id=progress_message.chat.id,
                                    document=text_file,
                                    caption=success_text,
                                    reply_markup=main_keyboard,
                                )

                            return plain_text, None

                        elif response_status in [401, 403, 429, 500]:
                            admin_message_key = "admin_api_key_invalid" if response_status in [401, 403] else (
                                "admin_rate_limited_notification" if response_status == 429 else "admin_internal_server_error_notification"
                            )
                            user_message_key = "user_transcription_failed_generic" if response_status in [401, 403] else (
                                "user_rate_limited_generic" if response_status == 429 else "user_internal_server_error_generic"
                            )
                            await _notify_admins(bot, admin_message_key, language)
                            user_error_msg = get_text(user_message_key, language)
                            logger.error(f"Speechmatics API error ({response_status}) during status check. Admin notified. User: {progress_message.from_user.id}")
                            return None, user_error_msg
                        elif response_status == 404:
                            logger.info(
                                f"Transcription not ready for job {job_id}. Status: running."
                            )
                            if bot and progress_message:
                                from utils.language import (
                                    get_text,
                                    get_user_language_from_db,
                                )

                                lang = await get_user_language_from_db(
                                    db, progress_message.from_user.id
                                )
                                progress_text = get_text("transcription_progress", lang)

                                if progress_message.text != progress_text:
                                    try:
                                        await bot.edit_message_text(
                                            chat_id=progress_message.chat.id,
                                            message_id=progress_message.message_id,
                                            text=progress_text,
                                        )
                                    except Exception as e:
                                        if "message is not modified" not in str(e):
                                            logger.warning(
                                                f"Не удалось обновить сообщение о прогрессе: {e}"
                                            )

                            await asyncio.sleep(wait_interval)
                            elapsed_time += wait_interval
                            continue
                        else:
                            error_msg = f"Ошибка при получении результата: {response_status}, {response_text}"
                            logger.error(error_msg)
                            return None, error_msg

                except aiohttp.ClientError as e:
                    error_msg = f"Ошибка сети при ожидании результата транскрипции: {e}"
                    logger.exception(error_msg)
                    return None, error_msg
                except json.JSONDecodeError as e:
                    error_msg = f"Ошибка при обработке JSON-ответа от Speechmatics: {e}"
                    logger.exception(error_msg)
                    return None, error_msg
                except Exception as e:
                    error_msg = (
                        f"Неизвестная ошибка при ожидании результата транскрипции: {e}"
                    )
                    logger.exception(error_msg)
                    return None, error_msg

        error_msg = "Превышено время ожидания результата транскрипции."
        logger.error(error_msg)
        return None, error_msg

    finally:
        pass