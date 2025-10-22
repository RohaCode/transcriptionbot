import os
import subprocess
import tempfile
import asyncio
import logging
from typing import Optional, Tuple

from utils.ffmpeg_utils import get_ffmpeg_path, get_ffprobe_path

logger = logging.getLogger(__name__)






async def get_audio_duration_async(input_file_path: str) -> float:
    # Асинхронное получение длительности аудио/видео файла с оптимизацией использования памяти
    try:
        process = await asyncio.create_subprocess_exec(
            get_ffprobe_path(),
            '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', input_file_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL  # Не загружаем stderr в память, так как он не используется
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            result = stdout.decode().strip()
            if result and result != 'N/A':
                return float(result)
            else:
                logger.warning(f"Не удалось получить длительность файла {file_path}: результат не определен")
                return 0.0
        else:
            logger.error(f"FFprobe duration error for file {file_path}")
            return 0.0
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Ошибка при определении длительности файла: {e}")
        return 0.0
    except Exception as e:
        logger.error(f"Неизвестная ошибка при определении длительности файла: {e}")
        return 0.0







# === НОВЫЕ АСИНХРОННЫЕ ФУНКЦИИ ===

async def extract_audio_from_video_async(input_file_path: str, output_file_path: str) -> Tuple[bool, Optional[str]]:
    # Асинхронное извлечение аудио из видео файла с оптимизацией использования памяти
    try:
        process = await asyncio.create_subprocess_exec(
            get_ffmpeg_path(),
            '-i', input_file_path, '-q:a', '0', '-map', 'a', output_file_path, '-y',
            stdout=asyncio.subprocess.DEVNULL,  # Не загружаем stdout в память
            stderr=asyncio.subprocess.PIPE       # Загружаем только stderr для получения ошибок
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return True, None
        else:
            error_msg = stderr.decode() if stderr else "FFmpeg extraction failed"
            logger.error(f"FFmpeg extraction error: {error_msg}")
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = f"FFmpeg не найден по пути: {get_ffmpeg_path()}."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка при извлечении аудио: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

async def convert_audio_to_wav_async(input_file_path: str, output_file_path: str) -> Tuple[bool, Optional[str]]:
    # Асинхронная конвертация аудио в WAV формат с оптимизацией использования памяти
    try:
        process = await asyncio.create_subprocess_exec(
            get_ffmpeg_path(),
            '-i', input_file_path, '-ac', '1', '-ar', '16000', output_file_path, '-y',
            stdout=asyncio.subprocess.DEVNULL,  # Не загружаем stdout в память
            stderr=asyncio.subprocess.PIPE       # Загружаем только stderr для получения ошибок
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return True, None
        else:
            error_msg = stderr.decode() if stderr else "FFmpeg conversion failed"
            logger.error(f"FFmpeg conversion error: {error_msg}")
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = f"FFmpeg не найден по пути: {get_ffmpeg_path()}."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка при конвертации аудио в WAV: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

async def process_file_for_transcription_async(file_path: str, is_video: bool) -> Tuple[Optional[str], Optional[str]]:
    # Асинхронная обработка файла для транскрипции
    temp_audio_path = None
    temp_extracted_path = None
    
    try:
        # Создаем временный файл для обработанного аудио
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
        
        if is_video:
            # Для видео сначала извлекаем аудио
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_extracted_file:
                temp_extracted_path = temp_extracted_file.name
            
            success, error_msg = await extract_audio_from_video_async(file_path, temp_extracted_path)
            if not success:
                return None, f"Не удалось извлечь аудио из видео: {error_msg}"
            
            # Затем конвертируем извлеченный аудио в нужный формат
            success, error_msg = await convert_audio_to_wav_async(temp_extracted_path, temp_audio_path)
            if not success:
                return None, f"Не удалось конвертировать аудио: {error_msg}"
            
            # Удаляем временный файл с извлеченным аудио
            await cleanup_temp_file_async(temp_extracted_path)
            temp_extracted_path = None
        else:
            # Для аудио сразу конвертируем в нужный формат
            success, error_msg = await convert_audio_to_wav_async(file_path, temp_audio_path)
            if not success:
                return None, f"Не удалось конвертировать аудио: {error_msg}"
        
        return temp_audio_path, None
        
    except Exception as e:
        logger.exception(f"Ошибка при асинхронной обработке файла: {e}")
        
        # Очищаем временные файлы в случае ошибки
        if temp_audio_path:
            await cleanup_temp_file_async(temp_audio_path)
        if temp_extracted_path:
            await cleanup_temp_file_async(temp_extracted_path)
            
        return None, f"Ошибка при обработке файла: {str(e)}"


async def process_file_for_transcription_optimized(file_path: str, is_video: bool) -> Tuple[Optional[str], Optional[str]]:
    # Оптимизированная асинхронная обработка файла для транскрипции с улучшенным использованием ресурсов
    temp_audio_path = None
    
    try:
        # Создаем временный файл для обработанного аудио
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_audio_file:
            temp_audio_path = temp_audio_file.name
        
        if is_video:
            # Для видео извлекаем аудио и конвертируем в нужный формат в одном процессе FFmpeg
            success, error_msg = await extract_and_convert_video_async(file_path, temp_audio_path)
            if not success:
                return None, f"Не удалось обработать видео: {error_msg}"
        else:
            # Для аудио сразу конвертируем в нужный формат
            success, error_msg = await convert_audio_to_wav_async(file_path, temp_audio_path)
            if not success:
                return None, f"Не удалось конвертировать аудио: {error_msg}"
        
        return temp_audio_path, None
        
    except Exception as e:
        logger.exception(f"Ошибка при оптимизированной асинхронной обработке файла: {e}")
        
        # Очищаем временный файл в случае ошибки
        if temp_audio_path:
            await cleanup_temp_file_async(temp_audio_path)
            
        return None, f"Ошибка при обработке файла: {str(e)}"


async def extract_and_convert_video_async(input_file_path: str, output_file_path: str) -> Tuple[bool, Optional[str]]:
    # Асинхронное извлечение и конвертация аудио из видео в один шаг для оптимизации
    try:
        # Объединяем извлечение аудио и конвертацию в один процесс FFmpeg для эффективности
        process = await asyncio.create_subprocess_exec(
            get_ffmpeg_path(),
            '-i', input_file_path, 
            '-ac', '1',  # моно
            '-ar', '16000',  # частота дискретизации 16kHz
            '-q:a', '0',  # лучшее качество аудио
            '-map', 'a',  # карта аудио дорожки
            output_file_path, 
            '-y',  # перезаписать выходной файл
            stdout=asyncio.subprocess.DEVNULL,  # Не загружаем stdout в память
            stderr=asyncio.subprocess.PIPE       # Загружаем только stderr для получения ошибок
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return True, None
        else:
            error_msg = stderr.decode() if stderr else "FFmpeg video processing failed"
            logger.error(f"FFmpeg video processing error: {error_msg}")
            return False, error_msg
            
    except FileNotFoundError:
        error_msg = f"FFmpeg не найден по пути: {get_ffmpeg_path()}."
        logger.error(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"Ошибка при обработке видео: {str(e)}"
        logger.error(error_msg)
        return False, error_msg

def get_file_size(file_path: str) -> int:
    # Получение размера файла в байтах
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


async def cleanup_temp_file_async(file_path: str):
    # Асинхронная очистка временных файлов
    try:
        if file_path and os.path.exists(file_path):
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, os.unlink, file_path)
    except Exception as e:
        logger.warning(f"Ошибка при удалении временного файла {file_path}: {e}")