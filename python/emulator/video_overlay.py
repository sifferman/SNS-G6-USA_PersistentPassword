from functools import cache

from PIL import Image, ImageDraw, ImageFont

from emulator.libretro_core import LIBRETRO_BUTTON_BY_NAME

VIDEO_WIDTH = 512
VIDEO_HEIGHT = 448

TITLE_FONT_SIZE = 16
LABEL_FONT_SIZE = 13
TEXT_MARGIN = 5
UNALIASED_MASK_MODE = "1"

BAR_BACKGROUND_COLOUR = (0, 0, 0)
TITLE_COLOUR = (255, 255, 255)
POWER_ON_COUNT_COLOUR = (176, 176, 176)

TITLE_BAR_HEIGHT = 22
SECOND_ROW_TOP = TITLE_BAR_HEIGHT
SECOND_ROW_HEIGHT = 18

HARD_RESET_BANNER_COLOUR = (192, 32, 32)
HARD_RESET_BANNER_TEXT = "HARD RESET"
HARD_RESET_BANNER_FRAMES = 90

INPUT_MONITOR_HEIGHT = 24
INPUT_MONITOR_BUTTON_WIDTH = 22
INPUT_MONITOR_BUTTON_HEIGHT = 16
INPUT_MONITOR_BUTTON_GAP = 2
HELD_BUTTON_COLOUR = (255, 216, 64)
RELEASED_BUTTON_COLOUR = (64, 64, 64)
HELD_BUTTON_LABEL_COLOUR = (0, 0, 0)
RELEASED_BUTTON_LABEL_COLOUR = (176, 176, 176)

INPUT_MONITOR_BUTTON_LABELS = (
    ("L", "L"),
    ("UP", "UP"),
    ("DN", "DOWN"),
    ("LT", "LEFT"),
    ("RT", "RIGHT"),
    ("SE", "SELECT"),
    ("ST", "START"),
    ("Y", "Y"),
    ("X", "X"),
    ("B", "B"),
    ("A", "A"),
    ("R", "R"),
)


def first_button_left_edge() -> int:
    button_row_width = (len(INPUT_MONITOR_BUTTON_LABELS)
                        * (INPUT_MONITOR_BUTTON_WIDTH + INPUT_MONITOR_BUTTON_GAP)
                        - INPUT_MONITOR_BUTTON_GAP)
    return (VIDEO_WIDTH - button_row_width) // 2


@cache
def unaliased_text_mask(font: ImageFont.FreeTypeFont, text: str) -> Image.Image:
    left, top, right, bottom = font.getbbox(text)
    PADDING_BEYOND_THE_REPORTED_TEXT_SIZE = 4
    mask = Image.new(UNALIASED_MASK_MODE,
                     (right + PADDING_BEYOND_THE_REPORTED_TEXT_SIZE,
                      bottom + PADDING_BEYOND_THE_REPORTED_TEXT_SIZE))
    ImageDraw.Draw(mask).text((0, 0), text, font=font, fill=1)
    return mask.crop(mask.getbbox())


class VideoOverlay:
    def __init__(self):
        self.title_font = ImageFont.load_default(TITLE_FONT_SIZE)
        self.label_font = ImageFont.load_default(LABEL_FONT_SIZE)

    def draw_text(self, frame: Image.Image, left: int, top: int, text: str,
                  font: ImageFont.FreeTypeFont, colour: tuple) -> None:
        frame.paste(colour, (left, top), unaliased_text_mask(font, text))

    def draw_text_centred_in(self, frame: Image.Image, box: tuple, text: str,
                             font: ImageFont.FreeTypeFont, colour: tuple) -> None:
        left, top, right, bottom = box
        mask = unaliased_text_mask(font, text)
        frame.paste(colour, (left + (right - left - mask.width) // 2,
                             top + (bottom - top - mask.height) // 2), mask)

    def draw_title_bar(self, frame: Image.Image, check_name: str) -> None:
        canvas = ImageDraw.Draw(frame)
        canvas.rectangle((0, 0, VIDEO_WIDTH, TITLE_BAR_HEIGHT), fill=BAR_BACKGROUND_COLOUR)
        self.draw_text_centred_in(frame, (TEXT_MARGIN, 0, VIDEO_WIDTH, TITLE_BAR_HEIGHT),
                                  check_name, self.title_font, TITLE_COLOUR)

    def draw_power_on_count(self, frame: Image.Image, power_on_count: int) -> None:
        text = f"power on {power_on_count}"
        mask_width = unaliased_text_mask(self.label_font, text).width
        left = VIDEO_WIDTH - mask_width - TEXT_MARGIN
        ImageDraw.Draw(frame).rectangle(
            (left - TEXT_MARGIN, SECOND_ROW_TOP, VIDEO_WIDTH, SECOND_ROW_TOP + SECOND_ROW_HEIGHT),
            fill=BAR_BACKGROUND_COLOUR)
        self.draw_text_centred_in(frame, (left, SECOND_ROW_TOP, left + mask_width,
                                          SECOND_ROW_TOP + SECOND_ROW_HEIGHT),
                                  text, self.label_font, POWER_ON_COUNT_COLOUR)

    def draw_hard_reset_banner(self, frame: Image.Image) -> None:
        mask_width = unaliased_text_mask(self.label_font, HARD_RESET_BANNER_TEXT).width
        banner = (0, SECOND_ROW_TOP, mask_width + 2 * TEXT_MARGIN,
                  SECOND_ROW_TOP + SECOND_ROW_HEIGHT)
        ImageDraw.Draw(frame).rectangle(banner, fill=HARD_RESET_BANNER_COLOUR)
        self.draw_text_centred_in(frame, banner, HARD_RESET_BANNER_TEXT,
                                  self.label_font, TITLE_COLOUR)

    def draw_input_monitor(self, frame: Image.Image, held_buttons: frozenset) -> None:
        strip_top = VIDEO_HEIGHT - INPUT_MONITOR_HEIGHT
        canvas = ImageDraw.Draw(frame)
        canvas.rectangle((0, strip_top, VIDEO_WIDTH, VIDEO_HEIGHT), fill=BAR_BACKGROUND_COLOUR)
        button_top = strip_top + (INPUT_MONITOR_HEIGHT - INPUT_MONITOR_BUTTON_HEIGHT) // 2
        for position, (label, name) in enumerate(INPUT_MONITOR_BUTTON_LABELS):
            left = (first_button_left_edge()
                    + position * (INPUT_MONITOR_BUTTON_WIDTH + INPUT_MONITOR_BUTTON_GAP))
            box = (left, button_top,
                   left + INPUT_MONITOR_BUTTON_WIDTH, button_top + INPUT_MONITOR_BUTTON_HEIGHT)
            held = LIBRETRO_BUTTON_BY_NAME[name] in held_buttons
            canvas.rectangle(box, fill=HELD_BUTTON_COLOUR if held else RELEASED_BUTTON_COLOUR)
            self.draw_text_centred_in(
                frame, box, label, self.label_font,
                HELD_BUTTON_LABEL_COLOUR if held else RELEASED_BUTTON_LABEL_COLOUR)

    def draw_on(self, frame: Image.Image, check_name: str, power_on_count: int,
                frames_since_hard_reset: int, held_buttons: frozenset) -> None:
        self.draw_title_bar(frame, check_name)
        self.draw_power_on_count(frame, power_on_count)
        if frames_since_hard_reset < HARD_RESET_BANNER_FRAMES:
            self.draw_hard_reset_banner(frame)
        self.draw_input_monitor(frame, held_buttons)
