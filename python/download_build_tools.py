#!/usr/bin/env python3
"""Puts the assembler and patch creator in the given tools directory.

The assembler publishes prebuilt binaries for Windows only, so on every other
platform it is built from source, which needs cmake and a C++ compiler.
"""
import sys

from toolchain.build_environment import assembler_executable, patch_creator_executable
from toolchain.command_line import argument_parser_needing_the_tools_directory
from toolchain.tool_installation import (
    install_assembler,
    install_patch_creator,
    installed_version_of,
)


def main() -> int:
    arguments = argument_parser_needing_the_tools_directory(__doc__).parse_args()
    install_assembler(arguments.tools_directory)
    install_patch_creator(arguments.tools_directory)
    print()
    print(installed_version_of(assembler_executable(arguments.tools_directory)))
    print(installed_version_of(patch_creator_executable(arguments.tools_directory)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
