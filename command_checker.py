#!/usr/bin/env python3
import sys
from yargy import Parser, rule, or_
from yargy.pipelines import morph_pipeline
from yargy.interpretation import fact

# Лингвистические правила для команд управления
STOP_MARKERS  = morph_pipeline(['стоп', 'останови', 'выключи', 'тишина'])
PAUSE_MARKERS = morph_pipeline(['пауза', 'паузу', 'приостанови', 'подожди'])
PLAY_MARKERS  = morph_pipeline(['играй', 'продолжи', 'воспроизведение', 'старт', 'запусти'])
NEXT_MARKERS  = morph_pipeline(['следующий', 'дальше', 'вперед', 'переключи'])

MPCommand = fact('MPCommand', [
        'stop',
        'pause',
        'play',
        'nxt',
    ]
)

CMD_STOP = rule(
    STOP_MARKERS.interpretation(MPCommand.stop),
)

CMD_PAUSE = rule(
    PAUSE_MARKERS.interpretation(MPCommand.pause),
)

CMD_PLAY = rule(
    PLAY_MARKERS.interpretation(MPCommand.play),
)

CMD_NEXT = rule(
    NEXT_MARKERS.interpretation(MPCommand.nxt),
)

COMMAND_RULE = or_ (
    CMD_STOP,
    CMD_PAUSE,
    CMD_PLAY,
    CMD_NEXT
).interpretation(MPCommand)

command_parser = Parser(COMMAND_RULE)

def check_system_command(text):
    """
    Проверяет, содержит ли текст системную команду управления.
    Возвращает строку ('stop', 'pause', 'play', 'next') или None.
    """
    clean_text = " ".join(text.lower().split()).strip()
    cmd = command_parser.find(clean_text)

    if not cmd: 
        return clean_text


    stop, pause, play, nxt = cmd.fact
    
    if pause:
        return 'pause'
    if stop:
        return 'stop'
    if play:
        return 'play'
    if nxt:
        return 'next'

    return clean_text

if __name__ == "__main__":
    # Быстрый встроенный тест работоспособности
    assert check_system_command("пауза") == "pause"
    assert check_system_command("играй") == "play"
    assert check_system_command("дальше") == "next"
    assert check_system_command("тишина") == "stop"
    print("✅ Модуль command_checker.py успешно прошел внутреннюю валидацию!")

