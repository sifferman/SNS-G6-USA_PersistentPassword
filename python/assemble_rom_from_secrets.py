#!/usr/bin/env python3
"""usage: assemble_rom_from_secrets.py

Rebuilds the base ROM from the BASE_ROM_SLICE_nn environment variables that
continuous integration populates from repository secrets, and writes it to
build/. The README says how to produce the slices.

Exits with a clear message when no slices are present, which is what happens on
a fork, where the secrets are deliberately unavailable.
"""
import base64
import gzip
import hashlib
import os
import sys

from toolchain.build_environment import (
    BASE_ROM_MD5_CHECKSUM,
    BUILD_DIRECTORY,
    SECRET_NAME_PREFIX,
)

REASSEMBLED_BASE_ROM_FILE = BUILD_DIRECTORY / "base_rom_from_secrets.sfc"


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
    actual = hashlib.md5(rom_bytes).hexdigest()
    if actual != BASE_ROM_MD5_CHECKSUM:
        raise SystemExit(f"the reassembled ROM is not headerless Goof Troop (USA).\n"
                         f"  expected md5 {BASE_ROM_MD5_CHECKSUM}\n"
                         f"  actual   md5 {actual}\n"
                         f"A slice is missing, truncated, or out of order.")

    BUILD_DIRECTORY.mkdir(parents=True, exist_ok=True)
    REASSEMBLED_BASE_ROM_FILE.write_bytes(rom_bytes)
    print(f"Rebuilt {len(rom_bytes)} bytes from {len(encoded_slices)} slices "
          f"into {REASSEMBLED_BASE_ROM_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
