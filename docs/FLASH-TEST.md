# R68S HAOS — 实机刷机验证清单（实验版）

## 首要结论

**尚未有经实机启动验证的 R68S 原生 HAOS 镜像。** GitHub Actions 生成的 `UNVERIFIED-DO-NOT-FLASH` 仅是编译产物；首刷前必须按本清单完成准备与判断。若恢复路径未验证，**不应写入 eMMC**。

设备：R68S / RK3568 / 4GB RAM / 16GB 板载 eMMC / 无 SD 卡槽 / USB 3.0。此前飞牛 OS 可启动属于已有系统运行证据，不等于本项目 DDR TPL、SPL 和 U-Boot 适配已通过。

## 1. 写入前：不改变设备的检查

在当前能启动的系统内，通过 SSH 执行以下**只读**命令，记录输出。若有序列号或其他私有信息，分享前可以打码：

```sh
echo '===== BOARD ====='
tr '\000' '\n' < /proc/device-tree/model 2>/dev/null
uname -a
cat /proc/cmdline
echo '===== MEMORY ====='
grep -E 'MemTotal|MemAvailable' /proc/meminfo
free -h 2>/dev/null || true
echo '===== MMC / STORAGE ====='
cat /proc/partitions
for p in /sys/block/mmcblk[0-9]*; do
  [ -d "$p" ] || continue
  echo "$p"
  cat "$p/size" "$p/device/name" "$p/device/type" 2>/dev/null
done
echo '===== CURRENT MOUNTS ====='
mount
echo '===== INTERFACES ====='
ip -br link 2>/dev/null || ip link
echo '===== HARDWARE LOG HINTS ====='
dmesg 2>/dev/null | grep -Ei 'mmc|rk3568|pcie|r8169|rtl8125|dwmac|gmac|usb' | tail -n 80
```

**不得仅凭“16G eMMC”猜测盘符 `/dev/mmcblk0`**；确认实际设备名、主分区表、当前启动分区后才讨论写入命令。不要把以上输出里的 MAC、序列号或网络标识公开。

## 2. 恢复和备份（任何写盘前）

- 必须备份**整块 eMMC**（含前 16MiB 引导区、GPT、系统和数据），备份文件放到 Windows **`D:\Codex\R68S-HA\backup`**，不要放 C 盘或公开 GitHub 仓库。正在运行的系统在线备份可能不一致；用于可靠恢复，应优先在可控离线/恢复模式下读取与校验。
- 记录原镜像来源、完整备份字节数、SHA256；如果存在独立 eMMC boot0/boot1 或 SPI 存储，还需额外确认其内容及恢复方案。
- 验证设备能进入**其自身**的 Rockchip Loader/Maskrom 或其他已实测可恢复模式，确认可被 PC 检测、能够从备份写回。**不能套用 ODROID-M1 的 Petitboot/SD 卡恢复方法**，R68S 无 SD 卡槽。
- 准备设备对应的刷机工具、已验证的恢复固件、可靠供电及正确的 OTG 数据接口。恢复链不清楚时不刷。

## 3. 验证构建产物（只读，不写盘）

1. GitHub Actions `R68S experimental HAOS build` 必须整体为 **success**。仅“Compile experimental image”结束不等于完整成功。
2. 下载 `haos_r68s-*.img.xz` 到 `D:\Codex\R68S-HA`，核实该文件在构建记录给出的 SHA256。
3. 在具备 Python 3 的环境中运行 `python scripts/check-image-gpt.py <镜像路径>`。脚本支持 `.img.xz` 和解压后的 `.img`，可直接检查 RKDevTool 中选中的文件。确认主备 GPT CRC、HAOS 的 9 个必要分区、16GB 限制，以及 eMMC **8MiB FIT** 预期位置（由官方 U-Boot `SPL_PAD_TO=0x7f8000` 与 HAOS 把 bootloader 放到 32KiB 得出）。**该检查不能证明启动成功。**
4. 编译工作目录中运行 `sh scripts/check-build-configs.sh /path/to/output`，检查最终 U-Boot/Linux 配置确实生效；这不是仅检查预设 fragment。
5. 不直接刷官方 ODROID-M1 的 `.img`：虽然同 SoC，它的 SPI/eMMC 启动方式及板级设备树与 R68S 不同。

## 4. 条件满足后的实机首启

仅在具备可恢复条件、确认镜像检查和选择正确目标 eMMC 后进行写盘；**本清单不提供未经针对性核实的 `dd of=` 或 RKDevTool 写入参数**。

- 最好准备 **3.3V TTL** 串口接头，设 **1,500,000 baud**，记录 SPL、U-Boot、Linux 启动日志；不要误用 RS-232 或给板子串口引脚加 5V。
- 实验版 U-Boot 设有 **3 秒串口中断窗口**（官方 HAOS 默认禁用中断），串口能进入 U-Boot 提示符时可用于诊断或手动切换启动槽；不要在不了解分区布局时执行 `mmc erase`、`gpt write` 等写入命令。
- 含 RockUSB 改动的镜像可在 U-Boot 提示符验证恢复入口。先用 `mmc list` 确认板载 eMMC 编号，再运行 `rockusb 0 mmc <编号>`，观察 PC 能否识别 Loader。该入口需要 DDR、SPL 和 U-Boot 已成功启动。
- 首次只连接一个**千兆**网口接 DHCP 局域网，排除双 2.5G PCIe 的影响；确认开机、串口、eMMC、IP、DHCP，再检查其他网口。
- HAOS 在首启可能需要联网下载 Core，不能以“IP 已获得但 8123 尚未打开”直接判定引导失败。
- 记录 4GB 内存是否完整识别、eMMC 容量/分区、两个千兆和两个 2.5G 的链路协商、USB 3.0 连接稳定性、Supervisor / OS Agent 状态。
- 网络基础功能正常后，逐口进行本地持续传输测试（先单个千兆口，再逐个 2.5G 口；不要一开始同时压满全部网口），同时观察 `dmesg -w` 是否出现 `Link is Down/Up` 循环、PHY 重初始化或整机卡死。已有 R68S 外部报告记录过高负载下 eth0 链路抖动并伴随系统挂死；若复现，先停止压测、保存日志，再区分线缆/交换机、PHY 复位和驱动问题。
- 首启在系统内核对 `/dev/watchdog` 是否存在、`systemd-analyze cat-config systemd/system.conf` 是否生效，并观察日志有无看门狗告警。**先不要主动触发设备死机测试**，待回滚/救砖能力验证后再测试。
- 固件确认能启动后，也**不要点击系统更新/OTA**：目前固件目标是 `r68s`，但 Supervisor 容器选择暂时映射到 `odroid-m1`。未经自己签名和 RAUC 回滚验证的升级包不能用于该设备。
- 任何早期引导异常或反复重启，应停止刷写和反复重试，保留串口日志与失败步骤。

## Run 16 实测刷写流程（R68S 4 GB / 16 GB eMMC）

1. 解压 Run 16 的 `.img.xz`。实测使用的原始 `.img` 为 954,224,640 字节，已与构建产物解压结果逐字节比对。压缩包 SHA-256 为 `064c07e66a01e5e8d770561095c1a917fcf332373928c4ef7ef504c8767981b2`。
2. 用 RKDevTool **2.86** 识别 Recovery 进入的 Loader 1.01，再在「高级功能」点「进入 Maskrom」，等工具显示 MASKROM。
3. 在「下载镜像」勾选两行。Loader 使用该工具随附的 `Image/MiniLoaderAll.bin`，地址 `0xCCCCCCCC`，文件 SHA-256 为 `6e951ade1632de76959ca8ba9ad8560f527ca91ad9a49dd9746f762e68de84ce`。System 使用上面的 Run 16 原始镜像，地址 `0x00000000`。实测成功时「强制按地址写」未勾选。
4. 点「执行」，观察 Boot 下载成功、设备测试成功、系统镜像下载到 100% 并显示「下载完成」。2026-11-14 01:28 的 RKDevTool 日志记录 `ret=1`。整盘写入会覆盖现有系统和数据。
5. 自动重启后在 DHCP 租约中找设备，打开 Home Assistant。首次启动会下载 Core，等欢迎页或登录页出现。Supervisor Observer 位于同一 IP 的 4357 端口。

本机已完成一次 HAOS 整盘刷写及首次启动。Supervisor 日志识别 HAOS 19.0.dev0 和 A 槽，RAUC 将 A 槽标为正常。Core 2026.11.1 进入首次配置页，硬件页识别 `r68s` 并显示内存 0.9 GB / 4 GB。后续复查 Observer 仍显示 Connected、Supported、Healthy。QWRT 也使用同一套工具、MiniLoader 和起始地址成功刷入。HAOS 刷写成功目前只有一次，先前中断的根因仍未确认。

整机重启测试已执行。HA 网页确认重启命令已提交，随后连接中断。重启后原地址上的 Home Assistant 和 Observer 均未恢复响应，用户随后找到新的局域网地址。该地址的 Home Assistant 返回 HTTP 200，Observer 显示 Connected、Supported、Healthy。登录后的硬件页已复查，识别为 r68s，内存显示 0.8 GB / 4 GB。重启验证能证明现有安装可以再次启动。若要验证安装流程的重复性，应在备用设备或可恢复的测试环境中按相同步骤再完整刷写一次。整盘读回、各网口稳定性和系统 OTA 仍待验证。

SSH 用于进一步查看宿主机日志、内存、eMMC 和网口状态。网页与 Observer 足以验证服务启动。若已有 HAOS 本机控制台，在 `ha >` 输入 `login` 进入宿主机后，可用 `free -m`、`lsblk`、`ip -br link`、`journalctl -b -p warning --no-pager` 做只读检查。此机复查时 22 和 22222 均无法建立 TCP 连接。

## 5. Rockusb 写入中断排查

- 2026-11-13 的 RKDevTool 2.86 日志中，HAOS 写入分别在 0 字节、8 MiB 和约 730 MiB 中断。约 730 MiB 那次先出现 `WriteFile err=995, size=1048576, write=0`，随后重试返回 `err=31`。同日 QWRT 写入曾以 `ret=1` 结束。
- 设备仍显示为 Maskrom 时，单独运行「读取 Chip 信息」也复现了 31 字节请求发送失败。2.92 的日志同样记录了 Loader 下载失败和 Flash 查询发送失败。下次重新进入 Maskrom 后，先记录芯片查询结果，再单独将匹配的 Loader 下载到 RAM。进入 Loader 后读取 eMMC 型号和容量，并对小范围 LBA 重复读回比对。只有这些步骤稳定通过，才有依据继续验证完整镜像写入。

- QWRT 恢复后，按 Recovery 键进入的 Loader 成功读出 RK3568 和三星 eMMC（工具显示 14800 MB）。通过「进入 Maskrom」切换后，两个 RAM Loader 都在第一个 `Boot_VendorRequest471` 请求失败（`Total(2050), Sended(0)`）。
- ophub 的 R68S Armbian 主流程从 Recovery 进入 Loader，只选系统镜像，地址为 `0x00000000`。文档另列出已有系统时的擦除步骤，以及擦除失败后的 Maskrom 流程。[Armbian R68S 安装说明](https://github.com/ophub/amlogic-s9xxx-armbian/blob/7c3d671d11063fe9d2a40fe91bbd2dc5aa01e8ea/documents/README.md#823-installation-method-for-fastrhino-r68s)
- 飞牛的 Rockchip USB 流程从 Maskrom 开始，使用与 SoC 匹配的 MiniLoader，Boot 地址为 `0xCCCCCCCC`，整盘镜像地址为 `0x00000000`，并勾选「强制按地址写」。[飞牛 Rockchip 线刷说明](https://help.fnnas.com/articles/v1/arm/arm-rk-usb)
- ophub 的 R68S Armbian `bootloader.bin` 与本地可运行的 QWRT 镜像均使用 U-Boot 2017.09。HAOS 当前采用 U-Boot 2026.04。三个镜像的 Rockchip 引导标记均位于 32 KiB 和 8 MiB，区段内容各不相同。飞牛镜像的引导二进制尚未核对。首启应采集串口日志来确定 DDR、SPL、U-Boot 或内核的实际停止位置。

- RKDevTool 2.86 的成功对照使用界面中的 Loader 和 System 两行。截图显示随 2.86 附带的 `Image/MiniLoaderAll.bin` 下载成功，随后 QWRT 下载完成。2.86 日志另记录 QWRT 从 LBA 0 写入成功（11-14 00:48–00:49），以及 Run 16 同样从 LBA 0 写入、在已写 8 MiB 后中断（11-13 23:57）。两次日志未证明 RAM Loader 相同。QWRT 原始镜像为 1 GiB，HAOS Run 16 为 954,224,640 字节，因此不能用镜像总长度解释这次中断。Run 16 在现有 Loader 上的另两次中断分别发生在 39 和 180 MiB，其中 180 MiB 的测试读回了前 16 MiB，与镜像逐字节一致。3.37 勾选强制按地址写后也曾在 39 MiB 中断，该次使用已有 Loader。2026-11-14 01:26 从 Loader 通过 2.86 切换到 Maskrom，沿用 QWRT 成功时的 MiniLoader 和 LBA 0，只替换为 Run 16。工具显示 100% 和下载完成，01:28 日志记录 ret=1。首次启动已验证：Supervisor 识别 HAOS 19.0.dev0 和 BootSlot A，RAUC 将 A 槽标为 good，Core 2026.11.1 下载完成后浏览器进入首次配置欢迎页。整盘读回、重启和各网口仍待验证。

## 6. 判断与提交反馈

将**不含隐私信息**的编译错误、启动串口最后几十行、网口/块设备识别结果发回本项目；以此判断是 DDR/SPL、U-Boot、内核 DTB、网卡还是 Supervisor 层故障。不要上传完整 eMMC 备份或含个人配置的日志。

## 参考

- [HAOS 官方 ODROID-M1 引导说明](https://contributors.home-assistant.io/os/operating-system/odroid/)
- [U-Boot Rockchip 镜像格式](https://github.com/u-boot/u-boot/blob/v2026.04/doc/board/rockchip/rockchip.rst)
- [RAUC 安装脚本](https://github.com/home-assistant/operating-system/blob/dev/buildroot-external/ota/rauc-hook)

第二次整机重启后，旧地址停止响应，新地址上的 Supervisor 恢复 Connected、Supported、Healthy，随后 HA 首页返回 HTTP 200。两次重启均观察到局域网 IP 和对应 MAC 变化。用户确认第二次重启时网线始终接在同一个物理网口。两次观测到的 MAC 都属于本地管理地址。优先检查该接口的永久 MAC、当前 MAC 和 NetworkManager 有线连接的 cloned-mac-address 设置，确认地址从何处生成。

## Run 16：串口复现 PCIe 网口 MAC 随重启变化

通过 COM3（1500000、8N1、无流控）读取主机日志。重启前，两个 RTL8125B 的地址分配类型均为 1（随机），其中 enP1p17s0 正在使用 192.168.0.109。通过串口执行整机重启，随后记录新一轮内核初始化。

| PCIe 地址 | 接口 | 重启前 MAC | 重启后驱动报告的 MAC |
| --- | --- | --- | --- |
| 0001:11:00.0 | enP1p17s0 | 2e:38:b4:91:fc:17 | a2:8b:67:ee:6f:98 |
| 0002:21:00.0 | enP2p33s0 | 2e:21:61:4e:42:5d | e6:25:a3:c9:69:e6 |

两次启动，r8169 对两个端口均报告 `can't read MAC address, setting random one`。地址变化发生在驱动初始化。下一步核对 QWRT 和 Armbian 为同一 PCIe 网口提供 MAC 的路径，优先复用经确认的持久来源。修复后比较正常重启和冷启动时两个端口的地址。

## Run 16：整机启动和运行检查

- 串口复查确认 HAOS 启动完成。Supervisor 2026.11.0 报告 healthy、supported，Core 2026.11.1 在实际配置的 80 端口返回 HTTP 200。启动中的 setup 状态已退出。
- 内核识别 4 核、约 4 GB 内存和 14.5 GiB eMMC。数据分区 ext4 以读写方式挂载，剩余 7.8 GiB。eMMC 有低速时钟警告，随后以 HS200 识别并完成挂载。
- RAUC 识别 haos-r68s，A 槽启动并标记 good。B 槽未实测启动，未测试系统更新。
- 两个 PCIe 网口已枚举，当前连接的 enP1p17s0 已建立链路。两个板载 GMAC 均枚举，但未接线测试。GMAC 日志显示 PHY 供电配置缺失以及收发延迟使用默认值，需实测协商及收发。
- 唯一失败的 systemd 单元是 systemd-time-wait-sync，主机状态 degraded。直连拓扑下网关无 ICMP 响应，NTP 尚未同步，RTC 显示 2017 年。接回正常网络后需复查校时，再判断 RTC 是否有独立问题。
- USB 2.0/3.0 控制器已枚举，未测外设。Audio 容器已启动，但未枚举 ALSA 声卡和蓝牙控制器。另有 timezone 事件源、audit 规则缺失以及容器初始化警告，未阻止 Core 启动。

## 固定 MAC 实机验证

NetworkManager 连接配置的 stable 值在重启后被恢复为 preserve。改在 /etc/udev/rules.d/90-r68s-local-mac.rules 为这台测试机的两个 PCIe 地址设定各自的本地 MAC。整机重启后，驱动报告的随机值分别是 6a:8e:0d:ae:d7:8b 和 0a:a1:7a:2f:cd:db，系统接口实际地址分别是 c2:44:e6:d5:0d:fe 和 b2:e9:45:02:c9:31，均与本机规则一致。校时服务在当前直连拓扑下仍超时。

镜像源码使用 R68S 专用 systemd .link 文件和 persistent 策略生成每台机器、每个网口各自的稳定地址。镜像中不包含测试机的固定值。此镜像规则仍需构建后验证，测试机升级验证前应移除本机固定规则，避免掩盖镜像行为。

## Run 16：升级验收前的实机检查

- Windows 直连访问 HA 返回 HTTP 200，Supervisor 报告 healthy 和 supported。
- 当前从 A 槽运行。RAUC compatible 为 haos-r68s，实际 system.conf 仅声明 A/B 的 kernel、rootfs 四个槽。
- B 槽的内核分区没有 A 槽的文件头，blkid 未识别到 B 槽系统文件系统。RAUC 显示 good 是引导状态，不能作为 B 槽已经安装或已启动的证据。
- DesignWare 硬件看门狗已注册，sysfs 状态为 active。超时触发及自动回退仍未验证。
- 本地 Run 16 下载产物只有首次刷机镜像及校验文件，未取得能由本机信任链验证的 R68S OTA 包。以同一长期签名身份制作基线和更新包，实测 A→B 更新、B→A 回退，并验证共享引导区和 HA 数据。
- 当前直连环境仍只有校时等待服务失败。系统在线校时和逐口收发仍需验证。
