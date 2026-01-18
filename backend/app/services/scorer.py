import math
import numpy as np
from datetime import datetime

class TrendScorer:
    def __init__(self):
        # Веса для Universal Transfer Score (UTS)
        self.weights = {
            "l1": 0.30,  # Viral Lift
            "l2": 0.20,  # Velocity (Growth)
            "l3": 0.20,  # Retention (Bookmarks)
            "l4": 0.15,  # Cascade (Sound Network)
            "l5": 0.10,  # Saturation
            "l7": 0.05   # Stability
        }

    def calculate_uts(self, video_data: dict, history_data: dict = None, cascade_count: int = 1) -> float:
        """
        Главная функция расчета 6 слоев анализа.
        """
        views = video_data.get('views', 1)
        followers = video_data.get('author_followers', 1)
        bookmarks = video_data.get('collect_count', 0)
        shares = video_data.get('share_count', 0)

        # L1: Viral Lift (Отношение просмотров к подписчикам)
        l1_score = min(views / (followers + 1), 10.0) / 10.0

        # L2: Velocity (Скорость роста, если есть история в БД)
        l2_score = 0.5 # Default
        if history_data:
            old_views = history_data.get('play_count', views)
            l2_score = min((views - old_views) / (old_views + 1), 1.0)

        # L3: Retention Intensity (Закладки к просмотрам)
        l3_score = min((bookmarks / (views + 1)) * 20, 1.0)

        # L4: Sound Cascade (Кол-во видео под этот звук в текущей выборке)
        l4_score = min(math.log10(cascade_count + 1) / 2, 1.0)

        # L5: Saturation (Штраф за перегрев, если видео уже много в БД)
        total_in_db = history_data.get('total_sound_usage', 0) if history_data else 0
        l5_score = max(1.0 - (total_in_db / 1000), 0.0)

        # L7: Stability (На основе вовлеченности)
        l7_score = min((shares + bookmarks) / (views + 1) * 10, 1.0)

        # Итоговый взвешенный балл
        final_score = (
            l1_score * self.weights['l1'] +
            l2_score * self.weights['l2'] +
            l3_score * self.weights['l3'] +
            l4_score * self.weights['l4'] +
            l5_score * self.weights['l5'] +
            l7_score * self.weights['l7']
        ) * 10 # Приводим к 10-балльной шкале
        
        return round(final_score, 2)

    def analyze_profile_efficiency(self, videos: list) -> dict:
        """
        Новая логика: Анализ эффективности автора.
        """
        if not videos: return {"efficiency": 0, "status": "Unknown"}
        
        lifts = [v.get('views', 0) / (v.get('author_followers', 1) + 1) for v in videos]
        avg_lift = sum(lifts) / len(lifts)
        
        status = "Rising Star" if avg_lift > 2 else "Stable"
        if avg_lift < 0.5: status = "Struggling"
        
        return {
            "avg_viral_lift": round(avg_lift, 2),
            "efficiency_score": round(min(avg_lift * 2, 10), 1),
            "status": status
        }