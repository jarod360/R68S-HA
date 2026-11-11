# R68S HAOS — 实机刷机验证清单（实验版）

## 首要结论

**尚未有经实机启动验证的 R68S 原生 HAOS 镜像。** GitHub Actions 生成的 `UNVERIFIED-DO-NOT-FLASH` 仅是编译产物，明早应按本清单完成准备与判断；若恢复路径未验证，**不应写入 eMMC**。

设备：R68S / RK3568 / 4GB RAM / 16GB 板载 eMMC / 无 SD 卡槽 / USB 3.0。此前飞牛 OS 可启动属于已有系统运行证据，不等于本项目 DDR TPL、SPL 和 U-Boot 适配已通过。

## 1. 写入前：不改变设备的检查

在当前能启动的系统内，通过 SSH 执行以下**只读**命令，记录输出。若有序列号或其他私有信息，分享前可以打码：

```sh
echo '===== BOARD ====='
tr '\000' '\n' < /proc/device-tree/model 2>/dev/null
uname -a
cat /proc/cmdline
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
3. 在具备 Python 3 的环境中运行 `python scripts/check-image-gpt.py <镜像路径>`。确认主 GPT CRC、HAOS 的 9 个必要分区、16GB 限制，以及 eMMC **8MiB FIT** 预期位置（由官方 U-Boot `SPL_PAD_TO=0x7f8000` 与 HAOS 把 bootloader 放到 32KiB 得出）。**该检查不能证明启动成功。**
4. 编译工作目录中运行 `sh scripts/check-build-configs.sh /path/to/output`，检查最终 U-Boot/Linux 配置确实生效；这不是仅检查预设 fragment。
5. 不直接刷官方 ODROID-M1 的 `.img`：虽然同 SoC，它的 SPI/eMMC 启动方式及板级设备树与 R68S 不同。

## 4. 条件满足后的实机首启

仅在具备可恢复条件、确认镜像检查和选择正确目标 eMMC 后进行写盘；**本清单不提供未经针对性核实的 `dd of=` 或 RKDevTool 写入参数**。

- 最好准备 **3.3V TTL** 串口接头，设 **1,500,000 baud**，记录 SPL、U-Boot、Linux 启动日志；不要误用 RS-232 或给板子串口引脚加 5V。
- 首次只连接一个**千兆**网口接 DHCP 局域网，排除双 2.5G PCIe 的影响；确认开机、串口、eMMC、IP、DHCP，再检查其他网口。
- HAOS 在首启可能需要联网下载 Core，不能以“IP 已获得但 8123 尚未打开”直接判定引导失败。
- 记录 4GB 内存是否完整识别、eMMC 容量/分区、两个千兆和两个 2.5G 的链路协商、USB 3.0 连接稳定性、Supervisor / OS Agent 状态。
- 首启在系统内核对 `/dev/watchdog` 是否存在、`systemd-analyze cat-config systemd/system.conf` 是否生效，并观察日志有无看门狗告警。**先不要主动触发设备死机测试**，待回滚/救砖能力验证后再测试。
- 固件确认能启动后，也**不要点击系统更新/OTA**：目前固件目标是 `r68s`，但 Supervisor 容器选择暂时映射到 `odroid-m1`。未经自己签名和 RAUC 回滚验证的升级包不能用于该设备。
- 任何早期引导异常或反复重启，应停止刷写和反复重试，保留串口日志与失败步骤。

## 5. 判断与提交反馈

将**不含隐私信息**的编译错误、启动串口最后几十行、网口/块设备识别结果发回本项目；以此判断是 DDR/SPL、U-Boot、内核 DTB、网卡还是 Supervisor 层故障。不要上传完整 eMMC 备份或含个人配置的日志。

## 参考

- [HAOS 官方 ODROID-M1 引导说明](https://contributors.home-assistant.io/os/operating-system/odroid/)
- [U-Boot Rockchip 镜像格式](https://github.com/u-boot/u-boot/blob/v2026.04/doc/board/rockchip/rockchip.rst)
- [RAUC 安装脚本](https://github.com/home-assistant/operating-system/blob/dev/buildroot-external/ota/rauc-hook)
