#!/usr/bin/env python3
import os
import sys
import datetime
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

try:
    from mutagen.mp3 import MP3
    from mutagen.id3 import ID3, TIT2, TPE1, TALB, TCON, ID3NoHeaderError
except ImportError:
    print("❌ Ошибка: Не установлена библиотека mutagen. Выполните: pip install mutagen")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

DB_HOST = os.getenv('PG_HOST', '192.168.0.111')
DB_USER = os.getenv('PG_USER', 'player')
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

# Абсолютный корневой путь к вашей музыкальной папке на десктопе
MUSIC_ROOT = Path('~/Музыка').expanduser()

def sync_all_database_to_tags():
    print(f"🔄 [db2tags]: Запуск сквозной инкрементальной синхронизации с Cubi ({DB_HOST})...")
    print(f"📁 Корневая папка медиатеки десктопа: {MUSIC_ROOT}")
    
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        # 🔍 ВЫБИРАЕМ ВСЕ БОЕВЫЕ ТРЕКИ ИЗ СУБД (Игнорируем черновики < 1000)
        # Обязательно тянем ваше новое поле updated_at
        cur.execute("""
            SELECT file_path, title, artist, album, genre, style, form, updated_at 
            FROM tracks 
            WHERE playlist_number >= 1000;
        """)
        db_rows = cur.fetchall()
        
        if not db_rows:
            print("💤 В СУБД Cubi пока нет боевых записей для проверки.")
            cur.close()
            conn.close()
            return

        total_checked = len(db_rows)
        updated_count = 0
        missing_files_count = 0
        
        print(f"📈 Из СУБД получено записей для анализа: {total_checked}")
        print("⏳ Проверка соответствия таймстампов и прошивка тегов...")

        for row in db_rows:
            db_file_path, db_title, db_artist, db_album, db_genre, db_style, db_form, db_updated_at = row
            
            if not db_file_path:
                continue
                
            # Строим абсолютный физический путь к MP3-файлу на диске десктопа
            full_local_path = MUSIC_ROOT / db_file_path
            
            if not full_local_path.exists():
                missing_files_count += 1
                continue

            # 🌟 МАГИЯ ИНКРЕМЕНТАЛЬНОГО СРАВНЕНИЯ ВРЕМЕНИ:
            # Получаем время последнего изменения файла на диске (mtime) и переводим в datetime (UTC/локальный)
            file_mtime_ts = os.path.getmtime(full_local_path)
            file_mtime = datetime.datetime.fromtimestamp(file_mtime_ts, datetime.timezone.utc)
            
            # Гарантируем, что временная метка из базы тоже содержит информацию о таймзоне (Postgres timestamp tz)
            if db_updated_at.tzinfo is None:
                db_updated_at = db_updated_at.replace(tzinfo=datetime.timezone.utc)

            # ЕСЛИ ИЗМЕНЕНИЯ В СУБД СДЕЛАНЫ ПОЗДНЕЕ, ЧЕМ МЕНЯЛСЯ ФАЙЛ — НАДО ШИТЬ ТЕГИ!
            if db_updated_at > file_mtime:
                try:
                    audio = MP3(full_local_path, ID3=ID3)
                    if audio.tags is None:
                        audio.add_tags()
                        
                    # Накатываем эталонные русские строки из базы в блоки ID3v2.4
                    if db_title: audio.tags.add(TIT2(encoding=3, text=db_title))
                    if db_artist: audio.tags.add(TPE1(encoding=3, text=db_artist))
                    if db_album: audio.tags.add(TALB(encoding=3, text=db_album))
                    if db_genre: audio.tags.add(TCON(encoding=3, text=db_genre))
                    
                    # Переносим ИИ-теги стилей и форм во внутренние TXXX-фреймы
                    if db_style: audio.tags.add(type(audio.tags.get('TXXX:style') or TIT2)(encoding=3, desc='style', text=db_style))
                    if db_form: audio.tags.add(type(audio.tags.get('TXXX:form') or TIT2)(encoding=3, desc='form', text=db_form))
                    
                    # Сохраняем файл, полностью вырезая ломающийся старый блок ID3v1
                    audio.save(v1=2)
                    updated_count += 1
                    
                    print(f"🌟 [СИНХРОНИЗИРОВАН]: {db_file_path} ➡️ [{db_artist} - {db_title}]")
                    
                except Exception as tag_err:
                    print(f"⚠️ Ошибка прошивки тегов в {db_file_path}: {tag_err}")

        cur.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print(f"🎯 [Итог инспекции db2tags]: Проверено записей базы: {total_checked}")
        print(f"🚀 Физически обновлено и прошито файлов MP3 на диске: {updated_count}")
        if missing_files_count > 0:
            print(f"⚠️ Локальных файлов из базы не найдено на диске десктопа: {missing_files_count}")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Системная ошибка сквозной синхронизации: {e}")

if __name__ == "__main__":
    sync_all_database_to_tags()

