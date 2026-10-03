#!/usr/bin/env python3
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Импортируем готовый канонический функционал обратной совместимости
from command_checker import (
    process_rest_remote_action,
    get_media_catalog_data
)
from audio_conveyor import record_voice_to_text, process_cascade_routing
from track_checker import extract_meaningful_part

BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

E5_MODEL_PATH = str(BASE_DIR / "models" / "multilingual-e5-large")

# 🌟 СОХРАНЯЕМ СТАРЫЙ КОРНЕВОЙ ПУТЬ ДЛЯ БЕСШОВНОЙ РАБОТЫ SVELTE
app = FastAPI(title="Schulbert Media Server Core", root_path='/api')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = None
if os.path.exists(E5_MODEL_PATH) and any(Path(E5_MODEL_PATH).iterdir()):
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(E5_MODEL_PATH)
    except ImportError:
        pass

class TextQuery(BaseModel):
    query: str

def run_fallback_semantic_e5(raw_text: str):
    if model is None:
        return {"status": "ignored", "reason": "ИИ-модель отключена"}
    meaningful_text = extract_meaningful_part(raw_text)
    try:
        query_vector = model.encode(f"query: {meaningful_text}").tolist()
        import psycopg2
        DB_NAME = os.getenv('PG_DATABASE', 'player')
        conn = psycopg2.connect(host="localhost", database=DB_NAME, user=os.getenv('PG_USER', 'player'), password=os.getenv('PG_PASSWORD'))
        cur = conn.cursor()
        cur.execute("""
            SELECT playlist_number, track_number FROM tracks 
            WHERE embedding IS NOT NULL AND playlist_number >= 1000
            ORDER BY embedding <=> %s::vector LIMIT 1;
        """, (json.dumps(query_vector),))
        ai_track = cur.fetchone()
        cur.close()
        conn.close()
        
        if ai_track:
            from command_checker import execute_mpc_action
            execute_mpc_action(ai_track[0], ai_track[1])
            return {"status": "success", "mode": "semantic_e5"}
    except Exception:
        pass
    return {"status": "ignored"}

# =====================================================================
# ЗЕРКАЛЬНЫЕ И СОВМЕСТИМЫЕ РУЧКИ ДЛЯ ФРОНТЕНДА SVELTE И ГОЛОСА
# =====================================================================

@app.post("/text-search")
async def text_search(data: TextQuery):
    raw_text = data.query.strip()
    routing = process_cascade_routing(raw_text)
    if routing:
        from command_checker import execute_system_mpc_cmd, execute_mpc_action
        if routing["action"] == "system_cmd":
            execute_system_mpc_cmd(routing["target"])
            return {"status": "success", "mode": "syntax", "command": routing["target"]}
        elif routing["action"] == "load_playlist":
            execute_mpc_action(routing["playlist"], routing["track"])
            return {"status": "success", "mode": "syntax_yargy", "playlist": f"Плейлист {routing['playlist']}"}
    return run_fallback_semantic_e5(raw_text)

@app.post("/voice-search")
async def voice_search(file: UploadFile = File(...)):
    temp_wav = Path(f"/tmp/{file.filename}")
    with open(temp_wav, "wb") as buffer:
        buffer.write(await file.read())
    raw_text = record_voice_to_text(str(temp_wav))
    if temp_wav.exists(): os.remove(temp_wav)
    if not raw_text: return {"status": "ignored"}
    
    routing = process_cascade_routing(raw_text)
    if routing:
        from command_checker import execute_system_mpc_cmd, execute_mpc_action
        if routing["action"] == "system_cmd":
            execute_system_mpc_cmd(routing["target"])
            return {"status": "success", "mode": "syntax", "command": routing["target"]}
        elif routing["action"] == "load_playlist":
            execute_mpc_action(routing["playlist"], routing["track"])
            return {"status": "success", "mode": "syntax_yargy", "playlist": f"Плейлист {routing['playlist']}"}
    return run_fallback_semantic_e5(raw_text)

# 🌟 ЭТАЛОННЫЙ РЕСТ-ШЛЮЗ К MPC (ПОЛНАЯ УНИФИКАЦИЯ С СТАРЫМ ФРОНТЕНДОМ)
@app.post("/mpc")
@app.get("/mpc")
async def mpc_network_remote(
    action: str = Query(None, description="Действие: play, pause, toggle, next, prev, clear, status"),
    volume: str = Query(None, description="Изменение громкости, например: +5, -10, 50"),
    load: str = Query(None, description="Номер плейлиста для поиска и загрузки"),
    track: int = Query(None, description="Номер трека в плейлисте для мгновенного запуска")
):
    res = process_rest_remote_action(action, volume, load, track)
    if res.get("status") == "error":
        raise HTTPException(status_code=400, detail=res.get("message"))
    return res

# 🌟 ЭТАЛОННЫЙ КАТАЛОГ (ЛЕВАЯ И ПРАВАЯ ПАНЕЛЬ ДЛЯ SVELTE В ОДИН КЛИК)
@app.get("/catalog")
async def get_media_catalog(id: int = Query(None, description="ID плейлиста для получения его треков")):
    res = get_media_catalog_data(id)
    if res.get("status") == "error":
        raise HTTPException(status_code=500, detail=res.get("message"))
    return res

# Классический старт uvicorn
if __name__ == "__main__":
    import uvicorn
    print("🚀 [Старт]: Сетевой FastAPI-сервер запускается на порту 8080...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)

