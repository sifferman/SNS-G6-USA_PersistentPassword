#!/usr/bin/env python3
"""Assembles the patch into a copy of the base ROM and writes a distributable patch.

Run verify_patch_in_emulator.py afterwards to check that it behaves.
"""
import shutil
import subprocess
import sys
from pathlib import Path

from goof_troop_usa.base_rom import (
    A_COPIER_HEADER_IS_THE_USUAL_CAUSE,
    require_headerless_base_rom,
)
from toolchain.assembler import assemble_into
from toolchain.build_environment import (
    BUILD_DIRECTORY,
    PATCHED_ROM_FILE,
    PATCH_FILE,
    RELEASE_DIRECTORY,
    REPOSITORY_ROOT,
    patch_creator_executable,
)
from toolchain.command_line import (
    argument_parser_needing_the_tools_directory_and_base_rom,
    base_rom_file_from,
)


def create_patch(base_rom_file: Path, tools_directory: Path) -> None:
    if not patch_creator_executable(tools_directory).exists():
        raise SystemExit(f"the patch creator is missing from {tools_directory} -- run "
                         f"python/download_build_tools.py {tools_directory} first")
    subprocess.run(
        [str(patch_creator_executable(tools_directory)), "--create", "--bps",
         str(base_rom_file), str(PATCHED_ROM_FILE), str(PATCH_FILE)],
        check=True, capture_output=True)


def main() -> int:
    arguments = argument_parser_needing_the_tools_directory_and_base_rom(__doc__).parse_args()
    base_rom_file = base_rom_file_from(arguments.base_rom)
    require_headerless_base_rom(base_rom_file.read_bytes(), A_COPIER_HEADER_IS_THE_USUAL_CAUSE)

    BUILD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    RELEASE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(base_rom_file, PATCHED_ROM_FILE)

    print("Assembling...")
    assemble_into(PATCHED_ROM_FILE, arguments.tools_directory)
    create_patch(base_rom_file, arguments.tools_directory)

    for produced in (PATCHED_ROM_FILE, PATCH_FILE):
        relative = str(produced.relative_to(REPOSITORY_ROOT)).replace("\\", "/")
        print(f"  {relative}  ({produced.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
