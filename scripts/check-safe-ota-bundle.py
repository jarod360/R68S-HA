#!/usr/bin/env python3
"""Verify an actual R68S RAUC bundle and the target's RAUC slot policy.

Does not test installation or hardware rollback; refuse to approve unknown formats.
"""
import configparser
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 6:
    raise SystemExit(
        "Usage: check-safe-ota-bundle.py bundle.raucb rauc-bin "
        "keyring.pem system.conf intermediate-ca.pem"
    )

bundle, rauc, keyring, config, intermediate = map(Path, sys.argv[1:])
for p in (bundle, rauc, keyring, config, intermediate):
    if not p.is_file() or not p.stat().st_size:
        raise SystemExit(f"Missing verification input: {p}")

# Buildroot's host-rauc is compiled with -Djson=disabled. The upstream
# shell formatter is always available and still performs full signature checks.
command = [
    str(rauc),
    f"--keyring={keyring}",
    f"--intermediate={intermediate}",
    "info",
    "--output-format=shell",
    str(bundle),
]
result = subprocess.run(command, check=False, capture_output=True, text=True)
if result.returncode:
    detail = result.stderr.strip() or result.stdout.strip() or "no RAUC diagnostic"
    raise SystemExit(f"RAUC bundle verification failed: {detail}")

info = {}
for line in result.stdout.splitlines():
    if not line.strip():
        continue
    if "=" not in line:
        raise SystemExit(f"Unexpected RAUC shell output: {line!r}")
    key, raw_value = line.split("=", 1)
    info[key] = raw_value

compatible = info.get("RAUC_MF_COMPATIBLE")
if compatible != "haos-r68s":
    raise SystemExit(f"Unexpected update compatibility: {compatible!r}")

try:
    image_count = int(info.get("RAUC_MF_IMAGES", "-1"))
except ValueError:
    raise SystemExit("Invalid RAUC image count")

if image_count != 2:
    raise SystemExit(f"Expected exactly two OTA images: {image_count!r}")
classes = {info.get(f"RAUC_IMAGE_CLASS_{i}") for i in range(image_count)}
if classes != {"kernel", "rootfs"}:
    raise SystemExit(f"Unsafe OTA slot classes: {classes!r}")

ini = configparser.ConfigParser(interpolation=None)
ini.read(config)
for name in ("slot.kernel.0", "slot.kernel.1",
             "slot.rootfs.0", "slot.rootfs.1"):
    if name not in ini:
        raise SystemExit(f"Missing RAUC A/B slot: {name}")
for name in ini.sections():
    if name.startswith("slot.") and not (
        name.startswith("slot.kernel.") or name.startswith("slot.rootfs.")
    ):
        raise SystemExit(f"Unexpected mutable RAUC slot: {name}")

print("R68S_RAUC_SIGNATURE_AND_AB_IMAGES_VALID")
print("Compatible=haos-r68s; only kernel/rootfs images; no boot/SPL slots")
print("BUILD_ONLY: not an install, recovery, or kernel/DTB compatibility test")
