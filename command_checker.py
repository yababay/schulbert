#!/usr/bin/env python3
import sys
from yargy import Parser, rule, or_
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact

# Лингвистические правила для команд управления
STOP_MARKERS  = morph_pipeline(['стоп', 'останови', 'выключи', 'тишина'])
PAUSE_MARKERS = morph_pipeline(['пауза', 'паузу', 'приостанови', 'подожди'])
PLAY_MARKERS  = morph_pipeline(['играй', 'продолжи', 'воспроизведение', 'старт', 'запусти'])
NEXT_MARKERS  = morph_pipeline(['следующий', 'дальше', 'вперед', 'переключи'])

MPCommand = fact('MPCommand', [
        'stop',
        'pause',
        'play',
        'nxt',
    ]
)

CMD_STOP = rule(
    STOP_MARKERS.interpretation(MPCommand.stop),
)

CMD_PAUSE = rule(
    PAUSE_MARKERS.interpretation(MPCommand.pause),
)

CMD_PLAY = rule(
    PLAY_MARKERS.interpretation(MPCommand.play),
)

CMD_NEXT = rule(
    NEXT_MARKERS.interpretation(MPCommand.nxt),
)

COMMAND_RULE = or_ (
    CMD_STOP,
    CMD_PAUSE,
    CMD_PLAY,
    CMD_NEXT
).interpretation(MPCommand)

command_parser = Parser(COMMAND_RULE)

def check_system_command(text):
    """
    Проверяет, содержит ли текст системную команду управления.
    Возвращает строку ('stop', 'pause', 'play', 'next') или None.
    """
    clean_text = " ".join(text.lower().split()).strip()
    cmd = command_parser.find(clean_text)

    if not cmd: 
        return clean_text


    stop, pause, play, nxt = cmd.fact
    
    if pause:
        return 'pause'
    if stop:
        return 'stop'
    if play:
        return 'play'
    if nxt:
        return 'next'

    return clean_text

import subprocess
import psycopg2
import os

# Параметры СУБД для каталога (черпаются из окружения)
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_USER = os.getenv('PG_USER', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

def execute_system_mpc_cmd(cmd: str) -> bool:
    """Выполняет базовые команды управления очередью MPD"""
    if cmd in ["play", "pause", "next", "stop"]:
        # Отображаем 'next' в команду 'next' для mpc
        mpc_cmd = "next" if cmd == "next" else cmd
        result = subprocess.run(["mpc", mpc_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    return False

def execute_mpc_action(playlist_num: int, track_num: int = None) -> bool:
    """Очищает очередь, загружает плейлист и запускает нужный трек"""
    try:
        subprocess.run(["mpc", "clear"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        res_load = subprocess.run(["mpc", "load", str(playlist_num)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res_load.returncode != 0:
            return False
            
        if track_num is not None:
            subprocess.run(["mpc", "play", str(track_num)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.run(["mpc", "play"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def get_music_catalog() -> list:
    """
    Вытаскивает из СУБД структурированный список доступных 
    боевых плейлистов для веб-интерфейса 'Шульберта'
    """
    catalog = []
    try:
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        # Извлекаем плейлисты, упорядоченные по номерам
        cur.execute("""
            SELECT playlist_number, name 
            FROM playlists 
            WHERE playlist_number >= 1000 
            ORDER BY playlist_number ASC;
        """)
        rows = cur.fetchall()
        for p_num, p_name in rows:
            catalog.append({
                "playlist_number": p_num,
                "title": p_name
            })
        cur.close()
        conn.close()
    except Exception as e:
        print(f"⚠️ Ошибка чтения каталога из СУБД: {e}", file=sys.stderr)
    return catalog

if __name__ == "__main__":
    # Быстрый встроенный тест работоспособности
    assert check_system_command("пауза") == "pause"
    assert check_system_command("играй") == "play"
    assert check_system_command("дальше") == "next"
    assert check_system_command("тишина") == "stop"
    print("✅ Модуль command_checker.py успешно прошел внутреннюю валидацию!")

