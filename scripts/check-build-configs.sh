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
mac_link="$out/target/usr/lib/systemd/network/90-r68s-rtl8125.link"
check "$mac_link" 'Driver=r8169'
check "$mac_link" 'MACAddressPolicy=persistent'
check "$uboot" 'CONFIG_DEFAULT_DEVICE_TREE="rockchip/rk3568-fastrhino-r68s"'
check "$uboot" 'CONFIG_OF_LIST="rockchip/rk3568-fastrhino-r68s"'
check "$uboot" 'CONFIG_SPL_OF_LIST="rockchip/rk3568-fastrhino-r68s"'
check "$uboot" 'CONFIG_TARGET_EVB_RK3568=y'
check "$uboot" '# CONFIG_ROCKCHIP_SPI_IMAGE is not set'
check "$uboot" 'CONFIG_SPL_PAD_TO=0x7f8000'
check "$uboot" 'CONFIG_MMC_SDHCI_ROCKCHIP=y'
check "$uboot" 'CONFIG_CMD_MMC=y'
check "$uboot" 'CONFIG_CMD_PART=y'
check "$uboot" 'CONFIG_CMD_FS_GENERIC=y'
check "$uboot" 'CONFIG_CMD_FAT=y'
check "$uboot" 'CONFIG_CMD_SQUASHFS=y'
check "$uboot" 'CONFIG_CMD_FDT=y'
check "$uboot" 'CONFIG_CMD_BOOTI=y'
check "$uboot" 'CONFIG_USB_DWC3_GENERIC=y'
check "$uboot" 'CONFIG_PHY_ROCKCHIP_INNO_USB2=y'
check "$uboot" 'CONFIG_USB_GADGET=y'
check "$uboot" 'CONFIG_USB_GADGET_DOWNLOAD=y'
check "$uboot" 'CONFIG_USB_FUNCTION_ROCKUSB=y'
check "$uboot" 'CONFIG_CMD_ROCKUSB=y'
check "$uboot" 'CONFIG_FS_FAT=y'
check "$uboot" 'CONFIG_FS_SQUASHFS=y'
check "$uboot" 'CONFIG_BOOTDELAY=3'
check "$uboot" 'CONFIG_SPL_MMC=y'
check "$uboot" 'CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_USE_SECTOR=y'
check "$uboot" 'CONFIG_SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR=0x4000'
check "$linux" 'CONFIG_DWMAC_ROCKCHIP=y'
check "$linux" 'CONFIG_MMC_SDHCI_OF_DWCMSHC=y'
check "$linux" 'CONFIG_PCIE_ROCKCHIP_DW_HOST=y'
check "$linux" 'CONFIG_R8169=m'
check "$linux" 'CONFIG_R8169_LEDS=y'
check "$linux" 'CONFIG_DW_WATCHDOG=y'
fdtget="$out/host/bin/fdtget"
dtb="$out/images/rk3568-fastrhino-r68s.dtb"
test -x "$fdtget" || { echo "Missing host fdtget" >&2; exit 1; }
compatible=$("$fdtget" -t s "$dtb" / compatible)
printf '%s\n' "$compatible" | grep -Fq 'lunzn,fastrhino-r68s' || {
  echo "Compiled DTB has the wrong board compatible: $compatible" >&2; exit 1; }
printf '%s\n' "$compatible" | grep -Fq 'rockchip,rk3568' || {
  echo "Compiled DTB is not an RK3568 device tree: $compatible" >&2; exit 1; }
model=$("$fdtget" -t s "$dtb" / model)
test "$model" = "Lunzn FastRhino R68S" || {
  echo "Unexpected R68S DTB model: $model" >&2; exit 1; }
for node in /ethernet@fe010000 /ethernet@fe2a0000 \
            /pcie@fe270000 /pcie@fe280000 \
            /mmc@fe310000 /watchdog@fe600000 /serial@fe660000; do
  status=$("$fdtget" -t s "$dtb" "$node" status) || {
    echo "Missing R68S hardware node: $node" >&2; exit 1; }
  test "$status" = "okay" || {
    echo "R68S hardware node is disabled: $node ($status)" >&2; exit 1; }
done
echo 'R68S_COMPILED_CONFIGS_VALID (build-level only; not a boot test)'
