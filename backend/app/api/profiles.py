# backend/app/api/profiles.py
from fastapi import APIRouter, HTTPException
from ..services.collector import TikTokCollector
from ..services.scorer import TrendScorer

router = APIRouter()
scorer = TrendScorer()

def get_universal_val(item: dict, keys: list, default=0):
    """Извлекает значения из разных форматов ответа TikTok (stats или корень)."""
    stats = item.get("stats") or {}
    for k in keys:
        val = item.get(k) or stats.get(k)
        if val is not None:
            try: return int(val)
            except: return val
    return default

def get_universal_cover(item: dict) -> str:
    """Обеспечивает корректный формат обложек видео и аватаров."""
    v = item.get("video") or item.get("videoMeta") or {}
    cover = (
        v.get("coverUrl") or v.get("cover") or v.get("origin_cover") or 
        item.get("coverUrl") or item.get("cover") or v.get("thumbnail") or ""
    )
    # Заменяем формат heic на jpeg для совместимости с браузерами
    return cover.replace(".heic", ".jpeg") if ".heic" in cover else cover

@router.get("/{username}")
async def get_unified_profile_report(username: str):
    """
    Проводит глубокий аудит профиля в реальном времени.
    ДАННЫЕ НЕ СОХРАНЯЮТСЯ В БД (100% Live) для экономии места.
    """
    clean_username = username.lower().strip().replace("@", "")
    collector = TikTokCollector()
    
    # 1. Запрос свежих данных из TikTok (последние 30 видео)
    raw_videos = collector.collect([clean_username], limit=30, mode="profile")
    
    if not raw_videos:
        raise HTTPException(status_code=404, detail="Профиль не найден или закрыт")

    # 2. Получение данных об авторе из первого видео
    first_item = raw_videos[0]
    channel = first_item.get("channel") or first_item.get("authorMeta") or {}
    followers = int(get_universal_val(first_item, ["followers", "fans", "followerCount"], default=1))
    
    full_feed = []
    for v in raw_videos:
        views = get_universal_val(v, ["playCount", "views"])
        likes = get_universal_val(v, ["diggCount", "likes"])
        bookmarks = get_universal_val(v, ["collectCount", "bookmarks"])
        shares = get_universal_val(v, ["shareCount", "shares"])
        
        # Расчет UTS как "снимка" (насколько видео успешно относительно подписчиков сейчас)
        uts = scorer.calculate_uts(
            {"views": views, "author_followers": followers, "collect_count": bookmarks, "share_count": shares}
        )
        
        full_feed.append({
            "id": v.get("id"),
            "url": v.get("postPage") or v.get("webVideoUrl") or v.get("url"),
            "title": v.get("title") or v.get("desc") or "Без описания",
            "cover_url": get_universal_cover(v),
            "views": views,
            "uts_score": uts,
            "stats": {"likes": likes, "comments": 0, "shares": shares, "bookmarks": bookmarks},
            "uploaded_at": v.get("uploadedAt") or v.get("createTime") or 0
        })

    # 3. Расчет общих метрик эффективности аккаунта
    total_views = sum(v["views"] for v in full_feed)
    total_eng = sum(v["stats"]["likes"] + v["stats"]["bookmarks"] + v["stats"]["shares"] for v in full_feed)
    
    # Engagement Rate (ER)
    er = round((total_eng / (total_views + 1) * 100), 2)
    
    # Анализ виральности и стабильности через скорер
    efficiency = scorer.analyze_profile_efficiency(full_feed)

    # 4. Формирование финального отчета для фронтенда
    return {
        "author": {
            "username": clean_username,
            "nickname": channel.get("name") or channel.get("nickName") or clean_username,
            "avatar": get_universal_cover({"video": {"cover": channel.get("avatar") or channel.get("avatarThumb")}}),
            "followers": followers
        },
        "metrics": {
            "avg_views": int(total_views / len(full_feed)) if full_feed else 0,
            "engagement_rate": er,
            "efficiency_score": efficiency.get("efficiency_score", 0),
            "status": efficiency.get("status", "Stable"),
            "avg_viral_lift": efficiency.get("avg_viral_lift", 0)
        },
        "top_3_hits": sorted(full_feed, key=lambda x: x["views"], reverse=True)[:3],
        "full_feed": sorted(full_feed, key=lambda x: x["uploaded_at"], reverse=True)
    }