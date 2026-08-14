import io
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from toolchain.build_environment import (
    ASSEMBLER_RELEASE_TAG,
    ASSEMBLER_SOURCE_SUBDIRECTORY,
    BUILT_ASSEMBLER_PATH_WITHIN_BUILD_DIRECTORY,
    DOWNLOADED_TOOLS_DIRECTORY,
    PATCH_CREATOR_RELEASE_TAG,
    assembler_executable,
    assembler_has_a_prebuilt_release,
    assembler_prebuilt_download_url,
    emulator_core_download_url,
    emulator_core_file,
    patch_creator_download_url,
    patch_creator_executable,
)

ASSEMBLER_SOURCE_REPOSITORY = "https://github.com/RPGHacker/asar"
COMMANDS_NEEDED_TO_BUILD_THE_ASSEMBLER = ("git", "cmake", "c++")


def downloaded_bytes(download_url: str) -> bytes:
    with urllib.request.urlopen(download_url) as response:
        return response.read()


def extract_from_zip_archive(download_url: str, destination: Path,
                             member_name: str = None) -> None:
    archive = zipfile.ZipFile(io.BytesIO(downloaded_bytes(download_url)))
    wanted = member_name or destination.name
    matches = [name for name in archive.namelist()
               if Path(name).name == wanted and not name.endswith("/")]
    if not matches:
        raise SystemExit(f"{wanted} is not present in the downloaded archive")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(archive.read(matches[0]))
    destination.chmod(destination.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def run_command(command: list, failure_message: str) -> None:
    if subprocess.run(command).returncode != 0:
        raise SystemExit(failure_message)


def build_assembler_from_source() -> None:
    missing = [name for name in COMMANDS_NEEDED_TO_BUILD_THE_ASSEMBLER
               if shutil.which(name) is None]
    if missing:
        raise SystemExit(
            f"The assembler has no prebuilt release for this platform and must be built from "
            f"source, but {' and '.join(missing)} {'are' if len(missing) > 1 else 'is'} not "
            f"installed.\nOn Debian or Ubuntu: sudo apt install git cmake g++")

    with tempfile.TemporaryDirectory() as staging_directory:
        staging = Path(staging_directory)
        run_command(["git", "clone", "--depth", "1", "--branch", ASSEMBLER_RELEASE_TAG,
                     "--quiet", ASSEMBLER_SOURCE_REPOSITORY, str(staging / "asar")],
                    "cloning the assembler source failed")
        build = staging / "build"
        run_command(["cmake", "-S", str(staging / "asar" / ASSEMBLER_SOURCE_SUBDIRECTORY),
                     "-B", str(build), "-DCMAKE_BUILD_TYPE=Release"],
                    "configuring the assembler build failed")
        run_command(["cmake", "--build", str(build), "-j", str(os.cpu_count() or 1)],
                    "building the assembler failed")
        built = build / BUILT_ASSEMBLER_PATH_WITHIN_BUILD_DIRECTORY
        if not built.is_file():
            raise SystemExit(f"the assembler build produced no binary at {built}")
        DOWNLOADED_TOOLS_DIRECTORY.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(built, assembler_executable())
    assembler_executable().chmod(assembler_executable().stat().st_mode | stat.S_IXUSR)


def install_assembler() -> None:
    if assembler_has_a_prebuilt_release():
        print(f"Downloading assembler {ASSEMBLER_RELEASE_TAG}...")
        extract_from_zip_archive(assembler_prebuilt_download_url(), assembler_executable())
    else:
        print(f"Building assembler {ASSEMBLER_RELEASE_TAG} from source...")
        build_assembler_from_source()


def install_patch_creator() -> None:
    print(f"Downloading patch creator {PATCH_CREATOR_RELEASE_TAG}...")
    extract_from_zip_archive(patch_creator_download_url(), patch_creator_executable())


def install_emulator_core() -> None:
    extract_from_zip_archive(emulator_core_download_url(), emulator_core_file())


def installed_version_of(executable_file: Path) -> str:
    completed = subprocess.run([str(executable_file), "--version"],
                               capture_output=True, text=True)
    return (completed.stdout or completed.stderr).splitlines()[0]
