#!/usr/bin/env python3
"""Keep R68S OS updates restricted to RAUC A/B kernel + rootfs slots.

The full flash image still contains the original HAOS boot/SPL images.
Fails on upstream template drift; it must be reviewed before upgrades.
"""
from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("Usage: configure-safe-ota.py <buildroot-external> <board-dir>")

ext = Path(sys.argv[1])
board = Path(sys.argv[2])


def remove_once(path, block):
    content = path.read_text()
    if content.count(block) != 1:
        raise SystemExit(f"Upstream OTA template changed: {path} ({block[:35]!r})")
    path.write_text(content.replace(block, "", 1))


manifest = ext / "ota" / "manifest.raucm.gtpl"
remove_once(manifest, "[image.boot]\nfilename=boot.vfat\nhooks=install;\n\n")
remove_once(manifest, '{{- if eq (env "BOOT_SPL") "true" }}\n[image.spl]\nfilename=spl.img\nhooks=install\n{{- end }}\n')

system = ext / "ota" / "system.conf.gtpl"
remove_once(system, '[slot.boot.0]\ndevice=/dev/disk/by-partlabel/hassos-boot\ntype=vfat\nallow-mounted=true\n')
remove_once(system, '{{- if eq (env "BOOT_SPL") "true" }}\n[slot.spl.0]\ndevice=/dev/disk/by-partlabel/hassos-boot\ntype=raw\n{{- end }}\n')

# Genimage resolves includes from BOARD_DIR before the shared genimage dir.
# Override only the OTA bundle recipe; the full disk image still includes SPL.
recipe = (ext / "genimage" / "image-raucb-spl.cfg").read_text()
for block in ('\tfile spl.img { image = "spl.img" }\n',
              '\tfile boot.vfat { image = "boot.vfat" }\n'):
    if recipe.count(block) != 1:
        raise SystemExit("Upstream RAUC bundle recipe changed; review required")
    recipe = recipe.replace(block, "", 1)

if 'file kernel.img' not in recipe or 'file rootfs.img' not in recipe:
    raise SystemExit("Missing kernel/rootfs in OTA bundle recipe")

(board / "image-raucb-spl.cfg").write_text(recipe)

if "[image.boot]" in manifest.read_text() or "[image.spl]" in manifest.read_text():
    raise SystemExit("Boot image entries unexpectedly retained in OTA manifest")
if "[slot.boot.0]" in system.read_text() or "[slot.spl.0]" in system.read_text():
    raise SystemExit("Mutable boot/SPL RAUC slots unexpectedly retained")
print("R68S_KERNEL_ROOTFS_ONLY_OTA_CONFIGURED=1")
