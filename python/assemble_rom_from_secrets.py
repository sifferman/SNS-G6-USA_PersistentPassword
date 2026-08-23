#!/usr/bin/env python3
"""Rebuilds the base ROM from the BASE_ROM_SLICE_nn environment variables that
continuous integration populates from repository secrets, verifies its sha256
checksum, and writes it to build/. The README says how to produce the slices.

Exits with a clear message when no slices are present, which is what happens on
a fork, where the secrets are deliberately unavailable.
"""
import base64
import gzip
import os
import sys

from goof_troop_usa.base_rom import require_headerless_base_rom
from toolchain.build_environment import BUILD_DIRECTORY, SECRET_NAME_PREFIX

REASSEMBLED_BASE_ROM_FILE = BUILD_DIRECTORY / "base_rom_from_secrets.sfc"
A_MISSING_SLICE_IS_THE_USUAL_CAUSE = "A slice is missing, truncated, or out of order."


def encoded_slices_from_environment() -> list[str]:
    slices = []
    while True:
        value = os.environ.get(f"{SECRET_NAME_PREFIX}{len(slices):02d}")
        if not value:
            return slices
        slices.append(value.strip())


def main() -> int:
    encoded_slices = encoded_slices_from_environment()
    if not encoded_slices:
        raise SystemExit(f"no {SECRET_NAME_PREFIX}nn variables are set, so the base ROM "
                         f"cannot be rebuilt")

    rom_bytes = gzip.decompress(base64.b64decode("".join(encoded_slices)))
    require_headerless_base_rom(rom_bytes, A_MISSING_SLICE_IS_THE_USUAL_CAUSE)

    BUILD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    REASSEMBLED_BASE_ROM_FILE.write_bytes(rom_bytes)
    print(f"Rebuilt {len(rom_bytes)} bytes from {len(encoded_slices)} slices "
          f"into {REASSEMBLED_BASE_ROM_FILE}, sha256 verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
