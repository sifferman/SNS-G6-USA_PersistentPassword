#!/usr/bin/env python3
"""Prepares the base ROM for continuous integration, which cannot keep it in the repository.

Compresses the ROM, encodes it, splits it into pieces small enough to be
repository secrets, writes each to build/base_rom_secrets/, and prints the
commands that upload them.

A secret is capped at 64 kilobytes after GitHub encrypts and encodes it, which
inflates the value by about a third, so the slices are sized well under that.

Run once. The workflow rebuilds the ROM with assemble_rom_from_secrets.py.
"""
import base64
import gzip
import sys

from goof_troop_usa.base_rom import (
    A_COPIER_HEADER_IS_THE_USUAL_CAUSE,
    require_headerless_base_rom,
)
from toolchain.build_environment import (
    BUILD_DIRECTORY,
    SECRET_NAME_PREFIX,
    SECRET_SLICE_SIZE_IN_CHARACTERS,
)
from toolchain.command_line import argument_parser_needing_the_base_rom, base_rom_file_from

SECRET_SLICE_DIRECTORY = BUILD_DIRECTORY / "base_rom_secrets"


def main() -> int:
    arguments = argument_parser_needing_the_base_rom(__doc__).parse_args()
    rom_bytes = base_rom_file_from(arguments.base_rom).read_bytes()
    require_headerless_base_rom(rom_bytes, A_COPIER_HEADER_IS_THE_USUAL_CAUSE)

    encoded = base64.b64encode(gzip.compress(rom_bytes, 9)).decode("ascii")
    slices = [encoded[start:start + SECRET_SLICE_SIZE_IN_CHARACTERS]
              for start in range(0, len(encoded), SECRET_SLICE_SIZE_IN_CHARACTERS)]

    SECRET_SLICE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    for index, encoded_slice in enumerate(slices):
        (SECRET_SLICE_DIRECTORY / f"{SECRET_NAME_PREFIX}{index:02d}.txt").write_text(
            encoded_slice, encoding="ascii")

    print(f"{len(rom_bytes)} bytes compressed and encoded into {len(slices)} slices of at "
          f"most {SECRET_SLICE_SIZE_IN_CHARACTERS} characters, in {SECRET_SLICE_DIRECTORY}.")
    print("\nUpload each as a repository secret:\n")
    for index in range(len(slices)):
        name = f"{SECRET_NAME_PREFIX}{index:02d}"
        print(f"  gh secret set {name} < {SECRET_SLICE_DIRECTORY / (name + '.txt')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
