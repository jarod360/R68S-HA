#!/usr/bin/env python3
"""Package the R68S device tree in each kernel slot."""

from pathlib import Path
import sys


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f"Unexpected upstream boot template: {old.splitlines()[0]}")
    return text.replace(old, new, 1)


ext, board = map(Path, sys.argv[1:])
dtb = "rk3568-fastrhino-r68s.dtb"

# Preserve Image at its existing path so the original boot script can still
# boot a candidate carrying the shared DTB. The new script prefers the slot DTB.
recipe = (ext / "genimage" / "images-os.cfg").read_text()
recipe = replace_once(
    recipe,
    '${BINARIES_DIR:-PLEASE_SPECIFY_BINARIES_DIR}/${KERNEL_FILE:-PLEASE_SPECIFY_KERNEL_FILE}',
    '${BINARIES_DIR:-PLEASE_SPECIFY_BINARIES_DIR}/r68s-kernel-slot',
)
(board / "images-os.cfg").write_text(recipe)

hook = board / "haos-hook.sh"
hook.write_text(replace_once(
    hook.read_text(),
    '    cp "${BINARIES_DIR}/boot.scr" "${BOOT_DATA}/boot.scr"',
    f'''    local slot_dir="${{BINARIES_DIR}}/r68s-kernel-slot"
    mkdir -p "$slot_dir"
    cp "${{BINARIES_DIR}}/Image" "${{BINARIES_DIR}}/{dtb}" "$slot_dir/"
    cp "${{BINARIES_DIR}}/boot.scr" "${{BOOT_DATA}}/boot.scr"''',
))

boot = board / "uboot-boot.ush"
script = boot.read_text()
load_start = f"# Load device tree\nsetenv fdtfile {dtb}\n"
load_end = "# Refill the tries when no slot in BOOT_ORDER has any left"
if script.count(load_start) != 1 or script.count(load_end) != 1:
    raise SystemExit("Unexpected upstream R68S device tree block")
start = script.index(load_start)
end = script.index(load_end, start)
original = script[start:end]
overlays_start = "# load dt overlays"
if original.count(overlays_start) != 1:
    raise SystemExit("Unexpected upstream R68S overlay block")
overlays = original[original.index(overlays_start):]
overlays = replace_once(
    overlays,
    '  fatload ${devtype} ${devnum}:${boot_partnum} ${fdt_addr_r} ${fdtfile}',
    '  if run load_slot_fdt; then true; else reset; fi',
)

script = replace_once(script, original, "")
script = replace_once(script, 'echo "Starting kernel"', f'''# kernel_partnum still refers to the slot whose Image was loaded.
setenv fdtfile {dtb}
if test -e ${{devtype}} ${{devnum}}:${{kernel_partnum}} ${{fdtfile}}; then
  echo "Loading device tree from kernel partition ${{kernel_partnum}}"
  setenv load_slot_fdt 'load ${{devtype}} ${{devnum}}:${{kernel_partnum}} ${{fdt_addr_r}} ${{fdtfile}} && fdt addr ${{fdt_addr_r}}'
  setenv bootargs "${{bootargs}} r68s.slot_dtb=1"
else
  echo "Loading shared device tree for a legacy kernel slot"
  setenv load_slot_fdt 'fatload ${{devtype}} ${{devnum}}:${{boot_partnum}} ${{fdt_addr_r}} ${{fdtfile}} && fdt addr ${{fdt_addr_r}}'
fi
if run load_slot_fdt; then
  setenv overlay_error
else
  echo "Failed to load device tree, resetting..."
  reset
fi

{overlays}echo "Starting kernel"''')
boot.write_text(script)
