import hashlib

from goof_troop_usa import memory_map

LOW_ROM_BANK_SIZE_IN_BYTES = 0x8000

HEADERLESS_BASE_ROM_SHA256_CHECKSUM = (
    "2bb368c47189ce813ad716eef16c01cd47685cb98e2c1cb35fa6f0173c97dd7c")
A_COPIER_HEADER_IS_THE_USUAL_CAUSE = (
    "A 512-byte copier header is the usual cause; strip it and retry.")


def require_headerless_base_rom(rom_bytes: bytes, likely_cause: str) -> None:
    actual = hashlib.sha256(rom_bytes).hexdigest()
    if actual != HEADERLESS_BASE_ROM_SHA256_CHECKSUM:
        raise SystemExit(f"this is not headerless Goof Troop (USA).\n"
                         f"  expected sha256 {HEADERLESS_BASE_ROM_SHA256_CHECKSUM}\n"
                         f"  actual   sha256 {actual}\n"
                         f"{likely_cause}")


def rom_bytes_at(rom_bytes: bytes, snes_address: int, length: int) -> bytes:
    start = (((snes_address >> 16) & 0x7F) * LOW_ROM_BANK_SIZE_IN_BYTES
             + (snes_address & 0xFFFF) - 0x8000)
    return rom_bytes[start:start + length]


def require_unused_free_space(rom_bytes: bytes) -> None:
    free_space = rom_bytes_at(rom_bytes, memory_map.FREE_SPACE_IN_ROM,
                              memory_map.FREE_SPACE_SIZE_IN_BYTES)
    if any(free_space):
        raise SystemExit(
            f"${memory_map.FREE_SPACE_IN_ROM:06X} is where the patch routines go, and the base "
            f"ROM does not have {memory_map.FREE_SPACE_SIZE_IN_BYTES} free bytes there.")
