# backend/app/services/scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from ..core.database import SessionLocal
from ..db.models import Trend
from ..services.collector import TikTokCollector
from ..services.scorer import TrendScorer 

scheduler = AsyncIOScheduler()

async def rescan_videos_task(video_urls: list, batch_id: str):
    print(f"⏰ [AUTO-RESCAN] Начало задачи сверки (Batch: {batch_id})")
    
    db = SessionLocal()
    scorer = TrendScorer() 
    
    try:
        collector = TikTokCollector()
        # Собираем самые свежие данные (Точка Б)
        raw_items = collector.collect(video_urls, limit=len(video_urls), mode="urls")
        
        if not raw_items:
            print("⚠️ Rescan: Нет новых данных для сверки.")
            return

        for item in raw_items:
            url = item.get("postPage") or item.get("webVideoUrl") or item.get("url")
            video = db.query(Trend).filter(Trend.url == url).first()
            
            if video:
                stats = item.get("stats") or {}
                fresh_views = int(item.get("views") or stats.get("playCount") or 0)
                
                new_stats = {
                    "playCount": fresh_views,
                    "diggCount": int(item.get("likes") or stats.get("diggCount") or 0),
                    "commentCount": int(item.get("comments") or stats.get("commentCount") or 0),
                    "shareCount": int(item.get("shares") or stats.get("shareCount") or 0),
                    "collectCount": int(item.get("bookmarks") or stats.get("collectCount") or 0)
                }

                # --- ✅ СВЕРКА: Новые данные vs Временные старые данные (Point A) ---
                history_data = {
                    "play_count": video.initial_stats.get("playCount", 0) if video.initial_stats else fresh_views
                }

                # Пересчитываем балл UTS на базе динамики роста между Точкой А и Точкой Б
                video.uts_score = scorer.calculate_uts(
                    video_data={
                        "views": fresh_views,
                        "author_followers": video.author_followers,
                        "collect_count": new_stats["collectCount"],
                        "share_count": new_stats["shareCount"]
                    },
                    history_data=history_data,
                    cascade_count=1
                )
                
                video.stats = new_stats
                video.last_scanned_at = datetime.utcnow()
                
        db.commit()
        print(f"✅ [AUTO-RESCAN] Сверка завершена. Статистика и UTS-баллы обновлены.")
        
    except Exception as e:
        print(f"❌ Ошибка рескана: {e}")
        db.rollback()
    finally:
        db.close()

def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("⏳ Background Scheduler успешно запущен.")