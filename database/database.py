from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from sqlalchemy import select
import os
import logging

from config.settings import settings
from database.models import Base, Package, Setting

logger = logging.getLogger(__name__)

# Создание асинхронного движка базы данных
database_url = settings.database_url
# Для SQLite используем aiosqlite
if database_url.startswith("sqlite:///"):
    database_url = database_url.replace("sqlite:///", "sqlite+aiosqlite:///")

async_engine = create_async_engine(
    database_url,
    echo=False,  # Установите True для отладки SQL-запросов
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if database_url.startswith("sqlite+aiosqlite") else {}
)

# Создание асинхронной сессии
AsyncSessionLocal = sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

@asynccontextmanager
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session

async def seed_packages(db: AsyncSession):
    # Асинхронно заполняет базу данных начальными пакетами, если их там еще нет.
    result = await db.execute(select(Package))
    all_packages = result.scalars().all()
    count = len(all_packages)
    
    if count == 0:
        packages = [
            Package(name="Стартовый", minutes_count=10, price=100.0),
            Package(name="Базовый", minutes_count=60, price=500.0),
            Package(name="Продвинутый", minutes_count=150, price=1000.0),
            Package(name="Профи", minutes_count=300, price=2000.0),
        ]
        for package in packages:
            db.add(package)
        await db.commit()
        logger.info("База данных заполнена начальными пакетами.")

async def seed_settings(db: AsyncSession):
    # Асинхронно заполняет базу данных начальными настройками, если их там еще нет.
    settings_to_seed = {
        "max_audio_duration_minutes": "10"
    }
    
    for key, value in settings_to_seed.items():
        result = await db.execute(
            select(Setting).filter(Setting.key == key)
        )
        setting = result.scalars().first()
        
        if not setting:
            db_setting = Setting(key=key, value=value)
            db.add(db_setting)
    
    await db.commit()
    logger.info("База данных заполнена начальными настройками.")

async def init_db():
    # Асинхронная инициализация базы данных - создание всех таблиц и заполнение начальными данными.
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("База данных инициализирована")
    
    async with AsyncSessionLocal() as db:
        await seed_packages(db)
        await seed_settings(db)

async def test_db_connection():
    # Асинхронное тестирование подключения к базе данных
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(1))
        logger.info("Подключение к базе данных успешно")
        return True
    except Exception as e:
        logger.error(f"Ошибка подключения к базе данных: {e}")
        return False