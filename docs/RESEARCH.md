# R68S-HA 技术核查（2026-11-12）

## 已核实的代码基础

- **Linux v6.18** 包含 `rk3568-fastrhino-r68s.dts`，R68S 的 `&sdhci` 描述 8-bit eMMC、两个 GMAC PHY；共用 `rk3568-fastrhino-r66s.dtsi` 提供 PCIe 与 USB 配置。
- **R68S 4GB/16GB 型号确实存在**，双 RTL8125BG 2.5G PCIe 网卡、双 RTL8211F 千兆 PHY；不是仅有 1GB/2GB 版本。
- **HAOS 官方 ODROID-M1 构建目标**同为 RK3568，Buildroot + Supervisor + OS Agent + RAUC A/B 分区的体系可复用。
- **U-Boot v2026.04** 有 R66S defconfig 和 R68S 的 Linux DTS，但未找到完整 R68S defconfig。当前使用 R66S 配置 + R68S eMMC/GMAC config fragment + U-Boot DTS 补丁。
- **Armbian** 有 R68S 专用 `build-armbian/u-boot/r68s/bootloader.bin`，但该预编译文件的 DDR 4GB 初始化能力、许可及 HAOS 分区兼容性没有核实，尚未纳入构建。

## 技术难点与验收标准

1. **DDR TPL**：HAOS ODROID-M1 配置沿用 Rockchip DDR blob，不能假定 4GB R68S 初始化一定成功；这是首要实机风险。
2. **eMMC / 引导**：R68S 没有 SD 卡槽，必须保证 BootROM → TPL/SPL → U-Boot → GPT → HAOS A/B；不能直接采用 OpenWrt `sysupgrade` 格式和升级方法。
3. **网卡**：Linux 内核已经有 STMMAC、R8169 等驱动，但仍需检查两个千兆及两个 2.5G 的枚举、复位和吞吐。
4. **存储**：16GB eMMC 可尝试引导，但 HAOS 长期数据需要空间；以后可选择外接 USB 3.0 SSD 迁移数据盘，不等于 USB 启动。
5. **OTA**：使用 `odroid-m1` Supervisor 机器标识仅为构建阶段兼容性策略；不能声明得到官方 R68S 支持。必须另测 RAUC 签名、更新和回滚。

## 构建检查新增内容

- `scripts/prepare-haos.sh` 固定上游提交，启用 `console=ttyS2,1500000n8` 串口日志。
- `scripts/check-image-gpt.py` 检查 GPT/MBR、CRC、HAOS 分区名称和镜像容量。
- CI artifact 标注 `UNVERIFIED-DO-NOT-FLASH`。**通过以上检查仅代表分区结构合理，不代表可刷机。**

## 参考

- https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r68s.dts
- https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r66s.dtsi
- https://github.com/u-boot/u-boot/blob/v2026.04/configs/fastrhino-r66s-rk3568_defconfig
- https://github.com/SmartElec/rockchip-armbian/tree/main/build-armbian/u-boot/r68s
- https://github.com/home-assistant/operating-system/tree/dev/buildroot-external/board/hardkernel/odroid-m1
- https://contributors.home-assistant.io/os/operating-system/partitions/
