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

from fastapi import Form

# ... (весь ваш существующий код эндпоинтов /catalog и /mpc остается без изменений) ...

@app.post("/update")
async def update_track_metadata(
    playlist_id: int = Form(...),
    track_number: int = Form(...),
    title: str = Form(None),
    album: str = Form(None),
    artists: str = Form(None),
    composers: str = Form(None)
):
    """
    Реляционный обработчик для Svelte-редактора метаданных.
    Принимает FormData, нормализует справочники и обновляет tracks.
    """
    try:
        import psycopg2
        from command_checker import get_or_create_person_id, get_or_create_album_id, get_connection 
        
        DB_NAME = os.getenv('PG_DATABASE', 'player')
        DB_USER = os.getenv('PG_USER', 'player')
        DB_PASS = os.getenv('PG_PASSWORD', 'player_secure_pass')
        
        conn = get_connection() #psycopg2.connect(host="localhost", database=DB_NAME, user=DB_USER, password=DB_PASS)
        if not conn:
            return {"status": "error", "message": "Не удалось подключиться к СУБД."}
        cur = conn.cursor()
        
        # 1. Работаем со справочником альбомов
        album_id = None
        if album and album.strip():
            # Вытаскиваем текущий год, чтобы не затереть его при обновлении имени альбома
            cur.execute("SELECT release_year FROM tracks WHERE playlist_id = %s AND track_number = %s;", (playlist_number, track_number))
            current_year_row = cur.fetchone()
            current_year = current_year_row[0] if current_year_row else None
            
            # Получаем или регистрируем альбом в СУБД
            album_id = get_or_create_album_id(cur, album, current_year)

        # 2. Пересобираем массив артистов (artists_ids)
        artist_ids = []
        if artists and artists.strip():
            for part in artists.split(';'):
                p_id = get_or_create_person_id(cur, part)
                if p_id:
                    artist_ids.append(p_id)

        # 3. Пересобираем массив композиторов (composer_ids)
        composer_ids = []
        if composers and composers.strip():
            for part in composers.split(';'):
                c_id = get_or_create_person_id(cur, part)
                if c_id:
                    composer_ids.append(c_id)

        # 4. Выполняем точечное обновление записи в таблице tracks
        # Конструкция с тернарными операторами сохранит массивы или запишет NULL
        cur.execute("""
            UPDATE tracks 
            SET title = %s,
                album_id = %s,
                artist_ids = %s,
                composer_ids = %s
            WHERE playlist_id = %s AND track_number = %s;
        """, (
            title.strip() if title else None,
            album_id,
            artist_ids if artist_ids else None,
            composer_ids if composer_ids else None,
            playlist_id,
            track_number
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"📝 [СУБД]: Успешно обновлен трек {playlist_id}-{track_number} через веб-редактор.")
        return {"status": "success", "message": "Данные сохранены"}

    except Exception as e:
        print(f"❌ Ошибка веб-обновления трека: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка СУБД: {e}")


# Классический старт uvicorn
if __name__ == "__main__":
    import uvicorn
    print("🚀 [Старт]: Сетевой FastAPI-сервер запускается на порту 8080...", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=8080)

