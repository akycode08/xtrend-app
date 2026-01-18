# backend/app/services/filter.py
from datetime import datetime, timedelta
from typing import List

class ViralContentFilter:
    def __init__(self, is_profile_mode: bool = False):
        self.is_profile_mode = is_profile_mode 
        # Настройки порогов (для поиска трендов)
        self.min_views_fresh = 1000       # < 48 часов
        self.min_likes_recent = 1000      # < 60 дней
        self.min_views_timeless = 100000  # Старое, но легендарное
        
    def filter_content(self, raw_items: List[dict]) -> List[dict]:
        """Оставляет только виральный контент или всё подряд (если это аудит профиля)"""
        filtered = []
        now = datetime.utcnow() # Используем UTC для единообразия

        for item in raw_items:
            # Техническая проверка
            if not item.get("webVideoUrl"):
                continue

            # Если анализируем профиль/конкурента — берем ВСЁ (нам нужна история)
            if self.is_profile_mode:
                filtered.append(item)
                continue

            # --- ЛОГИКА ДЛЯ ПОИСКА ТРЕНДОВ ---
            views = item.get("stats", {}).get("playCount", 0)
            likes = item.get("stats", {}).get("diggCount", 0)
            create_time = item.get("createTime", 0)
            
            try:
                created_at = datetime.fromtimestamp(create_time)
                age = now - created_at
            except:
                age = timedelta(days=365)

            is_viral = False
            
            # 1. Свежий взлет (до 48ч)
            if age <= timedelta(hours=48):
                if views >= self.min_views_fresh: is_viral = True
            
            # 2. Уверенный тренд (до 60 дней)
            elif age <= timedelta(days=60):
                if likes >= self.min_likes_recent: is_viral = True
                    
            # 3. Классика
            else:
                if views >= self.min_views_timeless: is_viral = True

            if is_viral:
                filtered.append(item)

        return filtered