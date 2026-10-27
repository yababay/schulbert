#!/usr/bin/env python3
import os
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Импортируем обновленный, совместимый со Svelte функционал
from command_checker import process_rest_remote_action, get_media_catalog_data
from audio_conveyor import record_voice_to_text, process_cascade_routing
from track_checker import extract_meaningful_part

BASE_DIR = Path(__file__).resolve().parent
from dotenv import load_dotenv
load_dotenv(dotenv_path=BASE_DIR / '.env')

# Настраиваем root_path='/api' для полной бесшовной интеграции со старым Svelte-фронтендом
app = FastAPI(title="Schulbert Media Server Core", root_path='/api')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TextQuery(BaseModel):
    query: str

def run_fallback_semantic_e5(raw_text: str):
    """Резервный ход: векторная база отключена до расширения физической памяти"""
    return {"status": "ignored", "reason": "Семантическое ИИ-ядро отключено до апгрейда ОЗУ"}

# --- МАРШРУТЫ ДЛЯ ГОЛОСОВОГО КОНВЕЙЕРА (ДЕСКТОП И МИКРОФОН) ---

@app.post("/text-search")
async def text_search(data: TextQuery):
    raw_text = data.query.strip()
    print(f"📥 [Сервер /text-search]: Буквы с десктопа: \"{raw_text}\"")
    
    routing = process_cascade_routing(raw_text)
    if routing:
        from command_checker import execute_mpc
        if routing["action"] == "system_cmd":
            valid_cmds = {"play": "mpc play", "pause": "mpc pause", "next": "mpc next", "stop": "mpc stop"}
            execute_mpc(valid_cmds[routing["target"]])
            return {"status": "success", "mode": "syntax", "command": routing["target"]}
        elif routing["action"] == "load_playlist":
            p_num = routing["playlist"]
            t_num = routing["track"]
            if t_num:
                execute_mpc(f"mpc clear && mpc load \"{p_num}\" && mpc play {t_num}")
            else:
                execute_mpc(f"mpc clear && mpc load \"{p_num}\" && mpc play")
            return {"status": "success", "mode": "syntax_yargy", "playlist": f"Плейлист {p_num}"}
            
    return run_fallback_semantic_e5(raw_text)

@app.post("/voice-search")
async def voice_search(file: UploadFile = File(...)):
    temp_wav = Path(f"/tmp/{file.filename}")
    with open(temp_wav, "wb") as buffer:
        buffer.write(await file.read())
        
    raw_text = record_voice_to_text(str(temp_wav))
    if temp_wav.exists(): os.remove(temp_wav)
    if not raw_text: return {"status": "ignored"}
    
    print(f"📋 [Серверный Vosk расшифровал]: \"{raw_text}\"")
    
    routing = process_cascade_routing(raw_text)
    if routing:
        from command_checker import execute_mpc
        if routing["action"] == "system_cmd":
            valid_cmds = {"play": "mpc play", "pause": "mpc pause", "next": "mpc next", "stop": "mpc stop"}
            execute_mpc(valid_cmds[routing["target"]])
            return {"status": "success", "mode": "syntax", "command": routing["target"]}
        elif routing["action"] == "load_playlist":
            p_num = routing["playlist"]
            t_num = routing["track"]
            if t_num:
                execute_mpc(f"mpc clear && mpc load \"{p_num}\" && mpc play {t_num}")
            else:
                execute_mpc(f"mpc clear && mpc load \"{p_num}\" && mpc play")
            return {"status": "success", "mode": "syntax_yargy", "playlist": f"Плейлист {p_num}"}
            
    return run_fallback_semantic_e5(raw_text)

# --- УНИФИЦИРОВАННЫЙ REST-ШЛЮЗ ДЛЯ КЛИЕНТА SVELTE ---

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

