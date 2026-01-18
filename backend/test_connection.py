#!/usr/bin/env python3
"""Скрипт для проверки подключения к базе данных Supabase"""

import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql

# Загружаем переменные окружения
load_dotenv()

def test_connection():
    """Проверяет подключение к базе данных"""
    
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL не найден в .env файле")
        return False
    
    print("=" * 60)
    print("🔍 Проверка подключения к базе данных...")
    print("=" * 60)
    print(f"📋 DATABASE_URL: {database_url[:50]}...")
    print()
    
    try:
        # Подключаемся к базе данных
        print("⏳ Попытка подключения...")
        conn = psycopg2.connect(database_url)
        
        # Создаем курсор
        cur = conn.cursor()
        
        # Проверяем версию PostgreSQL
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ Подключение успешно!")
        print(f"📊 PostgreSQL версия: {version.split(',')[0]}")
        print()
        
        # Проверяем текущую базу данных
        cur.execute("SELECT current_database();")
        db_name = cur.fetchone()[0]
        print(f"📦 Текущая база данных: {db_name}")
        
        # Проверяем текущего пользователя
        cur.execute("SELECT current_user;")
        user = cur.fetchone()[0]
        print(f"👤 Текущий пользователь: {user}")
        print()
        
        # Проверяем расширение pgvector
        print("🔍 Проверка расширения pgvector...")
        cur.execute("""
            SELECT EXISTS(
                SELECT 1 FROM pg_extension WHERE extname = 'vector'
            );
        """)
        has_vector = cur.fetchone()[0]
        
        if has_vector:
            print("✅ Расширение pgvector установлено")
        else:
            print("⚠️  Расширение pgvector НЕ установлено")
            print("   Попробуйте выполнить: CREATE EXTENSION IF NOT EXISTS vector;")
        print()
        
        # Проверяем список таблиц
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cur.fetchall()
        
        if tables:
            print(f"📋 Найдено таблиц: {len(tables)}")
            for table in tables[:10]:  # Показываем первые 10
                print(f"   - {table[0]}")
            if len(tables) > 10:
                print(f"   ... и еще {len(tables) - 10} таблиц")
        else:
            print("📋 Таблицы не найдены (база данных пустая)")
        
        print()
        print("=" * 60)
        print("✅ Проверка завершена успешно!")
        print("=" * 60)
        
        # Закрываем соединение
        cur.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print("❌ Ошибка подключения:")
        print(f"   {str(e)}")
        print()
        print("💡 Возможные причины:")
        print("   1. Неверный DATABASE_URL")
        print("   2. Неверный пароль")
        print("   3. База данных недоступна")
        print("   4. Неверный хост или порт")
        return False
        
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {type(e).__name__}")
        print(f"   {str(e)}")
        return False

if __name__ == "__main__":
    success = test_connection()
    exit(0 if success else 1)
