# backend/app/services/clustering.py
import numpy as np
from sklearn.cluster import DBSCAN

def cluster_trends_by_visuals(trends_list: list) -> list:
    """
    Принимает список объектов Trend.
    Группирует их по векторам (embedding) и проставляет cluster_id.
    """
    # 1. Отбираем только те видео, у которых есть эмбеддинг
    valid_trends = [t for t in trends_list if t.embedding is not None]
    
    if not valid_trends:
        return trends_list

    try:
        # Превращаем список векторов в матрицу numpy
        X = np.array([t.embedding for t in valid_trends])

        # 2. Запускаем DBSCAN
        # eps=0.15 - насколько похожи должны быть картинки (0.0 - копии, 1.0 - разные)
        # min_samples=2 - минимальное кол-во видео, чтобы считать это группой
        clustering = DBSCAN(eps=0.15, min_samples=2, metric='cosine').fit(X)
        
        labels = clustering.labels_ # Список типа [0, 0, 1, -1, 1 ...]

        # 3. Присваиваем ID кластеров обратно объектам
        for i, trend in enumerate(valid_trends):
            # -1 означает "шум" (уникальное видео, ни на что не похоже)
            trend.cluster_id = int(labels[i])
            
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        print(f"🧩 Visual Clustering: Найдено {n_clusters} визуальных групп среди {len(valid_trends)} видео.")
        
    except Exception as e:
        print(f"⚠️ Ошибка кластеризации: {e}")

    return trends_list