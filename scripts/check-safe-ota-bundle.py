#!/usr/bin/env python3
"""Verify an actual R68S RAUC bundle and the target's RAUC slot policy.

Does not test installation or hardware rollback; refuse to approve unknown formats.
"""
import configparser
import json
from pathlib import Path
import subprocess
import sys

if len(sys.argv) != 5:
    raise SystemExit(
        "Usage: check-safe-ota-bundle.py bundle.raucb rauc-bin "
        "keyring.pem system.conf"
    )

bundle, rauc, keyring, config = map(Path, sys.argv[1:])
for p in (bundle, rauc, keyring, config):
    if not p.is_file() or not p.stat().st_size:
        raise SystemExit(f"Missing verification input: {p}")

# Full certificate verification: --no-verify would make the result unsafe.
result = subprocess.run(
    [str(rauc), f"--keyring={keyring}", "info", "--output-format=json-2", str(bundle)],
    check=True, capture_output=True, text=True,
)
info = json.loads(result.stdout)
update = info.get("update", {})
if update.get("compatible") != "haos-r68s":
    raise SystemExit(f"Unexpected update compatibility: {update!r}")

images = info.get("images")
if not isinstance(images, list) or len(images) != 2:
    raise SystemExit(f"Expected exactly two OTA images: {images!r}")
classes = {i.get("slot-class") for i in images}
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
