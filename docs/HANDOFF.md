# R68S 原生 HAOS 安装与交接

适用实测机型为 FastRhino R68S、RK3568、4 GB RAM、16 GB 板载 eMMC。实机已完成原生 HAOS 19.0.dev0 整盘安装、重启和签名 A/B 更新。

## Recovery 进入 Loader

实机刷回原路由固件 QWRT 后，通过 Recovery 进入过 Loader 1.01。操作时先让 R68S 断电，连接电脑与设备的 USB 刷机口，按住 Recovery 再接入 12 V 电源。约两秒后松手，查看 RKDevTool 是否显示发现 LOADER 设备。两秒是 Armbian 给出的操作参考，实际模式以工具显示为准。已刷 HAOS 或 eMMC 引导损坏时，Recovery 能否进入 Loader 尚未验证。若工具直接显示 MASKROM，按下节的 Maskrom 步骤继续。 [Armbian R68S 说明](https://github.com/ophub/amlogic-s9xxx-armbian/blob/7c3d671d11063fe9d2a40fe91bbd2dc5aa01e8ea/documents/README.md#823-installation-method-for-fastrhino-r68s)

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

合并候选版提供 `r68s-os-update --check` 查询稳定 Release，以及 `r68s-os-update VERSION` 按版本安装。安装入口核对共享设备树 SHA-256，并验证签名、版本、型号和内核与根文件系统两项内容。当前构建会上传签名包与设备树校验文件到 Actions。测试 Release 下载、跨版本安装和启动仍待实测。 [合并版构建](https://github.com/jarod360/R68S-HA/actions/runs/43571281080)

## 实机验收状态

| 项目 | 已验证 | 待验证 |
| --- | --- | --- |
| 启动与 HA | 整盘安装、正常重启、HA 网页响应、Supervisor 健康；内核识别约 3.83 GiB 可用内存 | 合并版启动验收 |
| 2.5G 网口 | 两口均识别；第一口协商 2.5 Gbps 全双工并可访问 HA；两口临时赋值符合 QWRT 的 eMMC CID 规则；两口 LED 配置支持硬件卸载 | 合并版重启后自动固定 MAC 和点灯；第二口接线收发 |
| 千兆网口 | 两口都识别 RTL8211F PHY | 逐口协商与收发 |
| 128 GB USB | USB 3.0 以 5 Gbps 枚举，NTFS 和 FAT 只读挂载通过；FAT 小文件写入、读回校验和清理通过 | HA 数据迁移 |
| A/B 更新与回退 | 同版本签名包 A→B、B→A 均启动；将 A 剩余次数置零后自动选 B，再切回 A | 实际启动故障触发回退；自有仓库跨版本更新 |

详细日志见 [刷机验证记录](FLASH-TEST.md)。接手后从合并版构建产物核对签名及设备树，安装到备用槽，检查重启后 MAC、LED、网络、Supervisor 和 HA，再验证测试 Release。
