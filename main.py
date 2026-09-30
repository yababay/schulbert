#!/usr/bin/env python3
import os
import sys
import json
import subprocess
import psycopg2
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File
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

# Классический старт uvicorn
if __name__ == "__main__":
    import uvicorn
    print("🚀 [Старт]: Сетевой FastAPI-сервер запускается на порту 8080...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)

