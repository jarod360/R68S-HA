# R68S-HA — FastRhino R68S Native Home Assistant OS

**当前阶段：实验性适配，不能直接刷机。**

## 目标设备

- FastRhino R68S / RK3568 / **4GB RAM + 16GB eMMC**
- **没有 SD 卡槽**；支持 USB 3.0
- **原生 HAOS**（Buildroot、Supervisor、OS Agent、Docker 和 RAUC），不是普通 Linux 下的 Container 安装

## 唯一移植基础

1. **[官方 Home Assistant OS — ODROID-M1 RK3568](https://github.com/home-assistant/operating-system/tree/dev/buildroot-external/board/hardkernel/odroid-m1)**：继承 Buildroot、HAOS 分区、引导逻辑、RAUC 和系统更新。
2. **[Linux 主线 R68S DTS](https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r68s.dts)**：直接编译适用于 R68S 的主线设备树。
3. **[U-Boot 主线 v2026.04](https://github.com/u-boot/u-boot/tree/v2026.04)**：以 ODROID-M1 的 RK3568 配置为基础，禁用 M1 的 SPI 引导模式，采用 R68S eMMC 启动并使用主线 DTS。

**不使用第三方 Linux 内核、外部驱动或预编译 Bootloader。**

## 最小差异

- `board/r68s/kernel.config`：补足 RK3568 GMAC、eMMC 内建驱动；2.5G PCIe 使用官方 HAOS 内置 `r8169`。
- `board/r68s/uboot.config`：将 ODROID-M1 U-Boot 的 SPI 启动改为 R68S 所需的 eMMC 模式，切换到通用 RK3568 板级初始化，使用 R68S DTS。
- `patches/uboot/`：只补充 R68S SPL 的 eMMC 启动顺序；不覆盖主线驱动。
- `scripts/prepare-haos.sh`：对固定版本的官方 HAOS 进行板级适配，保留官方磁盘布局。
- `scripts/check-image-gpt.py`：编译后验证 GPT 结构、CRC、分区清单、标称 16GB 容量及 8MiB U-Boot FIT 位置。

## 构建与验证

GitHub 仓库：[jarod360/R68S-HA](https://github.com/jarod360/R68S-HA)

工作流：[R68S experimental HAOS build](https://github.com/jarod360/R68S-HA/actions/workflows/experimental-build.yml)。完成后会在 Actions Artifacts 出现 `R68S-HAOS-UNVERIFIED-DO-NOT-FLASH`，**仅表示构建候选产物，绝非可直接刷机证明**。

本地源码与构建请放在 Windows 的 `D:\Codex\R68S-HA`，不要将项目文件写到 C 盘。

```bash
git clone https://github.com/jarod360/R68S-HA.git
git clone https://github.com/home-assistant/operating-system.git haos
git -C haos checkout 945ba38d88e7e7d7321d42294b222b8deb2208d2
git -C haos submodule update --init --recursive
bash R68S-HA/scripts/prepare-haos.sh haos
# 使用 HAOS 官方 Docker builder 进行 make r68s-config 与 make 编译
```

## 已知风险

- R68S 4GB 上曾有其他 OS 成功运行的实机经历，表明硬件可用；**但不能证明 ODROID-M1 的 DDR TPL 与 R68S 兼容**。
- 必须验证 BootROM、DDR 初始化、SPL、U-Boot、eMMC 和完整 HAOS A/B 分区启动链。
- 两个千兆及两个 2.5G 网口、USB 3.0、Supervisor、OS Agent、RAUC 升级/回滚仍需实机验证。
- 固件测试前必须备份整块 eMMC，并确认 Recovery/Maskrom 恢复路径。
- 默认映射到 `odroid-m1` Supervisor 机器标识属于临时实验兼容方案，**不是官方 R68S 支持**。

核查与验证日志见 [docs/RESEARCH.md](docs/RESEARCH.md)；明早刷机准备及停止条件见 [docs/FLASH-TEST.md](docs/FLASH-TEST.md)。

**状态：源码适配及自动构建配置已提交；尚无实机测试通过的镜像。**
