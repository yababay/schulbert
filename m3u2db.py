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

# Параметры удаленной БД на Cubi
DB_HOST = os.getenv('PG_HOST', '192.168.0.111')
DB_USER = os.getenv('PG_USER', 'player')
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

def get_or_create_person_id(cur, person_name):
    """
    Ищет музыканта в справочнике по имени. 
    Если не находит — создает и возвращает новый сгенерированный ID.
    """
    if not person_name:
        return None
    name_clean = str(person_name).strip()
    if not name_clean:
        return None

    cur.execute("""
        INSERT INTO persons_and_collectives (name) 
        VALUES (%s) 
        ON CONFLICT (name) DO NOTHING;
    """, (name_clean,))
    
    cur.execute("SELECT id FROM persons_and_collectives WHERE name = %s;", (name_clean,))
    res = cur.fetchone()
    return res[0] if res else None

def m3u_to_database(m3u_path):
    if not Path(m3u_path).exists():
        print(f"❌ Файл не найден: {m3u_path}")
        return

    m3u_name = Path(m3u_path).stem
    # Исправлено разделение строки для надежного извлечения префикса
    playlist_number = int(m3u_name.split('-')[0]) if m3u_name.split('-')[0].isdigit() else 0
    
    if playlist_number == 0:
        print("❌ Ошибка: Имя плейлиста должно начинаться с цифр (например, 2022-aquarium).")
        return

    print(f"🚀 [m3u2db]: Прямая заливка плейлиста {playlist_number} на Cubi ({DB_HOST}) по новой схеме...")

    with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=5432)
        cur = conn.cursor()
        
        # Гарантируем наличие записи в родительской таблице playlists
        cur.execute("""
            INSERT INTO playlists (id, name, dvd, title)
            VALUES (%s, %s, NULL, NULL)
            ON CONFLICT (id) DO NOTHING;
        """, (playlist_number, m3u_name))
        
        # Очищаем старые треки перед перезаливкой
        cur.execute("DELETE FROM tracks WHERE playlist_id = %s;", (playlist_number,))
        
        track_counter = 0
        inserted_count = 0
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            track_counter += 1
            
            # Извлекаем метаданные из MP3-файла десктопа
            tags = extract_mp3_tags(line)
            
            # Разрешаем текстовые имена артистов в ID
            artist_text = tags.get('artist')
            artist_ids = []
            if artist_text:
                for part in artist_text.split(';'):
                    p_id = get_or_create_person_id(cur, part)
                    if p_id:
                        artist_ids.append(p_id)
            
            # Разрешаем композиторов в ID
            composer_text = tags.get('form')  
            composer_ids = []
            if composer_text:
                for part in composer_text.split(';'):
                    c_id = get_or_create_person_id(cur, part)
                    if c_id:
                        composer_ids.append(c_id)

            # Парсим год релиза
            release_year = None
            date_tag = tags.get('date')
            if date_tag and str(date_tag).isdigit():
                release_year = int(date_tag)

            # 🌟 ШАГ 3: Вставка в tracks с поддержкой новой колонки 'title'
            cur.execute("""
                INSERT INTO tracks (playlist_id, track_number, path, title, album, release_year, composer_ids, artist_ids)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                playlist_number,
                track_counter,
                line,
                tags.get('title'),  # 🌟 Новая колонка улетает в базу данных
                tags.get('album'),
                release_year,
                composer_ids if composer_ids else None,
                artist_ids if artist_ids else None
            ))
            
            inserted_count += 1
            
        conn.commit()
        cur.close()
        conn.close()
        print(f"✅ Успешно импортировано треков по новой схеме: {inserted_count}. Названия песен и ID привязаны.")
        
    except Exception as e:
        print(f"❌ Ошибка сетевого импорта в новую СУБД: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 m3u2db.py <плейлист.m3u>")
        sys.exit(1)
    m3u_to_database(sys.argv[1])

