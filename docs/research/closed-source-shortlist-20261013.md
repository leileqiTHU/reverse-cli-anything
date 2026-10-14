# 闭源软件重新选题：优先 Axure RP 原生编辑

调研日期：2026-10-13。范围：公开产品文档、开发接口、用户任务及现有第三方实现。排除 CapCut 与另一 session 负责的 Shapr3D。本轮没有安装候选软件、启动试用或验证其二进制调用。

## 决策

**推荐本 session 下一步研究 Axure RP 11：让 Agent 修改原生交互原型。**

主候选按建议顺序为 Axure RP、DxO PhotoLab、CLIP STUDIO PAINT。共同要求是最终产物保留目标软件的实际价值：可继续编辑的原生项目，或经过目标软件专有处理流程的输出。下面的技术路径均是待验证假设，不表示已经找到内部函数。

这次筛选要求具体说明三个问题：用户要完成什么任务，公开接口在哪个必要步骤中断，恢复哪个内部能力才能继续。官方已有的能力优先复用并如实归因；仅有“软件闭源”或“未找到 REST API”不足以立项。

| 候选 | 具体 Agent 任务 | 公开路径中断的位置 | 值得逆向补齐的部分 | 排序依据 |
| --- | --- | --- | --- | --- |
| **Axure RP 11** | 给现有报销表单增加字段、必填校验、错误/成功状态，保存 `.rp` 并输出可交互 HTML | 官方本地 MCP 明确只读；不能修改页面控件或交互 | 编辑命令、控件/条件/动作对象、原生保存及 HTML 生成 | 当前官方证据明确；能把新增写能力与现有读取能力直接对比 |
| **DxO PhotoLab** | 一组 RAW 按各自问题调整曝光、白平衡、裁剪和降噪，生成预览，经反馈再修改，交付 JPEG/TIFF | 预设、批量导出和 sidecar 交换存在；缺少已确认的完整逐图编辑、渲染任务与结果读回接口 | 原生修正参数、设置同步、预览/导出任务提交及完成状态 | 业务价值高；历史内部渲染进程有线索，但新版本协议待实测 |
| **CLIP STUDIO PAINT EX** | 把漫画译稿写回对应的原生文字对象，调整字号/框位、检查溢出，保留分层工程并批量出图 | 官方 SDK 面向滤镜；Auto Actions 只覆盖可录制操作，不能提供完整文字/图层对象 API | 文字、图层和页面对象访问，排版修改、撤销及原生保存/导出 | 视觉展示强；原生排版及多页对象复杂度较高 |

## 1. Axure RP：从读取设计推进到修改原型

### 任务与受益者

产品经理或 UX 团队已有 `.rp` 原型。Agent 根据需求变更，把“报销申请”页面增加金额/用途字段、空值提示、提交成功状态，并同步按钮文案和说明。交付仍是团队可以在 Axure 中继续编辑的工程，附应用生成的交互预览。

这类需求依赖现有控件、状态和交互的连续性。首次示例可以自建小工程，随后验证对既有工程的局部修改。Axure 的条件和事件可以表达表单校验及分支行为，原生生成器会输出 HTML/CSS/JavaScript。[产品能力](https://www.axure.com/axure-rp)、[条件逻辑](https://docs.axure.com/axure-rp/reference/conditional-logic/)、[原生预览与本地输出](https://docs.axure.com/axure-rp/reference/viewing-sharing-prototypes/)。

### 已有接口与明确缺口

最新官方文档说明，RP 11 的本地 MCP 可读取打开工程的页面、控件、交互、说明和渲染图，但 **全部访问目前都是只读，不能修改文件**。这直接阻断“读取原型 → 根据需求修改 → 保存”的后半段。Axure Cloud 的 MCP 面向另一组云端对象，不能据此推断它能写本地 RP 工程。[官方 MCP 范围](https://docs.axure.com/axure-rp/reference/mcp/)。

旧版 C# RP API 也是读取设计数据的技术预览，并标注支持 RP 8/9；Figma 导入属于素材交换路径。这些可以复用，但没有提供已确认的 RP 11 控件及条件交互写入契约。[Legacy API](https://www.axure.com/axure-rp-api)、[Figma 导入](https://www.axure.com/a/figma-and-axure)。

### 逆向目标

重点寻找应用内部负责以下业务的命令及事务：创建/更新控件，创建事件—条件—动作关系，撤销/重做，保存工程和触发原生 HTML 生成。现有 MCP 用作读取与结果观察的一条路径；生成的 HTML 和重开工程用于另外两层验收。

不能只修改预览页面的 DOM：这样不会把控件和交互写回 `.rp`。若采用文件格式或剪贴板格式作为导入路径，应明确标识，并验证导入后对象、交互和保存行为；只有静态图像导入不算完成原型编辑。

### 首个案例与边界

先完成一个最小原生写操作，再扩展到“报销申请”表单：空值提交显示错误，合法输入切到成功状态；随后通过 CLI 修改提示文案和按钮位置，再保存重开并导出。

截至本次读取，官方 changelog 最新列出的 Windows 版本为 **11.0.0.4150（2026-09-24）**，正式研究仍需对下载到的文件检查版本、签名及哈希。官网提供 PC/Mac 的 30 天完整功能试用；账号激活和本机安装条件尚未实测。[版本记录](https://www.axure.com/changelog?filter=Axure+RP)、[试用说明](https://www.axure.com/axure-rp)。

最大未知是写命令的对象生命周期、线程约束和保存一致性。已有读取 MCP 不代表写接口简单，更不能由旧 C# API 推断当前程序的完整技术栈。即使读取和截图都成功，仍需一次真正的写入—保存—重开证明。

## 2. DxO PhotoLab：逐图决策与专有 RAW 渲染

### 任务与受益者

摄影师给 Agent 一组高 ISO、曝光不一的 RAW。Agent 先查看低分辨率预览，按每张图的内容提出曝光/白平衡/裁剪方案，再调用 PhotoLab 的修正与降噪流程；查看结果后修订，并输出全尺寸文件和小型交付预览。设置随项目或 sidecar 保留，用户可继续修片。

使用目标软件的理由是复用其镜头配置、RAW 处理和降噪能力。单纯文件转格式不作为本案例的重点。

### 已有接口与具体中断点

PhotoLab 已有 GUI 批处理、预设和 `.dop` 设置交换；它不是完全没有自动化。当前官方手册说明 `.dop` 存储修正设置，并与内部数据库关联。因此研究应区分“把设置写入文件”与“运行中的编辑器实际加载并渲染了这些设置”。[设置与 sidecar](https://userguides.dxo.com/photolab/en/menus-preferences-and-functions/)、[原生导出](https://userguides.dxo.com/photolab/en/exporting-images/)。

本轮未找到覆盖逐图参数更新、预览、任务提交和完成状态的完整公开 API。2025-11 的官方社区用户仍在讨论 SDK 缺口；这是用户需求证据，不是厂商对所有渠道的否定声明。[SDK 需求](https://forum.dxo.com/t/no-photolab-sdk-something-can-be-done/53045)。

2020 年用户已记录过内部 `DopCor.exe` 的命令参数和监听模式，同时遇到设置文件语义问题。这意味着该候选应以**恢复内部渲染协议及设置契约**作为切口，不能宣传为“此前完全没有 CLI”，也不能假定 2026 版本仍采用同一结构。[历史实际调用记录](https://forum.dxo.com/t/dxo-photolab-command-line-interface/13972)。

### 逆向目标及验收

恢复当前版本的修正参数对象、编辑器与渲染器之间的请求/结果约定、缓存与设置同步规则。拟议能力为 `image inspect`、`adjust set`、`preview render`、`export submit/status`。先验证一张 RAW：改曝光 → 原生预览 → 原生导出 → 重开后读回设置；再加入多图决策与降噪。

原始 RAW 哈希应不变；参数读回符合请求；导出尺寸、色彩配置与格式正确；实际画面能体现修改。不要把“噪声方差变小”单独当作画质提升，验收还要检查细节和伪影。

官网当前提供 30 天完整试用，声明无水印和导出数量限制，下载涉及邮箱；尚未为本轮提交资料或激活。[官方试用](https://www.dxo.com/en/dxo-photolab/download/)。主要成本是 RAW 样本、相机/镜头模块、GPU 计算及版本适配。作为 Axure 之后的候选，优先级高。

## 3. CLIP STUDIO PAINT EX：漫画文字与图层的结构化编辑

### 任务与受益者

漫画作者或本地化团队提供分层漫画和译稿。Agent 对照页面，将每段译文写回对应文字对象，调整字号、换行和位置，检查是否越出气泡，再交付原生 `.clip`/多页工程及分页图片。首轮用自制两页漫画，避免在复杂作品上开始验证。

该任务利用 Agent 的语言与图像理解，要求文字继续可编辑、线稿和其他图层不被改动。官方 Story Editor 的多页文字编辑和批量字体设置说明，这些本来就是应用中的实际工作流。[Story Editor](https://help.clip-studio.com/en-us/manual_en/570_pages/Use_Story_Editor.htm)、[批量字体设置](https://support.clip-studio.com/en-us/faq/articles/20190032)。

### 已有接口与具体中断点

官方 SDK 面向 PAINT EX 的图像处理滤镜；不是完整文档、文字、页面、图层管理接口。Auto Actions 可以录制重复操作，但官方手册明确列出录制范围限制，参数改变时还可能需要对话框输入。它不能直接满足按对象 ID 读取不同气泡文字、写入不同译文并根据结果再排版的完整契约。[SDK 范围](https://www.clipstudio.net/ja/sdk/)、[Auto Actions](https://help.clip-studio.com/en-us/manual_en/720_preferences/Auto_Actions.htm)。

已有第三方 `clip-studio-paint-5.1.2-production-mcp`，作者明确说明它依赖窗口截图、输入操作、快捷键、Auto Actions 和文件交换，不是原生图层对象 API。本轮只阅读其实现说明，未运行或确认所有能力。[项目说明](https://github.com/A2pha/clip-studio-paint-5.1.2-production-mcp)。

### 逆向目标及验收

恢复文字/图层树读取、对象属性修改、页面与导出命令。拟议能力为 `document inspect`、`text update`、`layer transform`、`page preview/export`。第一关只更改一个文字对象，保留其可编辑性，撤销后能恢复原值；再验证原生保存重开、字体和位置修改。

两页漫画的验收应同时检查文本映射、对象坐标、合成画面、未修改图层及重开后的编辑性。只把译文贴成像素覆盖层，不能算原生文字接口。

SDK 的 EX 范围、版本差异和多页能力需要现场确认。官方说明 30 天试用可以体验全部功能，期满后保存/导出会受限；“Doodle Mode”不能代替完整试用。[试用限制](https://support.clip-studio.com/en-us/faq/articles/20190178)。该候选的业务价值明确，但文字布局、多页事务和原生对象模型使首轮风险高于 Axure。

## 未入主名单的对象

| 软件 | 本轮处理 |
| --- | --- |
| CapCut、Shapr3D | 按要求排除，本 session 不介入另一 session 的研发 |
| Xmind | 官方 MCP 已覆盖创建、读取和编辑；基础任务优先走官方接口。[官方说明](https://xmind.com/integrations/mcp) |
| Affinity | 官方脚本及 AI Connector 已覆盖广泛生产操作，普通编辑任务不构成新的逆向理由。[发布说明](https://www.affinity.studio/blog/affinity-automation-scripting-claude) |
| Capture One Windows | 值得继续观察：当前官方脚本文章针对 macOS，但另有 Windows 插件 SDK；本轮未取得足够新的完整 SDK 覆盖证据，不把整套 Windows 编辑能力武断归为不可调用。[脚本](https://support.captureone.com/hc/en-us/articles/360002681418-Capture-One-Workflow-Automation-with-AppleScript)、[开发入口](https://www.captureone.com/en/partnerships/developer) |
| FL Studio | 补充发现 2026-05 用户实际调查了 Playlist 片段枚举缺口，说明“已有很多 API”不能推出“没有逆向价值”。它可作为后续特定缺口案例，但本轮优先选择文档边界更明确、且与当前视频案例不同的 Axure。[实际需求与接口调查](https://forum.image-line.com/viewtopic.php?p=2057337) |

## 本 session 的建议启动范围

### 第一关：只验证一个可持久化的原生写操作

1. 从官方获取 Axure RP Windows 安装包，放在 `D:\Installers\Axure`，优先安装到 `D:\Apps\AxureRP`；核对实际目的地。缓存、研究输出和测试工程优先放 D 盘，不迁移既有数据。
2. 固定版本、签名与模块哈希；建立独立测试工程。通过官方本地 MCP 读取对象基线，记录实际能力清单。
3. 按发行包识别的实际运行时选择 REA 分析方式，定位一个编辑命令及其线程、对象和撤销关系。
4. 通过 CLI 将指定控件文字从 A 改成 B，读取原生对象和画面，验证撤销/重做。
5. 原生保存，关闭重开，确认 B 保留；随后让应用生成 HTML，确认输出也含 B。

通过后再实施完整表单案例。若只能控制鼠标、修改导出 HTML 或读取对象而不能写入原工程，就记录未通过，不将其加入已支持列表。

### 拟议首批命令组

| 命令组 | 范围 | 实现归因 |
| --- | --- | --- |
| `inspect` | 页面、控件、交互、原生预览 | 优先复用官方 MCP，并记录其能力限制 |
| `widget` | 创建控件，修改文本、几何与样式 | 原生编辑路径待逆向验证 |
| `interaction` | 事件、条件分支、显示/隐藏或状态切换 | 原生交互对象路径待逆向验证 |
| `project` | 创建、打开、保存、关闭；关联对象上下文 | 原生生命周期待验证 |
| `export` | 本地 HTML 导出、状态与产物校验 | 原生生成器入口待验证 |

命令名是规划，不代表已实现。完整演示会验证空字段、有效字段及修改后的提示文案；编辑操作不用鼠标。浏览器中的交互行为测试仅用于检验应用导出的产物，应与原生编辑通路分开记录。

**选择理由：**Axure 的写能力缺口有当前官方文档支持，原生输出和项目重开可以独立验证，且覆盖了视频/CAD 之外的产品设计场景。已有 MCP 为观察提供条件，但新案例的成功标准落在原生写入、交互和持久化上。
