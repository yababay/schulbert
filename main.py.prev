import os
import re
import io
import json
import wave
import subprocess
import psycopg2
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Query
from vosk import Model as VoskModel, KaldiRecognizer, SetLogLevel

# 🌟 ИМПОРТЫ КОМПОНЕНТОВ YARGY
from yargy import Parser, rule, or_
from yargy.predicates import gram
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Глушим отладочный C++ шум Vosk для чистоты серверных логов
SetLogLevel(-1)

app = FastAPI(root_path='/api')

# Базовые пути проекта
BASE_DIR = Path(__file__).resolve().parent
VOSK_MODEL_PATH = str(BASE_DIR / "models" / "vosk-model-small-ru")
E5_MODEL_PATH = str(BASE_DIR / "models" / "multilingual-e5-large")

PG_USER = os.getenv("PG_USER", "player")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")
PG_DATABASE = os.getenv("PG_DATABASE", "player")


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

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# ... (весь предыдущий импорт, грамматика Yargy, функция execute_mpc и эндпоинт /voice-search остаются без изменений) ...

# 🌟 ВАЖНО ДЛЯ SVELTE: Разрешаем CORS-запросы, чтобы фронтенд, запущенный на другом порту 
# или на десктопе, мог беспрепятственно общаться с API нашего Cubi
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В локальной сети можно открыть для всех
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# 5. REST-ИНТЕРФЕЙС УПРАВЛЕНИЯ ПЛЕЕРОМ (Расширенный)
# =====================================================================

def execute_mpc(command: str):
    """
    Универсальная функция безопасного выполнения команд mpc.
    Подавляет вывод в stdout/stderr, чтобы не засорять системный лог journalctl,
    и корректно отрабатывает цепочки команд через оператор &&.
    """
    try:
        # shell=True необходим, так как мы используем цепочки команд через '&&' и кавычки
        subprocess.run(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при выполнении системной команды mpc: {e}")
    except Exception as e:
        print(f"❌ Непредвиденное исключение при вызове mpc: {e}")

@app.post("/mpc")
@app.get("/mpc")
def mpc_network_remote(
    action: str = Query(None, description="Действие: play, pause, toggle, next, prev, clear, status"),
    volume: str = Query(None, description="Изменение громкости, например: +5, -10, 50"),
    load: str = Query(None, description="4-значный номер плейлиста для поиска и загрузки, например: 2022"),
    track: int = Query(None, description="Номер трека в плейлисте для мгновенного запуска, например: 5")
):
    """Универсальный сетевой шлюз к утилите mpc с поддержкой выбора трека и считывания статуса."""
    executed_commands = []

    # 🌟 ОБРАБОТКА ХОЛОДНОГО СТАТУСА (Выносим в приоритетную проверку)
    if action == "status":
        print("🕹️ [REST-Пульт]: Запрос статуса воспроизведения и громкости")
        
        # 1. Получаем текущую песню (Исполнитель - Название)
        res_track = subprocess.run("mpc current", shell=True, capture_output=True, text=True)
        current_track = res_track.stdout.strip()
        
        # 2. Вычисляем состояние паузы. В mpc при паузе вторая строка вывода содержит "[paused]"
        res_state = subprocess.run("mpc", shell=True, capture_output=True, text=True)
        if "[paused]" in res_state.stdout:
            current_track += " [paused]"
            
        # 3. Вытаскиваем точное число громкости
        res_vol = subprocess.run("mpc volume", shell=True, capture_output=True, text=True)
        volume_value = 50  # Дефолт на случай n/a
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

    # --- ВСЯ ОСТАЛЬНАЯ ВАША СТАНДАРТНАЯ РАБОЧАЯ ЛОГИКА ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ ---
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
            raise HTTPException(status_code=400, detail=f"Неизвестное действие '{action}'")

    if volume:
        if re.match(r'^[+-]?\d+$', volume):
            execute_mpc(f"mpc volume {volume}")
            executed_commands.append(f"volume: {volume}")
        else:
            raise HTTPException(status_code=400, detail="Неверный формат громкости")

    # Модернизированный блок загрузки плейлиста и трека
    if load:
        if re.match(r'^\d{1,4}$', load):
            prefix = f"{int(load):04d}"
            full_playlist_name = find_full_playlist_name(prefix)
            
            if full_playlist_name:
                print(f"🕹️ [REST-Пульт]: По префиксу {prefix} загружаю \"{full_playlist_name}\"")
                
                # Если передан номер трека, мы очищаем, загружаем плейлист, но команду 'play' 
                # вызываем с указанием конкретной позиции в очереди (mpc play X)
                if track and track > 0:
                    execute_mpc(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play {track}")
                    executed_commands.append(f"load_playlist: {full_playlist_name}, play_track: {track}")
                else:
                    execute_mpc(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play")
                    executed_commands.append(f"load_playlist: {full_playlist_name}")
            else:
                raise HTTPException(status_code=444, detail=f"Плейлист с префиксом {prefix}- не найден")
        else:
            raise HTTPException(status_code=400, detail="Номер плейлиста должен состоять только из цифр")
    
    # Если передали ТОЛЬКО номер трека (без параметра load) — переключаем внутри текущего играющего списка
    elif track and track > 0:
        execute_mpc(f"mpc play {track}")
        executed_commands.append(f"play_track_in_current: {track}")

    if not executed_commands:
        return {"status": "ignored", "message": "Не передано параметров."}

    return {"status": "success", "mode": "rest_remote", "executed": executed_commands}


# =====================================================================
# 6. JSON-ЭНДПОИНТ ДЛЯ БУДУЩЕГО SVELTE-ФРОНТЕНДА (Каталог фонотеки)
# =====================================================================
@app.get("/catalog")
def get_media_catalog(id: int = Query(None, description="ID плейлиста для получения его треков")):
    """
    Эндпоинт отдает структуру данных нашей фонотеки.
    Без параметров: список всех уникальных плейлистов (для левой панели).
    С параметром ?id=2022: список песен выбранного плейлиста (для правой панели).
    """
    # 🔌 Подключаемся к нашей очищенной PostgreSQL от имени пользователя player
    # (В будущем эти параметры будут красиво стягиваться из файла .env)
    try:
        # conn = psycopg2.connect("dbname=player user=player host=localhost")
        conn = psycopg2.connect(f"dbname={PG_DATABASE} user={PG_USER} password={PG_PASSWORD} host=localhost")
        cur = conn.cursor()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка подключения к СУБД: {e}")

    # РЕЖИМ А: Запрос треков конкретного плейлиста (Правая панель Svelte)
    if id is not None:
        cur.execute("""
            SELECT track_number, title, artist, album 
            FROM tracks 
            WHERE playlist_number = %s 
            ORDER BY track_number ASC;
        """, (id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        tracks_list = []
        for row in rows:
            tracks_list.append({
                "track_number": row[0],
                "title": row[1],
                "artist": row[2],
                "album": row[3]
            })
        return {"mode": "playlist_tracks", "playlist_id": id, "total": len(tracks_list), "tracks": tracks_list}

    # РЕЖИМ Б: Запрос списка всех плейлистов (Левая панель Svelte, исключая черновики < 1000)
    cur.execute("""
        SELECT DISTINCT playlist_number, COALESCE(album, 'Плейлист ' || playlist_number) 
        FROM tracks 
        WHERE playlist_number >= 1000 
        ORDER BY playlist_number ASC;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    playlists_list = []
    for row in rows:
        playlists_list.append({
            "playlist_id": row[0],
            "name": row[1]
        })
    return {"mode": "playlists_index", "total": len(playlists_list), "playlists": playlists_list}

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

        # 🚀 ЭТАП 1: Быстрые синтаческо-голосовые команды управления плеером
        if any(word in raw_text for word in ["пауза", "стоп", "останови"]):
            # 🌟 ЗАДЕЙСТВОВАНО ЕДИНООБРАЗИЕ
            execute_mpc("mpc pause")
            return {"status": "success", "mode": "syntax", "command": "pause"}
            
        if any(word in raw_text for word in ["играй", "продолжи", "запусти"]):
            # 🌟 ЗАДЕЙСТВОВАНО ЕДИНООБРАЗИЕ
            execute_mpc("mpc play")
            return {"status": "success", "mode": "syntax", "command": "play"}
            
        if any(word in raw_text for word in ["громче", "добавь звук"]):
            # 🌟 ЗАДЕЙСТВОВАНО ЕДИНООБРАЗИЕ
            execute_mpc("mpc volume +10")
            return {"status": "success", "mode": "syntax", "command": "volume_up"}
            
        if any(word in raw_text for word in ["тише", "убавь звук"]):
            # 🌟 ЗАДЕЙСТВОВАНО ЕДИНООБРАЗИЕ
            execute_mpc("mpc volume -10")
            return {"status": "success", "mode": "syntax", "command": "volume_down"}

        # Запрос статуса текущего трека (оставляем с capture_output, так как тут нам критически нужен вывод mpc)
        if any(word in raw_text for word in ["что играет", "статус", "трек", "инфо", "информация"]):
            print("🕹️ [Команда]: Запрос статуса воспроизведения")
            res_mpc = subprocess.run("mpc current", shell=True, capture_output=True, text=True)
            current_track = res_mpc.stdout.strip()
            if not current_track:
                current_track = "Воспроизведение остановлено или очередь пуста."
            return {"status": "success", "mode": "syntax", "command": "status", "track": current_track}

        # 🚀 ЭТАП 2: Парсим номер плейлиста строго через ваш оригинальный Yargy-модуль
        playlist_number = check_playlist_phrase(raw_text)
        
        if playlist_number > 0:
            print(f"🎯 [Yargy триумф]: Извлечен номер: {playlist_number}")
            prefix = f"{playlist_number:04d}"
            
            # Ищем полное имя файла в медиатеке
            full_playlist_name = find_full_playlist_name(prefix)
            
            if full_playlist_name:
                print(f"🎵 Найдено полное совпадение в mpd: \"{full_playlist_name}\"")
                
                # 🌟 ЗАДЕЙСТВОВАНО ЕДИНООБРАЗИЕ ДЛЯ ГОЛОСОВОГО КАНАЛА
                execute_mpc(f"mpc clear && mpc load \"{full_playlist_name}\" && mpc play")
                
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

