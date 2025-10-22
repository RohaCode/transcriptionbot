from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import os

Base = declarative_base()


class User(Base):
    # Модель пользователя
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)  # ID пользователя в Telegram
    username = Column(String(255), nullable=True)  # Имя пользователя в Telegram
    first_name = Column(String(255), nullable=True)  # Имя
    last_name = Column(String(255), nullable=True)  # Фамилия
    language_code = Column(String(10), default='ru')  # Язык пользователя
    balance = Column(Float, default=0.0)  # Баланс минут для транскрипции
    is_active = Column(Boolean, default=True)  # Статус пользователя (активен/заблокирован)
    is_admin = Column(Boolean, default=False)  # Является ли пользователь администратором
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    transcriptions = relationship("Transcription", back_populates="user")
    payments = relationship("Payment", back_populates="user")


class Transcription(Base):
    # Модель транскрипции
    __tablename__ = "transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    file_name = Column(String(255))  # Имя оригинального файла
    file_path = Column(String(500))  # Путь к файлу
    duration = Column(Float)  # Длительность аудио/видео в секундах
    language = Column(String(10), default='ru')  # Язык транскрипции
    result_text = Column(Text)  # Результат транскрипции
    result_format = Column(String(10), default='text')  # Формат результата: text, srt, json
    cost = Column(Float)  # Стоимость транскрипции в минутах
    status = Column(String(20), default='processing')  # Статус: processing, completed, failed
    error_message = Column(String(500), nullable=True)  # Сообщение об ошибке, если была ошибка
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)  # Время завершения
    
    # Связи
    user = relationship("User", back_populates="transcriptions")


class Package(Base):
    # Модель пакета минут для транскрипции
    __tablename__ = "packages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))  # Название пакета
    minutes_count = Column(Integer)  # Количество минут в пакете
    price = Column(Float)  # Цена в рублях
    discount = Column(Float, default=0.0)  # Скидка в процентах
    is_active = Column(Boolean, default=True)  # Активен ли пакет
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Payment(Base):
    # Модель платежа
    __tablename__ = "payments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    package_id = Column(Integer, ForeignKey("packages.id"), nullable=True)  # ID пакета (если покупка пакета)
    minutes_count = Column(Integer)  # Количество минут, купленных отдельно
    amount = Column(Float)  # Сумма платежа
    currency = Column(String(3), default='RUB')  # Валюта
    payment_system = Column(String(50))  # Платежная система (tg_payments, yookassa)
    payment_id = Column(String(255), unique=True)  # ID платежа в платежной системе
    status = Column(String(20), default='pending')  # Статус: pending, success, failed, refunded
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="payments")

class Setting(Base):
    # Модель для хранения настроек ключ-значение
    __tablename__ = 'settings'

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)