#!/usr/bin/env python3
import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from extract_tags import extract_mp3_tags

SCRIPT_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPT_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

# Параметры удаленной БД
DB_HOST = os.getenv('PG_HOST',     '192.168.0.111')
DB_USER = os.getenv('PG_USER',     'player')
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player')

def m3u_to_database(m3u_path):
    if not Path(m3u_path).exists():
        print(f"❌ Файл не найден: {m3u_path}")
        return

    m3u_name = Path(m3u_path).stem
    playlist_number = int(m3u_name.split('-')[0]) if m3u_name.split('-')[0].isdigit() else 0
    
    if playlist_number == 0:
        print("❌ Ошибка: Имя плейлиста должно начинаться с цифр (например, 2022-aquarium).")
        return

    print(f"🚀 [m3u2db]: Прямая заливка плейлиста {playlist_number} на Cubi ({DB_HOST})...")

    with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=5432)
        cur = conn.cursor()
        
        # 🌟 ШАГ 1: ГАРАНТИРУЕМ НАЛИЧИЕ ПЛЕЙЛИСТА В ГЛАВНОЙ ТАБЛИЦЕ (Исправлено имя колонки на 'name')
        # ON CONFLICT DO NOTHING защищает от ошибок, если этот номер уже был создан ранее
        cur.execute("""
            INSERT INTO playlists (playlist_number, playlist_title)
            VALUES (%s, %s)
            ON CONFLICT (playlist_number) DO NOTHING;
        """, (playlist_number, m3u_name))
        
        #cur.execute("""
        #    INSERT INTO playlists (playlist_number, title)
        #    VALUES (%s, %s)
        #    ON CONFLICT (playlist_number) DO NOTHING;
        #""", (playlist_number, m3u_name))
        
        # 🌟 ШАГ 2: Очищаем старые метаданные треков этого плейлиста перед заливкой обновленных
        cur.execute("DELETE FROM tracks WHERE playlist_number = %s;", (playlist_number,))
        
        track_counter = 0
        inserted_count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            track_counter += 1
            
            # Извлекаем свежезашитые русские теги
            tags = extract_mp3_tags(line)
            
            # Напрямую вставляем данные треков (file_path теперь на месте)
            cur.execute("""
                INSERT INTO tracks (playlist_number, track_number, file_path, title, artist, album, genre, style, form, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL);
            """, (
                playlist_number,
                track_counter,
                line,
                tags.get('title'),
                tags.get('artist'),
                tags.get('album'),
                tags.get('genre'),
                tags.get('style'),
                tags.get('form')
            ))
            inserted_count += 1
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Успешно импортировано треков: {inserted_count}. Векторы выставлены в NULL для ночного обсчета.")
        
        
    except Exception as e:
        print(f"❌ Ошибка сетевого импорта в PostgreSQL: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 m3u2db.py <плейлист.m3u>")
        sys.exit(1)
    m3u_to_database(sys.argv[1])

