# backend/app/core/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "TrendScout V2 API"
    VERSION: str = "2.0.0"
    
    # База данных
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/trendscout_db")
    
    # Ключи API
    APIFY_API_TOKEN: str = os.getenv("APIFY_API_TOKEN", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # === ДОБАВИЛИ ЭТИ СТРОКИ, ЧТОБЫ ИСПРАВИТЬ ОШИБКУ ===
    SECRET_KEY: str = "supersecretkey123"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # ===================================================

    # Настройки CORS
    BACKEND_CORS_ORIGINS: list = ["http://localhost:3000", "http://127.0.0.1:3000"]

    class Config:
        case_sensitive = True
        env_file = ".env"
        # Добавляем, чтобы он не ругался на лишние переменные в .env
        extra = "ignore" 

settings = Settings()