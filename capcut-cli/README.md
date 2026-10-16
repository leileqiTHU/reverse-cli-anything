# capcut-cli

[Native automation overview and evidence (English)](../docs/native-automation-examples.md#capcut-cli-control-the-native-editor-and-export-video) · [原生控制说明与证据](../docs/native-automation-examples.zh-CN.md#capcut-cli控制原生编辑器并导出视频)

**CapCut video editing automation through a native JSON CLI for AI agents.** This reverse-cli-anything example imports media, edits timelines, adds editable captions and exports video through recovered internal CapCut calls. Verified on Windows x64 with CapCut 9.5.0.4050; speech recognition and translation in the demo use external helpers. [Project overview](../README.md) · [Automation FAQ](../docs/faq.md).

**[Watch the English CLI demo · 4:08](assets/capcut-cli-demo.mp4)** — real footage, fresh ASR and bilingual captions, music, native MP4 export and result playback. [Shared demo gallery and provenance](../docs/demos/README.md).

CapCut 的原生 JSON CLI 适配器，也是 [reverse-cli](../README.zh-CN.md) 的第一个已验收案例。

**已验证：Windows x64，CapCut 9.5.0.4050。** 原生模块 SHA-256 固定校验；其他版本不能直接视为兼容。

For an agent with shell access, this adapter provides a command-line route to the running CapCut editor. If you are evaluating draft automation or an MCP server, compare the execution backend and native export evidence in the [automation route guide](../docs/desktop-automation.md). Jianying compatibility and headless operation are not established.

## 实际完成过什么

- 创建、打开、关闭项目，向素材库导入本地视频。
- 新建和切换独立时间线，添加视频与新视频层，裁剪、拆分、移动、删除、撤销/重做。
- 添加本地配乐、音量和淡入淡出；导入原生可编辑字幕；修改片段缩放、位置等属性。
- 获取原生合成帧、渲染指定区间、通过 CapCut 原生导出 MP4。
- 无需启动 CapCut 的文件取帧/预览使用 FFmpeg，是另一路明确标识的辅助能力。

[真实素材案例](examples/real-media.md) · [完整录屏与现场字幕生成](examples/recorded-real-media.md) · [命令说明](docs/commands.md) · [实现与限制](docs/implementation.md) · [测试说明](tests/README.md) · [Agent skill](../skills/reverse-cli-capcut/SKILL.md)

## 设置

需自行安装合法可用的受支持 CapCut build、Python 3.11+，并安装适配器依赖。新环境建议放在 D 盘。

```powershell
cd D:\ChatGPT\reverse-cli\capcut-cli
$env:CAPCUT_PYTHON = 'D:\Apps\Python\python.exe' # 改为实际已安装的 Python
$env:CAPCUT_DIR = 'D:\Apps\CapCut\9.5.0.4050'  # 包含 CapCut.exe 和原生 DLL 的目录
$env:PIP_CACHE_DIR = 'D:\Caches\pip'
& $env:CAPCUT_PYTHON -m pip install --target .native-tools -r requirements.txt
.\capcut-agent.ps1 capabilities
.\capcut-agent.ps1 version
```

`CAPCUT_PYTHON` 优先于本机被忽略的 `local.settings.json`；都未设置时使用[公共 Python 配置](../docs/runtime.zh-CN.md)，最后查找 PATH。也可直接执行 `python -B capcut_agent.py ...`。`--capcut-dir` 可覆盖 `CAPCUT_DIR`。不要把本机配置中的用户路径提交到仓库。

公共入口提供 `doctor`、工具 schema 和持久化回执，原命令保持可用。[原生导出修复记录](../examples/reports/upgrades-20261014.zh-CN.md)说明字幕自动隐藏问题的版本绑定防护，以及保存重开、原生预览和成片验证结果（[English](../examples/reports/upgrades-20261014.md)）。

`capabilities` / 适配器 `help` 不需要原生程序。`version` / `probe` 会实际加载并校验目标 DLL。REA、Ghidra 和 Capstone 用于研究新能力，不是日常运行 CLI 的前提。

## 从读取开始

```powershell
$cli = '.\capcut-agent.ps1'
# 查找正在运行的主进程；核对返回进程，不复用历史 PID。
Get-Process CapCut | Select-Object Id, MainWindowTitle
& $cli project list --pid <PID>
& $cli editor inspect --pid <PID> --project '<projectPath>' --timeline '<timelineId>'
```

`<PID>` 等是待替换占位符。项目操作优先使用稳定 `projectId`；CapCut 可能在关闭时重命名草稿目录，打开后使用返回的 `projectPath`。

## 执行约定

- stdout 始终为 UTF-8 JSON，无需 `--json`；成功退出 0，预期失败 2，内部错误 1。
- 编辑要求应用进程已运行、目标项目打开、目标时间线激活。没有鼠标/键盘自动化，也不宣称完全 headless。
- 时间参数为整数微秒；命令的绝对/相对语义见[命令说明](docs/commands.md)。
- 保存通过 CapCut 完成；读取草稿用于验证，不靠离线改 JSON 来伪造原生编辑成功。
- 每个 PID 互斥。`partially-applied` / `unknown` 先检查回执及真实状态，不盲目重放。
- 导出路径必须不存在；已有文件拒绝覆盖。媒体预览和原生导出的输出/临时文件按当前实现要求放在 D 盘。

运行日志与恢复回执在本适配器 `.runtime/`，依赖在 `.native-tools/`；均不进入发布源码。

## 目录

Python 文件负责参数、worker、保存状态与结果核验；`*_agent.js` 是版本固定的原生桥。`tests/` 保存回归测试，`examples/` 保存真实任务说明，`evidence/` 保存精选验证摘要。完整本地研究记录仍保留在被忽略的 `capcut-analysis/`。
