#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import psycopg2
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from pydantic import BaseModel

# Импортируем наш сквозной конвейер
from audio_conveyor import record_voice_to_text, process_cascade_routing
from track_checker import extract_meaningful_part

BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

DB_NAME = os.getenv('PG_DATABASE', 'player')
DB_USER = os.getenv('PG_USER', 'player')
DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')
E5_MODEL_PATH = str(BASE_DIR / "models" / "multilingual-e5-large")

app = FastAPI(title="Schulbert Media Server Core")

# Инициализация ИИ e5
model = None
if os.path.exists(E5_MODEL_PATH) and any(Path(E5_MODEL_PATH).iterdir()):
    try:
        from sentence_transformers import SentenceTransformer
        print("🧠 [ИИ-Ядро]: Инициализация модели multilingual-e5-large...")
        model = SentenceTransformer(E5_MODEL_PATH)
    except ImportError:
        pass

class TextQuery(BaseModel):
    query: str

def run_mpc_load(playlist_num, track_num=None):
    subprocess.run(["mpc", "clear"], stdout=subprocess.DEVNULL)
    subprocess.run(["mpc", "load", str(playlist_num)], stdout=subprocess.DEVNULL)
    if track_num is not None:
        subprocess.run(["mpc", "play", str(track_num)], stdout=subprocess.DEVNULL)
    else:
        subprocess.run(["mpc", "play"], stdout=subprocess.DEVNULL)

def run_mpc_cmd(cmd):
    if cmd in ["play", "pause", "next", "stop"]:
        subprocess.run(["mpc", cmd], stdout=subprocess.DEVNULL)

def execute_routing_instruction(routing, raw_text):
    """Вспомогательный исполнитель команд, сгенерированных конвейером"""
    if routing["action"] == "system_cmd":
        run_mpc_cmd(routing["target"])
        return {"status": "success", "mode": "syntax", "command": routing["target"]}
    elif routing["action"] == "load_playlist":
        run_mpc_load(routing["playlist"], routing["track"])
        return {"status": "success", "mode": "syntax_yargy", "playlist": f"Цель ({routing['playlist']}, {routing['track']})"}
    return {"status": "ignored"}

def run_fallback_semantic_e5(raw_text):
    """Резервный ход: векторный ИИ-поиск по pgvector"""
    if model is None:
        return {"status": "ignored", "reason": "ИИ-ядро отключено до расширения памяти"}
        
    print("🌌 [ИИ-Ядро]: Включение семантического поиска e5...")
    meaningful_text = extract_meaningful_part(raw_text)
    try:
        query_vector = model.encode(f"query: {meaningful_text}").tolist()
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        cur = conn.cursor()
        cur.execute("""
            SELECT playlist_number, track_number, title, artist FROM tracks 
            WHERE embedding IS NOT NULL AND playlist_number >= 1000
            ORDER BY embedding <=> %s::vector LIMIT 1;
        """, (json.dumps(query_vector),))
        ai_track = cur.fetchone()
        cur.close()
        conn.close()
        
        if ai_track:
            pl_num, tr_num, title, artist = ai_track
            print(f"🚀 [ИИ-Успех]: Найдена ассоциация: {artist} - {title}")
            run_mpc_load(pl_num, tr_num)
            return {"status": "success", "mode": "semantic_e5", "display_text": f"{artist} — {title}"}
    except Exception as e:
        print(f"❌ Ошибка pgvector: {e}")
    return {"status": "ignored"}

# =====================================================================
# ЭНДПОИНТ 1: ПРИЕМ ГОТОВЫХ БУКВ С ДЕСКТОПА (Экономия трафика)
# =====================================================================
@app.post("/text-search")
async def text_search(data: TextQuery):
    raw_text = data.query.strip()
    print(f"📥 [Эндпоинт /text-search]: Принят текст: \"{raw_text}\"")
    
    # Прогоняем через сквозной конвейер
    routing = process_cascade_routing(raw_text)
    if routing:
        return execute_routing_instruction(routing, raw_text)
        
    # Если каскад промолчал — отдаем на откуп ИИ
    return run_fallback_semantic_e5(raw_text)

# =====================================================================
# ЭНДПОИНТ 2: ПРИЕМ СЫРОГО АУДИО С КОНТРОЛЛЕРА (Универсальный вход)
# =====================================================================
@app.post("/voice-search")
async def voice_search(file: UploadFile = File(...)):
    print(f"📥 [Эндпоинт /voice-search]: Принят аудиофайл {file.filename}")
    
    # Сохраняем временный файл во временную директорию Cubi
    temp_wav = Path(f"/tmp/{file.filename}")
    with open(temp_wav, "wb") as buffer:
        buffer.write(await file.read())
        
    # Превращаем звук в буквы через встроенную в конвейер функцию Vosk
    raw_text = record_voice_to_text(str(temp_wav))
    if temp_wav.exists(): 
        os.remove(temp_wav)
        
    if not raw_text:
        return {"status": "ignored", "reason": "Vosk на сервере не смог разобрать звук"}
        
    print(f"📋 [Серверный Vosk расшифровал]: \"{raw_text}\"")
    
    # Передаем расшифрованный текст в ТОТ ЖЕ САМЫЙ сквозной конвейер!
    routing = process_cascade_routing(raw_text)
    if routing:
        return execute_routing_instruction(routing, raw_text)
        
    return run_fallback_semantic_e5(raw_text)

# Старый REST-интерфейс пульта сохраняем для совместимости
@app.post("/api/mpc")
async def api_mpc(load: int = None, track: int = None, cmd: str = None):
    if cmd: run_mpc_cmd(cmd)
    if load: run_mpc_load(load, track)
    return {"status": "success"}

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

# Классический старт uvicorn
if __name__ == "__main__":
    import uvicorn
    print("🚀 [Старт]: Сетевой FastAPI-сервер запускается на порту 8080...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)

