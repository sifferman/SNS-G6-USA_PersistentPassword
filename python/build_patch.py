#!/usr/bin/env python3
"""usage: build_patch.py <path to "Goof Troop (USA).sfc">

Assembles the patch into a copy of the base ROM and writes a distributable
patch. The base ROM may also be given by the GOOF_TROOP_USA_ROM environment
variable.

Run verify_patch_in_emulator.py afterwards to check that it behaves.
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from toolchain.assembler import assemble_into
from toolchain.build_environment import (
    BASE_ROM_MD5_CHECKSUM,
    BUILD_DIRECTORY,
    PATCHED_ROM_FILE,
    PATCH_FILE,
    RELEASE_DIRECTORY,
    REPOSITORY_ROOT,
    patch_creator_executable,
)

BASE_ROM_ENVIRONMENT_VARIABLE = "GOOF_TROOP_USA_ROM"


def base_rom_file_from_command_line() -> Path:
    given_path = (sys.argv[1] if len(sys.argv) > 1
                  else os.environ.get(BASE_ROM_ENVIRONMENT_VARIABLE, ""))
    if not given_path:
        raise SystemExit(__doc__)
    base_rom_file = Path(given_path)
    if not base_rom_file.is_file():
        raise SystemExit(f"no such file: {base_rom_file}")
    return base_rom_file


def require_expected_base_rom(base_rom_file: Path) -> None:
    actual = hashlib.md5(base_rom_file.read_bytes()).hexdigest()
    if actual != BASE_ROM_MD5_CHECKSUM:
        raise SystemExit(
            f"base ROM is not headerless Goof Troop (USA).\n"
            f"  expected md5 {BASE_ROM_MD5_CHECKSUM}\n"
            f"  actual   md5 {actual}\n"
            f"A 512-byte copier header is the usual cause; strip it and retry.")


def create_patch(base_rom_file: Path) -> None:
    if not patch_creator_executable().exists():
        raise SystemExit("build tools missing -- run python/download_build_tools.py first")
    subprocess.run(
        [str(patch_creator_executable()), "--create", "--bps",
         str(base_rom_file), str(PATCHED_ROM_FILE), str(PATCH_FILE)],
        check=True, capture_output=True)


def main() -> int:
    base_rom_file = base_rom_file_from_command_line()
    require_expected_base_rom(base_rom_file)

    BUILD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    RELEASE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base_rom_file, PATCHED_ROM_FILE)

    print("Assembling...")
    assemble_into(PATCHED_ROM_FILE)
    create_patch(base_rom_file)

    for produced in (PATCHED_ROM_FILE, PATCH_FILE):
        relative = str(produced.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
        print(f"  {relative}  ({produced.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
