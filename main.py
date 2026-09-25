#!/usr/bin/env python3
import sys
import os
import subprocess
import requests
from dotenv import load_dotenv

load_dotenv()

# Сетевой адрес музыкального сервера
MUSIC_SERVER = os.getenv('MUSIC_SERVER', 'schulbert')
SERVER_URL = f"http://{MUSIC_SERVER}:8080/voice-search"

AUDIO_RAW = "/tmp/client_voice.raw"
AUDIO_WAV = "/tmp/client_voice.wav"

def show_notification(text, icon="audio-speakers", title="Голосовой пульт", timeout=4000):
    """Служебная функция отправки уведомления на рабочий стол десктопа"""
    # Флаг -h string:x-canonical-private-synchronous:anything заставляет уведомления 
    # плавно обновлять друг друга в одном окне, не создавая надоедливую стопку окон!
    cmd = [
        'notify-send',
        '-t', str(timeout),
        '-i', icon,
        '-h', 'string:x-canonical-private-synchronous:music-pulse',
        title,
        text
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():
    # 🌟 1. СИГНАЛ СТАРТА: Приглашаем пользователя говорить
    show_notification(
        "Слушаю вас! Озвучьте свой запрос в микрофон...", 
        icon="audio-input-microphone", 
        timeout=5000
    )
    
    # Записываем 5 секунд сырого звука с микрофона десктопа
    subprocess.run(f"arecord -f cd -t raw -d 5 > {AUDIO_RAW}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Конвертируем в идеальный для Vosk формат (16000Гц, 1 канал, WAV)
    subprocess.run(f"ffmpeg -y -f s16le -ar 44100 -ac 2 -i {AUDIO_RAW} -ar 16000 -ac 1 {AUDIO_WAV}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if not os.path.exists(AUDIO_WAV):
        show_notification("Ошибка: Аудиофайл записи не сформирован.", icon="dialog-error")
        sys.exit(1)
        
    # show_notification("Обработка и распознавание запроса...", icon="applications-science", timeout=2000)
    
    try:
        # Отправляем аудиофайл по сети на Cubi
        with open(AUDIO_WAV, 'rb') as f:
            files = {'file': ('voice.wav', f, 'audio/wav')}
            response = requests.post(SERVER_URL, files=files, timeout=10)
            
        if response.status_code == 200:
            result = response.json()
            status = result.get("status")
            mode = result.get("mode")
            
            # 🌟 2. ДИНАМИЧЕСКИЙ РАЗБОР ОТВЕТОВ СЕРВЕРА СИСУБИ
            if status == "success" and mode == "syntax":
                cmd = result.get("command")
                if cmd == "pause":
                    show_notification("Плеер поставлен на паузу ⏸️", icon="media-playback-pause")
                elif cmd == "play":
                    show_notification("Плеер продолжает воспроизведение ▶️", icon="media-playback-start")
                elif cmd == "volume_up":
                    show_notification("Громкость увеличена 🔊", icon="audio-volume-high")
                elif cmd == "volume_down":
                    show_notification("Громкость уменьшена 🔉", icon="audio-volume-low")
                elif cmd == "status":
                    # Фича "Что играет?"
                    track_info = result.get("track", "Информация о треке отсутствует.")
                    show_notification(track_info, icon="media-optical-audio", title="🎵 Сейчас играет:")

            elif status == "success" and mode == "syntax_yargy":
                playlist_name = result.get("playlist", "Неизвестный")
                show_notification(f"Загружен плейлист:\n{playlist_name} 🎶", icon="media-playlist-normal")
                
            elif status == "ignored":
                reason = result.get("reason")
                text = result.get("recognized_text", "")
                if reason == "empty_speech":
                    show_notification("Команда не распознана. Повторите громче.", icon="dialog-warning")
                else:
                    show_notification(f"Фраза: \"{text}\"\nСемантика e5 отключена offline.", icon="dialog-information")
        else:
            show_notification(f"Ошибка связи с Cubi: Код {response.status_code}", icon="dialog-error")
            
    except requests.exceptions.RequestException as e:
        show_notification("Не удалось связаться с ИИ-станцией по сети.", icon="network-disconnect")
        print(f"Ошибка: {e}", file=sys.stderr)
        
    finally:
        # Чистим временные файлы на десктопе
        for f in [AUDIO_RAW, AUDIO_WAV]:
            if os.path.exists(f): os.remove(f)

if __name__ == "__main__":
    main()

