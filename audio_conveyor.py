#!/usr/bin/env python3
import os
import sys
import json
import wave
import subprocess
from pathlib import Path
from vosk import Model, KaldiRecognizer, SetLogLevel

# Импортируем наши атомарные чекеры
from command_checker import check_system_command
from playlist_checker import check_playlist_phrase
from track_checker import check_direct_track_target

BASE_DIR = Path(__file__).resolve().parent
AUDIO_RAW = "/tmp/server_voice.raw"
VOSK_MODEL_PATH = "/usr/share/schulbert/music-voice-assistant/models/vosk-model-small-ru"

def record_voice_to_text(audio_wav_path):
    """
    Вынесено сюда: физическое декодирование входящего WAV-файла 
    или локальная запись через Vosk в текстовую строку.
    """
    if not os.path.exists(audio_wav_path):
        return ""
    try:
        SetLogLevel(-1)
        if not os.path.exists(VOSK_MODEL_PATH):
            print(f"⚠️  [Конвейер]: Модель Vosk не найдена по пути {VOSK_MODEL_PATH}", file=sys.stderr)
            return ""
            
        model = Model(VOSK_MODEL_PATH)
        wf = wave.open(audio_wav_path, "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        data = wf.readframes(wf.getnframes())
        wf.close()
        
        res = json.loads(rec.Result() if rec.AcceptWaveform(data) else rec.FinalResult())
        return res.get('text', '').strip()
    except Exception as e:
        print(f"⚠️  [Конвейer]: Ошибка Vosk: {e}", file=sys.stderr)
        return ""

def process_cascade_routing(raw_text):
    """
    🌟 ЕДИНЫЙ КАСКАДНЫЙ СЕРДЦЕВИННЫЙ КОНВЕЙЕР «СТАРОЙ ШКОЛЫ»
    Принимает текст, последовательно прогоняет через чекеры.
    Возвращает словарь-инструкцию для выполнения или None.
    """
    clean_text = raw_text.strip()
    if not clean_text:
        return None

    # РУБЕЖ 1: Проверка системных команд управления (play, pause, next, stop)
    system_cmd = check_system_command(clean_text)
    if system_cmd:
        return {"action": "system_cmd", "target": system_cmd}

    # РУБЕЖ 2: Проверка численных фраз номеров плейлистов через Yargy
    playlist_num = check_playlist_phrase(clean_text)
    if playlist_num:
        return {"action": "load_playlist", "playlist": playlist_num, "track": None}

    # РУБЕЖ 3: Проверка экспертной таблицы галлюцинаций СУБД
    direct_target = check_direct_track_target(clean_text)
    if direct_target:
        return {
            "action": "load_playlist", 
            "playlist": direct_target["load"], 
            "track": direct_target["track"]
        }

    # Если каскад пуст — старая школа бессильна, нужен векторный ИИ
    return None
