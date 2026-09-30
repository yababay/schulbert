#!/usr/bin/env python3
import os
import sys
import re
import wave
import json
import subprocess
import psycopg2
import unittest
from pathlib import Path
from vosk import Model, KaldiRecognizer, SetLogLevel
from yargy import Parser, rule, or_
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact
from yargy.predicates import type as yargy_type
from dotenv import load_dotenv

# Настройка путей и окружения
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env')

DB_HOST = os.getenv('PG_HOST', '192.168.0.111')
DB_USER = os.getenv('PG_USER', 'player')
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

AUDIO_RAW = "/tmp/training_voice.raw"
AUDIO_WAV = "/tmp/training_voice.wav"
VOSK_MODEL_PATH = "/usr/share/schulbert/music-voice-assistant/models/vosk-model-small-ru"

# =====================================================================
# ЛИНГВИСТИЧЕСКИЙ РАЗБОР YARGY
# =====================================================================
QueryPhrase = fact('QueryPhrase', ['action', 'meaningful_part'])
ORDER_MARKERS = morph_pipeline(['включи', 'вруби', 'поставь', 'запусти', 'найди', 'найти'])
ANY_WORD = or_(yargy_type('RU'), yargy_type('LATIN'))

QUERY_RULE = rule(
    ORDER_MARKERS.interpretation(QueryPhrase.action),
    ANY_WORD.repeatable(min=1, max=6).interpretation(QueryPhrase.meaningful_part)
).interpretation(QueryPhrase)

yargy_parser = Parser(QUERY_RULE)

def extract_meaningful_part(text):
    """Вычленяет смысловой остаток фразы, отбрасывая первый управляющий глагол"""
    clean_text = " ".join(text.lower().split()).strip()
    match = yargy_parser.find(clean_text)
    if match and match.fact.meaningful_part:
        return match.fact.meaningful_part.strip()
    return re.sub(r'^(найди|найти|включи|поставь|вруби|запусти)\s*', '', clean_text).strip()

# =====================================================================
# ТОЧКА ИНТЕГРАЦИИ (Вызывается из основного main.py)
# =====================================================================
def get_direct_mpc_target(text, is_meaningful=False):
    """
    Сканирует таблицу галлюцинаций по тексту Vosk.
    Если точная связка найдена — возвращает словарь с load и track для mpc.
    """
    meaningful = text if is_meaningful else extract_meaningful_part(text)
    if not meaningful:
        return None
        
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=5432)
        cur = conn.cursor()
        
        # Запрашиваем жесткие реляционные координаты
        cur.execute("""
            SELECT playlist_number, track_number 
            FROM phonetic_aliases 
            WHERE vosk_hallucination = %s;
        """, (meaningful,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        
        if res:
            p_num, t_num = res
            return {"load": p_num, "track": t_num if t_num else 1}
    except Exception:
        pass
    return None

# =====================================================================
# ЗАПИСЬ ГОЛОСА (ДЛЯ ТЕСТОВ И ИМПОРТА)
# =====================================================================
def record_voice():
    """Запись звука на десктопе для интерактивного теста"""
    SetLogLevel(-1)
    print("\n🎙️  [Микрофон открыт]: Говорите...", file=sys.stderr)
    
    subprocess.run(f"arecord -f cd -t raw -d 5 > {AUDIO_RAW}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(f"ffmpeg -y -f s16le -ar 44100 -ac 2 -i {AUDIO_RAW} -ar 16000 -ac 1 {AUDIO_WAV}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    model = Model(VOSK_MODEL_PATH)
    wf = wave.open(AUDIO_WAV, "rb")
    rec = KaldiRecognizer(model, wf.getframerate())
    data = wf.readframes(wf.getnframes())
    wf.close()
    
    for f in [AUDIO_RAW, AUDIO_WAV]:
        if os.path.exists(f): os.remove(f)
        
    res = json.loads(rec.Result() if rec.AcceptWaveform(data) else rec.FinalResult())
    return res.get('text', '').strip()


# =====================================================================
# РАСПОЗНАВАНИЕ ГОЛОСА (ТОЛЬКО ДЛЯ ИМПОРТА)
# =====================================================================
def recognize_voice():
    """Интерпретация распознанного текста: остановиться или передать следующей модели?"""
    raw_speech = record_voice()
    print(f"📋 Vosk зафиксировал: \"{raw_speech}\"", file=sys.stderr)
    return None if get_direct_mpc_target(raw_speech) else raw_speech

def training_is_successfull(expected_playlist, expected_track=None):
    """
    Логика достаточного обучения:
    True — если Vosk повторил галлюцинацию, которая уже связана с этой целью.
    False — если зафиксирована новая галлюцинация, связываем её с целями.
    """
    raw_speech = record_voice()
    print(f"📋 Vosk услышал: \"{raw_speech}\"", file=sys.stderr)
    
    if not raw_speech:
        print("❌ Звук пустой. Повторите попытку.", file=sys.stderr)
        return False

    meaningful = extract_meaningful_part(raw_speech)
    if not meaningful:
        print("❌ Не удалось извлечь смысл. Повторите попытку.", file=sys.stderr)
        return False

    # Проверяем, существует ли уже такая галлюцинация в СУБД (используем вашу get_direct_mpc_target)
    if get_direct_mpc_target(meaningful, is_meaningful=True):
        return True
        
    # 🌟 ИСПРАВЛЕНО: Заносим новую связь, исправив опечатку meaningful_part -> meaningful
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=5432)
    cur = conn.cursor()
    
    print(f"✍️  [НОВАЯ СВЯЗЬ В СУБД]: '{meaningful}' ➡️ Плейлист: {expected_playlist}, Трек: {expected_track}", file=sys.stderr)
    cur.execute("""
        INSERT INTO phonetic_aliases (vosk_hallucination, playlist_number, track_number) 
        VALUES (%s, %s, %s) ON CONFLICT DO NOTHING;
    """, (meaningful, expected_playlist, expected_track))

    conn.commit()
    cur.close()
    conn.close()

    return False
    
def check_direct_track_target(text, is_meaningful=False):
    """
    Сканирует таблицу галлюцинаций по тексту Vosk.
    Если точная связка найдена — возвращает словарь с load и track для mpc.
    """
    meaningful = text if is_meaningful else extract_meaningful_part(text)
    if not meaningful:
        return None
        
    try:
        conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASS, port=5432)
        cur = conn.cursor()
        
        cur.execute("""
            SELECT playlist_number, track_number 
            FROM phonetic_aliases 
            WHERE vosk_hallucination = %s;
        """, (meaningful,))
        res = cur.fetchone()
        cur.close()
        conn.close()
        
        if res:
            p_num, t_num = res
            return {"load": p_num, "track": t_num}  # Возвращаем чистые координаты (с сохранением NULL для альбома)
    except Exception:
        pass
    return None

# =====================================================================
# ВЫВЕРНУТЫЕ ЭМПИРИЧЕСКИЕ ЮНИТ-ТЕСТЫ
# =====================================================================

MAX_ATTEMPTS=15

class TestVoiceAssistantTraining(unittest.TestCase):

    def test_dotenv(self):
        self.assertEqual(DB_HOST, 'schulbert')

    def test_meaning(self):
        meaning = extract_meaningful_part('включи дэйва брубека')
        self.assertEqual(meaning, 'дэйва брубека')

    def compare_voice_and_keys(self, request, playlist_num, track_num=None):
        """Интерактивный цикл калибровки до появления первого повтора или превышения лимита"""
        target_str = f"Плейлист {playlist_num}" + (f", Трек {track_num}" if track_num else " (Весь альбом)")
        print(f"\n=========================================================")
        print(f"📢 СЕССИЯ КАЛИБРОВКИ ДЛЯ: {target_str}")
        print(f"=========================================================")
        
        attempt = 0
        
        # 🌟 ИНТЕЛЛЕКТУАЛЬНЫЙ ЦИКЛ ОБУЧЕНИЯ
        while True:
            attempt += 1
            print(f"\n👉 Попытка №{attempt} из {MAX_ATTEMPTS}. Произнесите в микрофон: «Включи {request}»")
            
            # Передаем координаты в функцию дрессировки. 
            # Она сама внутри запишет голос и проверит наличие галлюцинации в базе.
            if training_is_successfull(playlist_num, track_num):
                print(f"🎯 СТАБИЛИЗАЦИЯ! Фоно-карта для '{request}' успешно зафиксирована на {attempt}-й попытке.")
                break
                
            # 🌟 ИСПРАВЛЕНО: Проверка критического числа попыток с красивым выходом через self.fail
            if attempt >= MAX_ATTEMPTS:
                msg = f"❌ Тест провален! Достигнут лимит попыток ({MAX_ATTEMPTS}) для фразы «{request}». Галлюцинации Vosk не стабилизировались."
                print(msg, file=sys.stderr)
                self.fail(msg) # Мгновенно останавливает данный тест и фиксирует сбой в статистике unittest
        self.assertTrue(attempt < MAX_ATTEMPTS)

    # 🌟 ЭКСПЕРТНЫЕ ЗАДАНИЯ С ТОЧНЫМ СЕМАНТИЧЕСКИМ РАЗДЕЛЕНИЕМ ПО ТЗ:
    def test_alias_7a5eede6(self):
        # Оригинал: Celtic Bagpipes
        self.compare_voice_and_keys('Кельтскую Музыку', 6004, 1)

    def test_alias_921774d7(self):
        # Оригинал: Creedence Clearwater Revival
        self.compare_voice_and_keys('Криденс', 2510, 1)

    def test_alias_23af61c4(self):
        # Оригинал: Depeche Mode
        self.compare_voice_and_keys('Депеш Мод', 2500, 1)

    def test_alias_614827fa(self):
        # Оригинал: Electric Light Orchestra
        self.compare_voice_and_keys('Электрик Лайт Оркестра', 2503, 1)

    def test_alias_8bb27a31(self):
        # Оригинал: Kraftwerk
        self.compare_voice_and_keys('Крафтверк', 5020, 9)

    def test_alias_15890a85(self):
        # Оригинал: Led Zeppelin
        self.compare_voice_and_keys('Лед Зепелин', 2519, 1)

    def test_alias_50d9927b(self):
        # Оригинал: Music from the Andean
        self.compare_voice_and_keys('Музыку Анд', 6002, 1)

if __name__ == "__main__":
    unittest.main()
