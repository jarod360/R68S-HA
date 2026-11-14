# R68S-HA — FastRhino R68S Native Home Assistant OS

**已在 R68S 4 GB / 16 GB eMMC 上完成原生 HAOS 19.0.dev2 整盘刷写和正常启动，并通过自有仓库的跨版本签名 OTA。** Recovery、刷机、后续 OTA 和已验证项目见 [安装与交接说明](docs/HANDOFF.md)。

## 部署与日常使用

1. 首次安装或恢复时，先把 HA 完整备份导出到另一台设备，再按交接说明使用 RKDevTool 和 R68S 整盘镜像刷入 eMMC。整盘刷机会覆盖系统和数据。 [刷机与恢复步骤](docs/HANDOFF.md#首次安装或整盘恢复)
2. 首次启动接入有 DHCP 和互联网的网络，从路由器查到 R68S 的 IP 后打开 `http://设备IP:8123`。等待 Core 下载完成；也可用 `http://设备IP:4357` 查看 Supervisor Observer。欢迎页可新建系统或恢复已有 HA 备份。
3. 已安装签名版的设备，从 HAOS 主机控制台运行 `r68s-os-update --check` 查询稳定发布，运行 `r68s-os-update <版本>` 下载自有仓库的签名 OS 包。安装完成后重启并确认 HA 恢复。测试预发行版可按 Release 说明显式指定版本。Core、Supervisor 和应用使用 Home Assistant 官方渠道。 [R68S Releases](https://github.com/jarod360/R68S-HA/releases)

短按 Reset 已验证可正常关机。按住 Recovery 上电实测进入 MASKROM，按键进入 LOADER 仍待验证。

## 目标硬件

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

## 适配官方 HAOS 大版本

1. 选定官方稳定 tag，解析为完整的 40 位提交 SHA。在 Actions 手动运行 `R68S experimental HAOS build`，填入 `haos_sha`，启用 `require_ota`。默认分支上的定时任务也会检查官方稳定版并生成候选产物。 [构建工作流](https://github.com/jarod360/R68S-HA/actions/workflows/experimental-build.yml)
2. 如果上游目录、ODROID-M1 配置或镜像模板变更，先对比上一次已通过实测的 HAOS 提交。调整 `scripts/prepare-haos.sh` 中的配置匹配和板级文件复制，按需要更新 `board/r68s/`、`patches/linux/`、`patches/uboot/`。如果 RAUC 模板变更，同步修改 `scripts/configure-safe-ota.py` 和产物校验。
3. 编译后核对 R68S 设备树、GPT/FIT、签名和 A/B 槽内容。用旧版实机验证 OTA、重启、HA 数据和回退。如果设备树校验不同，普通 OTA 会拒绝安装。涉及 U-Boot 或共享启动区的变更，另行验收整盘镜像和恢复路径。
4. 实机通过后，将签名 `.raucb` 和 `R68S-DTB-SHA256` 发布到对应的 `r68s-<版本>` Release。签名身份继续由仓库的 GitHub Actions Secrets 提供。 [更新方案与验收清单](docs/UPDATE-STRATEGY.md)

## 使用限制

- 新构建需单独验收。尚待验证的项目见 [实机验收状态](docs/HANDOFF.md#实机验收状态)。
- 固件测试前必须备份整块 eMMC，并确认 Recovery/Maskrom 恢复路径。
- 默认映射到 `odroid-m1` Supervisor 机器标识属于临时实验兼容方案，**不是官方 R68S 支持**。

核查与验证日志见 [docs/RESEARCH.md](docs/RESEARCH.md)；[docs/FLASH-TEST.md](docs/FLASH-TEST.md) 是首次实机清单；[docs/UPDATE-STRATEGY.md](docs/UPDATE-STRATEGY.md) 说明持续适配官方 HAOS、A/B 更新和长期签名策略。
