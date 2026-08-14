import ctypes
from pathlib import Path

WORK_RAM_FIRST_ADDRESS = 0x7E0000

MEMORY_SAVE_RAM = 0
MEMORY_WORK_RAM = 2

ENVIRONMENT_GET_CAN_DUPE = 3
ENVIRONMENT_GET_SYSTEM_DIRECTORY = 9
ENVIRONMENT_SET_PIXEL_FORMAT = 10
ENVIRONMENT_GET_SAVE_DIRECTORY = 31

environment_callback_type = ctypes.CFUNCTYPE(ctypes.c_bool, ctypes.c_uint, ctypes.c_void_p)
video_refresh_callback_type = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_uint,
                                               ctypes.c_uint, ctypes.c_size_t)
audio_sample_callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int16, ctypes.c_int16)
audio_sample_batch_callback_type = ctypes.CFUNCTYPE(ctypes.c_size_t,
                                                    ctypes.POINTER(ctypes.c_int16),
                                                    ctypes.c_size_t)
input_poll_callback_type = ctypes.CFUNCTYPE(None)
input_state_callback_type = ctypes.CFUNCTYPE(ctypes.c_int16, ctypes.c_uint, ctypes.c_uint,
                                             ctypes.c_uint, ctypes.c_uint)


class GameInfo(ctypes.Structure):
    _fields_ = [("path", ctypes.c_char_p),
                ("data", ctypes.c_void_p),
                ("size", ctypes.c_size_t),
                ("meta", ctypes.c_char_p)]


class LibretroCore:
    def __init__(self, core_file: Path, temporary_directory: Path):
        self.library = ctypes.CDLL(str(core_file))
        self.library.retro_get_memory_data.restype = ctypes.c_void_p
        self.library.retro_get_memory_size.restype = ctypes.c_size_t
        self.library.retro_load_game.restype = ctypes.c_bool

        self.held_buttons = frozenset()
        self.temporary_directory = ctypes.c_char_p(str(temporary_directory).encode())
        self.retained_callbacks = [
            environment_callback_type(self.on_environment),
            video_refresh_callback_type(lambda *arguments: None),
            audio_sample_callback_type(lambda *arguments: None),
            audio_sample_batch_callback_type(lambda samples, frame_count: frame_count),
            input_poll_callback_type(lambda: None),
            input_state_callback_type(self.on_input_state),
        ]
        self.library.retro_set_environment(self.retained_callbacks[0])
        self.library.retro_init()
        self.library.retro_set_video_refresh(self.retained_callbacks[1])
        self.library.retro_set_audio_sample(self.retained_callbacks[2])
        self.library.retro_set_audio_sample_batch(self.retained_callbacks[3])
        self.library.retro_set_input_poll(self.retained_callbacks[4])
        self.library.retro_set_input_state(self.retained_callbacks[5])
        self.retained_rom_buffer = None

    def on_environment(self, command: int, data: int) -> bool:
        if command == ENVIRONMENT_SET_PIXEL_FORMAT:
            return True
        if command in (ENVIRONMENT_GET_SYSTEM_DIRECTORY, ENVIRONMENT_GET_SAVE_DIRECTORY):
            ctypes.cast(data, ctypes.POINTER(ctypes.c_char_p))[0] = self.temporary_directory
            return True
        if command == ENVIRONMENT_GET_CAN_DUPE:
            ctypes.cast(data, ctypes.POINTER(ctypes.c_bool))[0] = True
            return True
        return False

    def on_input_state(self, port: int, device: int, index: int, button: int) -> int:
        return 1 if port == 0 and button in self.held_buttons else 0

    def load_rom(self, rom_file: Path) -> None:
        rom_bytes = rom_file.read_bytes()
        self.retained_rom_buffer = ctypes.create_string_buffer(rom_bytes, len(rom_bytes))
        game_info = GameInfo(path=str(rom_file).encode(),
                             data=ctypes.cast(self.retained_rom_buffer, ctypes.c_void_p),
                             size=len(rom_bytes), meta=None)
        if not self.library.retro_load_game(ctypes.byref(game_info)):
            raise SystemExit(f"the emulator core refused to load {rom_file}")

    def unload_rom(self) -> None:
        self.library.retro_unload_game()

    def shut_down(self) -> None:
        self.library.retro_deinit()

    def run_frames(self, frame_count: int, held_buttons=frozenset(),
                   frozen_work_ram: dict = {}) -> None:
        self.held_buttons = frozenset(held_buttons)
        for _ in range(frame_count):
            self.library.retro_run()
            for snes_address, value in frozen_work_ram.items():
                self.write_work_ram(snes_address, bytes([value]))
        self.held_buttons = frozenset()

    def memory_size(self, memory_id: int) -> int:
        return self.library.retro_get_memory_size(memory_id)

    def read_memory(self, memory_id: int) -> bytes:
        return ctypes.string_at(self.library.retro_get_memory_data(memory_id),
                                self.memory_size(memory_id))

    def write_save_ram(self, contents: bytes) -> None:
        save_ram_size = self.memory_size(MEMORY_SAVE_RAM)
        if len(contents) > save_ram_size:
            raise SystemExit(f"{len(contents)} bytes do not fit in {save_ram_size} of save RAM")
        pointer = self.library.retro_get_memory_data(MEMORY_SAVE_RAM)
        ctypes.memset(pointer, 0x00, save_ram_size)
        ctypes.memmove(pointer, contents, len(contents))

    def read_save_ram(self, length: int) -> bytes:
        return self.read_memory(MEMORY_SAVE_RAM)[:length]

    def read_work_ram(self, snes_address: int, length: int = 1) -> bytes:
        offset = snes_address - WORK_RAM_FIRST_ADDRESS
        return self.read_memory(MEMORY_WORK_RAM)[offset:offset + length]

    def write_work_ram(self, snes_address: int, contents: bytes) -> None:
        pointer = self.library.retro_get_memory_data(MEMORY_WORK_RAM)
        ctypes.memmove(pointer + snes_address - WORK_RAM_FIRST_ADDRESS,
                       contents, len(contents))
