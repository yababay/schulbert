#!/usr/bin/env python3
import os
import sys
import re
import subprocess
import psycopg2
from pathlib import Path
from yargy import Parser, rule, or_
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact

BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

# Параметры СУБД (Канонично черпаются из .env)
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_USER = os.getenv('PG_USER', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

# --- 1. ЛИНГВИСТИЧЕСКИЙ БЛОК YARGY ДЛЯ КОМАНД ---
STOP_MARKERS  = morph_pipeline(['стоп', 'останови', 'выключи', 'тишина'])
PAUSE_MARKERS = morph_pipeline(['пауза', 'паузу', 'приостанови', 'подожди'])
PLAY_MARKERS  = morph_pipeline(['играй', 'продолжи', 'воспроизведение', 'старт', 'запусти'])
NEXT_MARKERS  = morph_pipeline(['следующий', 'дальше', 'вперед', 'переключи'])

MPCommand = fact('MPCommand', ['stop', 'pause', 'play', 'nxt'])

CMD_STOP  = rule(STOP_MARKERS.interpretation(MPCommand.stop))
CMD_PAUSE = rule(PAUSE_MARKERS.interpretation(MPCommand.pause))
CMD_PLAY  = rule(PLAY_MARKERS.interpretation(MPCommand.play))
CMD_NEXT  = rule(NEXT_MARKERS.interpretation(MPCommand.nxt))

COMMAND_RULE = or_(CMD_STOP, CMD_PAUSE, CMD_PLAY, CMD_NEXT).interpretation(MPCommand)
command_parser = Parser(COMMAND_RULE)

def check_system_command(text):
    """Проверяет, содержит ли текст системную команду управления"""
    clean_text = " ".join(text.lower().split()).strip()
    cmd = command_parser.find(clean_text)
    if not cmd: 
        return None
    stop, pause, play, nxt = cmd.fact
    if pause: return 'pause'
    if stop:  return 'stop'
    if play:  return 'play'
    if nxt:   return 'next'
    return None

# --- 2. БЛОК НИЗКОУРОВНЕВОЙ РАБОТЫ С MPC (СТАРАЯ ШКОЛА) ---

def execute_mpc(command: str):
    """Универсальная безопасная функция выполнения цепочек команд mpc"""
    try:
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception as e:
        print(f"❌ Ошибка выполнения системной команды mpc: {e}", file=sys.stderr)
        return False

def find_full_playlist_name(prefix: str) -> str:
    """Ищет реальное имя файла плейлиста в СУБД по его числовому префиксу"""
    #full_name = None
    res_lspl = subprocess.run("mpc lsplaylists", shell=True, capture_output=True, text=True)
    lspl = res_lspl.stdout
    pref_dash = f'{prefix}-'
    if pref_dash in lspl:
        for line in lspl.split():
            if line.startswith(pref_dash):
                return line.strip()
    return None

def get_mpc_status() -> dict:
    """🌟 СОХРАНЕНИЕ СТАРЫХ СОСТОЯНИЙ: Сборка статуса плеера для Svelte"""
    # 1. Получаем текущую песню
    res_track = subprocess.run("mpc current", shell=True, capture_output=True, text=True)
    current_track = res_track.stdout.strip()
    
    # 2. Вычисляем состояние паузы
    res_state = subprocess.run("mpc", shell=True, capture_output=True, text=True)
    if "[paused]" in res_state.stdout:
        current_track += " [paused]"
        
    # 3. Вытаскиваем точное число громкости
    res_vol = subprocess.run("mpc volume", shell=True, capture_output=True, text=True)
    volume_value = 50  # Дефолт
    volume_match = re.search(r'volume:\s*(\d+)%', res_vol.stdout)
    if volume_match:
        volume_value = int(volume_match.group(1))

    if not current_track or "volume:" in current_track:
        current_track = "Воспроизведение остановлено или очередь пуста."
        
    return {
        "status": "success",
        "mode": "syntax",
        "command": "status",
        "track": current_track,
        "volume": volume_value
    }

def process_rest_remote_action(action: str, volume: str, load: str, track: int) -> dict:
    """🌟 ПОЛНАЯ ЭМУЛЯЦИЯ СТАРЫХ МЕТОДОВ ДЛЯ ШЛЮЗА /mpc"""
    executed_commands = []

    if action == "status":
        return get_mpc_status()

    if action:
        valid_actions = {
            "play": "mpc play", "pause": "mpc pause", "toggle": "mpc toggle", 
            "next": "mpc next", "prev": "mpc prev", "clear": "mpc clear"
        }
        if action in valid_actions:
            execute_mpc(valid_actions[action])
            executed_commands.append(f"action: {action}")
        else:
            return {"status": "error", "message": f"Неизвестное действие '{action}'"}

    if volume:
        if re.match(r'^[+-]?\d+$', volume):
            execute_mpc(f"mpc volume {volume}")
            executed_commands.append(f"volume: {volume}")
        else:
            return {"status": "error", "message": "Неверный формат громкости"}

    if load:
        if re.match(r'^\d{1,4}$', load):
            prefix = f"{int(load):04d}"
            full_playlist_name = find_full_playlist_name(prefix)
            
            if full_playlist_name:
                if track and track > 0:
                    execute_mpc(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play {track}")
                    executed_commands.append(f"load_playlist: {full_playlist_name}, play_track: {track}")
                else:
                    execute_mpc(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play")
                    executed_commands.append(f"load_playlist: {full_playlist_name}")
            else:
                return {"status": "error", "message": f"Плейлист с префиксом {prefix}- не найден"}
        else:
            return {"status": "error", "message": "Номер плейлиста должен состоять только из цифр"}
            
    elif track and track > 0:
        execute_mpc(f"mpc play {track}")
        executed_commands.append(f"play_track_in_current: {track}")

    if not executed_commands:
        return {"status": "ignored", "message": "Не передано параметров."}

    return {"status": "success", "mode": "rest_remote", "executed": executed_commands}

def get_media_catalog_data(playlist_id: int = None) -> dict:
    """🌟 СОХРАНЕНИЕ СТАРЫХ СОСТОЯНИЙ: Режимы А и Б для эндпоинта /catalog"""
    try:
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
    except Exception as e:
        return {"status": "error", "message": f"Ошибка подключения к СУБД: {e}"}

    # РЕЖИМ А: Запрос треков конкретного плейлиста (Правая панель Svelte)
    if playlist_id is not None:
        cur.execute("""
            SELECT track_number, title, artist, album, composer 
            FROM tracks 
            WHERE playlist_number = %s 
            ORDER BY track_number ASC;
        """, (playlist_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        tracks_list = []
        for row in rows:
            # 🌟 ИСПРАВЛЕНО: Четко возвращаем элементы кортежа по индексам
            tracks_list.append({
                "track_number": row[0],
                "title": row[1],
                "artist": row[2],
                "album": row[3]
            })
        return {"mode": "playlist_tracks", "playlist_id": playlist_id, "total": len(tracks_list), "tracks": tracks_list}

    # РЕЖИМ Б: Запрос списка всех плейлистов (Левая панель Svelte)
    cur.execute("""
        SELECT DISTINCT playlist_number, COALESCE(album, 'Плейлист ' || playlist_number) || ' ' || coalesce(artist, '') || ' ' || coalesce(composer, '')
        FROM tracks 
        WHERE playlist_number >= 1000 
        ORDER BY playlist_number ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    playlists_list = []
    for row in rows:
        # 🌟 ИСПРАВЛЕНО: Четко возвращаем элементы кортежа по индексам
        playlists_list.append({
            "playlist_id": row[0],
            "name": row[1]
        })
    return {"mode": "playlists_index", "total": len(playlists_list), "playlists": playlists_list}

if __name__ == "__main__":
    # Быстрый встроенный тест работоспособности
    assert check_system_command("пауза") == "pause"
    assert check_system_command("играй") == "play"
    assert check_system_command("дальше") == "next"
    assert check_system_command("тишина") == "stop"
    print("✅ Модуль command_checker.py успешно прошел внутреннюю валидацию!")

