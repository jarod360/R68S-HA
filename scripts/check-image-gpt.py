#!/usr/bin/env python3
"""Verify the R68S image stream, both GPT copies and Rockchip SPL/FIT layout.

This is a static image check only; it is not a DDR, boot or hardware test.
"""
import lzma
import struct
import sys
import zlib

SECTOR_SIZE = 512
FIT_OFFSET = 8 * 1024 * 1024
UBOOT_PARTITION_SIZE = 8 * 1024 * 1024
READ_CHUNK = 8 * 1024 * 1024
TAIL_SIZE = 128 * 512 + 512
MAX_EMMC_BYTES = 16_000_000_000
NEEDED = {
    "uboot", "hassos-boot", "hassos-kernel0", "hassos-system0",
    "hassos-kernel1", "hassos-system1", "hassos-bootstate",
    "hassos-overlay", "hassos-data",
}


def parse_gpt_header(raw, label):
    if len(raw) != SECTOR_SIZE or raw[:8] != b"EFI PART":
        raise ValueError(f"{label} GPT signature missing")
    header = bytearray(raw)
    header_size = struct.unpack_from("<I", header, 12)[0]
    if not 92 <= header_size <= SECTOR_SIZE:
        raise ValueError(f"{label} GPT header size is invalid")
    expected_crc = struct.unpack_from("<I", header, 16)[0]
    struct.pack_into("<I", header, 16, 0)
    if zlib.crc32(header[:header_size]) & 0xFFFFFFFF != expected_crc:
        raise ValueError(f"{label} GPT header CRC mismatch")
    current_lba, alternate_lba, first_usable, last_usable = struct.unpack_from(
        "<QQQQ", raw, 24
    )
    entries_lba, entry_count, entry_size, entries_crc = struct.unpack_from(
        "<QIII", raw, 72
    )
    if not 1 <= entry_count <= 128 or not 128 <= entry_size <= 512:
        raise ValueError(f"{label} GPT partition geometry is invalid")
    if entry_size % 8:
        raise ValueError(f"{label} GPT entry size is invalid")
    if first_usable > last_usable or last_usable >= max(current_lba, alternate_lba):
        raise ValueError(f"{label} GPT usable-LBA range is invalid")
    return {
        "current_lba": current_lba, "alternate_lba": alternate_lba,
        "first_usable": first_usable, "last_usable": last_usable,
        "entries_lba": entries_lba, "entry_count": entry_count,
        "entry_size": entry_size, "entries_crc": entries_crc,
    }


def parse_partitions(entries, header):
    parts, ranges = {}, []
    stride = header["entry_size"]
    for index in range(header["entry_count"]):
        entry = entries[index * stride:(index + 1) * stride]
        if entry[:16] == b"\x00" * 16:
            continue
        first_lba, last_lba = struct.unpack_from("<QQ", entry, 32)
        label = entry[56:128].decode("utf-16-le", errors="replace").rstrip("\x00")
        if not label or label in parts:
            raise ValueError(f"GPT partition {index} has an empty or duplicate label")
        if first_lba < header["first_usable"] or last_lba > header["last_usable"]:
            raise ValueError(f"GPT partition is outside usable LBAs: {label}")
        if first_lba > last_lba:
            raise ValueError(f"GPT partition has an invalid range: {label}")
        parts[label] = (first_lba, last_lba)
        ranges.append((first_lba, last_lba, label))
    ranges.sort()
    for previous, current in zip(ranges, ranges[1:]):
        if current[0] <= previous[1]:
            raise ValueError(f"GPT partitions overlap: {previous[2]} and {current[2]}")
    return parts


def verify_stream(image, stream_format="XZ"):
    prefix_size = FIT_OFFSET + UBOOT_PARTITION_SIZE
    prefix = image.read(prefix_size)
    if len(prefix) != prefix_size:
        raise ValueError("Image is truncated before the U-Boot FIT partition")
    mbr = prefix[:SECTOR_SIZE]
    if mbr[510:512] != b"\x55\xaa":
        raise ValueError("MBR signature missing")
    mbr_entries = [mbr[446 + i * 16:446 + (i + 1) * 16] for i in range(4)]
    if not any(entry[4] == 0xEE for entry in mbr_entries):
        raise ValueError("Protective MBR partition is missing")

    primary = parse_gpt_header(prefix[512:1024], "Primary")
    if primary["current_lba"] != 1 or primary["entries_lba"] != 2:
        raise ValueError("Primary GPT is not at the standard location")
    primary_bytes = primary["entry_count"] * primary["entry_size"]
    primary_off = primary["entries_lba"] * SECTOR_SIZE
    primary_end = primary_off + primary_bytes
    if primary_end > len(prefix) or primary_end > primary["first_usable"] * SECTOR_SIZE:
        raise ValueError("Primary GPT entry array is truncated or overlaps usable space")
    primary_entries = prefix[primary_off:primary_end]
    if zlib.crc32(primary_entries) & 0xFFFFFFFF != primary["entries_crc"]:
        raise ValueError("Primary GPT entry-array CRC mismatch")

    parts = parse_partitions(primary_entries, primary)
    if NEEDED - set(parts):
        raise ValueError("Missing HAOS partitions: " + str(NEEDED - set(parts)))
    uboot_first, uboot_last = parts["uboot"]
    if uboot_first * SECTOR_SIZE != FIT_OFFSET:
        raise ValueError("U-Boot GPT partition does not start at eMMC 8 MiB")
    if (uboot_last - uboot_first + 1) * SECTOR_SIZE != UBOOT_PARTITION_SIZE:
        raise ValueError("U-Boot GPT partition is not the expected 8 MiB")

    boot_first, boot_last = parts["hassos-boot"]
    mbr_boot = next((e for e in mbr_entries if e[4] in (0x0B, 0x0C)), None)
    if mbr_boot is None:
        raise ValueError("Hybrid MBR FAT boot partition is missing")
    mbr_start, mbr_count = struct.unpack_from("<II", mbr_boot, 8)
    if (mbr_start, mbr_count) != (boot_first, boot_last - boot_first + 1):
        raise ValueError("Hybrid MBR boot partition does not match GPT")
    if (primary["alternate_lba"] + 1) * SECTOR_SIZE > MAX_EMMC_BYTES:
        raise ValueError("Disk image cannot fit nominal 16GB eMMC")

    if prefix[32 * 1024:32 * 1024 + 4] != b"RKNS":
        raise ValueError("Rockchip SPL RKNS header missing at 32 KiB")
    fit_header = prefix[FIT_OFFSET:FIT_OFFSET + 40]
    fit_magic, fit_size = struct.unpack_from(">II", fit_header, 0)
    if fit_magic != 0xD00DFEED or not 40 <= fit_size <= UBOOT_PARTITION_SIZE:
        raise ValueError("Invalid U-Boot FIT/FDT header at eMMC 8 MiB")
    uboot_partition = prefix[FIT_OFFSET:FIT_OFFSET + UBOOT_PARTITION_SIZE]
    fit = uboot_partition[:fit_size]
    for marker in (b"lunzn,fastrhino-r68s", b"rk3568-fastrhino-r68s"):
        if marker not in fit:
            raise ValueError(f"R68S U-Boot FIT metadata missing: {marker.decode()}")
    for marker in (b"u-boot,spl-boot-order", b"same-as-spl", b"/mmc@fe310000"):
        if marker not in uboot_partition:
            raise ValueError(f"R68S U-Boot DTB boot-order metadata missing: {marker.decode()}")

    # Read to EOF so the XZ decoder validates the complete compressed stream.
    total_bytes = len(prefix)
    tail = bytearray(prefix[-TAIL_SIZE:])
    while True:
        chunk = image.read(READ_CHUNK)
        if not chunk:
            break
        total_bytes += len(chunk)
        tail.extend(chunk)
        if len(tail) > TAIL_SIZE:
            del tail[:-TAIL_SIZE]
    if total_bytes % SECTOR_SIZE:
        raise ValueError("Decompressed image size is not sector-aligned")
    total_sectors = total_bytes // SECTOR_SIZE
    if primary["alternate_lba"] != total_sectors - 1:
        raise ValueError("Primary GPT backup-LBA does not point to image end")

    backup = parse_gpt_header(bytes(tail[-SECTOR_SIZE:]), "Backup")
    if (backup["current_lba"] != primary["alternate_lba"]
            or backup["alternate_lba"] != primary["current_lba"]
            or backup["first_usable"] != primary["first_usable"]
            or backup["last_usable"] != primary["last_usable"]
            or backup["entry_count"] != primary["entry_count"]
            or backup["entry_size"] != primary["entry_size"]):
        raise ValueError("Primary and backup GPT headers disagree")
    backup_bytes = backup["entry_count"] * backup["entry_size"]
    tail_base = total_bytes - len(tail)
    backup_off = backup["entries_lba"] * SECTOR_SIZE - tail_base
    backup_end = backup_off + backup_bytes
    if backup_off < 0 or backup_end > len(tail) - SECTOR_SIZE:
        raise ValueError("Backup GPT entry array is outside the image tail")
    if backup_end != len(tail) - SECTOR_SIZE:
        raise ValueError("Backup GPT entry array is not immediately before its header")
    backup_entries = bytes(tail[backup_off:backup_end])
    if zlib.crc32(backup_entries) & 0xFFFFFFFF != backup["entries_crc"]:
        raise ValueError("Backup GPT entry-array CRC mismatch")
    if backup_entries != primary_entries:
        raise ValueError("Primary and backup GPT partition arrays differ")

    print(f"R68S_{stream_format}_STREAM_VALID ({total_bytes} bytes)")
    print("R68S_PRIMARY_AND_BACKUP_GPT_CRC_VALID")
    print("R68S_PARTITIONS_AND_HYBRID_MBR_VALID")
    print("R68S_ROCKCHIP_SPL_AND_FIT_LAYOUT_VALID")
    print("UNVERIFIED: no DDR training, eMMC boot, network, or OTA hardware test")


def verify(path):
    if path.endswith(".img"):
        with open(path, "rb") as image:
            verify_stream(image, "RAW")
    else:
        with lzma.open(path, "rb") as image:
            verify_stream(image)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check-image-gpt.py <image.img.xz|image.img>")
    try:
        verify(sys.argv[1])
    except (EOFError, lzma.LZMAError, OSError, ValueError) as exc:
        raise SystemExit(f"R68S image verification failed: {exc}")
