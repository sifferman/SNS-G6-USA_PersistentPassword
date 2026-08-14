import platform
from pathlib import Path

PATCH_NAME = "SNS-G6-USA_PersistentPassword"
BASE_ROM_MD5_CHECKSUM = "bb6a1198e291c8ae58e9581a4296ed4d"

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent.parent
BUILD_DIRECTORY = REPOSITORY_ROOT / "build"
RELEASE_DIRECTORY = REPOSITORY_ROOT / "release"
DOWNLOADED_TOOLS_DIRECTORY = REPOSITORY_ROOT / "tools"
INPUT_RECORDING_DIRECTORY = REPOSITORY_ROOT / "input_recordings"

MAIN_SOURCE_FILE = REPOSITORY_ROOT / "asm" / "apply_persistent_password_patch.asm"
GENERATED_MEMORY_MAP_INCLUDE_FILE = BUILD_DIRECTORY / "goof_troop_usa_memory_map.asm"
PATCHED_ROM_FILE = BUILD_DIRECTORY / f"{PATCH_NAME}.sfc"
PATCH_FILE = RELEASE_DIRECTORY / f"{PATCH_NAME}.bps"

COLD_BOOT_TO_CHANGE_SETTINGS_RECORDING = (
    INPUT_RECORDING_DIRECTORY / "cold_boot_to_change_settings.tasproj")
COLD_BOOT_TO_COMPLETE_LEVEL_1_WITH_CHEATS_RECORDING = (
    INPUT_RECORDING_DIRECTORY / "cold_boot_to_complete_LV1_wcheats.tasproj")
CHEATS_HELD_DURING_THE_LEVEL_RECORDING = {0x7E011D: 0x06, 0x7E00B7: 0x0E}

SECRET_NAME_PREFIX = "BASE_ROM_SLICE_"
SECRET_SLICE_SIZE_IN_CHARACTERS = 47000
FRAMES_TO_REACH_THE_TITLE_SCREEN = 600

ASSEMBLER_RELEASE_TAG = "v1.91"
PATCH_CREATOR_RELEASE_TAG = "v198"
ASSEMBLER_SOURCE_SUBDIRECTORY = "src"
BUILT_ASSEMBLER_PATH_WITHIN_BUILD_DIRECTORY = "asar/bin/asar"
EMULATOR_CORE_NAME = "bsnes_mercury_accuracy_libretro.so"

OPERATING_SYSTEM = platform.system()
EXECUTABLE_FILE_EXTENSION = ".exe" if OPERATING_SYSTEM == "Windows" else ""


def assembler_executable() -> Path:
    return DOWNLOADED_TOOLS_DIRECTORY / f"asar{EXECUTABLE_FILE_EXTENSION}"


def patch_creator_executable() -> Path:
    return DOWNLOADED_TOOLS_DIRECTORY / f"flips{EXECUTABLE_FILE_EXTENSION}"


def emulator_core_file() -> Path:
    return DOWNLOADED_TOOLS_DIRECTORY / EMULATOR_CORE_NAME


def assembler_has_a_prebuilt_release() -> bool:
    return OPERATING_SYSTEM == "Windows"


def assembler_prebuilt_download_url() -> str:
    version = ASSEMBLER_RELEASE_TAG.replace("v", "").replace(".", "")
    return ("https://github.com/RPGHacker/asar/releases/download/"
            f"{ASSEMBLER_RELEASE_TAG}/asar{version}.zip")


def assembler_source_download_url() -> str:
    return ("https://github.com/RPGHacker/asar/archive/refs/tags/"
            f"{ASSEMBLER_RELEASE_TAG}.tar.gz")


def patch_creator_download_url() -> str:
    if OPERATING_SYSTEM not in ("Windows", "Linux"):
        raise SystemExit(f"No prebuilt patch creator is published for {OPERATING_SYSTEM}.")
    return ("https://github.com/Alcaro/Flips/releases/download/"
            f"{PATCH_CREATOR_RELEASE_TAG}/flips-{OPERATING_SYSTEM.lower()}.zip")


def emulator_core_download_url() -> str:
    if OPERATING_SYSTEM != "Linux":
        raise SystemExit(f"Emulator verification is only wired up for Linux, "
                         f"not {OPERATING_SYSTEM}.")
    return ("https://buildbot.libretro.com/nightly/linux/x86_64/latest/"
            f"{EMULATOR_CORE_NAME}.zip")
