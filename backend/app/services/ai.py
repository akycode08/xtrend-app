# backend/app/services/ai.py
import os
import requests
import base64
import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
from anthropic import Anthropic

# Глобальные переменные для ленивой загрузки (чтобы не грузить память при старте)
_clip_model = None
_clip_processor = None
_claude_client = None

def get_claude_client():
    global _claude_client
    if not _claude_client:
        key = os.getenv("ANTHROPIC_API_KEY")
        if key:
            _claude_client = Anthropic(api_key=key)
    return _claude_client

def load_clip():
    global _clip_model, _clip_processor
    if _clip_model is None:
        print("🧠 Загрузка модели CLIP...")
        try:
            _clip_model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
            _clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
            print("✅ CLIP загружен.")
        except Exception as e:
            print(f"⚠️ Ошибка CLIP: {e}")

def get_text_embedding(text: str) -> list:
    """Превращает текст в вектор (список из 512 чисел)"""
    load_clip()
    if not _clip_model or not text: return None
    try:
        inputs = _clip_processor(text=[text], return_tensors="pt", padding=True)
        with torch.no_grad():
            outputs = _clip_model.get_text_features(**inputs)
        return outputs.squeeze().numpy().tolist()
    except: return None

def get_image_embedding(image_url: str) -> list:
    """Скачивает картинку и превращает в вектор"""
    load_clip()
    if not _clip_model or not image_url: return None
    try:
        resp = requests.get(image_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=5)
        if resp.status_code != 200: return None
        image = Image.open(resp.raw)
        inputs = _clip_processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = _clip_model.get_image_features(**inputs)
        return outputs.squeeze().numpy().tolist()
    except: return None

def generate_trend_summary(description: str, views: int, cover_url: str = None) -> str:
    """Спрашивает у Claude суть тренда"""
    client = get_claude_client()
    if not client: return "AI Not Configured"

    prompt = f"Тренд TikTok. Описание: {description}. Просмотров: {views}. В чем суть тренда? Ответь одной короткой фразой."
    
    try:
        # Пытаемся отправить с картинкой, если есть
        messages = []
        if cover_url:
             # Логика загрузки картинки опущена для краткости, можно добавить позже
             pass
        
        # Простой текстовый запрос (самый надежный)
        resp = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=60,
            messages=[{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        )
        return resp.content[0].text.strip()
    except Exception as e:
        print(f"⚠️ AI Summary Error: {e}")
        return "Pending"