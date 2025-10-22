import subprocess
import sys


def install_requirements():
    # Установка зависимостей из requirements.txt
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Зависимости успешно установлены")
    except subprocess.CalledProcessError:
        print("Ошибка при установке зависимостей")
        sys.exit(1)


if __name__ == "__main__":
    install_requirements()