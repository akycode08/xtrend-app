# backend/app/core/database.py
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

# 1. Создаем движок (Engine)
# Используем URL из настроек.
# Добавляем connect_args для стабильности (опционально)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Проверяет соединение перед запросом
    echo=False           # Ставь True, если хочешь видеть SQL запросы в консоли
)

# 2. Создаем фабрику сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Базовый класс для моделей
Base = declarative_base()

# 4. Dependency (функция, которую будем использовать в API)
def get_db():
    db = SessionLocal()
    try:
        # Активируем расширение vector для работы с эмбеддингами
        db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        db.commit()
        yield db
    finally:
        db.close()