#!/usr/bin/env python3
import re
import sys
import yaml
from pathlib import Path
from extract_tags import extract_mp3_tags

def m3u_to_yaml(m3u_path, output_yaml_path=None):
    if not Path(m3u_path).exists():
        print(f"❌ Файл не найден: {m3u_path}")
        return

    m3u_name = Path(m3u_path).stem
    # Надежно вытаскиваем только первые цифры регулярным выражением (например, "5000")
    playlist_match = re.search(r'^\d+', m3u_name)
    playlist_number = int(playlist_match.group(0)) if playlist_match else 0

    # 🌟 ИСПРАВЛЕНО: Строим строго структурированный корневой узел playlist согласно ТЗ
    yaml_data = {
        "playlist": {
            "title": m3u_name,
            "number": playlist_number,
            "tracks": []
        }
    }

    print(f"📂 [m3u2yaml]: Анализ плейлиста {m3u_path} (Номер: {playlist_number})...")

    with open(m3u_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    track_counter = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        track_counter += 1
        track_entry = {
            "track_number": track_counter,
            "file_path": line
        }

        # Извлекаем теги через наш общий модуль extract_tags.py
        tags = extract_mp3_tags(line)
        if tags:
            track_entry["metadata"] = tags

        # 🌟 ИСПРАВЛЕНО: Добавляем трек внутрь иерархического списка playlist.tracks
        yaml_data["playlist"]["tracks"].append(track_entry)

    # Вычисляем имя выходного файла (заменяем расширение .m3u на .yaml)
    if output_yaml_path:
        out_path = output_yaml_path
    else:
        out_path = str(Path(m3u_path).with_suffix('.yaml'))

    with open(out_path, 'w', encoding='utf-8') as out_f:
        # allow_unicode=True сохраняет кириллицу буквами
        # sort_keys=False удерживает последовательный порядок полей
        yaml.dump(yaml_data, out_f, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)

    print(f"✅ Иерархический RAG-манифест сохранен в: {out_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 m3u2yaml.py <плейлист.m3u>")
        sys.exit(1)
    m3u_to_yaml(sys.argv[1])

