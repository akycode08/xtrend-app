# 1. --- ВАЖНО: ГРУЗИМ ПЕРЕМЕННЫЕ СРАЗУ ---
from dotenv import load_dotenv
import os

load_dotenv()

# --- БЛОК ПРОВЕРКИ ---
print("--------------------------------------------------")
token = os.getenv("APIFY_API_TOKEN")
print(f"📂 Текущая папка запуска: {os.getcwd()}")
print(f"🔑 APIFY TOKEN: {'✅ НАЙДЕН' if token else '❌ ПУСТО (Проверь .env)'}")
print("🚀 MODE: 6-Layer Analysis + Auto-Rescan")
print("--------------------------------------------------")

# 2. --- ТЕПЕРЬ ОСТАЛЬНОЙ КОД ---
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.database import Base, engine
from .core.config import settings
# 👇 ВАЖНО: Явный импорт моделей, чтобы SQLAlchemy их увидела!
from .db import models 
from .api import trends, profiles, competitors

# 👇 НОВЫЙ ИМПОРТ: Планировщик задач
from .services.scheduler import start_scheduler

# --- 🔥 ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТАБЛИЦ ПРИ ЗАПУСКЕ 🔥 ---
print("🏗️  Force creating database tables in PostgreSQL...")
try:
    Base.metadata.create_all(bind=engine)
    print("✅  Tables created successfully!")
except Exception as e:
    print(f"❌  Error creating tables: {e}")
# --------------------------------------------------------

app = FastAPI(
    title="TrendScout AI Pro", 
    version=settings.VERSION,
    description="TikTok Trend Analysis with 6-Layer Scoring & Auto-Rescan"
)

# CORS — настроен для работы с твоим Next.js фронтендом
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем ручки (API Endpoints)
app.include_router(trends.router, prefix="/api/trends", tags=["Trends"])
app.include_router(profiles.router, prefix="/api/profiles", tags=["Profiles"])

# --- ⏰ ЗАПУСК ПЛАНИРОВЩИКА (SCHEDULER) ---
@app.on_event("startup")
async def startup_event():
    """Эта функция запускается один раз при старте сервера"""
    print("⏳ Initializing Background Scheduler...")
    start_scheduler()
    print("✅ Scheduler is running and waiting for tasks.")
# ------------------------------------------

@app.get("/")
def health_check():
    """Проверка жизнеспособности сервера и текущего режима анализа"""
    return {
        "status": "ok", 
        "version": settings.VERSION,
        "engine": "6-layer-math-v2",
        "features": ["Deep Scan", "Cluster Analysis", "Auto-Rescan"],
        "database": "PostgreSQL Connected"
    }

if __name__ == "__main__":
    import uvicorn
    # Запуск через модуль app.main для корректной работы путей
    print("🔥 Starting TrendScout Backend on http://0.0.0.0:8000")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)