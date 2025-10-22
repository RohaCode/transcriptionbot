from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, delete
from typing import Optional
from datetime import datetime

from database.models import User, Transcription, Package, Payment, Setting

#--- Асинхронные функции для User ---

async def get_all_users(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[User]:
    result = await db.execute(
        select(User)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def count_all_users(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(User.id)))
    return result.scalar()

async def update_user_balance(db: AsyncSession, user_id: int, new_balance: float) -> Optional[User]:
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    db_user = result.scalars().first()
    if db_user:
        db_user.balance = new_balance
        db_user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_user)
    return db_user

async def update_user_is_active_status(db: AsyncSession, user_id: int, is_active: bool) -> Optional[User]:
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    db_user = result.scalars().first()
    if db_user:
        db_user.is_active = is_active
        db_user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_user)
    return db_user

async def get_user_total_transcriptions_count(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Transcription.id))
        .filter(Transcription.user_id == user_id)
    )
    return result.scalar()

async def create_user(db: AsyncSession, telegram_id: int, username: Optional[str] = None, 
                      first_name: Optional[str] = None, last_name: Optional[str] = None,
                      language_code: str = 'ru') -> User:
    existing_user = await get_user_by_telegram_id(db, telegram_id)
    if existing_user:
        return existing_user
    initial_balance = 5.0 # Возвращаем бонусные минуты
    db_user = User(
        telegram_id=telegram_id, username=username, first_name=first_name,
        last_name=last_name, language_code=language_code, balance=initial_balance,
        is_active=True, is_admin=False, created_at=datetime.utcnow()
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    result = await db.execute(
        select(User).filter(User.telegram_id == telegram_id)
    )
    return result.scalars().first()

async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    result = await db.execute(
        select(User).filter(User.id == user_id)
    )
    return result.scalars().first()

async def add_minutes_to_balance(db: AsyncSession, telegram_id: int, minutes: float) -> Optional[User]:
    db_user = await get_user_by_telegram_id(db, telegram_id)
    if db_user:
        db_user.balance += minutes
        db_user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_user)
    return db_user

async def deduct_minutes_from_balance(db: AsyncSession, telegram_id: int, minutes: float) -> Optional[User]:
    db_user = await get_user_by_telegram_id(db, telegram_id)
    if db_user and db_user.balance >= minutes:
        db_user.balance -= minutes
        db_user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_user)
        return db_user
    return None

#--- Асинхронные функции для Transcription ---

async def create_transcription(db: AsyncSession, user_id: int, file_name: str, file_path: str, duration: float, language: str, cost: float) -> Transcription:
    db_transcription = Transcription(
        user_id=user_id, file_name=file_name, file_path=file_path, duration=duration,
        language=language, cost=cost, status='processing', created_at=datetime.utcnow()
    )
    db.add(db_transcription)
    await db.commit()
    await db.refresh(db_transcription)
    return db_transcription

async def update_transcription_status_and_result(db: AsyncSession, transcription_id: int, status: str, result_text: Optional[str] = None, error_message: Optional[str] = None) -> Optional[Transcription]:
    result = await db.execute(
        select(Transcription).filter(Transcription.id == transcription_id)
    )
    db_transcription = result.scalars().first()
    if db_transcription:
        db_transcription.status = status
        if result_text:
            db_transcription.result_text = result_text
        if error_message:
            db_transcription.error_message = error_message
        db_transcription.completed_at = datetime.utcnow()
        await db.commit()
        await db.refresh(db_transcription)
    return db_transcription

async def get_transcriptions_by_user_id(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 5) -> list[Transcription]:
    result = await db.execute(
        select(Transcription)
        .filter(Transcription.user_id == user_id)
        .order_by(Transcription.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def count_transcriptions_by_user_id(db: AsyncSession, user_id: int) -> int:
    result = await db.execute(
        select(func.count(Transcription.id))
        .filter(Transcription.user_id == user_id)
    )
    return result.scalar()

async def get_transcription_by_id(db: AsyncSession, transcription_id: int) -> Optional[Transcription]:
    result = await db.execute(
        select(Transcription).filter(Transcription.id == transcription_id)
    )
    return result.scalars().first()

async def delete_transcription_by_id(db: AsyncSession, transcription_id: int) -> bool:
    result = await db.execute(
        select(Transcription).filter(Transcription.id == transcription_id)
    )
    db_transcription = result.scalars().first()
    if db_transcription:
        await db.delete(db_transcription)
        await db.commit()
        return True
    return False

async def delete_all_transcriptions_by_user_id(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(
        delete(Transcription).where(Transcription.user_id == user_id)
    )
    await db.commit()
    return result.rowcount > 0

#--- Асинхронные функции для Package ---

async def get_all_packages(db: AsyncSession) -> list[Package]:
    result = await db.execute(
        select(Package).order_by(Package.price)
    )
    return result.scalars().all()

async def get_active_packages(db: AsyncSession, skip: int = 0, limit: int = 4) -> list[Package]:
    result = await db.execute(
        select(Package)
        .filter(Package.is_active == True)
        .order_by(Package.price)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def count_active_packages(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(Package.id))
        .filter(Package.is_active == True)
    )
    return result.scalar()

async def get_package_by_id(db: AsyncSession, package_id: int) -> Optional[Package]:
    result = await db.execute(
        select(Package).filter(Package.id == package_id)
    )
    return result.scalars().first()

async def delete_package_by_id(db: AsyncSession, package_id: int) -> bool:
    result = await db.execute(
        select(Package).filter(Package.id == package_id)
    )
    package = result.scalars().first()
    if package:
        await db.delete(package)
        await db.commit()
        return True
    return False

async def create_package(db: AsyncSession, name: str, minutes_count: int, price: float, discount: float, is_active: bool = True) -> Package:
    db_package = Package(
        name=name,
        minutes_count=minutes_count,
        price=price,
        discount=discount,
        is_active=is_active
    )
    db.add(db_package)
    await db.commit()
    await db.refresh(db_package)
    return db_package

#--- Асинхронные функции для статистики ---

async def count_total_transcriptions(db: AsyncSession) -> int:
    # Считаем все транскрипции, включая мягко удаленные, для общей статистики
    result = await db.execute(select(func.count(Transcription.id)))
    return result.scalar()

async def count_total_payments(db: AsyncSession) -> int:
    result = await db.execute(select(func.count(Payment.id)))
    return result.scalar()

async def count_active_users(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(User.id))
        .filter(User.is_active == True)
    )
    return result.scalar()

async def count_blocked_users(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(User.id))
        .filter(User.is_active == False)
    )
    return result.scalar()

async def create_payment(db: AsyncSession, user_id: int, package_id: Optional[int], minutes_count: int, amount: float, currency: str, payment_system: str, payment_id: str, status: str = 'success') -> Payment:
    db_payment = Payment(
        user_id=user_id,
        package_id=package_id,
        minutes_count=minutes_count,
        amount=amount,
        currency=currency,
        payment_system=payment_system,
        payment_id=payment_id,
        status=status,
        created_at=datetime.utcnow(),
        completed_at=datetime.utcnow()
    )
    db.add(db_payment)
    await db.commit()
    await db.refresh(db_payment)
    return db_payment

async def get_total_payments_amount(db: AsyncSession) -> float:
    result = await db.execute(select(func.sum(Payment.amount)))
    total_amount = result.scalar()
    return total_amount if total_amount is not None else 0.0

#--- Асинхронные функции для Settings ---

async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    # Асинхронно получает значение настройки по ключу.
    result = await db.execute(
        select(Setting).filter(Setting.key == key)
    )
    setting = result.scalars().first()
    return setting.value if setting else None

async def update_setting(db: AsyncSession, key: str, value: str):
    # Асинхронно обновляет или создает настройку.
    result = await db.execute(
        select(Setting).filter(Setting.key == key)
    )
    setting = result.scalars().first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    await db.commit()