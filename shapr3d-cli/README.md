# Shapr3D native CLI pilot

[Native CAD automation and evidence (English)](../docs/native-automation-examples.md#shapr3d-cli-edit-native-cad-geometry-and-export-a-model) · [原生建模与证据](../docs/native-automation-examples.zh-CN.md#shapr3d-cli修改原生-cad-几何并导出模型)

**Shapr3D CAD automation through a native CLI for AI agents.** This reverse-cli-anything pilot demonstrates mounting-plate modeling, parameter edits, a through-hole and native project/STL export on Windows x64 with Shapr3D 26.180.11926.0. It does not implement arbitrary sketch construction, general project navigation or STEP export. [Project overview](../README.md) · [Automation FAQ](../docs/faq.md).

**[Watch the English CLI demo · 0:56](assets/shapr3d-cli-demo.mp4)** — build a plate, edit thickness and hole spacing, drill a center hole, and export the native model and STL. [Shared demo gallery and provenance](../docs/demos/README.md).

Windows x64 **26.180.11926.0** 的首个原生建模闭环已验收：正常新建项目 → 导入软件自带阀门模型副本 → 修改原生拉伸历史 → 保存并关闭 → 重开 → 原生 STL 导出。

新增 **前台可见建模与钻孔**：CLI 在当前打开的项目中建立双孔固定板，修改厚度和孔距，再增加 Ø8 mm 中心贯穿孔。49 秒连续实录包含从空模型到最终成品的全过程；独立网格验收 78 项通过。[演示、命令与限制](VISIBLE-DRILL-DEMO.md) · [验收摘要](evidence/visible-drill-proof-20261013.json)。

已整理 **56 秒英文演示版**：无片头，直接从空白模型开始；采用与 CapCut、Axure 一致的“软件画面 + 底部命令栏”，展示 28 条完整 CLI 调用语法及独立验收命令。[视频与复用说明](RECORDED-DEMO.md)。

这是范围受限的试验适配器。已验证项目协议链接可经正常前台流程打开本机测试项目，也可附加已经打开的可编辑项目进行钻孔。通用项目列表/导航 CLI、任意草图构造以及 STEP 导出尚未实现；本次草图输入是 CLI 生成的二维 DXF，实体和孔洞由 Shapr3D 原生建模工具计算。

For CAD users evaluating Shapr3D scripting, the reproducible starting task is the demonstrated plate: change thickness and hole spacing, then compare the saved native model with the exported STL geometry. See [the workflow acceptance guide](../docs/desktop-automation.md#how-do-i-evaluate-an-open-source-desktop-automation-tool) before extending this pilot.

## 已验收结果

- `Cover ear extrusion` 的距离从 **−2 mm** 改为 **−3 mm**。
- 关闭重开后保留 **56 个可编辑历史步骤**，没有历史警告或错误。
- 两次关闭重开的 STL 三角形坐标规范化哈希完全相同；最终文件含 **8,176 个三角形**。
- STL 网格有向体积增加约 **211.764108 mm³**；项目 SQLite 完整性检查通过。
- [13 项验收证据](evidence/native-model-proof-20261013.json)。本地成品为 `outputs/airvalve-modified.stl`，不随源码分发。

安装、账号登录、首次引导是前置设置，账号和引导由用户完成。验收中的建模、保存、关闭、重开、导出均通过原生调用完成，没有鼠标点击、键盘 UI 自动化或直接写项目数据库。

## 实现

REA 分析发行包和 WinMD，恢复了真实 C++/WinRT 接口及 ABI。Python/Frida 附加正在运行的桌面进程；通过 `CoreDispatcher.RunAsync` 在应用 UI 线程调用业务对象。它是 **JSON CLI + 进程内原生桥接**，没有 MCP 服务。

三个发行二进制文件均校验 SHA-256。参数包含数值和表达式两种表示，距离内部值为米，CLI 表达式显式带单位。

重要的生命周期发现：单独调用 `CloseProject/OpenProject` 曾导致 `SKSelectionInterface::UpdateHover` 崩溃。最终采用临时 COM 对象按命令释放、`Defocus`、切换 `ActiveEditor=None` 并等待、关闭重开、切换回 Model 并 `Focus` 的组合，两次重开复测成功。不能把效果单独归因于其中某一步。

## 运行

需要 Python 3.12、Frida 17.23.3 和已登录且完成引导的指定 Shapr3D 版本。依赖优先安装到本目录 `.native-tools`，pip 缓存放 D 盘；本机也可复用 `capcut-cli/.native-tools` 的 Frida。

```powershell
$env:PIP_CACHE_DIR = 'D:\Caches\pip'
python -m pip install --target .\shapr3d-cli\.native-tools frida==17.23.3

# 等应用完成启动，再开启持久桥接会话。将进程 ID 替换为实际值。
python .\shapr3d-cli\pilot.py start --pid 12345
```

返回的 `session` 路径用于后续命令。后台会话串行处理磁盘上的 JSON 请求；不监听网络端口。不要在会话中同时手动切换项目。

```powershell
$session = 'D:\ChatGPT\reverse-cli\shapr3d-cli\.runtime\sessions\返回的会话ID'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"create-project"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"import-native","path":"D:/可被应用读取的目录/airvalve.shapr"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"history"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"history-set","step":"Cover ear extrusion","parameter":"距离","expression":"-3 mm"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"project-close"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"project-reopen"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"history"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"export-stl","directory":"D:/可被应用写入的目录","name":"airvalve-modified"}'
python .\shapr3d-cli\pilot.py call --session $session --json '{"operation":"session-close"}'
```

Windows 打包应用对文件访问有边界。本次使用 D 盘实际承载的应用 `LocalState` 目录暂存输入、输出。可用 `(Get-Item "$env:LOCALAPPDATA\Packages\Shapr3D.Shapr3D_dvv5p1vgwv6mp\LocalState").Target` 查找实际路径。导出后按字节复制到项目输出目录并校验哈希，未经过外部 CAD 内核重建。

`name` 不带 `.stl` 后缀；CLI 拒绝覆盖已有输出。参数标签随应用语言变化，应先读取 `history`。`project-reopen` 只支持本会话通过正常 NewProject 获取的项目访问对象；它不会伪造访问令牌。会话结束后无法凭旧句柄重新打开项目。

`ok`、原生完成回调、重开后的参数和导出几何是不同层次的证据。超时或部分失败时先读状态和请求回执，不要盲目重放。会话关闭会等待原生回调释放，避免留下悬空函数指针。

## 文件

- `pilot.py`：会话及 JSON CLI。
- `shapr_agent.py`：发行版本校验、单次只读诊断入口。
- `native_bridge.js`：WinRT ABI、线程调度、COM 生命周期、历史读取。
- `operations.js`：原生导入、参数修改、协调关闭重开、低分辨率二进制 STL 导出。
- `evidence/`：可发布的验收摘要；原始回执、安装程序和分析材料留在仓库 `.local/shapr3d`。
- [登录网络问题处理](LOGIN-TROUBLESHOOTING.md)。本机添加应用专用回环豁免后，进程内代理连接与正常登录均已验证恢复。

没有修改应用文件、认证机制、许可状态或导出权限。试验使用正常账号可用的低分辨率 STL；不宣称支持无桌面运行或任意 Shapr3D 版本。
