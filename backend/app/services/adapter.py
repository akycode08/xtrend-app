# backend/app/services/adapter.py

def adapt_apidojo_to_standard(item: dict) -> dict:
    """
    Универсальный адаптер для данных Apify (Apidojo scraper).
    Превращает сырой JSON в чистую структуру для TrendScout.
    """
    try:
        # --- ВАРИАНТ 0: ПЛОСКИЙ ФОРМАТ (Flattened JSON) ---
        if "video.cover" in item or "channel.username" in item:
            stats = {
                "playCount": item.get("views", 0),
                "diggCount": item.get("likes", 0),
                "commentCount": item.get("comments", 0),
                "shareCount": item.get("shares", 0)
            }
            cover_url = item.get("video.cover") or item.get("video.thumbnail")
            
            return {
                "id": item.get("id"),
                "webVideoUrl": item.get("postPage") or item.get("video.url"),
                "text": item.get("title", ""),
                "createTime": item.get("uploadedAt", 0),
                "authorMeta": {
                    "id": item.get("channel.id"),
                    "name": item.get("channel.username"),
                    "nickName": item.get("channel.name"),
                    "fans": item.get("channel.followers", 0),
                    "avatar": item.get("channel.avatar")
                },
                "videoMeta": {
                    "coverUrl": cover_url,
                    "duration": item.get("video.duration", 0),
                    "downloadAddr": item.get("video.url")
                },
                "stats": stats,
                "playCount": stats["playCount"],
                "diggCount": stats["diggCount"]
            }

        # --- ВАРИАНТ 1: ВЛОЖЕННЫЕ СЛОВАРИ (Стандартный Apidojo) ---
        elif "channel" in item and isinstance(item["channel"], dict):
            channel = item.get("channel", {})
            video_data = item.get("video", {})
            stats = {
                "playCount": item.get("views", 0),
                "diggCount": item.get("likes", 0),
                "commentCount": item.get("comments", 0),
                "shareCount": item.get("shares", 0)
            }
            return {
                "id": item.get("id"),
                "webVideoUrl": item.get("postPage") or video_data.get("url"),
                "text": item.get("title", ""),
                "createTime": item.get("uploadedAt", 0),
                "authorMeta": {
                    "id": channel.get("id"),
                    "name": channel.get("username"),
                    "nickName": channel.get("name"),
                    "fans": channel.get("followers", 0),
                    "avatar": channel.get("avatar")
                },
                "videoMeta": {
                    "coverUrl": video_data.get("cover") or video_data.get("thumbnail"),
                    "duration": video_data.get("duration", 0),
                    "downloadAddr": video_data.get("url")
                },
                "stats": stats,
                "playCount": stats["playCount"],
                "diggCount": stats["diggCount"]
            }
            
        # --- FALLBACK: Если формат не распознан, возвращаем None ---
        return None

    except Exception as e:
        print(f"⚠️ Ошибка адаптации элемента: {e}")
        return None