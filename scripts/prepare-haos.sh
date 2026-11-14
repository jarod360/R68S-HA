#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HAOS_SHA="${2:-945ba38d88e7e7d7321d42294b222b8deb2208d2}"
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Usage: bash scripts/prepare-haos.sh /path/to/haos [expected-official-commit-sha]" >&2
    exit 2
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HAOS_ROOT="$(cd "$1" && pwd)"
actual="$(git -C "$HAOS_ROOT" rev-parse HEAD)"
if [ "$actual" != "$EXPECTED_HAOS_SHA" ]; then
    echo "Unexpected HAOS commit: $actual (requires $EXPECTED_HAOS_SHA)" >&2
    exit 1
fi

EXT="$HAOS_ROOT/buildroot-external"
SOURCE="$EXT/board/hardkernel/odroid-m1"
BOARD="$EXT/board/fastrhino/r68s"
CONFIG="$EXT/configs/r68s_defconfig"
if [ -e "$BOARD" ] || [ -e "$CONFIG" ]; then
    echo "R68S target already exists; refusing to overwrite" >&2
    exit 1
fi

mkdir -p "$BOARD/patches/uboot" "$BOARD/patches/linux"
for file in boot-env.txt cmdline.txt haos-hook.sh image-spl-spl.cfg \
            partition-spl-spl.cfg uboot-boot.ush; do
    cp "$SOURCE/$file" "$BOARD/$file"
done
cp "$REPO_ROOT/board/r68s/meta" "$BOARD/meta"
# Headless RK3568 serial port for early boot diagnosis.
printf 'console=ttyS2,1500000n8\n' > "$BOARD/cmdline.txt"
cp "$REPO_ROOT/board/r68s/kernel.config" "$BOARD/kernel.config"
cp "$REPO_ROOT/board/r68s/uboot.config" "$BOARD/uboot.config"
cp -a "$REPO_ROOT/board/r68s/rootfs-overlay" "$BOARD/"
chmod 0755 "$BOARD/rootfs-overlay/usr/libexec/r68s-port-leds"
chmod 0755 "$BOARD/rootfs-overlay/usr/libexec/r68s-port-mac"
chmod 0755 "$BOARD/rootfs-overlay/usr/libexec/r68s-reset-poweroff"
chmod 0755 "$BOARD/rootfs-overlay/usr/sbin/r68s-os-update"
cp "$REPO_ROOT"/patches/uboot/*.patch "$BOARD/patches/uboot/"
cp "$REPO_ROOT"/patches/linux/*.patch "$BOARD/patches/linux/"
sed -i 's/rk3568-odroid-m1\.dtb/rk3568-fastrhino-r68s.dtb/g' "$BOARD/uboot-boot.ush"

# Fast-fail on upstream layout changes instead of building an incompatible image.
for expected in \
  'BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-odroid-m1"' \
  'BR2_TARGET_UBOOT_BOARD_DEFCONFIG="odroid-m1-rk3568"' \
  'BR2_PACKAGE_HASSIO_MACHINE="odroid-m1"'; do
    if [ "$(grep -Fxc "$expected" "$EXT/configs/odroid_m1_defconfig")" -ne 1 ]; then
        echo "Official HAOS board contract changed: $expected" >&2
        exit 1
    fi
done

cp "$EXT/configs/odroid_m1_defconfig" "$CONFIG"
sed -i \
    -e 's|board/hardkernel/odroid-m1|board/fastrhino/r68s|g' \
    -e 's|BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-odroid-m1"|BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-fastrhino-r68s"|' \
    "$CONFIG"

# Older stable HAOS releases only list the global patch directory.
board_patches='$(BR2_EXTERNAL_HAOS_PATH)/board/fastrhino/r68s/patches'
if ! grep '^BR2_GLOBAL_PATCH_DIR=' "$CONFIG" | grep -Fq "$board_patches"; then
    sed -i '/^BR2_GLOBAL_PATCH_DIR=/s|"$| '"$board_patches"'"|' "$CONFIG"
fi
grep '^BR2_GLOBAL_PATCH_DIR=' "$CONFIG" | grep -Fq "$board_patches"

# RTL8125B PCIe is already supported by Linux r8169 (module).
# ODROID-M1 does not select rtl_nic/rtl8125b-2.fw: install Realtek Ethernet firmware.
printf '\nBR2_PACKAGE_LINUX_FIRMWARE_RTL_8169=y\n' >> "$CONFIG"

# Apply stable, per-device MAC addresses to RTL8125 adapters with random MACs.
overlay='BR2_ROOTFS_OVERLAY="$(BR2_EXTERNAL_HAOS_PATH)/rootfs-overlay"'
grep -Fxq "$overlay" "$CONFIG"
sed -i '/^BR2_ROOTFS_OVERLAY=/s|"$| $(BR2_EXTERNAL_HAOS_PATH)/board/fastrhino/r68s/rootfs-overlay"|' "$CONFIG"

grep -Fq 'BR2_PACKAGE_LINUX_FIRMWARE_RTL_8169=y' "$CONFIG"
grep -Fq 'BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-fastrhino-r68s"' "$CONFIG"
grep -Fq 'BR2_TARGET_UBOOT_BOARD_DEFCONFIG="odroid-m1-rk3568"' "$CONFIG"
grep -Fq '# CONFIG_ROCKCHIP_SPI_IMAGE is not set' "$BOARD/uboot.config"
grep -Fq 'CONFIG_TARGET_EVB_RK3568=y' "$BOARD/uboot.config"
grep -Fq 'setenv fdtfile rk3568-fastrhino-r68s.dtb' "$BOARD/uboot-boot.ush"
grep -Fq 'BOARD_ID=r68s' "$BOARD/meta"

# Keep the full first-flash image, but never ship shared bootloader/boot files
# inside an Operating System A/B update bundle.
python3 "$REPO_ROOT/scripts/configure-safe-ota.py" "$EXT" "$BOARD"

echo "R68S_EXPERIMENTAL_SOURCE_READY=1"
echo "WARNING: no R68S 4GB boot-chain or flashing validation has been completed"
