#!/usr/bin/env python3
"""usage: split_rom_into_secrets.py <path to "Goof Troop (USA).sfc">

Continuous integration needs the base ROM to build and boot the patch, and the
ROM cannot live in the repository. This compresses it, encodes it, splits it
into pieces small enough to be repository secrets, and writes each to
build/base_rom_secrets/ ready to upload.

A secret is capped at 64 kilobytes after GitHub encrypts and encodes it, which
inflates the value by about a third, so the slices are sized well under that.

Run once. The workflow rebuilds the ROM with assemble_rom_from_secrets.py.
"""
import base64
import gzip
import hashlib
import sys
from pathlib import Path

from toolchain.build_environment import (
    BASE_ROM_MD5_CHECKSUM,
    BUILD_DIRECTORY,
    SECRET_NAME_PREFIX,
    SECRET_SLICE_SIZE_IN_CHARACTERS,
)

SECRET_SLICE_DIRECTORY = BUILD_DIRECTORY / "base_rom_secrets"


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    rom_bytes = Path(sys.argv[1]).read_bytes()
    actual = hashlib.md5(rom_bytes).hexdigest()
    if actual != BASE_ROM_MD5_CHECKSUM:
        raise SystemExit(f"base ROM is not headerless Goof Troop (USA).\n"
                         f"  expected md5 {BASE_ROM_MD5_CHECKSUM}\n"
                         f"  actual   md5 {actual}")

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
