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
    if not m3u_files:
        print(f"📁 В директории {MUSIC_DIR} не найдено m3u-файлов для проверки.")
        cur.close()
        conn.close()
        return

    print(f"📈 Найдено локальных плейлистов для сверки: {len(m3u_files)}")
    if not args.all:
        print("💡 По умолчанию отображаются ТОЛЬКО проблемные плейлисты. Для полного списка используйте: audit-db --all\n")
    else:
        print("💡 Отображается полный отчет (режим --all).\n")

    # Шапка таблицы
    header = f"{'Плейлист':<35} | {'Строк':<6} | {'В СУБД':<6} | {'Статус':<14} | {'Без векторов'}"
    print(header)
    print("-" * len(header))

    total_playlists_checked = 0
    total_errors = 0
    hidden_ok_count = 0
    skipped_drafts_count = 0  # 🌟 Счетчик пропущенных черновиков

    for m3u_path in sorted(m3u_files):
        m3u_name = m3u_path.stem
        match = re.search(r'^\d+', m3u_name)
        if not match:
            continue
        playlist_number = int(match.group(0))

        # 🌟 ЖЕСТКИЙ ФИЛЬТР ЧЕРНОВИКОВ: Игнорируем всё, что меньше 1000
        if playlist_number < 1000:
            skipped_drafts_count += 1
            continue
        total_playlists_checked += 1

        # 1. Считаем реальные mp3-строки в локальном файле
        file_lines_count = 0
        with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    file_lines_count += 1

        # 2. Запрашиваем количество треков в удаленной СУБД Cubi
        cur.execute("SELECT COUNT(*) FROM tracks WHERE playlist_number = %s;", (playlist_number,))
        db_tracks_count = cur.fetchone()[0]

        # 3. Проверяем наличие пустых эмбеддингов для этого плейлиста
        cur.execute("SELECT COUNT(*) FROM tracks WHERE playlist_number = %s AND embedding IS NULL;", (playlist_number,))
        null_embeddings = cur.fetchone()[0]

        # Вычисляем статус целостности данных
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

        # Логика скрытия: если всё хорошо и ключ --all НЕ передан, просто увеличиваем счетчик и скрываем строку
        if is_ok and not args.all:
            hidden_ok_count += 1
            continue

        null_emb_str = f"{null_embeddings} ⏳" if null_embeddings > 0 else "0"
        print(f"{m3u_name:<35} | {file_lines_count:<6} | {db_tracks_count:<6} | {status:<14} | {null_emb_str}")

    cur.close()
    conn.close()
    print("-" * len(header))
    print(f"⚙️  Аудит завершен. Всего проверено плейлистов: {total_playlists_checked}")
    if hidden_ok_count > 0:
        print(f"🌲 Полностью корректных плейлистов скрыто из виду: {hidden_ok_count}")
    print(f"🚨 Требуют внимания и перезаливки: {total_errors}")

if __name__ == "__main__":
    run_audit()

