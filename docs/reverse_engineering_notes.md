# Research notes

How the patch was derived. Line citations are into
[Yoshifanatic1's Goof Troop disassembly](https://github.com/Yoshifanatic1/Goof-Troop-Disassembly),
`GOOFT/Routine_Macros_GOOFT.asm`. Byte offsets are into the headerless USA ROM,
md5 `bb6a1198e291c8ae58e9581a4296ed4d`.

---

## 1. The feature already exists

Goof Troop's password screen is **already** preloaded with the password for
your furthest level (`CODE_82BDE5`, `:43999`):

```asm
LDA.w $00C3                 ; furthest level reached, 0-4
ASL : ASL : ADC.w $00C3     ; ×5
TAY
CODE_82BE04:
    LDA.w DATA_83C67A,y     ; password table, five symbols per level
    STA.b $30,x             ; $30-$34, the symbols on screen
```

So no password encoding work is needed. The entire job is making `$00C3`
survive a power cycle. It is loaded from `$7F:FF01` at boot (`CODE_82B659`,
`:42868`), and `$7F:FF01` lives in a block that survives a *soft* reset but not
a power cut.

The password table at `DATA_83C67A` (ROM `0x1C67A`), five symbols per level,
each 0-3:

| level | symbols |
|---|---|
| 0 | `00 00 00 00 00` |
| 1 | `01 02 00 01 00` |
| 2 | `00 02 03 00 01` |
| 3 | `02 00 03 03 02` |
| 4 | `01 00 03 02 01` |

---

## 2. The settings block at `$7F:FF00`

256 bytes the game already treats as a save file. Only `$00`-`$08` carry state:

| offset | contents |
|---|---|
| `$00` | attract mode demo cycler |
| **`$01`** | **furthest level reached — the password** |
| `$03`-`$07` | sound and gameplay options |
| `$08` | sound driver uploaded flag — see §5 |
| `$09`-`$12` | sound engine scratch, rewritten every boot |
| `$20`-`$FF` | fixed signature |

**The block validates itself** (`:3146`-`:3203`), before anything reads it:
word-compare `$20`-`$FF` against `DATA_838530+$20`, require the reserved bytes
zero and each field in range, and on any failure `MVN` all 256 default bytes
over it and re-check.

That check is the patch's integrity check, which is why the patch carries no
magic number. Blank save RAM fails the signature compare and falls back to a
fresh game — the same path vanilla takes for garbage work RAM on a cold boot.

The signature is a hidden developer credit:

```
   WALT DISNEY      GOOF TROOP     Birth Day       1967 3 26
   phone      06-951-9057    0792-45-1112    0792-46-0064
   1993 CAPCOM     Programed         by       Masatsugu
   Shinohara        U.S.A
```

---

## 3. The copy protection must be removed

`CODE_80F2A9` (`:15537`), called unconditionally by the reset handler:

```asm
LDX.w #$707F00
CODE_80F2B4:
    STA.w $707F00&$FF0000,x     ; write into the save RAM window
    CMP.w $707F00&$FF0000,x     ; read it back
    BNE CODE_80F2D3             ; readback failed -> no save RAM -> continue
    ...
    STA.w !REGISTER_ScreenDisplayRegister   ; force blank
CODE_80F2D1:
    BRA.b CODE_80F2D1                       ; hang forever
```

Goof Troop **deliberately bricks itself if it detects writable save RAM.** Any
save patch for this game must remove it. Its 42 bytes are where the boot loader
now lives, overwritten to the last byte so no fragment survives.

---

## 4. The hooks

Seven call sites, all replaced by an equally sized long call so nothing shifts.

**Two furthest-level stores**, both `STA.l $7FFF01` with 8-bit A holding the new
level, replaced by `JSL RecordFurthestLevelReachedToSaveRam` which performs the
displaced store itself:

| site | when |
|---|---|
| `$82:BD66` (`:43908`) | level completed |
| `$82:BF30` (`:44164`) | password accepted |

**Five option writes**, each `STA.l $7FFF0x` followed by an identical
`JSL $82B659`. Hooking the shared call rather than the differing store means
one wrapper, `SaveSettingsThenReloadThem`, serves all five — it saves, then
tail-calls `$82:B659` so the vanilla reload still happens:

| site | option |
|---|---|
| `$82:B548` | `$7FFF04` |
| `$82:B635` | `$7FFF03`, sound |
| `$82:B6AB` | `$7FFF05`, player one throw type |
| `$82:B714` | `$7FFF06` |
| `$82:B73F` | `$7FFF07` |

### Are those all the writes?

Audited rather than assumed, because a missed write is a silent gap:

```sh
grep -nE '\$7FFF[0-9A-F]{2}' Routine_Macros_GOOFT.asm | \
  awk '{print ($2 ~ /^(STA|STZ|INC|DEC|TSB|TRB)/ ? "WRITE" : "read"), $0}'
```

**Nineteen writes exist, seven are hooked.** The other twelve are the sound
driver flag (`$08`, must not persist), the music and APU bytes (`$09`-`$12`),
the attract mode cycler (`$00`), and the validator's own reset to defaults —
all volatile or derived.

Four ways to reach the block that grep would miss were also checked, all clear:
no absolute `$FFxx` stores under `DB=$7F`, no indirect long stores anywhere in
the disassembly, no block move reaching past `$7F:FBFF`, and the WRAM port
`$2180`-`$2183` is never referenced.

`$7FFF00` rides along with a save because it shares the block; the only effect
is the attract sequence resuming mid-cycle.

---

## 5. Two hazards

### `$7FFF08` must not be restored

The reset handler zeroes it at `$80:8013`, and `:3251` gates the SPC700 driver
upload on it. A saved `1` restored from save RAM would skip sound
initialisation entirely, so `RestoreSettingsFromSaveRamOnBoot` re-clears it
after the copy. It exploits `MVN` leaving DB set to the destination bank, so a
3-byte `STZ.w $FF08` suffices.

### Expanding the ROM woke a dormant jump

Hooking the option writes needs more than the 42 freed bytes, so the ROM is
expanded to one megabyte and everything except the boot loader lives in the
added bank. Vanilla contains a long jump into that bank:

```asm
DATA_8081E3:
	...
	dw CODE_80821B          ; entry 8 of a dispatch table
CODE_80821B:                ; Note: The ROM is only 512KB large, so this just leads to $808000.
	JML.l $908000
```

At 512 KB, bank `$90` mirrored to offset 0 and this behaved as a jump to the
reset entry. At one megabyte `$90:8000` is real memory, and the first routine
placed there would be entered mid-flight by any dispatch through entry 8, then
`RTL` on a frame that was never a `JSL`.

`PreserveVanillaJumpIntoTheAddedBank` sits at `$90:8000` and does nothing but
`JML $808000`, reproducing vanilla exactly. Found by the entry-point scan, not
by inspection.

### Layout

| address | routine |
|---|---|
| `$80:F2A9` | `RestoreSettingsFromSaveRamOnBoot`, then `$EA` filler to `$80:F2D2` |
| `$90:8000` | `PreserveVanillaJumpIntoTheAddedBank` |
| `$90:8004` | `CopySettingsBlockToSaveRam` |
| `$90:8017` | `RecordFurthestLevelReachedToSaveRam` |
| `$90:801F` | `SaveSettingsThenReloadThem` |

The boot loader stays in bank `$80` because the reset handler reaches it with a
near `JSR`, which cannot cross banks. The added half is zeros, so the patch
grows only to 162 bytes and a compressed ROM is unchanged in size.

---

## 6. Why the checks are not circular

`python/goof_troop_usa/memory_map.py` is the single definition of every
vanilla address. `python/toolchain/assembler.py` generates the assembler
include from it before every build, then reads the routine addresses back
out of asar's symbol file, so nothing restates the layout in Python.

The same constants therefore both place the patch and check it, which would be
circular — except that every address is anchored against what the base ROM
actually contains:

| anchor | address |
|---|---|
| holds `STA.l $7FFF01` | both furthest-level sites |
| holds `JSL $82B659` | all five option sites |
| holds the 42-byte copy protection routine | `$80:F2A9` |
| holds `JSR $F2A9` | `$80:8024` |

Every address has to agree with real vanilla content before any check passes.
Moving one hook four bytes fails with:

```
[FAIL] $82BD6A  level cleared: was the expected vanilla instruction
```

The routine addresses the entry-point check compares against come from asar's
own symbol file rather than from a table in Python, so adding or resizing a
routine cannot silently disagree with what the checks expect.

---

## 7. Traps

Three things that cost time and would cost it again.

**`$7FFF10` and `$7FFF11` are not init markers.** They are written by the sound
init path (`:3261`-`:3263`), which makes them look like proof it ran, but
`CODE_8099C8` and `CODE_8099D9` also write them during ordinary playback: they
are the requested and playing music tracks. The check settles for observing
that music plays at all.

**`bsnes_mercury` lies about its pixel format.** It reports `0RGB1555` through
the environment callback but emits 32-bit `XRGB8888`. `pitch / width` is the
reliable signal, and `python/emulator/video_capture.py` uses that instead of
the declaration.

**Not every SNES libretro core exposes work RAM.** `bsnes` and `bsnes_hd_beta`
return a null pointer for `RETRO_MEMORY_SYSTEM_RAM`, which rules them out
despite being closest to BizHawk's core. `bsnes_mercury_accuracy` and
`bsnes2014_accuracy` both work.
