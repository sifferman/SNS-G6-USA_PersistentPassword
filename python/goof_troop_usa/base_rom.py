import hashlib

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
