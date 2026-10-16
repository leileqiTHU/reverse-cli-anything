# reverse-cli-anything

**通过逆向，为闭源软件建立 Agent 友好的 CLI。**

**[中文文档站](https://leileqithu.github.io/reverse-cli-anything/zh/)** · [Documentation website](https://leileqithu.github.io/reverse-cli-anything/)

`reverse-cli-anything` 是面向 **AI Agent 闭源桌面软件自动化**的开源逆向工程工具链。当公开 CLI、API 或 MCP 无法覆盖任务时，编程 Agent 利用本框架恢复软件内部操作、构建可复用的命令行工具，并在真实软件中验证。仓库提供 **CapCut 视频剪辑、Axure RP 交互原型和 Shapr3D CAD 建模**的实测案例。

[English](README.md) · [最简安装](#最简安装复制给你的-agent) · [对话使用](#安装后通过对话生成和使用-cli) · [工作方式](#工作方式) · [展示案例](#展示案例) · [常见问题](docs/faq.zh-CN.md) · [开发文档](#开发与扩展) · [致敬与感谢](#致敬与感谢)

**没有源码，也能通过逆向构建 CLI，让 Agent 调用软件的原生能力。** 中英双语项目介绍：[YouTube · 1 分 48 秒](https://www.youtube.com/watch?v=BVbwRFlK0nM) · [X · 60 秒](https://x.com/lei_le77716/status/2110290745844437485)。

**先看实际效果：通过 CLI 驱动 CapCut 原生视频编辑。**

[![CapCut CLI：剪辑时间线、添加可编辑字幕、查看导出结果](capcut-cli/assets/capcut-cli-teaser.gif)](https://github.com/leileqiTHU/reverse-cli-anything/raw/refs/heads/main/capcut-cli/assets/capcut-cli-45s.mp4)

**[45 秒视频 · MP4 · 4.2 MB](https://github.com/leileqiTHU/reverse-cli-anything/raw/refs/heads/main/capcut-cli/assets/capcut-cli-45s.mp4)** · [CapCut 完整流程 · 4:08](capcut-cli/assets/capcut-cli-demo.mp4) · [Axure + Shapr3D 演示](#展示案例)

MP4 链接会根据浏览器设置直接打开或下载视频。预告从实际录像中选取片段，保留原速；动图为无声预览。CapCut 的编辑和导出通过逆向恢复的内部调用完成，语音识别和翻译使用外部辅助工具。[剪辑来源](docs/demos/README.md#short-overview) · [素材署名](docs/demos/CREDITS.md)。

**让 Agent 安装一次，之后通过对话指定软件和所需操作。** 用户的入口是对话，Agent 的交付物是经过实测的 CLI 集合；环境配置、逆向研究、接口开发和验收都由 Agent 执行。

## 使用场景

- Agent 需要在某个软件里完成工作，但公开 CLI、API 或 MCP 不支持所需操作。
- 希望建立可重复的原生工作流，例如创建文档、修改对象、调整参数、导入素材或导出结果。
- 希望把一次成功的逆向实验整理成其他 Agent 可以发现和使用的工具。

软件和任务由你决定。你可以列出所需操作，也可以直接描述工作目标，让 Agent 拆解需要补齐的接口。

### 按你的任务找到入口

| 你的任务 | 从这里开始 |
| --- | --- |
| 让 AI Agent 操作没有合适 API 或 CLI 的桌面软件 | [没有公开 API，如何自动化闭源软件](docs/desktop-automation.zh-CN.md) |
| 在 GUI 自动化、项目文件编辑、软件原生控制之间选型 | [选择自动化路线](docs/desktop-automation.zh-CN.md#选择自动化路线) |
| 用 CapCut 剪辑导出视频、生成 Axure 原型、修改 Shapr3D 模型 | [原生软件自动化案例与证据](docs/native-automation-examples.zh-CN.md) |
| 让 Agent 直接运行命令，或评估是否需要 MCP 封装 | [CLI 调用入口与自动化后端](docs/desktop-automation.zh-CN.md#climcp-与-gui-自动化区分调用入口和执行后端) |
| 核对原生保存重开、导出和工作流复现证据 | [评估开源桌面自动化工具](docs/desktop-automation.zh-CN.md#如何评估一个开源桌面自动化工具) |
| 将逆向恢复的内部函数变成可复用的 Agent 工具 | [闭源应用 CLI 工程手册](docs/HARNESS.zh-CN.md) |
| 软件升级后修复 CLI，或在新会话接续研究 | [新建、扩展、恢复与升级流程](docs/workflows.zh-CN.md) |

源码仓库为 **[leileqiTHU/reverse-cli-anything](https://github.com/leileqiTHU/reverse-cli-anything)**。[REA 和 CLI-Anything 是另外两个项目](docs/faq.zh-CN.md#reverse-cli-anything-与-reacli-anything-是什么关系)：REA 提供本项目研究中使用的分析工具，CLI-Anything 为面向 Agent 的 CLI 方法提供了启发。

## 最简安装：复制给你的 Agent

点击代码块的复制按钮，粘贴给具备本机终端与文件访问能力的 Codex 等编程 Agent。

```text
请安装并配置 reverse-cli-anything：https://github.com/leileqiTHU/reverse-cli-anything。
读取仓库内的通用 Agent Skill，并按照安装文档完成配置和自检。
如果当前 Agent 支持安装 Skill，将完整 Skill 及其引用资源一并安装并验证发现状态。
遵循我的安装与存储偏好，完成后告诉我执行目录、Skill 路径、安装记录、发现状态和安装验证结果。
此次只安装本仓库；等待我后续通过对话指定软件和所需操作，再开展分析与逆向。
```

Agent 会按[安装说明](docs/install.zh-CN.md)准备仓库和 Python 3.11+，并完成自检。目标软件及相应分析工具在后续任务需要时再配置。

## 安装后：通过对话生成和使用 CLI

**先提出需要补齐的操作集合。** 例如，另发一条消息给 Agent：

```text
用 reverse-cli-anything 为 <软件名称> 建立一组 CLI，让你能够完成：
<操作一>、<操作二>、<操作三>。
检查现有接口，针对缺失能力进行逆向、实现和实际验收。
交付可复用的 CLI 集合和调用说明，并验证这些操作能够串成完整工作流。
```

也可以直接说：“我需要你在 `<软件名称>` 中完成 `<工作目标>`。用 reverse-cli-anything 补齐完成这项工作所需的 CLI。”Agent 根据任务拆解操作、选择分析工具、编写接口，并在实际软件中验证。

**接口建好后，继续用对话安排工作。** 例如：

```text
使用刚才建立的 CLI，在 <软件名称> 中处理 <输入文件或项目>，
完成 <具体任务>，将结果保存到 <输出目录>，并检查结果。
```

用户不需要手动运行脚手架、注册适配器或编写命令。Agent 按[目标任务流程](docs/SOP.zh-CN.md#开始目标任务)推进，交付命令、参数说明、目标 Skill 和实际验收结果。后续任务可以复用这些 CLI；若换了 Agent 或会话，加载已安装 Skill，或提供其路径及已生成 CLI 的位置。安装记录说明应继续使用哪份框架配置和注册表。

## 工作方式

```text
你通过对话指定软件和操作集合
  → Agent 检查现有接口，定位能力缺口
  → 分析发行程序与运行行为，恢复内部操作
  → 实现所需 CLI 集合，串联并验证实际工作流
  → 交付可复用工具，供后续 Agent 任务调用
```

[通用 Skill](skills/reverse-cli-anything/SKILL.md) 和 [SOP](docs/SOP.zh-CN.md)指导 Agent 完成研究与实现；REA 或适合目标的分析工具提供逆向能力。仓库为 Agent 提供方法和开发工具，新软件的接口需要 Agent 根据实际程序研究、实现和验证。

| 阶段 | Agent 完成的工作 |
| --- | --- |
| 明确需求 | 将工作目标拆成操作集合，检查现有接口覆盖范围，确定需要逆向的缺口。 |
| 研究与实现 | 配置所需工具，分析程序及运行行为，恢复内部调用，封装为 Agent 友好的 CLI。 |
| 实际验收 | 执行所需操作及完整工作流，检查软件状态与结果，以及任务适用的保存、重开、导出和恢复行为。 |
| 交付与复用 | 提供 CLI、结构化参数与结果、调用说明、目标 Skill，以及逐项验证情况和限制。 |

完成范围以用户请求的操作集合为准，生成目录或跑通第一个接口只是开发过程中的步骤。具体软件能够支持哪些操作，需要实际验证；未实现或受阻的部分会明确列出。

### 框架为 Agent 提供什么

- **工程方法：** 从操作缺口到可复用交付的八个阶段，以及新建、扩展、故障恢复和版本适配的不同工作模式。
- **按产物选择的研究指南：** 原生命令与 ABI、托管编辑事务、WinRT 对象生命周期，以及打包脚本、协议和文件格式路线。Agent 只需读取相关指南。
- **可接续的研究记录：** 操作范围、入口契约、实验、版本身份、状态观察与交接模板；文件型助手检查依赖和证据引用，不把静态发现误标为已验证能力。
- **交付基础设施：** 适配器契约、工具发现、结构化调用、回执与恢复约定，以及根据工具目录生成调用说明、安装完整 Skill 的助手。

从[工程手册](docs/HARNESS.zh-CN.md)开始，按目标运行时与所需操作选择对应指南。

## 展示案例

以下案例展示这套方法的实际效果，不是软件支持名单，也不是安装或使用的前提。点击缩略图或播放链接观看，三段均为真实软件操作，全程没有鼠标点击。

| CapCut：视频剪辑 | Axure RP：交互原型 | Shapr3D：原生建模 |
| --- | --- | --- |
| [![CapCut CLI 演示](capcut-cli/assets/capcut-cli-demo.jpg)](capcut-cli/assets/capcut-cli-demo.mp4) | [![Axure CLI 演示](axure-cli/assets/axure-cli-demo.jpg)](axure-cli/assets/axure-cli-demo.mp4) | [![Shapr3D CLI 演示](shapr3d-cli/assets/shapr3d-cli-demo.jpg)](shapr3d-cli/assets/shapr3d-cli-demo.mp4) |
| **[播放 · 4:08](capcut-cli/assets/capcut-cli-demo.mp4)** | **[播放 · 1:46](axure-cli/assets/axure-cli-demo.mp4)** | **[播放 · 0:56](shapr3d-cli/assets/shapr3d-cli-demo.mp4)** |
| 空白工程 → 真实素材 → 裁剪 → 现场语音识别与翻译 → 配乐、字幕 → 原生导出及有声成片播放 | 空白工程 → 页面、按钮、输入框 → 布局、点击规则 → 保存、冷启动重开 → 原生 HTML 与浏览器交互 | 空白模型 → 草图导入 → 原生拉伸 → 厚度、孔距调整 → 中心贯穿孔 → 原生项目与 STL 导出 |
| [能力和命令](capcut-cli/README.md) · [26 项原生/成片检查](capcut-cli/evidence/recorded-real-media-20261014.json) | [能力和命令](axure-cli/README.md) · [29 项原生检查](axure-cli/evidence/native-login-acceptance.json) + [14 项浏览器检查](axure-cli/evidence/native-login-browser.json) | [能力和命令](shapr3d-cli/README.md) · [78 项几何检查](shapr3d-cli/evidence/recorded-demo-english-20261014.json) |

统一采用英文说明、软件画面与底部 CLI 命令栏，无片头，保持原速。原软件界面及作品内容保留，包括 CapCut 的双语字幕。CapCut、Axure 的命令来自实际执行日志；Shapr3D 展示与已验证原生请求对应的 CLI 语法。[录制来源、章节与校验](docs/demos/README.md) · [素材署名](docs/demos/CREDITS.md)。

### 案例中已展示的能力

| 案例 | Agent 可操作的内容 | 验证环境 |
| --- | --- | --- |
| [CapCut](capcut-cli/README.md) | 创建/打开/关闭项目，素材导入，独立时间线创建切换，放置/裁剪/拆分片段，配乐、可编辑字幕、片段属性，原生帧/区间预览与导出 | Windows x64 · 9.5.0.4050 |
| [Axure RP](axure-cli/README.md) | 创建切换页面，添加文本/按钮/输入框，文字与位置尺寸修改，支持的点击条件和动作，撤销/重做，保存及冷启动重开，原生 HTML 导出 | Windows x64 · 11.0.0.4150 |
| [Shapr3D](shapr3d-cli/README.md) | 原生新建项目或附加可编辑的当前模型，.shapr/DXF 导入，数字历史参数读写，本例拉伸、孔面移动与钻孔，原生 .shapr/STL 导出 | Windows x64 · 26.180.11926.0；范围受限的建模试验 |

CapCut 的语音识别、翻译由外部工具和 Agent 完成，再写入原生字幕。Shapr3D 可见建模目前限定本例 XY 固定板，不宣称通用草图构造或通用项目导航。各适配器说明书列出具体版本、能力及生命周期限制。

### 案例接口是如何恢复的

三个案例的核心编辑能力都来自对软件发行产物的逆向分析：恢复内部调用方式，再封装为我们自己的 CLI。软件内部已有的接口与官方向第三方公开支持的自动化 API 是不同的概念，下表明确各适配器恢复和复用了什么。

| 案例 | CLI 如何接入软件 | 复用内容与能力边界 |
| --- | --- | --- |
| **CapCut** | 分析 `lyra_cli_client.dll`、编辑器和前端模块，通过 Frida 调用内部命令、函数地址和活动编辑会话。 | **程序内部原本就有命令执行层。** 我们恢复其调用约定，并接通项目、时间线和导出的生命周期；不宣称所有底层命令都是从零创造的。[实现说明](capcut-cli/docs/implementation.md) |
| **Axure RP** | 反编译发行程序集，恢复编辑事务、控件、保存器和 HTML 生成器的调用链，通过自建桥接在 UI 线程执行。 | **部分只读操作复用了内置 MCP 文档服务组件**，例如 sitemap。创建页面、修改控件和安装交互规则等写入能力，使用逆向恢复的内部编辑入口。[逆向证据](axure-cli/reverse-engineering.md) |
| **Shapr3D** | 分析发行二进制和 WinMD 元数据，恢复应用内部 C++/WinRT 接口、虚表及部分函数地址，在进程内调用原生建模对象。 | DXF 是现成的导入格式，Windows 线程调度也是标准平台能力；建模操作、参数修改和对象生命周期通过逆向恢复的内部桥接驱动。[原生桥接代码](shapr3d-cli/native_bridge.js) |

二进制中的导出符号、类型元数据或内部命令，本身不等于受支持的第三方 SDK。逆向工作的关键是确定参数、对象状态、线程和生命周期要求，将这些入口变成可调用、可验证的 Agent 工具。


## 开发与扩展

以下文档供执行任务的 Agent 和框架贡献者使用。安装、自检、脚手架及注册命令位于开发文档，用户可直接使用上面的对话流程。

| 文档 | 内容 |
| --- | --- |
| [安装](docs/install.zh-CN.md) · [通用 Skill](skills/reverse-cli-anything/SKILL.md) | Agent 的环境准备与任务执行说明。 |
| [工程手册](docs/HARNESS.zh-CN.md) · [工作模式](docs/workflows.zh-CN.md) | 新建、扩展、恢复和升级的阶段交付物与决策。 |
| [专项指南](docs/HARNESS.zh-CN.md#按需阅读) · [研究模板](templates/research/README.zh-CN.md) | 按技术路线研究，以及入口卡、实验与交接记录。 |
| [开发助手](docs/development-tools.zh-CN.md) | 研究工作区、文件指纹、证据检查、调用说明与完整 Skill 资源包。 |
| [SOP](docs/SOP.zh-CN.md) · [架构](docs/architecture.zh-CN.md) | 通用研究流程、核心与目标适配器的职责。 |
| [运行层命令](docs/runtime.zh-CN.md) · [适配器契约](docs/adapter-contract.zh-CN.md) | 配置、脚手架、注册、调用、回执及工具结构。 |
| [验收标准](acceptance/README.zh-CN.md) | 框架检查、原生后置条件、持久化、产物及恢复要求。 |
| [贡献指南](CONTRIBUTING.zh-CN.md) | 扩展框架或添加新的软件适配器。 |
| [文档站构建与发布](site/README.md) | 复用中英文文档，通过免费的 GitHub Pages 项目站发布。 |

通用能力位于 `reverse_cli/`、`skills/reverse-cli-anything/`、`docs/` 和 `tools/`；软件相关实现位于各自的 `<software>-cli/` 目录。展示案例通过 `examples/` 单独索引，安装与通用流程不依赖任何案例。

## 致敬与感谢

感谢以下项目与作者。他们的理念、工具和公开资料，为本项目提供了启发与支持。

| 项目 / 作者 | 对 reverse-cli 的帮助 |
| --- | --- |
| [CLI-Anything](https://github.com/HKUDS/CLI-Anything) · [@HKUDS](https://github.com/HKUDS) | 启发了通过 CLI 让软件面向 Agent 的方向，以及通用方法、软件案例和 Skill 的项目组织方式。 |
| [REA](https://github.com/morluto/rea) · [@morluto](https://github.com/morluto) | 提供 Agent 可调用的逆向工具，用于发行产物分析及部分原生入口研究。 |
| [OpenChatCut](https://github.com/0xsline/OpenChatCut) · [@0xsline](https://github.com/0xsline) | 对话式视频剪辑的产品启发，也为剪辑、字幕、配乐及时间线检查等 Agent 操作提供了参考。 |
| [capcut-cli](https://github.com/renezander030/capcut-cli) · [@renezander030](https://github.com/renezander030) | 通过草稿文件实现 CapCut 自动化的对照参考，帮助明确本项目进程内原生编辑路线的范围。 |
| [shapr3d-mcp](https://github.com/Alfredoalv13/shapr3d-mcp) · [@Alfredoalv13](https://github.com/Alfredoalv13) | 外部建模与 STEP 交换的 Agent CAD 研究参考，帮助界定原生可编辑建模接口需要补齐的能力。 |

实现和演示也使用了以下开源工具：

- [Ghidra](https://github.com/NationalSecurityAgency/ghidra)、[ILSpy](https://github.com/icsharpcode/ILSpy)、[Capstone](https://github.com/capstone-engine/capstone)、[Frida](https://github.com/frida/frida)：原生及托管代码分析、反汇编和运行时插桩。
- [FFmpeg](https://ffmpeg.org/)、[faster-whisper](https://github.com/SYSTRAN/faster-whisper)、[Windows Capture](https://github.com/NiiightmareXD/windows-capture)：媒体准备与验收、语音识别和录屏。

也感谢 NASA 提供演示素材，以及 Kevin MacLeod 创作的 *Fluidscape*。来源、许可和必要署名见[素材致谢](docs/demos/CREDITS.md)。软件官方文档与其他研究资料的链接，保留在[候选调研](docs/research/closed-source-shortlist-20261013.md)、[前期对比](docs/research/next-example-20261013.md)和各案例的实现说明中。

## 许可证

本项目原创代码与文档采用 [MIT 许可证](LICENSE)。第三方软件及媒体素材保留各自的许可，参见上方致谢与[素材署名](docs/demos/CREDITS.md)。
