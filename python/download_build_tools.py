#!/usr/bin/env python3
"""usage: download_build_tools.py

Puts the assembler and patch creator in tools/. The assembler publishes
prebuilt binaries for Windows only, so on every other platform it is built from
source, which needs cmake and a C++ compiler.
"""
import sys

from toolchain.build_environment import assembler_executable, patch_creator_executable
from toolchain.tool_installation import (
    install_assembler,
    install_patch_creator,
    installed_version_of,
)


def main() -> int:
    install_assembler()
    install_patch_creator()
    print()
    print(installed_version_of(assembler_executable()))
    print(installed_version_of(patch_creator_executable()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
