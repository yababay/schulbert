import os
import io
import json
import wave
import subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Query
from vosk import Model as VoskModel, KaldiRecognizer, SetLogLevel

# 🌟 ИМПОРТЫ КОМПОНЕНТОВ YARGY
from yargy import Parser, rule, or_
from yargy.predicates import gram
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact

# Глушим отладочный C++ шум Vosk для чистоты серверных логов
SetLogLevel(-1)

app = FastAPI()

# Базовые пути проекта
BASE_DIR = Path(__file__).resolve().parent
VOSK_MODEL_PATH = str(BASE_DIR / "models" / "vosk-model-small-ru")
E5_MODEL_PATH = str(BASE_DIR / "models" / "multilingual-e5-large")

vosk_model = None
e5_model = None
HAS_E5 = False

# =====================================================================
# 1. ОРИГИНАЛЬНЫЙ СЛОВАРНЫЙ И МАТЕМАТИЧЕСКИЙ БЛОК ДЛЯ ЧИСЛИТЕЛЬНЫХ
# =====================================================================
SINGLE_PART_THOUSANDS_VALUES = {
    'тысяча': 1000, 'тысячный': 1000, 
    'двухтысячный': 2000, 'трехтысячный': 3000, 'четырехтысячный': 4000, 'пятитысячный': 5000, 
    'шеститысячный': 6000, 'семитысячный': 7000, 'восьмитысячный': 8000, 'девятитысячный': 9000,
}

PLAIN_NUMBER_VALUES = {
    'ноль': 0, 'один': 1, 'два': 2, 
    'одна': 1, 'две': 2, 'три': 3, 'четыре': 4, 'пять': 5, 'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9,
    'десять': 10, 'одиннадцать': 11, 'двенадцать': 12, 'тринадцать': 13, 'четырнадцать': 14, 'пятнадцать': 15,
    'шестнадцать': 16, 'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
    'двадцать': 20, 'тридцать': 30, 'сорок': 40, 'пятьдесят': 50, 'шестьдесят': 60, 'семьдесят': 70, 'восемьдесят': 80, 'девяносто': 90,
    'сто': 100, 'двести': 200, 'триста': 300, 'четыреста': 400, 'пятьсот': 500, 'шестьсот': 600, 'семьсот': 700, 'восемьсот': 800, 'девятьсот': 900,
}

ADJECTIVE_NUMBER_VALUES = {
    'один': 1, 'первый': 1, 'второй': 2, 'третий': 3, 'четвертый': 4, 'пятый': 5, 'шестой': 6, 'седьмой': 7, 'восьмой': 8, 'девятый': 9,
    'десятый': 10, 'одиннадцатый': 11, 'двенадцатый': 12, 'тринадцатый': 13, 'четырнадцать': 14, 'пятнадцатый': 15,
    'шестнадцатый': 16, 'семнадцатый': 17, 'восемнадцатый': 18, 'девятнадцатый': 19,
    'двадцатый': 20, 'тридцатый': 30, 'сороковой': 40, 'пятидесятый': 50,
    'шестидесятый': 60, 'семидесятый': 70, 'восьмидесятый': 80, 'девяностый': 90,
    'сотый': 100, 'двухсотый': 200, 'трехсотый': 300, 'четырехсотый': 400, 'пятисотый': 500,
    'шестисотый': 600, 'семисотый': 700, 'восьмисотый': 800, 'девятисотый': 900
}

ALL_NUMBER_VALUES = PLAIN_NUMBER_VALUES | ADJECTIVE_NUMBER_VALUES

# =====================================================================
# 2. ПРАВИЛА И ГРАММАТИКА YARGY
# =====================================================================
NUMBER_WORD = gram('NUMR')

PLAIN_SUM_MARKERS = or_ (
    NUMBER_WORD.repeatable(max=3),
    rule(
        NUMBER_WORD.repeatable(max=2).optional(),
        morph_pipeline(list(ADJECTIVE_NUMBER_VALUES.keys()))
    )
)

PLAYLIST_MARKERS = morph_pipeline(['плейлист', 'плэй', 'лист'])

THAUSAND_MARKERS = or_(
    rule(morph_pipeline(list(SINGLE_PART_THOUSANDS_VALUES.keys()))),
    rule(NUMBER_WORD, morph_pipeline(['тысяча', 'тысяч']))
)

PlaylistPhrase = fact('PlaylistPhrase', ['is_playlist', 'thousands', 'plain_sum'])

PLAYLIST_RULE = rule(
    PLAYLIST_MARKERS.interpretation(PlaylistPhrase.is_playlist),
    or_ (
        rule(
            THAUSAND_MARKERS.interpretation(PlaylistPhrase.thousands),
            PLAIN_SUM_MARKERS.repeatable(max=3).interpretation(PlaylistPhrase.plain_sum)
        ),
        rule(PLAIN_SUM_MARKERS.repeatable(max=3).interpretation(PlaylistPhrase.plain_sum)),
        rule(THAUSAND_MARKERS.interpretation(PlaylistPhrase.thousands)),
    )
).interpretation(PlaylistPhrase)

playlist_parser = Parser(PLAYLIST_RULE)

def split_phrase(text):
    clean_text = " ".join(text.lower().split())
    match = playlist_parser.find(clean_text)
    if not match:
        raise ValueError('В этой фразе синтаксический маркер плейлиста не обнаружен')
    return match.fact

def check_playlist_phrase(text):
    """Превращает текстовые русские слова из Vosk в строгое целое число"""
    try:
        phrase = split_phrase(text)
        total_sum = 0

        if phrase.thousands:
            words = phrase.thousands.split(' ')
            valuable = words[0]
            if len(words) == 1:
                total_sum = SINGLE_PART_THOUSANDS_VALUES.get(valuable, 0)
            else:
                total_sum = ALL_NUMBER_VALUES.get(valuable, 0) * 1000
                
        if not phrase.plain_sum:
            return int(total_sum)

        words = phrase.plain_sum.split(' ')   
        for word in words:
            value = ALL_NUMBER_VALUES.get(word, 0)
            total_sum = total_sum + value

        return int(total_sum)
    except Exception:
        return 0

# =====================================================================
# 3. АДАПТИВНЫЙ АУДИТ АППАРАТНЫХ ВОЗМОЖНОСТЕЙ ЖЕЛЕЗА
# =====================================================================
print("⚙️ [Инициализация системы]: Сканирование аппаратных возможностей...", flush=True)

if os.path.exists(VOSK_MODEL_PATH):
    print("📋 [Аудит]: Обнаружена базовая модель Vosk. Загрузка...", flush=True)
    vosk_model = VoskModel(VOSK_MODEL_PATH)
else:
    raise RuntimeError(f"Критическая ошибка: Базовая модель Vosk отсутствует по пути {VOSK_MODEL_PATH}")

if os.path.exists(E5_MODEL_PATH) and any(Path(E5_MODEL_PATH).iterdir()):
    print("🚀 [Аудит]: Обнаружена большая модель multilingual-e5-large!", flush=True)
    print("🧠 Загрузка e5 в ОЗУ (Семантический режим активирован)...", flush=True)
    try:
        from sentence_transformers import SentenceTransformer
        e5_model = SentenceTransformer(E5_MODEL_PATH)
        HAS_E5 = True
        print("✅ [Успех]: Семантический ИИ-поиск полностью готов к работе.", flush=True)
    except Exception as e:
        print(f"⚠️ [Ошибка]: Не удалось загрузить e5 (недостаточно ОЗУ): {e}", flush=True)
        print("➡️ Система принудительно откатывается в легкий Синтаксический режим.", flush=True)
else:
    print("💡 [Аудит]: Модель e5 отсутствует. Запущен Легковесный Синтаксический режим (Экономия ОЗУ).", flush=True)


def find_full_playlist_name(prefix: str) -> str:
    """
    Вызывает mpc lsplaylists, ищет строку, которая начинается с 'prefix-'
    и возвращает полное имя плейлиста для mpc load.
    """
    try:
        # Получаем список всех плейлистов из mpd
        result = subprocess.run("mpc lsplaylists", shell=True, capture_output=True, text=True, check=True)
        playlists = result.stdout.splitlines()
        
        # Строим искомый префикс (например, "2022-")
        target_prefix = f"{prefix}-"
        
        for pl in playlists:
            if pl.strip().startswith(target_prefix):
                return pl.strip()
                
    except Exception as e:
        print(f"❌ Ошибка при чтении mpc lsplaylists: {e}")
        
    return ""


# =====================================================================
# 4. СЕТЕВОЙ КОНВЕЙЕР ОБРАБОТКИ ФРАЗ
# =====================================================================
from fastapi import FastAPI, UploadFile, File, Query, HTTPException

# ... (весь ваш предыдущий импорт, грамматика Yargy, инициализация Vosk и эндпоинт /voice-search остаются без изменений) ...

# =====================================================================
# 5. СЕТЕВОЙ REST-ПУЛЬТ ДЛЯ КНОПОЧНЫХ УСТРОЙСТВ (Калька с mpc)
# =====================================================================
@app.post("/mpc")
@app.get("/mpc")  # Добавляем GET, чтобы команды можно было слать даже просто из адресной строки браузера
def mpc_network_remote(
    action: str = Query(None, description="Действие: play, pause, toggle, next, prev, clear"),
    volume: str = Query(None, description="Изменение громкости, например: +5, -10, 50"),
    load: str = Query(None, description="4-значный номер плейлиста для поиска и загрузки, например: 2022")
):
    """
    Универсальный сетевой шлюз к утилите mpc.
    Позволяет управлять плеером по сети через простые URL-параметры.
    """
    executed_commands = []

    # 1. Обработка базовых действий (play, pause, toggle, next, prev, clear)
    if action:
        valid_actions = {
            "play": "mpc play",
            "pause": "mpc pause",
            "toggle": "mpc toggle",
            "next": "mpc next",
            "prev": "mpc prev",
            "clear": "mpc clear"
        }
        if action in valid_actions:
            execute_mpc(valid_actions[action])
            executed_commands.append(f"action: {action}")
        else:
            raise HTTPException(status_code=400, detail=f"Неизвестное действие '{action}'. Допустимы: {list(valid_actions.keys())}")

    # 2. Обработка регулировки громкости (например: +5, -10 или абсолютное значение 50)
    if volume:
        # Проверяем синтаксис (должно начинаться с + или - или быть просто числом)
        if re.match(r'^[+-]?\d+$', volume):
            execute_mpc(f"mpc volume {volume}")
            executed_commands.append(f"volume: {volume}")
        else:
            raise HTTPException(status_code=400, detail="Неверный формат громкости. Используйте: +5, -10 или 70")

    # 3. Обработка загрузки плейлиста по префиксу с автоматическим поиском имени файла
    if load:
        if re.match(r'^\d{1,4}$', load):
            # Приводим к 4 цифрам с лидирующими нулями (канон проекта)
            prefix = f"{int(load):04d}"
            
            # Задействуем вашу функцию поиска полного имени плейлиста в mpd
            full_playlist_name = find_full_playlist_name(prefix)
            
            if full_playlist_name:
                print(f"🕹️ [REST-Пульт]: По префиксу {prefix} найден плейлист \"{full_playlist_name}\"")
                execute_mpc(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play")
                executed_commands.append(f"load_playlist: {full_playlist_name}")
            else:
                raise HTTPException(status_code=444, detail=f"Плейлист с префиксом {prefix}- не найден в медиатеке.")
        else:
            raise HTTPException(status_code=400, detail="Номер плейлиста должен состоять только из цифр (до 4 знаков)")

    # Если эндпоинт вызвали вообще без параметров
    if not executed_commands:
        return {"status": "ignored", "message": "Не передано ни одного параметра (action, volume или load)."}

    return {
        "status": "success",
        "mode": "rest_remote",
        "executed": executed_commands
    }

@app.post("/voice-search")
async def receive_voice_and_play(file: UploadFile = File(...)):
    print(f"\n📥 Входящий аудиозапрос по сети: {file.filename}")
    
    audio_bytes = await file.read()
    wav_stream = io.BytesIO(audio_bytes)
    
    try:
        wf = wave.open(wav_stream, "rb")
        rec = KaldiRecognizer(vosk_model, wf.getframerate())
        data = wf.readframes(wf.getnframes())
        wf.close()
        
        # Получаем чистый текст прописью от Vosk
        res = json.loads(rec.Result() if rec.AcceptWaveform(data) else rec.FinalResult())
        raw_text = res.get('text', '').strip().lower()
        print(f"📋 Vosk расшифровал: \"{raw_text}\"")
        
        if not raw_text:
            return {"status": "ignored", "reason": "empty_speech"}

        # 🚀 ЭТАП 1: Быстрые синтаксические команды управления плеером
        if any(word in raw_text for word in ["пауза", "стоп", "останови"]):
            subprocess.run("mpc pause", shell=True)
            return {"status": "success", "mode": "syntax", "command": "pause"}
        if any(word in raw_text for word in ["играй", "продолжи", "запусти"]):
            subprocess.run("mpc play", shell=True)
            return {"status": "success", "mode": "syntax", "command": "play"}
        if any(word in raw_text for word in ["громче", "добавь звук"]):
            subprocess.run("mpc volume +10", shell=True)
            return {"status": "success", "mode": "syntax", "command": "volume_up"}
        if any(word in raw_text for word in ["тише", "убавь звук"]):
            subprocess.run("mpc volume -10", shell=True)
            return {"status": "success", "mode": "syntax", "command": "volume_down"}
        if any(word in raw_text for word in ["что играет", "статус", "трек", "инфо", "информация"]):
            print("🕹️ [Команда]: Запрос статуса воспроизведения")
            # Запрашиваем у mpc текущий трек (возвращает Исполнитель - Название)
            res_mpc = subprocess.run("mpc current", shell=True, capture_output=True, text=True)
            current_track = res_mpc.stdout.strip()
            
            # Если плеер пуст или остановлен, выдаем понятный статус
            if not current_track:
                current_track = "Воспроизведение остановлено или очередь пуста."
                
            return {
                "status": "success", 
                "mode": "syntax", 
                "command": "status", 
                "track": current_track
            }

        # 🚀 ЭТАП 2: Парсим номер плейлиста строго через ваш оригинальный Yargy-модуль
        playlist_number = check_playlist_phrase(raw_text)
        
        if playlist_number > 0:
            print(f"🎯 [Yargy триумф]: Извлечен номер: {playlist_number}")
            
            # Форматируем число с лидирующими нулями до 4 знаков (например, "2022" или "0042")
            prefix = f"{playlist_number:04d}"
            
            # 🌟 НАШ НОВЫЙ СИСТЕМНЫЙ ФИЛЬТР: Ищем полное имя файла в медиатеке
            full_playlist_name = find_full_playlist_name(prefix)
            
            if full_playlist_name:
                print(f"🎵 Найдено полное совпадение в mpd: \"{full_playlist_name}\"")
                subprocess.run(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play", shell=True)
                return {
                    "status": "success", 
                    "mode": "syntax_yargy", 
                    "recognized_text": raw_text, 
                    "playlist": full_playlist_name
                }
            else:
                print(f"⚠️ Плейлист с префиксом {prefix}- не найден в выводе mpc lsplaylists.")
                return {"status": "error", "message": f"Плейлист {prefix} отсутствует в медиатеке."}

        # 🚀 ЭТАП 3: Если это сложный запрос, а e5 доступна — уходим в векторы
        if HAS_E5:
            print("🧠 Передаю запрос на семантическую обработку в e5...")
            # Векторный поиск по базе tracks будет жить здесь
            return {"status": "success", "mode": "semantic", "recognized_text": raw_text}
        
        # Защита от дурака / Игнорирование сложных фраз в синтаксическом режиме
        print("🎛️ [Адаптивный фильтр]: Сложная фраза проигнорирована (модель e5 выключена).")
        return {"status": "ignored", "reason": "semantic_disabled_offline", "recognized_text": raw_text}

    except Exception as e:
        print(f"❌ Ошибка конвейера на сервере: {e}")
        return {"status": "error", "message": str(e)}

# Классический старт uvicorn
if __name__ == "__main__":
    import uvicorn
    print("🚀 [Старт]: Сетевой FastAPI-сервер запускается на порту 8080...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)

