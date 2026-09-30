#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import psycopg2
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Импортируем зеркальный конвейер модулей на стороне сервера
from command_checker import check_system_command
from playlist_checker import check_playlist_phrase
from track_checker import check_direct_track_target, extract_meaningful_part

# Настройка окружения Cubi
BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

DB_USER = os.getenv('PG_USER', 'player')
DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')

E5_MODEL_PATH = str(BASE_DIR / "models" / "multilingual-e5-large")

app = FastAPI(title="Schulbert Media Server Core")

# Инициализация модели ИИ (если папка существует, сервер подгрузит её)
model = None
if os.path.exists(E5_MODEL_PATH) and any(Path(E5_MODEL_PATH).iterdir()):
    try:
        from sentence_transformers import SentenceTransformer
        print("🧠 [ИИ-Ядро]: Загрузка нейросети multilingual-e5-large...")
        model = SentenceTransformer(E5_MODEL_PATH)
    except ImportError:
        print("⚠️ Предупреждение: sentence_transformers не установлены. ИИ-поиск отключен.")

class TextQuery(BaseModel):
    query: str

def run_local_mpc_action(playlist_num, track_num=None):
    """Физическое управление локальным плеером MPD на Cubi через mpc"""
    try:
        # Очищаем текущую очередь и загружаем целевой плейлист
        subprocess.run(["mpc", "clear"], stdout=subprocess.DEVNULL)
        subprocess.run(["mpc", "load", str(playlist_num)], stdout=subprocess.DEVNULL)
        
        # Если указан конкретный трек — прыгаем на него, иначе просто запускаем
        if track_num is not None:
            subprocess.run(["mpc", "play", str(track_num)], stdout=subprocess.DEVNULL)
        else:
            subprocess.run(["mpc", "play"], stdout=subprocess.DEVNULL)
        return True
    except Exception as e:
        print(f"❌ Ошибка вызова mpc на Cubi: {e}")
        return False

def execute_system_mpc_cmd(cmd):
    """Выполнение базовых команд управления очередью"""
    if cmd in ["play", "pause", "next", "stop"]:
        subprocess.run(["mpc", cmd], stdout=subprocess.DEVNULL)

# =====================================================================
# 🌟 НОВАЯ УМНАЯ ТОЧКА ВХОДА ДЛЯ ПРИЕМА ЛЕГКОГО ТЕКСТА
# =====================================================================
@app.post("/text-search")
async def text_search(data: TextQuery):
    raw_speech = data.query.strip()
    if not raw_speech:
        raise HTTPException(status_code=400, detail="Пустой текстовый запрос")

    print(f"📥 [Сервер /text-search]: Приняты буквы: \"{raw_speech}\"")

    # -----------------------------------------------------------------
    -- РУБЕЖ 1: Серверная проверка системных команд (play, pause, next)
    # -----------------------------------------------------------------
    system_cmd = check_system_command(raw_speech)
    if system_cmd:
        print(f"🎯 [Сервер Каскад 1]: Выполнение команды управления: {system_cmd}")
        execute_system_mpc_cmd(system_cmd)
        return {"status": "success", "mode": "syntax", "command": system_cmd}

    # -----------------------------------------------------------------
    # РУБЕЖ 2: Серверная проверка явного номера плейлиста
    # -----------------------------------------------------------------
    playlist_num = check_playlist_phrase(raw_speech)
    if playlist_num:
        print(f"🎯 [Сервер Каскад 2]: Найдена числовая фраза. Загрузка плейлиста {playlist_num}")
        run_local_mpc_action(playlist_num)
        return {"status": "success", "mode": "syntax_yargy", "playlist": f"Плейлист №{playlist_num}"}

    # -----------------------------------------------------------------
    # РУБЕЖ 3: Серверная проверка таблицы «галлюцинаций» и точных имен
    # -----------------------------------------------------------------
    direct_target = check_direct_track_target(raw_speech)
    if direct_target:
        p_num = direct_target["load"]
        t_num = direct_target["track"]
        print(f"🎯 [Сервер Каскад 3]: Реляционное совпадение в СУБД. Наведение: load={p_num}, track={t_num}")
        run_local_mpc_action(p_num, t_num)
        return {"status": "success", "mode": "syntax_yargy", "playlist": f"Целевой трек ({p_num}, {t_num})"}

    # -----------------------------------------------------------------
    # РУБЕЖ 4: ДЕФОЛТНЫЙ ВЕКТОРНЫЙ RAG-ПОИСК E5 СРЕДСТВАМИ PGVECTOR
    # -----------------------------------------------------------------
    if model is None:
        print("💡 [Сервер]: Модель e5 не инициализирована в ОЗУ. Семантический поиск недоступен.")
        return {"status": "ignored", "reason": "ИИ-модель отключена до апгрейда памяти"}

    print("🌌 [Сервер Каскад 4]: Включение семантического поиска через pgvector...")
    meaningful_text = extract_meaningful_part(raw_speech)
    
    try:
        # Генерируем вектор для смыслового остатка (строго с префиксом query: по канону e5)
        query_vector = model.encode(f"query: {meaningful_text}").tolist()
        
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        
        # Делаем Cosine Distance ИИ-поиск по векторам в СУБД (оператор <=>)
        cur.execute("""
            SELECT playlist_number, track_number, title, artist 
            FROM tracks 
            WHERE embedding IS NOT NULL AND playlist_number >= 1000
            ORDER BY embedding <=> %s::vector 
            LIMIT 1;
        """, (json.dumps(query_vector),))
        
        ai_track = cur.fetchone()
        cur.close()
        conn.close()
        
        if ai_track:
            pl_num, tr_num, title, artist = ai_track
            print(f"🚀 [ИИ-Успех]: Модель e5 нашла ассоциацию: {artist} - {title} (Плейлист {pl_num})")
            run_local_mpc_action(pl_num, tr_num)
            return {
                "status": "success",
                "mode": "semantic_e5",
                "display_text": f"{artist} — {title}"
            }
            
    except Exception as err:
        print(f"❌ Ошибка выполнения ИИ-запроса в pgvector: {err}")

    return {"status": "ignored", "reason": "Ассоциаций в базе данных не найдено"}

# Старый эндпоинт управления через веб (mpc) сохраняем для совместимости пульта
@app.post("/api/mpc")
async def api_mpc(load: int = None, track: int = None, cmd: str = None):
    if cmd:
        execute_system_mpc_cmd(cmd)
        return {"status": "success"}
    if load:
        run_local_mpc_action(load, track)
        return {"status": "success"}
    raise HTTPException(status_code=400, detail="Неверные параметры REST")

# Классический старт uvicorn
if __name__ == "__main__":
    import uvicorn
    print("🚀 [Старт]: Сетевой FastAPI-сервер запускается на порту 8080...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)

