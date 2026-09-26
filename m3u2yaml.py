#!/usr/bin/env python3
import sys
import yaml
from pathlib import Path
from extract_tags import extract_mp3_tags

def m3u_to_yaml(m3u_path, output_yaml_path=None):
    if not Path(m3u_path).exists():
        print(f"❌ Файл не найден: {m3u_path}")
        return

    m3u_name = Path(m3u_path).stem
    playlist_number = int(Path(m3u_path).stem.split('-')[0]) if Path(m3u_path).stem.split('-')[0].isdigit() else 0

    yaml_data = {
        "playlist_title": m3u_name,
        "playlist_number": playlist_number,
        "tracks": []
    }

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

        # Извлекаем теги через единый модуль
        tags = extract_mp3_tags(line)
        if tags:
            track_entry["metadata"] = tags

        yaml_data["tracks"].append(track_entry)

    # 🌟 ИСПРАВЛЕНО: Теперь имя выходного файла строго формируется заменой расширения плейлиста
    if output_yaml_path:
        out_path = output_yaml_path
    else:
        out_path = str(Path(m3u_path).with_suffix('.yaml'))

    with open(out_path, 'w', encoding='utf-8') as out_f:
        yaml.dump(yaml_data, out_f, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)

    print(f"✅ Чистый RAG-манифест сохранен в: {out_path}")

    #out_path = output_yaml_path if output_yaml_path else f"{playlist_number}-raw.yaml"
    #with open(out_path, 'w', encoding='utf-8') as out_f:
    #    yaml.dump(yaml_data, out_f, allow_unicode=True, sort_keys=False, default_flow_style=False, indent=2)

    #print(f"✅ Черновой RAG-манифест сохранен в: {out_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 m3u2yaml.py <плейлист.m3u>")
        sys.exit(1)
    m3u_to_yaml(sys.argv[1])

