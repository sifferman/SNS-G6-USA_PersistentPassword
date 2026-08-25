# Goof Troop: Persistent Password

## About

A minimal save patch for **Goof Troop (USA)** (SNS-G6-USA). Clear a level, and
the password you were shown is still there next power on. Sound and option
settings persist too.

The furthest level reached (`$7F:FF01`) and the settings live in one 256 byte
block of work RAM at `$7F:FF00`. The patch declares 2 KB of battery
backed save RAM in the cartridge header, copies that block out of save RAM
(`$70:0000`) on boot, and copies it back on a level cleared, a password
accepted, or a setting changed. There is a piracy protection routine at
`$80:F2A9`, which hangs if save RAM is writable, so it is removed. The routines
fit free space at `$8B:FF00`; the ROM stays 512 KB.

Details: `asm/` and `python/goof_troop_usa/memory_map.py`.

## Applying

Download the latest .bps from [releases](https://github.com/sifferman/SNS-G6-USA_PersistentPassword/releases/latest)
and apply it with [RomPatcher.js](https://www.marcrobledo.com/RomPatcher.js/),
or any BPS patcher.

## Building

Requires Python 3.9+. Each script takes the tools directory first.

```sh
sudo apt install cmake g++ # linux only, linux must build asar from source
python3 python/download_build_tools.py tools/
python3 python/build_patch.py tools/ "path/to/Goof Troop (USA).sfc"
```

## Tools

* <https://github.com/RPGHacker/asar>
* <https://github.com/Alcaro/Flips>

## Verify with Emulator

This downloads a libretro core, boots the patched ROM with no gui, and reads
memory back to prove the patch behaves. Linux only. No ROM is distributed here.

```sh
python3 python/verify_patch_in_emulator.py tools/ "path/to/Goof Troop (USA).sfc"
```

### Tests

* Fresh boot with no save file
* Cold boot with a saved game
* Changing a setting and power cycling (`cold_boot_to_change_settings.tasproj`)
* Completing a level and power cycling (`cold_boot_to_complete_LV1_wcheats.tasproj`)

### Video Playback

Although the emulation is headless, you may generate a .mkv of it:

```sh
sudo apt install ffmpeg && pip install pillow
python3 python/verify_patch_in_emulator.py tools/ "path/to/Goof Troop (USA).sfc" \
    --video-file build/verification.mkv
```

The tests play back in printed order, each captioned, counting power ons,
flagging hard resets, and showing which buttons are held.

## Continuous integration

GitHub actions automatically builds, verifies, and releases the BPS patch.

To prevent piracy, this repo's workflow sources the vanilla ROM via GitHub Secrets
and verifies its sha256. To assist in initial CI setup, the following script
compresses and splits the rom apart, and prints the `gh secret set` commands that upload them.

```sh
python3 python/split_rom_into_secrets.py "path/to/Goof Troop (USA).sfc"
```

Forks will not include this repo's secrets, so the workflow skips with a notice.

## Repository layout

```
asm/                the patch, one file
input_recordings/   BizHawk recordings replayed by the checks
python/             build, verification, and CI scripts
  emulator/         libretro binding, input and video recording
  goof_troop_usa/   vanilla addresses and the base ROM checksum
  toolchain/        assembler, tool installation, paths, arguments
docs/               reverse engineering notes and style guide
```

## Licence and attribution

**GPL-3.0**, see `LICENSE`, matching the disassembly this derives from.

### Goof Troop Disassembly

<https://github.com/Yoshifanatic1/Goof-Troop-Disassembly> by Yoshifanatic1,
GPL-3.0. Every address in `python/goof_troop_usa/memory_map.py` was located by
reading it, and `docs/reverse_engineering_notes.md` quotes it verbatim, which is
why this repository matches its licence. No code was copied; the patch was
written from scratch.

### Goof Troop SRAM

*Goof Troop SRAM* (2022) by BillyTime! Games (<https://romhackplaza.org/romhacks/goof-troop-sram-super-nintendo>)
found that the copy protection routine must be removed before save RAM can be added.
This patch builds upon research.
