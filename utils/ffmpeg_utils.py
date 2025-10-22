import os
import platform


def get_ffmpeg_path():
    # Получение пути к исполняемому файлу FFmpeg в зависимости от операционной системы
    system = platform.system().lower()
    
    if system == "windows":
        ffmpeg_path = os.path.join("bin", "windows", "ffmpeg", "bin", "ffmpeg.exe")
    else:  # linux или другие Unix-системы
        ffmpeg_path = os.path.join("bin", "linux", "ffmpeg", "bin", "ffmpeg")
    
    # Если файл существует, возвращаем его абсолютный путь
    if os.path.exists(ffmpeg_path):
        return os.path.abspath(ffmpeg_path)
    else:
        # Если локальный файл не найден, возвращаем просто имя исполняемого файла
        # и надеемся, что он доступен в PATH
        return "ffmpeg"


def get_ffprobe_path():
    # Получение пути к исполняемому файлу ffprobe в зависимости от операционной системы
    system = platform.system().lower()
    
    if system == "windows":
        ffprobe_path = os.path.join("bin", "windows", "ffmpeg", "bin", "ffprobe.exe")
    else:  # linux или другие Unix-системы
        ffprobe_path = os.path.join("bin", "linux", "ffmpeg", "bin", "ffprobe")
    
    # Если файл существует, возвращаем его абсолютный путь
    if os.path.exists(ffprobe_path):
        return os.path.abspath(ffprobe_path)
    else:
        # Если локальный файл не найден, возвращаем просто имя исполняемого файла
        # и надеемся, что он доступен в PATH
        return "ffprobe"