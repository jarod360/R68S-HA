# R68S-HA：官方 ODROID-M1 基础的最小移植研究

更新日期：2026-11-12。

## 事实与推断

- **事实**：官方 HAOS `buildroot-external/configs/odroid_m1_defconfig` 是 RK3568 系统，包含 Buildroot、RAUC A/B、Docker、Supervisor 和 OS Agent。
- **事实**：Linux v6.18 包含 `rk3568-fastrhino-r68s.dts`，描述 R68S eMMC、双 GMAC，并经共用 DTSI 配置 PCIe、USB 等控制器。
- **事实**：官方 HAOS RK3568 内核已有 `CONFIG_R8169=m`、PCIe 驱动及 Realtek PHY 驱动；Buildroot 有 `BR2_PACKAGE_LINUX_FIRMWARE_RTL_8169`，用以安装有线网卡固件。
- **事实**：U-Boot v2026.04 的 `odroid-m1-rk3568_defconfig` 默认 `CONFIG_ROCKCHIP_SPI_IMAGE=y`；R68S 需要从 eMMC 进入 SPL。因此不能把 M1 的固件直接写入 R68S。
- **移植选择**：继续用官方 M1 作为 HAOS/U-Boot defconfig 起点；使用 fragment 关闭 SPI image，选择通用 RK3568 board 初始化并编译 R68S DTS；新增小补丁让 SPL 优先寻找 `sdhci`。
- **事实（用户实机经历）**：这台 R68S 曾正常运行过飞牛 OS，提供硬件、eMMC 可启动的间接证据。
- **未验证**：上述 ODROID-M1 改造的 U-Boot 是否能够初始化 4GB RAM、读取 R68S eMMC 并启动 Linux。

## 安全门槛

1. 完成 GitHub Actions 云编译并检验 GPT；即便成功，依然只标 `UNVERIFIED-DO-NOT-FLASH`。
2. 验证 Rockchip 官方 DDR TPL blob 是否兼容 R68S 4GB LPDDR4；必要时需正确的 R68S DDR 初始化源码或可信 blob，不能猜测。
3. 在刷机前离机备份现有 16GB eMMC，并确认 Recovery/Maskrom 恢复可用。
4. 实机依次验证 DDR/SPL、U-Boot/eMMC、内核、4 个网口、USB 3.0、Supervisor、OS Agent、RAUC 更新/回滚。
5. 长期使用可考虑 USB 3.0 外置 SSD 作为 HAOS data disk，不能把“USB 3.0 可用”等同“USB 启动已支持”。

## 参考（仅使用官方项目和主线）

- [Home Assistant OS 官方源码](https://github.com/home-assistant/operating-system)
- [ODROID-M1 官方 HAOS 板级配置](https://github.com/home-assistant/operating-system/tree/dev/buildroot-external/board/hardkernel/odroid-m1)
- [U-Boot v2026.04 的 ODROID-M1 配置](https://github.com/u-boot/u-boot/blob/v2026.04/configs/odroid-m1-rk3568_defconfig)
- [Linux v6.18 的 R68S 设备树](https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r68s.dts)
