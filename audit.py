#!/usr/bin/env python3
import os
import sys
import re
import argparse
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=SCRIPT_DIR / ".env")

DB_HOST = os.getenv('PG_HOST', '192.168.0.111')
DB_USER = os.getenv('PG_USER', 'player')
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

def parse_args():
    """Настройка парсера аргументов командной строки"""
    parser = argparse.ArgumentParser(description="Утилита аудита целостности СУБД проекта «Шульберт»")
    parser.add_argument(
        '-a', '--all', 
        action='store_true', 
        help='Показывать абсолютно все плейлисты, включая полностью корректные (ОК)'
    )
    return parser.parse_args()

def run_audit():
    args = parse_args()
    
    print(f"🔎 [Аудит СУБД]: Подключение к базе {DB_HOST}...")
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Ошибка подключения к базе Cubi: {e}")
        sys.exit(1)

    # Вычисляем путь к музыкальной папке с раскрытием тильды
    MUSIC_DIR = Path('~/Музыка').expanduser()
    m3u_files = list(MUSIC_DIR.glob('*.m3u'))

    print(f"📈 Найдено локальных плейлистов на десктопе: {len(m3u_files)}")
    if not args.all:
        print("💡 По умолчанию отображаются только проблемные зоны. Для полного отчета используйте: audit-db --all\n")

    # Шапка таблицы
    header = f"{'Плейлист / Имя в СУБД':<45} | {'Строк':<6} | {'В СУБД':<6} | {'Статус':<18} | {'Без векторов'}"
    print(header)
    print("-" * len(header))

    total_playlists_checked = 0
    total_errors = 0
    hidden_ok_count = 0
    skipped_drafts_count = 0
    
    # Множество для фиксации номеров плейлистов, которые физически существуют на диске
    found_local_numbers = set()

    # =====================================================================
    # ЭТАП 1: ПРОВЕРКА СУЩЕСТВУЮЩИХ ФАЙЛОВ ПЛЕЙЛИСТОВ
    # =====================================================================
    for m3u_path in sorted(m3u_files):
        m3u_name = m3u_path.stem
        match = re.search(r'^\d+', m3u_name)
        if not match:
            continue
        playlist_number = int(match.group(0))

        # Игнорируем технические черновики меньше 1000
        if playlist_number < 1000:
            skipped_drafts_count += 1
            continue

        total_playlists_checked += 1
        found_local_numbers.add(playlist_number)

        # 1. Считаем mp3-строки в локальном файле
        file_lines_count = 0
        with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    file_lines_count += 1

        # 2. Запрашиваем количество треков в удаленной СУБД
        cur.execute("SELECT COUNT(*) FROM tracks WHERE playlist_number = %s;", (playlist_number,))
        db_tracks_count = cur.fetchone()[0]

        # 3. Проверяем наличие пустых эмбеддингов
        cur.execute("SELECT COUNT(*) FROM tracks WHERE playlist_number = %s AND embedding IS NULL;", (playlist_number,))
        null_embeddings = cur.fetchone()[0]

        is_ok = False
        if db_tracks_count == 0:
            status = "❌ СЛЕПОЙ"
            total_errors += 1
        elif file_lines_count != db_tracks_count:
            status = "⚠️ РАСХОЖДЕНИЕ"
            total_errors += 1
        else:
            status = "✅ ОК"
            is_ok = True

        if is_ok and not args.all:
            hidden_ok_count += 1
            continue

        null_emb_str = f"{null_embeddings} ⏳" if null_embeddings > 0 else "0"
        print(f"{m3u_name:<45} | {file_lines_count:<6} | {db_tracks_count:<6} | {status:<18} | {null_emb_str}")

    # =====================================================================
    # ЭТАП 2: ОБНАРУЖЕНИЕ ФАНТОМНЫХ ПЛЕЙЛИСТОВ (Есть в базе, но удалены с диска)
    # =====================================================================
    # Вытаскиваем из СУБД все плейлисты, исключая черновики < 1000
    cur.execute("SELECT playlist_number, playlist_title FROM playlists WHERE playlist_number >= 1000 ORDER BY playlist_number ASC;")
    db_playlists = cur.fetchall()

    phantom_count = 0
    for p_num, p_name in db_playlists:
        # Если номер плейлиста есть в базе данных, но его физического .m3u файла больше нет на десктопе!
        if p_num not in found_local_numbers:
            phantom_count += 1
            total_errors += 1
            
            # Узнаем, сколько «мертвых» треков продолжает лежать под этим номером в базе
            cur.execute("SELECT COUNT(*) FROM tracks WHERE playlist_number = %s;", (p_num,))
            dead_tracks_count = cur.fetchone()[0]
            
            # Выводим фантомную строку ярким флагом
            print(f"[{p_num}] {p_name:<39} | {'0':<6} | {dead_tracks_count:<6} | 🚨 ФАНТОМ (УДАЛЕН) | 0")

    print("-" * len(header))
    print(f"⚙️  Аудит завершен. Боевых плейлистов на диске проверено: {total_playlists_checked}")
    if skipped_drafts_count > 0:
        print(f"📝 Технических черновиков (< 1000) отсечено: {skipped_drafts_count}")
    if hidden_ok_count > 0:
        print(f"🌲 Полностью корректных плейлистов скрыто из виду: {hidden_ok_count}")
    if phantom_count > 0:
        print(f"👻 Найдено фантомных (осиротевших) списков в СУБД Cubi: {phantom_count}")
    print(f"🚨 Итого объектов, требующих внимания и чистки: {total_errors}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    run_audit()

