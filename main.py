#!/usr/bin/env python3
import os
import sys
import json
import wave
import requests
from pathlib import Path
from vosk import Model, KaldiRecognizer, SetLogLevel

# 🌟 ИСПРАВЛЕНО: Импортируем вашу эталонную функцию записи звука 
# (укажите правильный путь импорта, если она лежит в соседнем библиотечном модуле)
from audio_recorder import record_audio  

# ИИ-распознаватели каскадного конвейера
from command_checker import check_system_command
from playlist_checker import check_playlist_phrase
from tracks_checker import check_direct_track_target

BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

MUSIC_SERVER = os.getenv('MUSIC_SERVER', 'schulbert')
SERVER_TEXT_URL = f"http://{MUSIC_SERVER}:8080/text-search"
API_MPC_URL = f"http://{MUSIC_SERVER}/api/mpc"

AUDIO_WAV = "/tmp/client_voice.wav"
VOSK_MODEL_PATH = "/usr/share/schulbert/music-voice-assistant/models/vosk-model-small-ru"

def show_notification(text, icon="audio-speakers", title="Шульберт Пульт"):
    import subprocess
    subprocess.run(['notify-send', '-t', '4000', '-i', icon, title, text])

def main():
    show_notification("Слушаю вас...", icon="audio-input-microphone")
    
    # 🌟 ИСПРАВЛЕНО: Нативно вызываем вашу общую функцию записи звука
    # Она сама запишет arecord, прогонит через ffmpeg и сохранит в AUDIO_WAV
    try:
        record_audio(AUDIO_WAV, duration=5)
    except Exception as e:
        show_notification("Ошибка физической записи звука.", icon="dialog-error")
        print(f"❌ record_audio упал: {e}")
        sys.exit(1)
    
    if not os.path.exists(AUDIO_WAV):
        show_notification("Аудиофайл записи не найден.", icon="dialog-error")
        sys.exit(1)
        
    # Локальная расшифровка сохраненного wav-файла движком Vosk
    try:
        SetLogLevel(-1)
        model = Model(VOSK_MODEL_PATH)
        wf = wave.open(AUDIO_WAV, "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        data = wf.readframes(wf.getnframes())
        wf.close()
        res = json.loads(rec.Result() if rec.AcceptWaveform(data) else rec.FinalResult())
        raw_speech = res.get('text', '').strip()
    except Exception as e:
        print(f"❌ Ошибка Vosk: {e}")
        raw_speech = ""

    # Полностью очищаем за собой диск десктопа, буквы уже у нас в памяти!
    if os.path.exists(AUDIO_WAV): 
        os.remove(AUDIO_WAV)

    if not raw_speech:
        show_notification("Команда не расслышана. Повторите громче.", icon="dialog-warning")
        sys.exit(0)

    print(f"📋 [Каскад]: Vosk зафиксировал текст: \"{raw_speech}\"")

    # =====================================================================
    # КАСКАДНЫЙ КОНВЕЙЕР РАСПОЗНАВАТЕЛЕЙ СТАРШЕЙ ШКОЛЫ
    # =====================================================================

    # РУБЕЖ 1: Системные команды управления MPD плером (play, pause, next, stop)
    system_cmd = check_system_command(raw_speech)
    if system_cmd:
        print(f"🎯 [Каскад 1]: Найдена команда плеера: '{system_cmd}'")
        show_notification(f"Выполняю команду: {system_cmd.upper()} 🛠️", icon="media-playback-start")
        requests.post(f"{API_MPC_URL}?cmd={system_cmd}")
        sys.exit(0)

    # РУБЕЖ 2: Явное числовое выделение номера плейлиста через Yargy
    playlist_num = check_playlist_phrase(raw_speech)
    if playlist_num:
        print(f"🎯 [Каскад 2]: Выделен жесткий номер плейлиста: {playlist_num}")
        show_notification(f"Загружаю плейлист №{playlist_num} 🎶", icon="media-playlist-normal")
        requests.post(f"{API_MPC_URL}?load={playlist_num}")
        sys.exit(0)

    # РУБЕЖ 3: 🌟 ИСПРАВЛЕНО: Работаем через переименованный tracks_checker
    direct_target = check_direct_track_target(raw_speech)
    if direct_target:
        load_num = direct_target["load"]
        track_num = direct_target["track"]
        
        # Строим гибкий URL: если track_num равен None (альбом целиком) — не шлем его в REST
        url = f"{API_MPC_URL}?load={load_num}"
        if track_num is not None:
            url += f"&track={track_num}"
            
        print(f"🎯 [Каскад 3]: Найдена цель в СУБД. Запуск: {url}")
        show_notification(f"Включаю целевой трек плейлиста {load_num} 🎶", icon="media-playlist-normal")
        requests.post(url)
        sys.exit(0)

    # =====================================================================
    # РУБЕЖ 4: ЕСЛИ СТАРШАЯ ШКОЛА БЕССИЛЬНА — ТЕКСТ ЛЕТИТ НА СЕРВЕР ДЛЯ E5
    # =====================================================================
    print("🌌 [Каскад исчерпан]: Отправка чистого текста на Cubi для ИИ-анализа...")
    show_notification("Поиск семантических ИИ-ассоциаций...", icon="applications-science")
    
    try:
        response = requests.post(SERVER_TEXT_URL, json={"query": raw_speech}, timeout=5)
        if response.status_code == 200:
            result = response.json()
            if result.get("status") == "success":
                show_notification(f"ИИ нашел соответствие:\n{result.get('display_text')}", icon="media-playlist-normal")
            else:
                show_notification("Ассоциаций в ИИ-базе не найдено.", icon="dialog-information")
        else:
            show_notification(f"Ошибка ИИ-сервера: Код {response.status_code}", icon="dialog-error")
    except Exception as e:
        print(f"❌ Сетевой сбой ИИ-анализа: {e}")
        show_notification("ИИ-станция недоступна по сети.", icon="network-disconnect")

if __name__ == "__main__":
    main()
