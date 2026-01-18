# backend/app/api/trends.py
import time
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, delete # ✅ Добавлена функция удаления
from typing import List, Optional
from pydantic import BaseModel, Field

from ..core.database import get_db
from ..db.models import Trend
from ..services.collector import TikTokCollector
from ..services.scorer import TrendScorer
from ..services.ai import get_image_embedding
from ..services.clustering import cluster_trends_by_visuals 

# ИМПОРТ ПЛАНИРОВЩИКА
from ..services.scheduler import scheduler, rescan_videos_task

router = APIRouter()

class SearchRequest(BaseModel):
    target: Optional[str] = None         # Основной ввод (ключ или @username)
    keywords: Optional[List[str]] = []   # Для обратной совместимости
    mode: str = "keywords"               # "keywords" или "username"
    business_desc: Optional[str] = ""
    is_deep: Optional[bool] = False
    time_window: Optional[str] = None
    rescan_hours: int = Field(default=24, ge=1)

def trend_to_dict(trend: Trend) -> dict:
    return {
        "id": trend.id,
        "platform_id": trend.platform_id,
        "url": trend.url,
        "cover_url": trend.cover_url,
        "description": trend.description,
        "author_username": trend.author_username,
        "stats": trend.stats,
        "initial_stats": trend.initial_stats, 
        "uts_score": trend.uts_score,
        "cluster_id": trend.cluster_id,       
        "music_id": trend.music_id,
        "music_title": trend.music_title,
        "last_scanned_at": trend.last_scanned_at
    }

# --- ✅ ЭНДПОИНТ «ПРОЧИТАЛ И УДАЛИЛ» ---
@router.get("/results")
def get_saved_results(keyword: str, mode: str = "keywords", db: Session = Depends(get_db)):
    """
    Бесплатный поиск по базе данных. 
    Если данные уже прошли рескан (Точка Б), они удаляются сразу после выдачи.
    """
    print(f"📂 DB Buffer Read: ищем '{keyword}' в режиме '{mode}'")
    clean_nick = keyword.lower().strip().replace("@", "")
    
    if mode == "username":
        # СТРОГО: ищем видео, где этот юзер является автором
        query = db.query(Trend).filter(Trend.author_username.ilike(clean_nick))
    else:
        # ОБЫЧНЫЙ ПОИСК: по ключевым словам в разных полях
        search_term = f"%{keyword}%"
        query = db.query(Trend).filter(
            or_(Trend.description.ilike(search_term), Trend.vertical.ilike(search_term))
        )
    
    results = query.order_by(Trend.uts_score.desc()).all()
    data_to_return = [trend_to_dict(t) for t in results]

    # ✅ САМООЧИСТКА: Удаляем записи, если сверка уже завершена (есть дата последнего скана)
    ids_to_clean = [t.id for t in results if t.last_scanned_at is not None]
    
    if ids_to_clean:
        db.execute(delete(Trend).where(Trend.id.in_(ids_to_clean)))
        db.commit()
        print(f"🧹 БД Очищена: Удалено {len(ids_to_clean)} временных записей после выдачи.")

    return {"status": "ok", "items": data_to_return}

@router.post("/search")
def search_trends(req: SearchRequest, db: Session = Depends(get_db)):
    """Deep Scan + Auto Rescan Scheduler (Point A Setup)"""
    search_targets = [req.target] if req.target else req.keywords
    if not search_targets or not search_targets[0]:
        return {"status": "error", "message": "No query provided"}

    print(f"🔎 API Search [{req.mode}]: {search_targets} (Deep: {req.is_deep})")
    
    collector = TikTokCollector()
    
    # 1. ВСЕГДА ПЕРВЫМ ДЕЛОМ LIVE ПАРСИНГ
    if req.mode == "username":
        limit = 20
        raw_items = collector.collect(search_targets, limit=limit, mode="profile", is_deep=True)
    else:
        limit = 50 if req.is_deep else 20
        raw_items = collector.collect(search_targets, limit=limit, mode="search", is_deep=req.is_deep)
    
    if not raw_items:
        return {"status": "empty", "items": []}

    # 2. ПРЕДВАРИТЕЛЬНАЯ ФИЛЬТРАЦИЯ
    clean_items = []
    if req.mode == "username":
        clean_items = raw_items # Для юзера берем всё без исключений
    else:
        # Для ключевых слов оставляем популярные
        for item in raw_items:
            v_count = int(item.get("views") or (item.get("stats") or {}).get("playCount") or 0)
            if v_count >= 5000: clean_items.append(item)

    # --- ✅ РЕЖИМ 1: ТРЕНДЫ (РАБОТАЕМ БЕЗ БАЗЫ ДАННЫХ) ---
    if not req.is_deep:
        live_results = []
        for item in clean_items:
            v_meta = item.get("video") or item.get("videoMeta") or {}
            live_results.append({
                "url": item.get("postPage") or item.get("url") or item.get("webVideoUrl"),
                "cover_url": (v_meta.get("coverUrl") or item.get("coverUrl") or "").replace(".heic", ".jpeg"),
                "description": item.get("title") or item.get("desc") or "No desc",
                "author_username": (item.get("channel") or item.get("authorMeta") or {}).get("username") or "unknown",
                "stats": {"playCount": int(item.get("views") or (item.get("stats") or {}).get("playCount") or 0)},
                "uts_score": 0
            })
        return {"status": "ok", "items": live_results}

    # --- ✅ РЕЖИМ 2: DEEP SCAN (ИСПОЛЬЗУЕМ ВРЕМЕННЫЙ БУФЕР БД) ---
    scorer = TrendScorer()
    processed_trends_objects = [] 
    cascade_total = len(clean_items)

    for item in clean_items:
        p_id = str(item.get("id"))
        video_url = item.get("postPage") or item.get("url") or item.get("webVideoUrl")
        views_now = int(item.get("views") or (item.get("stats") or {}).get("playCount") or 0)
        current_stats = {"playCount": views_now}

        existing_video = db.query(Trend).filter(or_(Trend.platform_id == p_id, Trend.url == video_url)).first()

        try:
            if existing_video:
                # ✅ Сброс Точки А при новом сканировании (храним временно для сверки)
                existing_video.initial_stats = current_stats 
                existing_video.stats = current_stats
                existing_video.last_scanned_at = None # Обнуляем, чтобы рескан поставил новую метку
                db.add(existing_video)
                processed_trends_objects.append(existing_video)
            else:
                # Создаем новую запись «буфера»
                new_trend = Trend(
                    platform_id=p_id, url=video_url, 
                    cover_url=(item.get("video", {}).get("coverUrl") or "").replace(".heic", ".jpeg"),
                    description=item.get("title") or "No desc",
                    stats=current_stats, initial_stats=current_stats,
                    author_username=(item.get("channel") or {}).get("username") or "unknown",
                    uts_score=0, vertical=search_targets[0] or "deep_scan",
                    last_scanned_at=None
                )
                db.add(new_trend)
                processed_trends_objects.append(new_trend)
            db.commit()
        except: db.rollback()

    # 3. КЛАСТЕРИЗАЦИЯ (Только для Deep Scan)
    if req.is_deep and processed_trends_objects:
        processed_trends_objects = cluster_trends_by_visuals(processed_trends_objects)
        for t in processed_trends_objects: db.add(t)
        try: db.commit()
        except: db.rollback()

    # 4. ПЛАНИРОВАНИЕ СВЕРКИ (2 МИНУТЫ ТЕСТ)
    if req.is_deep and processed_trends_objects:
        saved_urls = [t.url for t in processed_trends_objects if t.url]
        if saved_urls:
            run_date = datetime.now() + timedelta(minutes=2) 
            scheduler.add_job(
                rescan_videos_task, 'date', run_date=run_date, 
                args=[saved_urls, f"batch_{int(time.time())}"]
            )
            print(f"⏱️ ЗАДАЧА СВЕРКИ ОТПРАВЛЕНА: Запуск через 2 минуты.")

    return {"status": "ok", "items": [trend_to_dict(t) for t in processed_trends_objects]}