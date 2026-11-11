#!/bin/sh
# Inspect the compiled configurations after make completes. Does not flash.
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: sh scripts/check-build-configs.sh /path/to/haos/output" >&2
  exit 2
fi

out=$1
for file in "$out/.config" "$out/images/u-boot-rockchip.bin" \
            "$out/images/rk3568-fastrhino-r68s.dtb" "$out/images/boot.scr"; do
  test -s "$file" || { echo "Missing build output: $file" >&2; exit 1; }
done

set -- "$out"/build/uboot-*/.config
test -f "$1" || { echo "Missing built U-Boot .config" >&2; exit 1; }
uboot=$1
set -- "$out"/build/linux-*/.config
test -f "$1" || { echo "Missing built Linux .config" >&2; exit 1; }
linux=$1

check() {
  grep -Fqx "$2" "$1" || { echo "Expected '$2' in $1" >&2; exit 1; }
}

check "$out/.config" 'BR2_PACKAGE_LINUX_FIRMWARE_RTL_8169=y'
check "$uboot" 'CONFIG_DEFAULT_DEVICE_TREE="rockchip/rk3568-fastrhino-r68s"'
check "$uboot" 'CONFIG_TARGET_EVB_RK3568=y'
check "$uboot" '# CONFIG_ROCKCHIP_SPI_IMAGE is not set'
check "$uboot" 'CONFIG_SPL_PAD_TO=0x7f8000'
check "$uboot" 'CONFIG_MMC_SDHCI_ROCKCHIP=y'
check "$uboot" 'CONFIG_SPL_MMC=y'
check "$uboot" 'CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_USE_SECTOR=y'
check "$uboot" 'CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR=0x4000'
check "$linux" 'CONFIG_DWMAC_ROCKCHIP=y'
check "$linux" 'CONFIG_MMC_SDHCI_OF_DWCMSHC=y'
check "$linux" 'CONFIG_PCIE_ROCKCHIP_DW_HOST=y'
check "$linux" 'CONFIG_R8169=m'
echo 'R68S_COMPILED_CONFIGS_VALID (build-level only; not a boot test)'
