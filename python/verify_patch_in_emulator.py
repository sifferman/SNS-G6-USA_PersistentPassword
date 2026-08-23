#!/usr/bin/env python3
"""Boots the patched ROM in a headless emulator and reads work RAM and save RAM
back, to prove the patch behaves rather than only that it assembled. Needs the
base ROM as well, for the vanilla defaults and password table the expected
values are read from. Linux only.

Covers a fresh boot with no save file, a cold boot with a saved game, and
replays of the recordings in input_recordings/ that change a setting and
complete a level, each followed by a power cycle.
"""
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from emulator.input_recording import held_buttons_per_frame
from emulator.libretro_core import LibretroCore
from goof_troop_usa import memory_map
from toolchain.build_environment import (
    CHEATS_HELD_DURING_THE_LEVEL_RECORDING,
    COLD_BOOT_TO_CHANGE_SETTINGS_RECORDING,
    COLD_BOOT_TO_COMPLETE_LEVEL_1_WITH_CHEATS_RECORDING,
    FRAMES_TO_REACH_THE_TITLE_SCREEN,
    PATCHED_ROM_FILE,
    emulator_core_file,
)
from toolchain.command_line import (
    argument_parser_needing_the_tools_directory_and_base_rom,
    base_rom_file_from,
)
from toolchain.tool_installation import install_emulator_core

BLANK_SAVE_RAM = b""
SEEDED_FURTHEST_LEVEL = 3
COMPLETED_LEVEL = 1
NO_CHEATS = {}
LOW_ROM_BANK_SIZE_IN_BYTES = 0x8000


@dataclass(frozen=True)
class CheckResult:
    description: str
    passed: bool
    detail: str = ""


def read_rom_bytes_at(rom: bytes, snes_address: int, length: int) -> bytes:
    start = (((snes_address >> 16) & 0x7F) * LOW_ROM_BANK_SIZE_IN_BYTES
             + (snes_address & 0xFFFF) - 0x8000)
    return rom[start:start + length]


def offset_in_block(work_ram_address: int) -> int:
    return work_ram_address - memory_map.SETTINGS_BLOCK_IN_WORK_RAM


def password_symbols_for_level(base_rom: bytes, level: int) -> bytes:
    return read_rom_bytes_at(
        base_rom,
        memory_map.PASSWORD_TABLE_IN_ROM + level * memory_map.PASSWORD_SYMBOLS_PER_LEVEL,
        memory_map.PASSWORD_SYMBOLS_PER_LEVEL)


def settings_block_saved_at_level(base_rom: bytes, level: int) -> bytes:
    block = bytearray(read_rom_bytes_at(base_rom, memory_map.DEFAULT_SETTINGS_BLOCK_IN_ROM,
                                        memory_map.SETTINGS_BLOCK_SIZE_IN_BYTES))
    block[offset_in_block(memory_map.FURTHEST_LEVEL_REACHED_IN_WORK_RAM)] = level
    return bytes(block)


def booted_with_save_ram(core: LibretroCore, save_ram_contents: bytes) -> None:
    core.load_rom(PATCHED_ROM_FILE)
    core.write_save_ram(save_ram_contents)
    core.run_frames(FRAMES_TO_REACH_THE_TITLE_SCREEN)


def reached_the_title_screen(core: LibretroCore) -> bool:
    signature = core.read_work_ram(
        memory_map.SETTINGS_BLOCK_IN_WORK_RAM + memory_map.SETTINGS_BLOCK_SIGNATURE_OFFSET, 32)
    return memory_map.SETTINGS_BLOCK_SIGNATURE_TEXT in signature


def furthest_level(core: LibretroCore) -> int:
    return core.read_work_ram(memory_map.FURTHEST_LEVEL_REACHED_IN_WORK_RAM)[0]


def progress_level(core: LibretroCore) -> int:
    return core.read_work_ram(memory_map.PROGRESS_LEVEL_IN_WORK_RAM)[0]


def replayed_then_power_cycled(core, recording, watched_address, cheats):
    frames = held_buttons_per_frame(recording)
    core.load_rom(PATCHED_ROM_FILE)
    core.write_save_ram(BLANK_SAVE_RAM)
    for held_buttons in frames:
        core.run_frames(1, held_buttons, cheats)
    before_power_cycle = core.read_work_ram(watched_address)[0]
    saved = core.read_save_ram(memory_map.SETTINGS_BLOCK_SIZE_IN_BYTES)
    core.unload_rom()
    booted_with_save_ram(core, saved)
    return len(frames), before_power_cycle, saved, core.read_work_ram(watched_address)[0]


def check_blank_save_ram_starts_a_fresh_game(core, base_rom):
    booted_with_save_ram(core, BLANK_SAVE_RAM)
    return (
        CheckResult("the game reaches its title screen instead of the copy protection lockup",
                    reached_the_title_screen(core)),
        CheckResult("blank save RAM leaves the furthest level at zero", furthest_level(core) == 0),
        CheckResult("the password screen would preload the level zero password",
                    progress_level(core) == 0,
                    password_symbols_for_level(base_rom, 0).hex(" ")),
    )


def check_a_saved_game_is_restored_on_cold_boot(core, base_rom):
    block = bytearray(settings_block_saved_at_level(base_rom, SEEDED_FURTHEST_LEVEL))
    block[offset_in_block(memory_map.SOUND_DRIVER_UPLOADED_FLAG_IN_WORK_RAM)] = 0x01
    booted_with_save_ram(core, bytes(block))
    symbols = password_symbols_for_level(base_rom, SEEDED_FURTHEST_LEVEL)
    return (
        CheckResult(f"save RAM holding level {SEEDED_FURTHEST_LEVEL} restores it",
                    furthest_level(core) == SEEDED_FURTHEST_LEVEL
                    and progress_level(core) == SEEDED_FURTHEST_LEVEL,
                    f"password {symbols.hex(' ')}"),
        CheckResult("a saved sound driver flag does not stop it booting",
                    reached_the_title_screen(core)),
        CheckResult("the music engine is running, so sound initialisation was not skipped",
                    core.read_work_ram(memory_map.PLAYING_MUSIC_IN_WORK_RAM)[0]
                    != memory_map.NO_MUSIC_REQUESTED),
    )


def check_a_changed_setting_survives_a_power_cycle(core, base_rom):
    watched = memory_map.PLAYER_ONE_THROW_TYPE_IN_WORK_RAM
    expected = memory_map.PLAYER_ONE_THROW_TYPE_SECOND_SETTING
    frames, before, saved, after = replayed_then_power_cycled(
        core, COLD_BOOT_TO_CHANGE_SETTINGS_RECORDING, watched, NO_CHEATS)
    return (
        CheckResult("replaying the recording changes the player one throw type",
                    before == expected, f"${watched:06X} = {before:02X} after {frames} frames"),
        CheckResult("changing it writes save RAM without completing a level",
                    saved[offset_in_block(watched)] == expected),
        CheckResult("the setting is still there after a power cycle with no input",
                    after == expected),
    )


def check_completing_a_level_survives_a_power_cycle(core, base_rom):
    watched = memory_map.FURTHEST_LEVEL_REACHED_IN_WORK_RAM
    frames, before, saved, after = replayed_then_power_cycled(
        core, COLD_BOOT_TO_COMPLETE_LEVEL_1_WITH_CHEATS_RECORDING,
        watched, CHEATS_HELD_DURING_THE_LEVEL_RECORDING)
    symbols = password_symbols_for_level(base_rom, COMPLETED_LEVEL)
    return (
        CheckResult("replaying the recording completes a level",
                    before == COMPLETED_LEVEL, f"$7FFF01 = {before} after {frames} frames"),
        CheckResult("completing a level writes save RAM",
                    saved[offset_in_block(watched)] == COMPLETED_LEVEL),
        CheckResult("the progress survives a power cycle with no input",
                    after == COMPLETED_LEVEL and progress_level(core) == COMPLETED_LEVEL),
        CheckResult(f"the password screen would now preload {symbols.hex(' ')}",
                    progress_level(core) == COMPLETED_LEVEL),
    )


EMULATOR_CHECKS = (
    ("Fresh boot with no save file", check_blank_save_ram_starts_a_fresh_game),
    ("Cold boot with a saved game", check_a_saved_game_is_restored_on_cold_boot),
    ("Changing a setting and power cycling", check_a_changed_setting_survives_a_power_cycle),
    ("Completing a level and power cycling", check_completing_a_level_survives_a_power_cycle),
)


def run_and_report(core: LibretroCore, base_rom: bytes) -> int:
    failures = 0
    for section_name, run_section in EMULATOR_CHECKS:
        print(section_name)
        core.announce_check(section_name)
        for result in run_section(core, base_rom):
            failures += not result.passed
            detail = f"  {result.detail}" if result.detail else ""
            print(f"  [{'PASS' if result.passed else 'FAIL'}] {result.description}{detail}")
        print()
        core.unload_rom()
    print(f"FAILED: {failures} check(s)" if failures else "All checks passed.")
    return 1 if failures else 0


def parsed_arguments():
    parser = argument_parser_needing_the_tools_directory_and_base_rom(__doc__)
    parser.add_argument("--video-file", type=Path, default=None,
                        help="record everything the emulator draws into this .mkv, "
                             "which needs ffmpeg")
    return parser.parse_args()


def started_video_recording(video_file: Path):
    if video_file is None:
        return None
    from emulator.video_recording import VideoRecording
    return VideoRecording(video_file)


def main() -> int:
    arguments = parsed_arguments()
    base_rom_file = base_rom_file_from(arguments.base_rom)
    if not PATCHED_ROM_FILE.is_file():
        raise SystemExit(f"{PATCHED_ROM_FILE} is missing -- run python/build_patch.py "
                         f"{arguments.tools_directory} first")
    if not emulator_core_file(arguments.tools_directory).is_file():
        print("Downloading emulator core...")
        install_emulator_core(arguments.tools_directory)

    video_recording = started_video_recording(arguments.video_file)
    with tempfile.TemporaryDirectory() as temporary_directory:
        core = LibretroCore(emulator_core_file(arguments.tools_directory),
                            Path(temporary_directory), video_recording)
        print(f"Booting {PATCHED_ROM_FILE.name}...\n")
        exit_code = run_and_report(core, base_rom_file.read_bytes())
        core.shut_down()
    if video_recording:
        video_recording.finish()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
