# R68S Home Assistant Operating System 更新方案

**目标**：使用官方 HAOS / ODROID-M1 构建基础，能够在官方大版本发布后仅升级上游源码版本并快速重新构建，同时保留 R68S 已验证的 eMMC 启动链。**系统无法实现绝对零风险更新。**

## 更新分层

| 层级 | 首次刷机镜像 | 常规 R68S OS OTA 包 |
| --- | --- | --- |
| Rockchip DDR 初始化 / SPL / U-Boot | 包含 | **完全排除，不写 eMMC 前 16MiB** |
| 共用 `hassos-boot`（`boot.scr`、DTB、`cmdline.txt`） | 包含 | **不更新，保留已验证引导环境** |
| `hassos-kernel0/1` | 初始化 | **仅写非活动槽** |
| `hassos-system0/1` | 初始化 | **仅写非活动槽** |
| `hassos-data` / `hassos-overlay` | 初始化 | OTA 不格式化、通常保留 |

该设计基于官方 RAUC 的 A/B 系统槽。若新内核或根系统无法启动，通常可通过 BOOT_A_LEFT / BOOT_B_LEFT 回退，但前提是共享 Bootloader、引导脚本、DTB 本身仍可工作，且没有不可逆的数据迁移。

## 技术实现：把正常 OTA 的危险入口移除

`scripts/configure-safe-ota.py` 每次在**官方 HAOS 已检出的源码副本**中运行：
- 从 **R68S RAUC manifest** 排除 `image.boot` 和 `image.spl`；
- 从 **R68S 运行时 RAUC system.conf** 排除 `slot.boot.0` 和 `slot.spl.0`；
- 在板级 `image-raucb-spl.cfg` 只打包 `kernel.img`、`rootfs.img` 及标准检查 hook；
- 保留原始 **完整 eMMC 初次刷机镜像**的 Bootloader、启动分区和内核；
- 上游模板结构变动时直接失败，不进行模糊自动替换。

**这是预期中的更新安全策略，必须等构建通过、验证 RAUC manifest 和实机 A/B 回退后才能视为生效。**

## 官方 HAOS 新版本如何快速适配

1. 从 [官方 HAOS 仓库](https://github.com/home-assistant/operating-system) 找到准备升级版本对应的 **完整 40 位提交 SHA**；不要随意使用未验证的 `dev` 浮动分支。
2. GitHub Actions → **R68S experimental HAOS build** → Run workflow → 输入 `haos_sha`。工作流会只检出该官方提交，再调用 `prepare-haos.sh` 移植 R68S 差异。
3. 适配器校验官方 ODROID-M1 `defconfig`、U-Boot、RAUC 等结构；发现不兼容时退出，需人工比较新版本差异并更新适配层。
4. 完整构建并通过最终编译配置、GPT/FIT 与 R68S-only OTA manifest 检查。新版本仍需对内核设备树兼容和 RAUC A/B 回滚进行测试。
5. 镜像初次刷机及系统 OTA 是**不同产物**；不要将官方 ODROID-M1 `.raucb` 安装在 R68S 上。

**大版本更新可能更换内核子系统、Docker 存储驱动、HAOS 分区或启动脚本。更新适配可以自动尝试，但不能保证无人工干预且不需要实机验证。**

## 必须持久化 RAUC 签名身份

官方 `rauc.sh` 没有找到 `/build/key.pem` 时会在每次构建生成新的临时开发证书。首次刷机若使用这种证书，后续构建的 OTA 包可能不被旧设备信任。

长期密钥和证书由 GitHub Actions Secrets `R68S_RAUC_KEY_PEM_B64` 和 `R68S_RAUC_CERT_PEM_B64` 保管。构建任务临时解码，并在任务结束后清理私钥。签名材料不提交 Git，也不在工作电脑保存。更换签名身份前，需要为已安装设备安排信任链迁移。

默认分支每天北京时间 11:23 检查官方最新稳定版，解析为完整提交 SHA，以 R68S 配置构建。GitHub 调度可能延迟。签名、机型、分区及共享 DTB 检查通过后，工作流创建 Release 草稿并上传两个 OTA 附件。草稿准备完成后记录该源码组合，供后续定时构建去重。

## 手动发布 OTA

定时构建成功后，进入 [Releases](https://github.com/jarod360/R68S-HA/releases) 打开对应草稿，核对上游版本、构建记录以及签名包和 DTB 两个附件。完成实机验收后，取消勾选 **This is a pre-release**，勾选 **Set as latest release**，再点击 **Publish release**。草稿期间设备上的「系统更新」读到的是当前已发布的 Latest。设备发现新版后，由用户在 HA 中安装并重启。

手动运行的开发版、分支推送和独立 DTB 实验构建走 Actions 产物。需要手动创建 Release 时，按下面的步骤操作。

1. 打开 [GitHub Actions](https://github.com/jarod360/R68S-HA/actions/workflows/experimental-build.yml) 的成功构建，在 **Artifacts** 下载并解压 `R68S-HAOS-SIGNED-OTA-UNVERIFIED`。取出同一次构建的 `haos_r68s-<版本>.raucb` 和 `R68S-DTB-SHA256`，保留文件名。
2. 打开 [新建 Release](https://github.com/jarod360/R68S-HA/releases/new)，创建或选择 `r68s-<版本>` 标签，指向这次 Actions 构建使用的 **R68S 仓库提交**。标签版本必须与 OTA 包一致。例如 `haos_r68s-19.0.dev4.raucb` 对应 `r68s-19.0.dev4`。
3. 在 Release 说明填写版本变更和实机验收结果，将两个文件上传为独立附件。取消勾选 **This is a pre-release**，勾选 **Set as latest release**，点击 **Publish release**。已有 Release 可进入编辑页，核对附件后调整相同选项，并点击 **Update release**。
4. 打开 [仓库 Latest 页面](https://github.com/jarod360/R68S-HA/releases/latest)，确认跳转到目标标签，并确认两个附件都能下载。用运行较低版本的 R68S 在 HA「系统更新」中点击「检查更新」，核对目标版本。完成安装后从 HA 系统页面重启，检查版本、启动槽和 HA 状态。

需要单独验收的候选包可保留为 GitHub 预发行版，并在 HAOS 主机控制台执行 `r68s-os-update <版本>` 安装。两种安装方式均校验共享设备树及 RAUC 签名。

## 共享设备树与大版本

Actions 在上传签名 OTA 前，将候选设备树哈希与已实机验证的 [共享 DTB 基线](../board/r68s/verified-shared-dtb.sha256) 比较。相同就继续，变动就让构建失败并保留整盘候选镜像供验收。设备端安装前也会核对自己实际使用的共享 DTB。定时构建和手动构建走同一发布检查。

默认工作流仍使用共享 DTB。手动运行工作流时可勾选「构建 A/B 槽独立设备树实验镜像」生成候选包。实验版先选内核槽，再从同一内核分区加载 DTB。已有内核槽没有独立 DTB 时，使用原共享 DTB。已找到的槽内 DTB 如果加载失败，会消耗本槽一次启动机会并重启。常规 OTA 仍保留共享 DTB，实验版还未开放为网页升级。

### 槽内 DTB 实机验收

2026-11-15，第 26 次构建通过 SSH 验证一次旧机迁移。先替换候选 `boot.scr`，原有 dev4 从 A 槽使用共享 DTB 启动；再验签并安装 dev5 到 B 槽，启动参数显示 `rauc.slot=B` 和 `r68s.slot_dtb=1`，Supervisor 和 Core 正常。保留 B 槽启动优先级并将其剩余尝试次数置零后，设备自动回到 dev4 的 A 槽，随后恢复原启动脚本。两份 DTB 的哈希相同。不同 DTB 和实际启动故障仍待验证。 [第 26 次构建](https://github.com/jarod360/R68S-HA/actions/runs/43673125363)

在有完整 HA 备份、共享启动分区备份和已确认的 MASKROM 恢复路径的测试机上进行。实验签名包及候选 `boot.scr` 存放在 `R68S-SLOT-DTB-LAB-DO-NOT-PUBLISH`。

1. 用实验整盘镜像首次启动，说明中的常规 SSH 验收通过后，确认 `/proc/cmdline` 同时显示正确的 `rauc.slot=` 和 `r68s.slot_dtb=1`。用串口核对日志里的内核分区号和加载来源。
2. 在已有旧系统的测试机上，备份现有 `boot.scr` 后单独验证候选启动脚本。先用未更新的旧内核重启，确认脚本回退到原共享 DTB。若这一步失败，用已验证恢复路径还原原启动分区。
3. 安装实验包到备用槽，重启并检查其使用槽内 DTB；再验证旧槽能回到原共享 DTB。对新旧槽分别保留启动日志、SSH 检查结果以及共享 DTB 的哈希。
4. 在有现场恢复条件的测试机上验证候选槽无法启动、OTA 中断后旧槽可用，以及连续两次 OTA 后两槽各自加载对应 DTB。通过后再设计已部署设备的迁移交付和正式发布条件。

出现上游板级或启动接口变化时，仍需适配和验收。
## 为什么不建议在 HA 页面直接点官方 Operating System 更新

当前系统的 `SUPERVISOR_MACHINE=odroid-m1` 只是为了使用现有 aarch64 容器镜像。Supervisor 根据 `CPE/BOARD_ID=r68s` 识别系统板型，下载链接可能以 R68S 路径生成；即使某些页面沿用 ODROID-M1 的版本信息，官方版本服务器并没有 R68S 的已验证固件和下载链。

R68S 的签名 OTA 由本仓库 Release 提供，在 HA 侧栏「系统更新」应用中发起。RAUC 使用 `compatible=haos-r68s` 核对目标机型。Core 和 Supervisor 继续通过 HA 官方渠道更新。

## A/B 失败重启：硬件看门狗差异

官方 HAOS 有 `systemd/system.conf.d/watchdog.conf`，配置 `RuntimeWatchdogSec=300` 和 `/dev/watchdog`；基础内核已有 `CONFIG_DW_WATCHDOG=y`。但 R68S 主线设备树的 RK3568 `wdt: watchdog@fe600000` 默认 `status=disabled`，官方 ODROID-M1 还在自身 kernel fragment 显式禁用了此驱动。

R68S 使用单独 Linux DTS 最小补丁启用 `&wdt { status = "okay"; };`，并在编译后检查驱动与最终 DTB。**这不等于看门狗实机已通过**；需检查 systemd 正常喂狗、300 秒失去喂狗能否自动重启、B 槽失败是否按预期重新回到 A 槽。不能为了测试未经准备故意让真实系统死机。

## 仍未完全解决的风险（必须标注）

- **共用 DTB**：本方案保留共享 FAT 分区中的旧 R68S 设备树。如果未来官方 HAOS 把 Linux 6.18 升到另一主版本，新内核可能不能用旧 DTB；这种情况要先实机验证并设计“按 A/B 槽选择 DTB”的第二阶段，不能直接推送 OTA。
- **Core/Supervisor 数据迁移**：A/B 回滚只回滚内核和系统分区，不回滚共享数据。事前仍要做 HA 完整备份。
- **Bootloader 风险**：本方案不会自动改动底层，因此能保护已启动的引导程序，但也意味着某些未来系统版本**确实需要更新 Bootloader 才能支持**，此时必须走独立、可恢复的手动更新流程，而不是强推普通 OTA。

## 验证条件

1. RAUC bundle `manifest.raucm` 仅包含 `image.kernel` 和 `image.rootfs`；不能出现 `image.boot`/`image.spl`。
2. 系统内 `/etc/rauc/system.conf` 只声明 kernel/rootfs 的 A/B 槽；不能出现 boot/spl 可写槽。
3. 对比升级前后：eMMC 前 16MiB、`hassos-boot` 保持一致（若用户配置没有另行改变）；`hassos-data` 与 `hassos-overlay` 均未格式化。
4. CI 必须对**实际构建出的** `.raucb` 调用 RAUC `info --keyring --intermediate --output-format=shell`，核实签名可被镜像中内置的证书信任、`compatible=haos-r68s` 且只包含 kernel/rootfs 两种镜像；当前 HAOS host-rauc 构建禁用了 JSON 输出，因此验证脚本解析 RAUC shell formatter（包括带引号字段和空值）。同时检查系统实际 `/etc/rauc/system.conf` 中不再存在 boot/spl 槽。
5. 人工验证：成功升级一次和模拟新版无法启动后的自动回退、再次可用，以及正常 HA 数据仍在。
6. 新签名/证书要由已有系统验证；跨 HAOS 大版本时确认内核/DTB ABI 与 Docker/系统服务兼容性。

这个方案不需要复制整套官方 HAOS 源码进入本仓库：只维护设备树选择、eMMC/U-Boot 配置、少量构建适配和更新安全策略。
