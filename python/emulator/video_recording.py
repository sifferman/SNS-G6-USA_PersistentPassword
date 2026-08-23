import subprocess
from pathlib import Path

from PIL import Image

from emulator.libretro_core import (
    LIBRETRO_PIXEL_FORMAT_0RGB1555,
    LIBRETRO_PIXEL_FORMAT_RGB565,
    LIBRETRO_PIXEL_FORMAT_XRGB8888,
    CapturedFrame,
)
from emulator.video_overlay import VIDEO_HEIGHT, VIDEO_WIDTH, VideoOverlay

PILLOW_RAW_MODE_BY_LIBRETRO_PIXEL_FORMAT = {
    LIBRETRO_PIXEL_FORMAT_0RGB1555: "BGR;15",
    LIBRETRO_PIXEL_FORMAT_XRGB8888: "BGRX",
    LIBRETRO_PIXEL_FORMAT_RGB565: "BGR;16",
}
BYTES_PER_PIXEL_OF_XRGB8888 = 4

SUPER_NINTENDO_FRAMES_PER_SECOND = "60000/1001"
PIPED_FFMPEG_PIXEL_FORMAT = "rgb24"
CONSTANT_RATE_FACTOR = "18"


def pillow_raw_mode_of(captured_frame: CapturedFrame) -> str:
    pixel_format_the_frames_actually_use = (
        LIBRETRO_PIXEL_FORMAT_XRGB8888
        if captured_frame.bytes_per_pixel == BYTES_PER_PIXEL_OF_XRGB8888
        else captured_frame.declared_libretro_pixel_format)
    return PILLOW_RAW_MODE_BY_LIBRETRO_PIXEL_FORMAT[pixel_format_the_frames_actually_use]


class VideoRecording:
    def __init__(self, output_video_file: Path):
        self.output_video_file = output_video_file
        self.overlay = VideoOverlay()
        self.encoder = None
        self.check_name = ""
        self.power_on_count = 0
        self.frames_since_hard_reset = 0
        self.most_recent_frame = None
        self.frames_written = 0

    def announce_check(self, check_name: str) -> None:
        self.check_name = check_name

    def announce_hard_reset(self) -> None:
        self.power_on_count += 1
        self.frames_since_hard_reset = 0

    def started_encoder(self) -> subprocess.Popen:
        self.output_video_file.parent.mkdir(parents=True, exist_ok=True)
        command = ["ffmpeg", "-y", "-loglevel", "error",
                   "-f", "rawvideo",
                   "-pixel_format", PIPED_FFMPEG_PIXEL_FORMAT,
                   "-video_size", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
                   "-framerate", SUPER_NINTENDO_FRAMES_PER_SECOND,
                   "-i", "-",
                   "-c:v", "libx264", "-preset", "veryfast", "-crf", CONSTANT_RATE_FACTOR,
                   "-pix_fmt", "yuv420p", str(self.output_video_file)]
        try:
            return subprocess.Popen(command, stdin=subprocess.PIPE)
        except FileNotFoundError:
            raise SystemExit("ffmpeg is needed to record video, and is not installed.\n"
                             "On Debian or Ubuntu: sudo apt install ffmpeg")

    def write_frame(self, captured_frame: CapturedFrame, held_buttons: frozenset) -> None:
        self.most_recent_frame = captured_frame
        frame = Image.frombytes("RGB", (captured_frame.width, captured_frame.height),
                                captured_frame.pixels, "raw", pillow_raw_mode_of(captured_frame))
        if frame.size != (VIDEO_WIDTH, VIDEO_HEIGHT):
            frame = frame.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.NEAREST)
        self.overlay.draw_on(frame, self.check_name, self.power_on_count,
                             self.frames_since_hard_reset, held_buttons)
        if self.encoder is None:
            self.encoder = self.started_encoder()
        self.encoder.stdin.write(frame.tobytes())
        self.frames_written += 1
        self.frames_since_hard_reset += 1

    def repeat_previous_frame(self, held_buttons: frozenset) -> None:
        if self.most_recent_frame is not None:
            self.write_frame(self.most_recent_frame, held_buttons)

    def finish(self) -> None:
        if self.encoder is None:
            print("No frames were captured, so no video was written.")
            return
        self.encoder.stdin.close()
        self.encoder.wait()
        print(f"Wrote {self.frames_written} frames to {self.output_video_file}")
