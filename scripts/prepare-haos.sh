#!/usr/bin/env bash
set -euo pipefail

EXPECTED_HAOS_SHA="945ba38d88e7e7d7321d42294b222b8deb2208d2"
if [ "$#" -ne 1 ]; then
    echo "Usage: bash scripts/prepare-haos.sh /path/to/haos" >&2
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

mkdir -p "$BOARD/patches/uboot"
for file in boot-env.txt cmdline.txt haos-hook.sh image-spl-spl.cfg \
            partition-spl-spl.cfg uboot-boot.ush; do
    cp "$SOURCE/$file" "$BOARD/$file"
done
cp "$REPO_ROOT/board/r68s/meta" "$BOARD/meta"
cp "$REPO_ROOT/board/r68s/kernel.config" "$BOARD/kernel.config"
cp "$REPO_ROOT/board/r68s/uboot.config" "$BOARD/uboot.config"
cp "$REPO_ROOT"/patches/uboot/*.patch "$BOARD/patches/uboot/"
sed -i 's/rk3568-odroid-m1\.dtb/rk3568-fastrhino-r68s.dtb/g' "$BOARD/uboot-boot.ush"

cp "$EXT/configs/odroid_m1_defconfig" "$CONFIG"
sed -i \
    -e 's|board/hardkernel/odroid-m1|board/fastrhino/r68s|g' \
    -e 's|BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-odroid-m1"|BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-fastrhino-r68s"|' \
    -e 's|BR2_TARGET_UBOOT_BOARD_DEFCONFIG="odroid-m1-rk3568"|BR2_TARGET_UBOOT_BOARD_DEFCONFIG="fastrhino-r66s-rk3568"|' \
    "$CONFIG"

grep -Fq 'BR2_LINUX_KERNEL_INTREE_DTS_NAME="rockchip/rk3568-fastrhino-r68s"' "$CONFIG"
grep -Fq 'BR2_TARGET_UBOOT_BOARD_DEFCONFIG="fastrhino-r66s-rk3568"' "$CONFIG"
grep -Fq 'setenv fdtfile rk3568-fastrhino-r68s.dtb' "$BOARD/uboot-boot.ush"
grep -Fq 'BOARD_ID=r68s' "$BOARD/meta"

echo "R68S_EXPERIMENTAL_SOURCE_READY=1"
echo "WARNING: no R68S 4GB boot-chain or flashing validation has been completed"
