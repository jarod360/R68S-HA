# R68S 原生 HAOS 安装与交接

适用实测机型为 FastRhino R68S、RK3568、4 GB RAM、16 GB 板载 eMMC。实机已完成原生 HAOS 19.0.dev0 整盘安装、重启和签名 A/B 更新。

## Recovery 进入 Loader

实机刷回原路由固件 QWRT 后，通过 Recovery 进入过 Loader 1.01。操作时先让 R68S 断电，连接电脑与设备的 USB 刷机口，按住 Recovery 再接入 12 V 电源。约两秒后松手，查看 RKDevTool 是否显示发现 LOADER 设备。两秒是 Armbian 给出的操作参考，实际模式以工具显示为准。若工具显示 MASKROM，按下节继续。 [Armbian R68S 说明](https://github.com/ophub/amlogic-s9xxx-armbian/blob/7c3d671d11063fe9d2a40fe91bbd2dc5aa01e8ea/documents/README.md#823-installation-method-for-fastrhino-r68s)

现有 HAOS 已由用户实测按住 Recovery 上电，RKDevTool 未识别 Loader 或 Maskrom。使用后置触点仍可进入 Maskrom。原路由固件按键可进 Loader，飞牛按键可进 Maskrom。R68S 的设备树将 Recovery 定义在 SARADC 通道 0，而当前 U-Boot 的通用恢复逻辑读取通道 1。候选修复在 U-Boot 中启用 SARADC，并在 R68S 上改读通道 0，沿用 BootROM 下载模式的复位流程。实机验收需要写入包含该修复的引导区。现有签名 OTA 仅写内核和根文件系统槽。

## 首次安装或整盘恢复

已刷 HAOS 的机器，如果还能通过串口进入 U-Boot，可用 `help rockusb` 确认该镜像是否支持 RockUSB。支持时，先用 `mmc list` 确认板载 eMMC 编号，再执行 `rockusb 0 mmc <编号>`，以 RKDevTool 是否识别 Loader 为准。当前 HAOS 的这条入口仍待实机验证。U-Boot 无法启动时，整盘恢复需走 Maskrom。

1. 保存 HA 备份和整块 eMMC 备份，记录 SHA-256，准备已验证的原路由恢复镜像。整盘写入会覆盖现有系统和数据。
2. 选择有实机记录的 R68S 全盘镜像，例如 [签名基线构建 43536849497](https://github.com/jarod360/R68S-HA/actions/runs/43536849497)。校验 SHA-256，再解压 `.img.xz` 得到原始 `.img`。每个新构建需单独验收。
3. 在 Windows 安装 Rockchip DriverAssistant，打开 RKDevTool 2.86。若当前显示 Loader，在「高级功能」选择「进入 Maskrom」，等工具确认 MASKROM。
4. 在「下载镜像」勾选 Loader 和 System 两行。Loader 选已验证的 `Image/MiniLoaderAll.bin`，地址 `0xCCCCCCCC`。System 选解压后的 `.img`，地址 `0x00000000`。实测配置未勾选「强制按地址写」。已验证 Loader 的 SHA-256 和完整记录见 [刷机验证记录](FLASH-TEST.md#run-16-实测刷写流程r68s-4-gb--16-gb-emmc)。
5. 点「执行」，确认 Boot 下载成功、设备测试成功、镜像进度到 100% 并显示「下载完成」。若报错，保存工具版本、模式、最后一条日志和写入偏移。
6. 连接 DHCP 网络，在路由器租约中查 IP。首启联网下载 Core 后，在浏览器验证 HA 登录或欢迎页，并用同 IP 的 4357 端口检查 Supervisor Observer。必要时通过 3.3 V TTL 串口采集启动日志，参数为 1500000 baud、8N1、无流控。

## 已安装设备的 OS 更新

已签名的 R68S RAUC 包写入备用槽，重启后切换。Core、Supervisor 和应用从 Home Assistant 官方渠道更新。自有仓库仅提供 Operating System 的签名包，签名私钥存于 GitHub Actions Secrets。

合并版提供 `r68s-os-update --check` 查询稳定 Release，以及 `r68s-os-update VERSION` 按版本安装。实机已用 `r68s-os-update 19.0.dev0` 从测试 Release 下载并验签，成功从 B 槽写入 A 槽并重启。两个 2.5G 口的 CID MAC 在两槽启动中一致。两口 LED 服务在开机时写入失败，稍后重试成功，已将服务排序与重试修复并入下一版。实机随后从自有仓库执行 19.0.dev0 → 19.0.dev1 签名 OTA，重启进入 B 槽。两个 2.5G 口保持 CID MAC，LED 服务均在开机时成功，Supervisor 健康，HA 返回 HTTP 302。按键恢复使用同次构建的整盘镜像手动刷入后验收。 [19.0.dev1 测试 Release](https://github.com/jarod360/R68S-HA/releases/tag/r68s-19.0.dev1) [测试 Release](https://github.com/jarod360/R68S-HA/releases/tag/r68s-19.0.dev0)

## 实机验收状态

| 项目 | 已验证 | 待验证 |
| --- | --- | --- |
| 启动与 HA | 整盘安装、正常重启、HA 网页响应、Supervisor 健康；内核识别约 3.83 GiB 可用内存 | 合并版启动验收 |
| 2.5G 网口 | 两口均协商 2.5 Gbps 全双工并可访问 HA；两槽开机自动应用相同的 CID MAC；两口 LED 配置支持硬件卸载 | 已通过 19.0.dev1 开机点灯验收 |
| 千兆网口 | 两口都识别 RTL8211F，分别协商 1 Gbps 全双工并可访问 HA | 长时间满载稳定性 |
| 128 GB USB | USB 3.0 以 5 Gbps 枚举，NTFS 和 FAT 只读挂载通过；FAT 小文件写入、读回校验和清理通过 | HA 数据迁移 |
| A/B 更新与回退 | 同版本签名包 A→B、B→A 均启动；将 A 剩余次数置零后自动选 B，再切回 A | 实际启动故障触发回退；自有仓库跨版本更新已通过 |

详细日志见 [刷机验证记录](FLASH-TEST.md)。接手后从合并版构建产物核对签名及设备树，安装到备用槽，检查重启后 MAC、LED、网络、Supervisor 和 HA，再验证测试 Release。
