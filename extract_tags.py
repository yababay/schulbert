import os
import re
import sys
from pathlib import Path
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
    Абсолютно отказоустойчивая функция извлечения метаданных.
    Корректно читает списки Юникод-фреймов ID3v2.3/2.4 и кастомные TXXX-поля.
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
                
                # 1. Извлекаем текстовое значение фрейма (mutagen часто пакует его в список)
                if hasattr(frame, 'text') and frame.text:
                    if isinstance(frame.text, list):
                        value = " ".join([str(x) for x in frame.text])
                    else:
                        value = str(frame.text)
                else:
                    continue

                # 2. Обработка пользовательских текстовых тегов TXXX (style, form, instrument, period)
                if frame_id.startswith("TXXX:"):
                    txxx_desc = frame_id.split(":", 1)[1].strip().lower()
                    if txxx_desc in ALLOWED_TAGS:
                        key = txxx_desc
                
                # 3. Обработка стандартных ID3 фреймов (title, artist, album, genre, date)
                elif frame_id in ID3_MAP:
                    key = ID3_MAP[frame_id]
                
                # Записываем очищенный текст в итоговый словарь
                if key and key in ALLOWED_TAGS:
                    cleaned_val = clean_text(value)
                    
                    if key == "genre":
                        cleaned_val = re.sub(r'\s*\(\d+\)$', '', cleaned_val)
                        
                    if cleaned_val:
                        metadata[key] = cleaned_val
                        
    except ID3NoHeaderError:
        pass  # Файл чист, это штатно
    except Exception as e:
        print(f"⚠️ Ошибка mutagen в {file_path}: {e}", file=sys.stderr)

    # 🌟 ЗАЩИТНАЯ КАЗУИСТИКА: Если тег title по какой-то причине остался пуст,
    # мы принудительно вытянем имя файла в качестве названия трека, чтобы не нарушать NOT NULL базы!
    if not metadata.get('title'):
        file_name_stem = Path(file_path).stem
        # Очищаем имя файла от лидирующих цифр (например, "18_Devil_in_Disguise" -> "Devil in Disguise")
        cleaned_title = re.sub(r'^\d+[\s_.\-]+', '', file_name_stem).replace('_', ' ')
        metadata['title'] = cleaned_title if cleaned_title else "Неизвестный трек"

    return metadata

