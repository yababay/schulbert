#!/usr/bin/env python3
import sys
from yargy import Parser, rule, or_
from yargy.pipelines import morph_pipeline

# Лингвистические правила для команд управления
STOP_MARKERS = morph_pipeline(['стоп', 'останови', 'выключи музыку', 'тишина'])
PAUSE_MARKERS = morph_pipeline(['пауза', 'паузу', 'приостанови', 'подожди'])
PLAY_MARKERS = morph_pipeline(['играй', 'продолжи', 'воспроизведение', 'старт', 'запусти'])
NEXT_MARKERS = morph_pipeline(['следующий', 'дальше', 'вперед', 'переключи'])

COMMAND_RULE = or_(
    STOP_MARKERS.interpretation('stop'),
    PAUSE_MARKERS.interpretation('pause'),
    PLAY_MARKERS.interpretation('play'),
    NEXT_MARKERS.interpretation('next')
)

command_parser = Parser(COMMAND_RULE)

def check_system_command(text):
    """
    Проверяет, содержит ли текст системную команду управления.
    Возвращает строку ('stop', 'pause', 'play', 'next') или None.
    """
    clean_text = " ".join(text.lower().split()).strip()
    match = command_parser.find(clean_text)
    if match:
        return match.interpretation
    return None

if __name__ == "__main__":
    # Быстрый встроенный тест работоспособности
    assert check_system_command("сделай паузу пожалуйста") == "pause"
    assert check_system_command("включи следующую песню") == "next"
    print("✅ Модуль command_checker.py успешно прошел внутреннюю валидацию!")

