import argparse
import os
from pathlib import Path

BASE_ROM_ENVIRONMENT_VARIABLE = "GOOF_TROOP_USA_ROM"


def add_tools_directory_argument_to(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("tools_directory", type=Path,
                        help="directory the build tools live in, conventionally tools/")


def add_base_rom_argument_to(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("base_rom", type=Path, nargs="?",
                        help=f'path to a headerless "Goof Troop (USA).sfc", '
                             f"or ${BASE_ROM_ENVIRONMENT_VARIABLE} when omitted")


def argument_parser_needing_the_tools_directory(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    add_tools_directory_argument_to(parser)
    return parser


def argument_parser_needing_the_base_rom(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    add_base_rom_argument_to(parser)
    return parser


def argument_parser_needing_the_tools_directory_and_base_rom(
        description: str) -> argparse.ArgumentParser:
    parser = argument_parser_needing_the_tools_directory(description)
    add_base_rom_argument_to(parser)
    return parser


def base_rom_file_from(base_rom_argument: Path) -> Path:
    given_path = base_rom_argument or os.environ.get(BASE_ROM_ENVIRONMENT_VARIABLE, "")
    if not given_path:
        raise SystemExit(f"no base ROM was given, and {BASE_ROM_ENVIRONMENT_VARIABLE} is not set")
    base_rom_file = Path(given_path)
    if not base_rom_file.is_file():
        raise SystemExit(f"no such file: {base_rom_file}")
    return base_rom_file
