#!/usr/bin/env python3
import os
import sys
import json
import psycopg2
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
E5_MODEL_PATH = str(BASE_DIR / "models" / "multilingual-e5-large")

print("🌌 [Ночной воркер]: Запуск планового обновления эмбеддингов...")

# Проверяем, приехала ли большая ИИ-модель
if not os.path.exists(E5_MODEL_PATH) or not any(Path(E5_MODEL_PATH).iterdir()):
    print("💡 [Ночной воркер]: Модель e5 отсутствует в системе. Обсчет векторов отложен.")
    sys.exit(0)

try:
    from sentence_transformers import SentenceTransformer
    print("🧠 Загрузка нейросети multilingual-e5-large в память...")
    model = SentenceTransformer(E5_MODEL_PATH)
except Exception as e:
    print(f"❌ Не удалось инициализировать модель: {e}")
    sys.exit(1)

try:
    # Подключаемся к локальной базе player на Cubi
    conn = psycopg2.connect("dbname=player user=player host=localhost")
    cur = conn.cursor()
    
    # 🔍 Ищем записи, у которых текст обновился (триггер сбросил embedding в NULL)
    cur.execute("""
        SELECT id, title, artist, album, genre, style, form 
        FROM tracks 
        WHERE embedding IS NULL;
    """)
    rows = cur.fetchall()
    
    if not rows:
        print("💤 Все векторы в базе актуальны. Новых треков для обсчета нет.")
        cur.close()
        conn.close()
        sys.exit(0)
        
    print(f"📈 Найдено треков для обсчета: {len(rows)}")
    
    updated_count = 0
    for row in rows:
        track_id = row[0]
        
        # Собираем текстовое ядро для ИИ-анализа в строгом соответствии с хэш-функцией
        ai_text = (
            f"Название: {row[1] or ''} ; "
            f"Исполнитель: {row[2] or ''} ; "
            f"Альбом: {row[3] or ''} ; "
            f"Жанр: {row[4] or ''} ; "
            f"Стиль: {row[5] or ''} ; "
            f"Форма: {row[6] or ''}"
        )
        
        # Генерируем высокоточный семантический вектор
        embedding = model.encode(ai_text).tolist()
        
        # Записываем вектор обратно в pgvector
        cur.execute("UPDATE tracks SET embedding = %s WHERE id = %s;", (embedding, track_id))
        updated_count += 1
        
        if updated_count % 50 == 0:
            print(f"⏳ Обработано треков: {updated_count}...")
            conn.commit() # Фиксируем пачками, чтобы не держать длинную транзакцию
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"🎯 [Успех]: Ночной обсчет завершен! Успешно обновлено векторов: {updated_count}")

except Exception as e:
    print(f"❌ Ошибка в ходе работы ночного воркера: {e}")

