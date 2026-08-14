# Goof Troop — Persistent Password

A minimal save patch for **Goof Troop (USA)** (SNS-G6-USA). Clear a level, and
the password you were just shown is still there the next time you power the
console on.

Goof Troop already preloads its password screen with the password for your
furthest level — that state just lives in volatile work RAM. This patch makes
it battery-backed. 54 bytes changed, no ROM expansion, no new menus.

Also persisted, for free, since they live in the same block: the sound and
option settings.

## What it changes

| | |
|---|---|
| Cartridge header | declares 2 KB of battery-backed save RAM (`$FFD6 = $02`, `$FFD8 = $01`) |
| Boot | `RestoreSettingsFromSaveRamOnBoot` copies save RAM → `$7F:FF00` |
| Level cleared / password accepted | `RecordFurthestLevelReachedToSaveRam` copies `$7F:FF00` → save RAM |
| Save RAM detection routine | replaced (mandatory — see below) |

Goof Troop ships a copy-protection routine that probes the save RAM window and
**deliberately hangs on a black screen if it finds writable memory.** Any save
patch for this game must remove it. Its 42 freed bytes are exactly where this
patch's two routines live, so there is no ROM expansion.

## Behaviour with no save file

Clean fresh game, through the game's own code path.

`RestoreSettingsFromSaveRamOnBoot` copies save RAM into `$7F:FF00`
unconditionally. The vanilla validator at `$80:969B` then word-compares
offsets `$20`–`$FF` of that block against a fixed signature in ROM. Blank save
RAM fails on the first word, so the validator overwrites all 256 bytes with
defaults and re-checks. `$7FFF01` ends up `0`, and the password screen
preloads `00 00 00 00 00` — the vanilla level-0 password.

This is the same path the unpatched game takes for garbage work RAM on a cold
boot, so a missing or corrupt `.srm` carries no risk vanilla does not already
carry. It is also why the patch needs no magic number of its own.

## Building

Requires Python 3.9+.

```sh
python3 python/download_build_tools.py
python3 python/build_patch.py "path/to/Goof Troop (USA).sfc"
```

The first command puts the assembler ([asar](https://github.com/RPGHacker/asar))
and patch creator ([Flips](https://github.com/Alcaro/Flips)) in `tools/`. asar
publishes prebuilt binaries for Windows only, so on Linux it is built from
source and `cmake` and a C++ compiler are needed as well:

```sh
sudo apt install cmake g++
```

Both platforms produce a byte-identical patched ROM.

Produces:

- `build/SNS-G6-USA_PersistentPassword.sfc` — test build
- `release/SNS-G6-USA_PersistentPassword.bps` — the distributable patch

Both directories are untracked; released patches are published as GitHub
Release assets rather than committed.

Vanilla addresses are defined once, in `python/goof_troop_usa/memory_map.py`;
the assembler include is generated from it into `build/` before every
assembly. See [the notes](docs/reverse_engineering_notes.md) §6 for how the
checks stay independent of those constants.

The build refuses to run unless the base ROM is headerless Goof Troop (USA),
md5 `bb6a1198e291c8ae58e9581a4296ed4d`, then re-verifies the output
instruction by instruction.

To go further and actually run it, boot the build in a headless emulator:

```sh
python3 python/verify_patch_in_emulator.py "path/to/Goof Troop (USA).sfc"
```

That downloads a libretro core, boots the patched ROM with no display or
sound, and reads work RAM and save RAM back to prove the patch behaves. Linux
only. See **Status** for what it covers.

No ROM is included in or distributable from this repository.

## Continuous integration

Verification needs the base ROM, which cannot be committed. The workflow
rebuilds it from repository secrets: the ROM is compressed, encoded, and split
into pieces small enough to store as secrets.

```sh
python3 python/split_rom_into_secrets.py "path/to/Goof Troop (USA).sfc"
```

That writes the pieces to `build/base_rom_secrets/`, which is untracked, and
prints the `gh secret set` commands to upload them. Eight are needed. The
workflow then runs `python/assemble_rom_from_secrets.py`, which checks the
rebuilt ROM's md5 before anything uses it.

On a fork the secrets are unavailable and the workflow skips with a notice
rather than failing.

## Repository layout

```
asm/                              the patch itself, one file
input_recordings/                 BizHawk recordings replayed by the checks
python/
  build_patch.py                  assemble and write the .bps
  verify_patch_in_emulator.py     boot it headlessly and check memory
  download_build_tools.py         fetch or build asar, Flips and the core
  split_rom_into_secrets.py       prepare the base ROM for CI
  assemble_rom_from_secrets.py    rebuild it inside CI
  emulator/                       libretro binding, input recording parsing
  goof_troop_usa/memory_map.py    every vanilla address, defined once
  toolchain/                      assembler, tool installation, paths
docs/                             reverse engineering notes and style guide
```

Commands sit at the top of `python/` rather than in a subdirectory so that
running one directly puts `python/` on the import path and the packages
resolve with no `-m` invocation or path manipulation.

## Applying

Patch a headerless Goof Troop (USA) ROM with `release/*.bps` using
[Flips](https://git.disroot.org/Sir_Walrus/Flips) or any BPS patcher.



## Licence and attribution

**GPL-3.0** — see `LICENSE`, a verbatim copy of the licence of the disassembly
this project derives from.

### Goof Troop Disassembly

<https://github.com/Yoshifanatic1/Goof-Troop-Disassembly> — Yoshifanatic1,
GPL-3.0. Two distinct kinds of material were taken from it.

Every ROM and RAM address in `python/goof_troop_usa/memory_map.py` was located by reading that disassembly, and `docs/reverse_engineering_notes.md` quotes its source verbatim so each claim can be checked against the code it came from — which is why this repository is GPL-3.0 to match upstream. Nothing in `asm/apply_persistent_password_patch.asm` is copied from it; the patch was written from scratch against those addresses.

### Goof Troop SRAM

*Goof Troop SRAM* (2022) by BillyTime! Games found that Goof Troop's
copy-protection routine must be removed before save RAM can be added. This
patch implements that same feature.
