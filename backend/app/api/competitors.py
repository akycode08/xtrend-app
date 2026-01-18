from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..core.database import get_db
from ..db.models import ProfileData
from ..services.collector import TikTokCollector
from ..services.scorer import TrendScorer # Подключаем наш мозг для оценки

router = APIRouter()

def fix_tt_url(url: str) -> str:
    if not url or not isinstance(url, str): return None
    if ".heic" in url: return url.replace(".heic", ".jpeg")
    return url

def normalize_video_data(item: dict) -> dict:
    """
    Превращает любой JSON от Apify в наш стандартный формат.
    Точно так же, как мы сделали в trends.py.
    """
    # 1. Достаем статистику отовсюду
    stats = item.get("stats") or {}
    views = item.get("views") or item.get("playCount") or stats.get("playCount") or 0
    likes = item.get("likes") or item.get("diggCount") or stats.get("diggCount") or 0
    comments = item.get("comments") or item.get("commentCount") or stats.get("commentCount") or 0
    shares = item.get("shares") or item.get("shareCount") or stats.get("shareCount") or 0
    
    # 2. Достаем дату
    uploaded_at = item.get("uploadedAt") or item.get("createTime") or 0
    
    # 3. Достаем автора/канал
    channel = item.get("channel") or item.get("authorMeta") or {}
    author_name = channel.get("username") or channel.get("name") or "unknown"
    avatar = fix_tt_url(channel.get("avatar") or channel.get("avatarThumb"))
    
    # 4. Достаем обложку
    video_obj = item.get("video") or item.get("videoMeta") or {}
    cover = fix_tt_url(video_obj.get("cover") or video_obj.get("coverUrl") or item.get("cover_url"))

    # Собираем чистый объект
    return {
        "id": str(item.get("id")),
        "title": item.get("title") or item.get("desc") or "",
        "url": item.get("postPage") or item.get("webVideoUrl") or item.get("url"),
        "cover_url": cover,
        "uploaded_at": uploaded_at,
        "views": int(views),
        "stats": {
            "playCount": int(views),
            "diggCount": int(likes),
            "commentCount": int(comments),
            "shareCount": int(shares)
        },
        "author": {
            "username": author_name,
            "avatar": avatar,
            "followers": channel.get("followers") or channel.get("fans") or 0
        }
    }

@router.get("/{username}/spy")
def spy_competitor(username: str, db: Session = Depends(get_db)):
    clean_username = username.lower().strip().replace("@", "")
    
    # 1. Пробуем найти в базе (Кэш)
    profile = db.query(ProfileData).filter(ProfileData.username == clean_username).first()
    
    # Если профиля нет или у него нет видео — запускаем парсинг
    if not profile or not profile.recent_videos_data:
        print(f"🕵️‍♂️ Spy Mode: Парсим конкурента @{clean_username}...")
        collector = TikTokCollector()
        raw_videos = collector.collect([clean_username], limit=30, mode="profile")
        
        if not raw_videos:
            raise HTTPException(status_code=404, detail=f"Competitor @{clean_username} not found")
        
        # --- НОРМАЛИЗАЦИЯ И РАСЧЕТ МЕТРИК ---
        scorer = TrendScorer()
        clean_feed = []
        total_engagement = 0
        total_views = 0
        
        for raw in raw_videos:
            vid = normalize_video_data(raw)
            
            # Считаем UTS (виральность) для каждого видео
            # (Эмулируем video_data для скорера)
            scorer_data = {
                "views": vid["views"],
                "author_followers": vid["author"]["followers"],
                "collect_count": 0, # В профиле часто нет закладок, ставим 0
                "share_count": vid["stats"]["shareCount"]
            }
            # Упрощенный UTS без истории (так как это первый проход)
            vid["uts_score"] = scorer.calculate_uts(scorer_data, history_data=None, cascade_count=1)
            
            clean_feed.append(vid)
            
            # Суммируем для Engagement Rate
            total_views += vid["views"]
            total_engagement += (vid["stats"]["diggCount"] + vid["stats"]["commentCount"] + vid["stats"]["shareCount"])

        # Расчет Engagement Rate аккаунта
        avg_er = 0.0
        if total_views > 0:
            avg_er = (total_engagement / total_views) * 100
            
        # Формируем данные канала
        first_vid = clean_feed[0]
        channel_info = {
            "nickName": first_vid["author"]["username"],
            "uniqueId": clean_username,
            "avatarThumb": first_vid["author"]["avatar"],
            "fans": first_vid["author"]["followers"],
            "videos": len(clean_feed)
        }

        # --- СОХРАНЕНИЕ В БД ---
        if not profile:
            profile = ProfileData(username=clean_username)
        
        profile.channel_data = channel_info
        profile.recent_videos_data = clean_feed
        profile.total_videos = len(clean_feed)
        profile.avg_views = total_views / len(clean_feed) if clean_feed else 0
        profile.engagement_rate = round(avg_er, 2) # Заполняем новую колонку!
        
        db.add(profile)
        db.commit()
        db.refresh(profile)
    
    else:
        print(f"💾 Spy Mode: Отдаем из базы @{clean_username}")
        # Если данные из базы, они уже нормализованы при сохранении
        clean_feed = profile.recent_videos_data

    # 2. Сортировка для выдачи
    # Топ-3 по просмотрам
    top_videos = sorted(clean_feed, key=lambda x: x.get("views", 0), reverse=True)[:3]
    # Лента по новизне
    latest_videos = sorted(clean_feed, key=lambda x: x.get("uploaded_at", 0), reverse=True)

    return {
        "username": clean_username,
        "channel_data": profile.channel_data,
        "top_3_hits": top_videos,
        "latest_feed": latest_videos,
        "metrics": {
            "engagement_rate": profile.engagement_rate,
            "avg_views": int(profile.avg_views)
        }
    }