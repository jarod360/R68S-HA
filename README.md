# R68S-HA — FastRhino R68S Home Assistant OS (EXPERIMENTAL)

> **未验证 / NOT FLASHABLE YET.** 本仓库目前用于研究和构建 R68S 原生 HAOS 候选镜像。构建成功不代表可启动，不代表适合写入 eMMC。尚未完成 R68S 4GB 实机启动、网口、USB、RAUC A/B 更新及恢复测试。**请勿直接刷入现有机器。**

## 目标硬件

- FastRhino R68S / Rockchip RK3568 / 4GB RAM / 16GB eMMC
- 无 TF/SD 卡槽；有 USB 3.0
- 原生 Home Assistant Operating System（Buildroot + Supervisor + Docker + OS Agent），**不是 Armbian + Home Assistant Container**

## 已核实的上游基础

- [Home Assistant OS 官方源码](https://github.com/home-assistant/operating-system)：ODROID-M1 / RK3568 Buildroot 配置、HAOS 分区和 RAUC A/B 引导。
- [Linux 主线 R68S DTS](https://github.com/torvalds/linux/blob/master/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r68s.dts)：R68S 专用设备树已经存在。
- [U-Boot 主线 R66S 配置](https://github.com/u-boot/u-boot/blob/master/configs/fastrhino-r66s-rk3568_defconfig)：作为 RK3568 FastRhino SPL 起点。**R68S 的 eMMC 引导配置仍需验证。**
- [LEDE R68S U-Boot 补丁](https://github.com/coolsnowwolf/lede/blob/master/package/boot/uboot-rockchip/patches/311-rockchip-rk3568-Add-support-for-fastrhino-r6xs.patch)：提供 R68S eMMC 和 USB OTG 差异参考。
- [SmartElec rockchip-armbian](https://github.com/SmartElec/rockchip-armbian)：提供 R68S 相关构建/启动资料，并包含 `build-armbian/u-boot/r68s/bootloader.bin`。这是预编译文件，**未用于本项目，未验证来源/重分发许可**。
- [iStoreOS R68S 板级配置](https://github.com/istoreos/istoreos/blob/main/target/linux/rockchip/dts/rk3568/rk3568-fastrhino-r68s.dts)。

## 仓库结构

- `scripts/prepare-haos.sh`：把最小 R68S 变更应用到**固定 SHA** 的 HAOS 源码（不会复制整套上游源码）。
- `board/r68s/`：HAOS 元数据、内核与 U-Boot config fragment。
- `patches/uboot/`：R68S eMMC 启动优先级差异补丁。
- `.github/workflows/experimental-build.yml`：手动触发云构建，结果仅作为实验 artifacts。

## 构建

Linux + Git + Docker 环境；建议内存与磁盘较充足的 GitHub Actions runner 或专用 Linux 构建机。Windows 开发本地文件请放在 `D:\Codex\R68S-HA`，不要在 C 盘创建项目文件。

```bash
git clone https://github.com/jarod360/R68S-HA.git
git clone https://github.com/home-assistant/operating-system.git haos
git -C haos checkout 945ba38d88e7e7d7321d42294b222b8deb2208d2
git -C haos submodule update --init --recursive
bash R68S-HA/scripts/prepare-haos.sh haos
# 配好 HAOS 官方 Docker 构建环境后：
# make -C haos r68s-config
# make -C haos
```

或者到 GitHub Actions 手动运行 `R68S experimental HAOS build`。CI 仅构建候选镜像，不自动发布 Release，不自动刷机。

## 技术风险与验证门槛

1. **SPL/TPL DDR 初始化**：R68S 4GB 机器的内存初始化与现成 ODROID-M1/R66S 的 Rockchip blob 未证实兼容；该项不验证，**禁止刷机**。
2. **引导与分区**：HAOS 采用 SPL + GPT + A/B RAUC；要验证 eMMC boot ROM 与分区偏移、Recovery/Maskrom 救援，不得把 OpenWrt 的 sysupgrade 当作 HAOS 整盘写入工具。
3. **网络**：官方 HAOS 内核已有 PCIe `r8169`（包含 RTL8125B 支持），本项目额外启用 `BR2_PACKAGE_LINUX_FIRMWARE_RTL_8169`，补齐 `rtl_nic/rtl8125b-2.fw`；四端口枚举和 PHY 时序仍需实机测试。
4. **磁盘**：16GB eMMC 较紧张；后续优先考虑把 HAOS data partition 迁到 USB 3.0 SSD。
5. **Supervisor/OS-Agent/OTA**：初始使用官方 ODROID-M1 容器机器标识只是启动验证兼容策略，不代表官方认可 R68S。最终应消除平台伪装并确认 RAUC 签名/更新渠道。

核查记录：[docs/RESEARCH.md](docs/RESEARCH.md)。

已按官方 ODROID-M1 的方式精简适配：保留内核自带的 `r8169` 模块，仅补充 RTL8125B 固件包和 R68S 的 eMMC/GMAC 配置。

## 当前状态

- [x] 找到 Linux/R68S DTS、Armbian/LEDE 引导来源与官方 HAOS RK3568 基础
- [x] 建立最小可复现的源码适配与实验 CI
- [ ] 在 GitHub Actions 构建通过并核对产物 GPT、SHA256
- [ ] 验证 R68S 4GB DDR loader / eMMC 启动链
- [ ] 完成真实设备启动、双千兆/双 2.5G、USB 3.0 测试
- [ ] 验证 Supervisor、备份与 RAUC A/B 回滚
- [ ] 经过恢复方案演练后才发布可刷机测试版

**本仓库不会在没有实机验证之前把产物标成“可直接刷机”。**
