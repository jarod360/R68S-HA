#!/usr/bin/env python3
"""Verify the GPT of a built HAOS image; NOT a hardware boot/flash test."""
import lzma
import struct
import sys
import zlib

NEEDED = {
    "uboot", "hassos-boot", "hassos-kernel0", "hassos-system0",
    "hassos-kernel1", "hassos-system1", "hassos-bootstate",
    "hassos-overlay", "hassos-data",
}

def verify(path):
    with lzma.open(path, "rb") as image:
        prefix = image.read(1024 * 1024)
    if prefix[510:512] != b"\x55\xaa":
        raise ValueError("MBR signature missing")
    gpt = bytearray(prefix[512:1024])
    if gpt[:8] != b"EFI PART":
        raise ValueError("GPT signature missing")
    n = struct.unpack_from("<I", gpt, 12)[0]
    if not 92 <= n <= 512:
        raise ValueError("Invalid GPT header size")
    crc = struct.unpack_from("<I", gpt, 16)[0]
    struct.pack_into("<I", gpt, 16, 0)
    if zlib.crc32(gpt[:n]) != crc:
        raise ValueError("GPT header CRC mismatch")
    lba, count, stride, crc = struct.unpack_from("<QIII", gpt, 72)
    if not 1 <= count <= 128 or not 128 <= stride <= 512:
        raise ValueError("Invalid GPT partition geometry")
    off = lba * 512
    entries = prefix[off:off + count * stride]
    if len(entries) != count * stride or zlib.crc32(entries) != crc:
        raise ValueError("GPT entry array CRC mismatch")
    found = set()
    for i in range(count):
        e = entries[i * stride:(i + 1) * stride]
        if e[:16] != b"\x00" * 16:
            found.add(e[56:128].decode("utf-16-le").rstrip("\x00"))
    if NEEDED - found:
        raise ValueError("Missing HAOS partitions: " + str(NEEDED - found))
    backup_lba = struct.unpack_from("<Q", gpt, 32)[0]
    if (backup_lba + 1) * 512 > 16_000_000_000:
        raise ValueError("Disk image cannot fit nominal 16GB eMMC")
    print("R68S_GPT_STRUCTURE_VALID")
    print("UNVERIFIED: no DDR, U-Boot, device boot, network, or OTA tests")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check-image-gpt.py image.img.xz")
    verify(sys.argv[1])
