# backend/app/db/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from ..core.database import Base

class Trend(Base):
    """
    Таблица найденных трендов.
    Сюда пишем всё, что нашли через поиск и Deep Scan.
    """
    __tablename__ = "trends"

    id = Column(Integer, primary_key=True, index=True)
    platform_id = Column(String, index=True)       # ID видео из TikTok
    url = Column(String, unique=True, index=True)  # Ссылка на видео
    
    # Контент
    description = Column(Text)
    cover_url = Column(String)                     # Обложка
    vertical = Column(String, index=True)          # Тема поиска (bmw, crypto...)
    
    # --- 🎵 ДОБАВЛЕНО ДЛЯ DEEP SCAN ---
    music_id = Column(String, index=True, nullable=True)    # ID звука
    music_title = Column(String, nullable=True)             # Название звука
    
    # Автор
    author_username = Column(String, index=True)
    author_followers = Column(Integer, default=0)
    
    # --- 📊 КОГОРТНЫЙ АНАЛИЗ (Time-based) ---
    # stats = Текущие данные (обновляются при каждом скане)
    stats = Column(JSONB, default={}) 
    # initial_stats = Данные ПЕРВОГО парсинга (Точка А). Не меняются.
    initial_stats = Column(JSONB, default={}) 
    # last_scanned_at = Время последнего обновления
    last_scanned_at = Column(DateTime, default=datetime.utcnow)
    
    # --- 🧠 DEEP SCAN & CLUSTERING ---
    uts_score = Column(Float, default=0.0)         # Главный балл
    # ID визуальной группы (например: 1="Черные гелики", 2="Салон авто")
    cluster_id = Column(Integer, nullable=True, index=True) 
    
    similarity_score = Column(Float, default=0.0)  # Насколько похоже на нас
    reach_score = Column(Float, default=0.0)       # Normalized Reach
    uplift_score = Column(Float, default=0.0)      # Эффективность (L3)
    
    # AI Поля
    ai_summary = Column(Text)                      # Суть тренда
    embedding = Column(Vector(512))                # Вектор CLIP
    
    created_at = Column(DateTime, default=datetime.utcnow)


class ProfileData(Base):
    """
    Таблица для аналитики профилей (Audit & Spy Mode).
    """
    __tablename__ = "profile_data"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    
    # Инфо о канале
    channel_data = Column(JSONB, default={})
    
    # Список последних видео
    recent_videos_data = Column(JSONB, default=[])
    
    # Метрики для быстрой сортировки
    total_videos = Column(Integer, default=0)
    avg_views = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0) # Добавлено для аналитики
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)