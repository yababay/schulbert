import os
import re
import sys
from mutagen.mp3 import MP3
from mutagen.id3 import ID3NoHeaderError

# Строгий список разрешенных тегов проекта «Шульберт»
ALLOWED_TAGS = {
    'album', 'genre', 'title', 'artist', 'publisher', 
    'form', 'instrument', 'style', 'period', 'date'
}

# Карта маппинга стандартных ID3v2 фреймов
ID3_MAP = {
    'TIT2': 'title',
    'TPE1': 'artist',
    'TALB': 'album',
    'TCON': 'genre',
    'TPUB': 'publisher',
    'TDRC': 'date',
    'TYER': 'date'
}

def clean_text(value) -> str:
    """Очищает строку от управляющих символов и лишних пробелов"""
    if not value:
        return ""
    if isinstance(value, list):
        value = " ".join([str(x) for x in value])
    text = str(value).strip()
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text

def extract_mp3_tags(file_path) -> dict:
    """
    Единая функция извлечения метаданных из MP3 файла для всего проекта.
    Возвращает словарь только с разрешенными тегами, либо пустой словарь.
    """
    metadata = {}
    if not os.path.exists(file_path):
        return metadata

    try:
        audio = MP3(file_path)
        if audio.tags:
            for frame_id, frame in audio.tags.items():
                key = None
                value = ""
                
                # Обработка пользовательских текстовых тегов TXXX
                if frame_id.startswith("TXXX:"):
                    txxx_desc = frame_id.split(":", 1)[1].lower()
                    if txxx_desc in ALLOWED_TAGS:
                        key = txxx_desc
                        value = frame.text[0] if frame.text else ""
                # Обработка стандартных ID3 фреймов
                elif frame_id in ID3_MAP:
                    key = ID3_MAP[frame_id]
                    value = frame.text[0] if frame.text else ""
                
                if key and key in ALLOWED_TAGS:
                    cleaned_val = clean_text(value)
                    if key == "genre":
                        cleaned_val = re.sub(r'\s*\(\d+\)$', '', cleaned_val)
                    if cleaned_val:
                        metadata[key] = cleaned_val
                        
    except ID3NoHeaderError:
        pass  # Штатная ситуация: у файла просто нет тегов
    except Exception as e:
        print(f"⚠️ Ошибка чтения тегов в {file_path}: {e}", file=sys.stderr)

    return metadata

