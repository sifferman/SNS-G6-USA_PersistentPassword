import re
import zipfile
from pathlib import Path

INPUT_LOG_MEMBER_NAME = "Input Log.txt"
LOG_KEY_PREFIX = "LogKey:"

LIBRETRO_BUTTON_BY_RECORDED_NAME = {
    "P1 B": 0,
    "P1 Y": 1,
    "P1 Select": 2,
    "P1 Start": 3,
    "P1 Up": 4,
    "P1 Down": 5,
    "P1 Left": 6,
    "P1 Right": 7,
    "P1 A": 8,
    "P1 X": 9,
    "P1 L": 10,
    "P1 R": 11,
}


def input_log_text_of(recording_file: Path) -> str:
    with zipfile.ZipFile(recording_file) as archive:
        return archive.read(INPUT_LOG_MEMBER_NAME).decode("utf-8")


def recorded_button_names_of(input_log_text: str) -> list[str]:
    for line in input_log_text.splitlines():
        if line.startswith(LOG_KEY_PREFIX):
            sections = line[len(LOG_KEY_PREFIX):].split("#")
            return [name for name in sections[-1].split("|") if name]
    raise SystemExit("the recording has no LogKey line")


def held_buttons_per_frame(recording_file: Path) -> list[frozenset]:
    input_log_text = input_log_text_of(recording_file)
    button_names = recorded_button_names_of(input_log_text)
    frames = []
    for line in input_log_text.splitlines():
        if not re.fullmatch(r"\|[^|]*\|[^|]*\|", line):
            continue
        recorded_buttons = line.split("|")[2]
        frames.append(frozenset(
            LIBRETRO_BUTTON_BY_RECORDED_NAME[button_names[position]]
            for position, character in enumerate(recorded_buttons)
            if character != "." and button_names[position] in LIBRETRO_BUTTON_BY_RECORDED_NAME))
    return frames
