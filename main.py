#!/usr/bin/env python3
import os
import sys
import requests
from pathlib import Path

# Импортируем вашу эталонную функцию записи звука из локальной библиотеки
from audio_recorder import record_audio  

# Импортируем сквозной конвейер распознавателей (он теперь одинаковый везде!)
from audio_conveyor import record_voice_to_text, process_cascade_routing

BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

MUSIC_SERVER = os.getenv('MUSIC_SERVER', 'schulbert')
SERVER_TEXT_URL = f"http://{MUSIC_SERVER}:8080/text-search"
API_MPC_URL = f"http://{MUSIC_SERVER}/api/mpc"

AUDIO_WAV = "/tmp/client_voice.wav"

def show_notification(text, icon="audio-speakers", title="Шульберт Пульт"):
    import subprocess
    subprocess.run(['notify-send', '-t', '4000', '-i', icon, title, text])

def main():
    show_notification("Слушаю вас! Озвучьте команду...", icon="audio-input-microphone")
    
    # Шаг 1. Запись звука через вашу общую функцию
    try:
        record_audio(AUDIO_WAV, duration=5)
    except Exception as e:
        show_notification("Ошибка физической записи звука.", icon="dialog-error")
        print(f"❌ record_audio упал: {e}")
        sys.exit(1)
    
    if not os.path.exists(AUDIO_WAV):
        show_notification("Аудиофайл записи не найден.", icon="dialog-error")
        sys.exit(1)
        
    # Шаг 2. Переводим звук в буквы силами встроенного в конвейер Vosk
    raw_speech = record_voice_to_text(AUDIO_WAV)
    
    # Нам больше не нужны звуковые байты, буквы уже в памяти!
    if os.path.exists(AUDIO_WAV): 
        os.remove(AUDIO_WAV)

    if not raw_speech:
        show_notification("Команда не расслышана. Повторите громче.", icon="dialog-warning")
        sys.exit(0)

    print(f"📋 [Десктоп]: Vosk зафиксировал текст: \"{raw_speech}\"")

    # =====================================================================
    # 🌟 ЕДИНЫЙ КАСКАДНЫЙ КОНВЕЙЕР «СТАРОЙ ШКОЛЫ» НА ДЕСКТОПЕ
    # =====================================================================
    routing = process_cascade_routing(raw_speech)
    
    if routing:
        # УСПЕХ: Локальные модули (команды, плейлисты или галлюцинации) нашли цель!
        action = routing["action"]
        
        if action == "system_cmd":
            target_cmd = routing["target"]
            print(f"🎯 [Десктоп Каскад]: Найдена команда плеера: '{target_cmd}'")
            show_notification(f"Выполняю команду: {target_cmd.upper()} 🛠️", icon="media-playback-start")
            requests.post(f"{API_MPC_URL}?cmd={target_cmd}")
            sys.exit(0)
            
        elif action == "load_playlist":
            load_num = routing["playlist"]
            track_num = routing["track"]
            
            # Строим точечный REST-URL (сохраняя логику NULL для альбома целиком)
            url = f"{API_MPC_URL}?load={load_num}"
            if track_num is not None:
                url += f"&track={track_num}"
                
            print(f"🎯 [Десктоп Каскад]: Найдена точная реляционная цель. Запуск: {url}")
            show_notification(f"Включаю целевой трек плейлиста {load_num} 🎶", icon="media-playlist-normal")
            requests.post(url)
            sys.exit(0)

    # =====================================================================
    # 🌌 ЗАПАСНОЙ ХОД: СТАРАЯ ШКОЛА БЕССИЛЬНА -> ВЕКТОРНЫЙ ТЕКСТ НА CUBI ДЛЯ E5
    # =====================================================================
    print("🌌 [Каскад десктопа исчерпан]: Отправка легкого текста на Cubi для ИИ-анализа...")
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

