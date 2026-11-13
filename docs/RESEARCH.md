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

## 补充发现：先于刷机必须核对

- **U-Boot FIT 位置**：主线 U-Boot `rockchip-u-boot.dtsi` 将 FIT 放在 `CONFIG_SPL_PAD_TO`（Rockchip 默认 `0x7f8000`）；官方 M1 `image-spl-spl.cfg` 将 `u-boot-rockchip.bin` 放在 32KiB。因此期望 eMMC **8MiB** 处存在 FIT 标头 `0xd00dfeed`。检查静态镜像的此位置可发现引导布局明显错误，仍不能证明启动成功。
- **OTA 兼容性保护**：本项目 `BOARD_ID=r68s`，RAUC `compatible=haos-r68s`；而 Supervisor 容器阶段暂时使用 `odroid-m1` 机器标识。不能直接使用官方 M1 系统更新包。正式使用前要有 R68S 专属签名、更新和回滚测试。
- **boot0/boot1**：eMMC 除用户区域以外可能存在硬件启动分区，需要实机确认；只备份 GPT 分区并不一定能恢复原始引导链。
- **无显示屏和 SD 槽**：首启调试建议使用 3.3V UART（1500000 baud）；PC 的 Rockchip 恢复接口、Loader/Maskrom 必须在写盘前确认，不应套用 Hardkernel 的 Petitboot/SD 卡教程。

- **SPL 读取扇区**：U-Boot v2026.04 的 Rockchip 默认 `CONFIG_SPL_MMC=y`，`SYS_MMCSD_RAW_MODE_U_BOOT_SECTOR=0x4000`（每扇区 512 字节，即 8MiB）。这与官方 HAOS `u-boot-rockchip.bin` 从 32KiB 写入、FIT 偏移 `SPL_PAD_TO=0x7f8000` 相匹配。现已在 R68S fragment 中显式钉住配置并添加编译后检查。即使静态偏移正确，仍需实机验证 U-Boot 能读 eMMC。

## 2026-11-12 R68S 网口高负载稳定性外部报告

- [iStoreOS issue #2974](https://github.com/istoreos/istoreos/issues/2974) 记录一台 R68S 4GB / eMMC 设备在 iStoreOS 24.10.7、Linux 6.6.141 下进行高速下载时整机无响应；此前 `eth0`（RTL8211F / stmmac）出现 Link Down/Up 循环和 PHY 重初始化。该 issue 仍未给出确定根因或修复。
- 这是一个需要纳入验证的外部故障报告，**不能直接推断本项目固定的 Linux 6.18.63 一定存在相同问题**。首启网络测试除链路协商外，还应逐口进行本地持续传输并监视 `dmesg` 中 `Link is Down/Up`、PHY 重初始化、watchdog/reset 记录；先单口、再逐步增加负载，出现抖动立即停止并保留日志。

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

## 2026-11-12 编译日志发现的确定错误

- `43093516097` 和 `43086163101` 均在 **U-Boot Binman** 阶段失败：`default-dt ... rk3568-fastrhino-r68s not found in fdt list: rk3568-odroid-m1`。这并非 2.5G 网卡问题。
- U-Boot v2026.04 的 `dts/Kconfig` 使用 `CONFIG_OF_LIST` 为 FIT 选择设备树，`CONFIG_SPL_OF_LIST` 控制 SPL 设备树列表。之前只改 `CONFIG_DEFAULT_DEVICE_TREE`，导致 FIT 列表遗留 ODROID-M1。
- 修复：显式同步 R68S 的 `CONFIG_DEFAULT_DEVICE_TREE`、`CONFIG_OF_LIST`、`CONFIG_SPL_OF_LIST`；编译配置校验新增对应断言。修复提交后的构建未成功前，禁止刷机。


## 2026-11-12 Actions Run #11：RAUC 主机工具 GLIBC 不兼容

- Run #11（提交 `79e8e5a`）在 `Validate output presence and SHA256` 失败。HAOS 镜像编译、GPT 生成和 RAUC Bundle 生成均已完成；Bundle 生成阶段的内联签名检查成功。
- 失败原因不是编译超时，也不是 Bundle 签名错误：工作流把 `/mnt/output/host/bin/rauc` 直接放到 `ubuntu-22.04` runner 上执行，而 Buildroot host libraries 要求 `GLIBC_2.38`（另有依赖要求 `GLIBC_2.36`），Runner 系统库版本不满足。
- 修复提交 `170d074` 将 RAUC 验证脚本和 `rauc` 本体放回官方 `haos-builder:r68s` Debian Trixie 容器中运行，避免在宿主机加载不兼容的 host libraries；`0a6b981` 再修正 RAUC Shell 输出中引号字段和空值的解析。
- 最新 Run #13 使用 `0a6b981`，必须等它的最终验证和 Artifact 上传全部成功，才能认定这次修复通过。Run #12 因新提交触发 `cancel-in-progress` 被取消，不代表构建本身失败。

## 2026-11-12 R68S 专用 U-Boot 开源实现对照

- OpenWrt/ImmortalWrt 已维护 R68S 专用 `fastrhino-r68s-rk3568_defconfig`，其 U-Boot DTSI 除 `same-as-spl, &sdhci` eMMC 启动顺序外，还将 `usb_host0_xhci` 配置为 USB peripheral；defconfig 启用了 `CONFIG_CMD_ROCKUSB`、`CONFIG_USB_GADGET_DOWNLOAD` 和 `CONFIG_USB_FUNCTION_ROCKUSB`，提供 U-Boot 阶段的 RockUSB 恢复入口。参考：[OpenWrt R68S U-Boot patch](https://github.com/coolsnowwolf/lede/blob/80122feac964889bc69b62420cedfefaaf701eb0/package/boot/uboot-rockchip/patches/311-rockchip-rk3568-Add-support-for-fastrhino-r6xs.patch)、[ImmortalWrt U-Boot package](https://github.com/immortalwrt/immortalwrt/blob/4765b657625ec5bbda74b44400465fe043802b30/package/boot/uboot-rockchip/Makefile)。
- 当前 R68S-HA 的 U-Boot 补丁只处理 SPL eMMC 启动顺序，现有 fragment 未启用上述 RockUSB gadget 功能。它不是 Linux/HAOS 启动的必要条件，也不等于 BootROM Loader/Maskrom 不可用；但在无 SD 卡槽设备上，增加并验证 U-Boot USB 恢复入口会提升可维护性。
- **处理顺序**：不在正在运行的首次全量构建中途改 U-Boot；先取得当前构建产物，再按固定的 HAOS U-Boot v2026.04 源码版本核对 OpenWrt patch 的可移植性，单独编译和检查 USB OTG/RockUSB，不直接照搬不同 U-Boot 版本的配置。

## 2026-11-12 第二轮源码核对：DDR 与长期升级限制

以下是源码直接可验证的事实；**尚不是实机通过结论**。

1. 当前钉住的官方 HAOS `945ba38d88e7e7d7321d42294b222b8deb2208d2` 的 ODROID-M1 defconfig 采用 Linux `6.18.63`、U-Boot `2026.04`、Rockchip DDR/TPL `rk3568_ddr_1560MHz_v1.18.bin` 与 BL31 `rk3568_bl31_v1.43.elf`。R68S 适配沿用了这套 TPL；必须通过 R68S 4GB 真机 UART/运行日志确认 DDR 容量、训练及稳定性，不能因 SoC 相同直接推断可启动。参考：[固定版本 ODROID-M1 defconfig](https://github.com/home-assistant/operating-system/blob/945ba38d88e7e7d7321d42294b222b8deb2208d2/buildroot-external/configs/odroid_m1_defconfig)。
2. **R68S 内存规格存在公开资料冲突，不能把单一数据库当作定论**：原始上游 Linux DTS 提交说明 R68S 有 **2/4GB LPDDR4** 版本（[LKML patch](https://lkml.iu.edu/2304.3/04416.html)）；独立硬件资料也列出 **2GB/4GB LPDDR4X**（[CNX Software](https://www.cnx-software.com/2022/06/02/fastrhino-r68s-router-offers-4gb-ram-dual-2-5gbe-dual-gigabit-ethernet/)），并有 R68S 4GB 实机记录（[iStoreOS issue](https://github.com/istoreos/istoreos/issues/2974)）。Armbian 的机型数据库则写成 **1/2GB LPDDR4**，与上述资料不一致。结论：用户的 4GB 版本是合理存在的，不能据 Armbian 单行数据判定型号错误；首刷前仍须从原系统读取 `MemTotal` 并记录板卡版本。无论容量如何，R68S 的 DDR TPL 训练都必须通过串口实机验证。
3. 官方 ODROID-M1 的 `images-os.cfg` 将 `kernel.img` 打包为包含内核 `Image` 的 SquashFS，而 `uboot-boot.ush` 在选择 A/B 槽之前从共享 `hassos-boot` FAT 分区读取单一 `rk3568-fastrhino-r68s.dtb`。现有 OTA 仅修改 kernel/rootfs，**不会同步 DTB**。这能避免升级覆盖共用引导文件，但在跨内核版本时存在设备树与新内核不匹配的风险；首次实机通过后，应以版本矩阵测试确认兼容，否则阻止自动升级。参考：[images-os.cfg](https://github.com/home-assistant/operating-system/blob/945ba38d88e7e7d7321d42294b222b8deb2208d2/buildroot-external/genimage/images-os.cfg)、[ODROID-M1 U-Boot 脚本](https://github.com/home-assistant/operating-system/blob/945ba38d88e7e7d7321d42294b222b8deb2208d2/buildroot-external/board/hardkernel/odroid-m1/uboot-boot.ush)。
4. 要做到未来 DTB 随 A/B 内核安全升级，不能简单把 DTB 复制到现有 `kernel.img`：需要同时修改内核分区镜像生成、U-Boot 按槽加载 DTB 的路径和 RAUC 兼容/回滚测试。这是**后续设计任务**，不应在第 11 次首次全量构建尚未完成时改变启动格式。
5. RAUC 主线 `rauc info --output-format=shell` 确实提供 `RAUC_MF_COMPATIBLE`、`RAUC_MF_IMAGES` 和 `RAUC_IMAGE_CLASS_N`；当前项目第 11 次构建使用的 shell 解析字段与其源码一致。验证失败若再出现，应检查完整 RAUC stderr、实际签名证书链与镜像中的 system.conf，而不是猜测缺失 JSON 支持。
6. 官方 HAOS 将 **ODROID-M1** 列为支持板型，未将 **FastRhino R68S** 列入受支持设备。此仓库只能提供 R68S 自行维护的构建与 OTA，不能保证在 HA 前端直接通过官方通道安全执行 Operating System 大版本升级。参考：[HAOS 支持列表](https://contributors.home-assistant.io/os/operating-system/boards/)。

**下一步执行门槛**：先取得最新 Actions Run 完整成功，并核对 image + SHA256 + GPT/FIT/RAUC 校验；再对现役 R68S 做只读采样及恢复能力验证，最后才进入首刷。无需为文档核对重启或重刷设备。


## 2026-11-13 本轮研究记录：R68S Linux DTS 与 Actions Run #14

### 用户确认的排查边界

- 用户已明确：R68S 硬件、eMMC、供电、USB 线缆及刷机环境均已通过此前两次路由器系统刷写验证；本项目当前不再把这些列为待排查方向，也不再要求用户重复验证。
- MASKROM 是 Rockchip 救援下载模式，不是 HAOS 运行模式。设备断电后重新上电、蓝灯闪烁所观察到的 DHCP/MAC 变化，不能据此推断设备仍处于 MASKROM。
- 最近一次 HAOS 镜像写入日志：`Written(765460480)`，约 730 MiB；先出现 Windows `err=995`，ResetPipe 成功后再出现 `err=31`，最终 `RKU_WriteLBA failed, RetCode(-3)`。用户已明确不再将 USB 线缆/硬件作为排查方向。该失败只证明当次完整镜像写入未完成，不可把该残缺镜像的启动表现作为正式 HAOS 启动测试。
- 用户上传的 `MiniLoaderAll.bin`：465,344 bytes，SHA256 `6e951ade1632de76959ca8ba9ad8560f527ca91ad9a49dd9746f762e68de84ce`；字符串可见 DDR Version V1.11 20211103、LPDDR2/LPDDR3/LPDDR4/LPDDR4X。字符串扫描不构成 R68S 板级 DDR 参数兼容性证明；本轮不据此更换 Loader。

### Linux v6.18 R68S DTS 对照结果

核对文件：
- [Linux v6.18 R68S DTS](https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r68s.dts)
- [Linux v6.18 共用 R66S/R68S DTSI](https://github.com/torvalds/linux/blob/v6.18/arch/arm64/boot/dts/rockchip/rk3568-fastrhino-r66s.dtsi)
- [上游 PHY reset 修复提交 e261bd74000c](https://github.com/torvalds/linux/commit/e261bd74000ca80e5483ba8a8bda509de8cbe7fd)

源码确认：
1. R68S DTS 设置 model 为 `Lunzn FastRhino R68S`，compatible 为 `lunzn,fastrhino-r68s`、`rockchip,rk3568`。
2. `gmac0` 和 `gmac1` 均使用 `rgmii-id`，分别关联 `rgmii_phy0`、`rgmii_phy1`。
3. PHY 地址均为 MDIO address 1。
4. PHY reset 已使用通用 PHY binding：GPIO1 PB0/PB1、active-low、assert 20ms、deassert 100ms；这正是 2024 年上游提交 e261bd74000c 修正的内容。
5. 因此，不能再把“R68S 上游 DTS 缺少 PHY reset”当成当前根因；HAOS 固定的 Linux 6.18.63 应基于该上游 DTS，仍需从 Run #14 最终构建输出中的 DTB 实际反查属性，不能只看源文件。
6. DTS 的 `ethernet0/ethernet1` aliases 指向两个 GMAC。当前该 DTS 本身没有为两路 GMAC 硬编码 `mac-address` 或 `local-mac-address`；实际 MAC 由 SoC/Bootloader/驱动的地址来源机制提供。不能仅凭此断言随机 MAC 是 DTS 故障。
7. R68S DTS 从共用 DTSI 继承 PCIe、USB、PMIC、LED、按键等节点；本轮没有证据支持修改这些节点。

### 当前仓库代码审查结论

- `board/r68s/kernel.config` 中 `CONFIG_R8169=m`，Buildroot 选择 `BR2_PACKAGE_LINUX_FIRMWARE_RTL_8169=y`。必须在最终 rootfs 中确认 r8169 模块和 RTL8125B 所需固件实际安装，而不是只检查 Kconfig 字符串。
- `scripts/check-build-configs.sh` 当前只验证 GMAC/PCIe 节点 `status=okay`，尚未验证最终 DTB 的 PHY 地址、reset GPIO/延迟、phy-mode、驱动模块及固件文件。后续应扩展为对最终产物的只读检查。
- `board/r68s/meta` 中 `SUPERVISOR_MACHINE=odroid-m1` 仍是临时兼容映射，不代表官方支持；应继续检查它对 Supervisor/OS Agent 的影响，但不要在没有验证迁移方案前随意更改。
- U-Boot SPL 从 eMMC sector `0x4000`（8 MiB）读取 FIT；此项已有配置和镜像静态检查，仍需与最终 Run #14 产物交叉验证。

### 云编译缓存：Run #14 实测快照

- 最新提交：`230bb32adca991d8c300244152973921f6525baf`（`ci: persist Buildroot caches and strengthen R68S image checks`）。
- Actions Run #14：[#43338330075](https://github.com/jarod360/R68S-HA/actions/runs/43338330075)。
- 读取日志时，HAOS 源码检出、R68S 集成、缓存恢复步骤、Buildx Builder 镜像构建、Buildroot 配置均成功；当前停留在 `Compile experimental image`。
- 本次 `/mnt/cache/dl` 与 `/mnt/cache/cc` 的 actions/cache restore 均为 cache miss（无历史持久缓存，首次启用属预期），不能宣称 Buildroot 下载/ccache 已命中。
- Docker Buildx GHA cache 成功导入已有 manifest，并完成 Builder 镜像构建及 cache export。该项与 Buildroot 的下载/编译缓存是两层不同缓存。
- Buildroot 日志已显示编译命令使用 `/build/output/host/bin/ccache`，且 `/mnt/cache` 已挂载到容器 `/cache`；但最终命中率必须等 `ccache-stats` 步骤完成后才能判断。
- 当前日志最后可见时间约为 2026-11-13 02:10:23 UTC，仍在编译 NFS utilities 相关目标；这只是日志快照，后续应重新查询 Run #14 状态，不能把该快照当作最终结果。

### 下一步（按证据推进）

1. 等待并检查 Run #14 完整结果、ccache 统计、Artifact 上传和 GPT/FIT/RAUC 验证。
2. 下载 Run #14 最终镜像，只读解包最终 DTB、U-Boot FIT、boot script、kernel/rootfs 内容；对照本节记录逐项核验。
3. 在最终 rootfs 中确认 `r8169.ko`（或对应压缩模块）及 RTL8125B firmware 文件；核对模块依赖和启动时自动加载配置。
4. 扩展 `check-build-configs.sh`：从最终 DTB 检查 PHY reg、reset GPIO、assert/deassert 延迟、phy-mode；从最终 rootfs 检查 r8169 模块和固件。只增加有源码依据的断言。
5. 检查 HAOS 首次启动脚本、systemd 服务、Data 分区格式化/挂载依赖与 watchdog 设置；将“启动失败重启”与“网卡重新申请 DHCP”分开，不依据残缺镜像的现象推断根因。
6. 只有在源代码或最终产物证明配置缺失时才改代码；每次只做一个最小改动并触发构建验证。

**本节状态：源码对照和 CI 状态读取已完成；尚未提交新的 DTS/驱动修改，也尚未获得 Run #14 最终构建产物。**
