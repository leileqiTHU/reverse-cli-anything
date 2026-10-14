# 下一个闭源软件案例：选择 Shapr3D

调研日期：2026-10-13。状态：**选题完成，原生接口尚未验证**。本轮完成公开资料与现有实现对比，只获取了小型安装清单，没有安装候选软件、创建账号或启用付费试用。

## 结论与选择标准

建议第二个案例做 **Shapr3D 的原生参数化建模 CLI**，第三个候选保留 **FL Studio 的编曲与混音 CLI**。Shapr3D 优先级最高的依据是实际用户需求、现有控制能力的缺口，以及从视频编辑扩展到 CAD 的证明价值；这不是对逆向成功率的保证。

选择标准按以下顺序评估：

1. **有完整任务需求**：Agent 能交付可继续编辑的项目和有用产物，例如按尺寸制作安装件，再按用户反馈调整孔距。
2. **逆向有新增价值**：优先补足应用内的业务控制，而不是仅给已有官方导出命令换一个名字。
3. **能独立验收**：对象、参数、保存重开、原生输出和外部测量能相互印证。
4. **能扩大案例覆盖**：第二个软件应检验与 CapCut 不同的对象模型和执行机制。
5. **适合本机验证**：Windows 可用，账号和版本条件明确，有合理的初始成本；安装与缓存优先 D 盘。

## 候选比较

以下优先级是本项目的判断，不是软件功能排名。这里比较的对象都是闭源桌面产品；某个 SDK 或连接器开源，不代表应用本身源码公开。

| 候选 | 有意义的 Agent 任务 | 已知接口与关键条件 | 决策 |
| --- | --- | --- | --- |
| **Shapr3D** | 按尺寸创建零件，调整草图约束/孔距/厚度，批量生成规格，导出打印模型 | 找到明确的 API/MCP 需求；本次未找到覆盖原生建模的公开 API。已有第三方 MCP 主要走外部建模和 STEP 交换 | **下一案例**；先验证应用内操作入口 |
| **FL Studio** | 按音乐结构安排片段和音符、修改混音与自动化、交付可编辑工程和 WAV | 已有 MIDI Python 脚本及命令行渲染；标准免费试用不能重开保存的工程 | **备选**；先找官方脚本未覆盖的编排能力，并解决完整验收的授权条件 |
| **Affinity** | 批量商品图、图文排版、多尺寸营销素材 | 2026-09-15 已发布脚本和 Claude AI Connector | 暂不作为缺少控制接口的代表；先用官方机制 |
| **Live2D Cubism** | 修改角色参数、生成动作片段、批量导出角色资源 | 已有官方外部应用集成，可读写模型参数并记录动画关键帧 | 暂缓；需要先证明有重要能力超出官方接口 |
| **AutoCAD** | 图纸标准化、参数修改、批量出图 | 官方已有 Core Console | 暂缓；基础命令封装对本项目的逆向贡献较小 |
| **EdrawMax** | 编辑结构图、批量生成业务图与排版输出 | 找到署名 EdrawMax AI Team 的技能仓库，通过云端 API 生成图；尚未验证其与本机编辑器的控制关系 | 观察；不能仅凭产品闭源就断言缺少 Agent 接口 |

比较依据：[FL Studio MIDI 脚本](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/midi_scripting.htm)、[命令行导出](https://www.image-line.com/fl-studio-learning/fl-studio-online-manual/html/fformats_save_export.htm)、[标准试用限制](https://support.image-line.com/action/knowledgebase?ans=296)；[Affinity 发布说明](https://www.affinity.studio/blog/affinity-automation-scripting-claude)；[Live2D 外部集成](https://docs.live2d.com/en/cubism-editor-manual/external-application-integration/)；[AutoCAD Core Console](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/How-to-use-the-AutoCAD-Core-Console.html)；[EdrawMax 技能仓库](https://github.com/wondershare-boop/edrawmax-skills)。EdrawMax 的团队署名是仓库自身声明，本轮未独立核实发布者身份，也未调用其云端 API。

## 为什么是 Shapr3D

### 用户确实需要这类能力

官方社区的 API 讨论中，2026-08-16 有木工用户希望通过 AI 加快设计，2026-09-02 有用户明确提出 API/MCP 需求。可确认的工作人员 Peter_Gy 在 2024-01-19 表示当时没有公开 API；主题 JSON 将其列入 `shapr3d_staff`。2026-09-04 的相似答复来自未标明工作人员身份的用户，**不作为最新官方声明**。本轮检索未找到完整原生建模 API 文档，但这个检索结果不能证明所有版本和合作渠道都不存在接口。[讨论及日期](https://discourse.shapr3d.com/t/shapr3d-api/29917)、[身份元数据](https://discourse.shapr3d.com/t/29917.json)。

这支持选择“按需求修改真实 CAD 项目”作为任务，而不是只提供启动、截图、列窗口等命令。Shapr3D 本身有草图约束、实体建模和可编辑的特征历史，因而存在值得接入的业务对象；有这些功能不等于已找到它们的可调用入口。[Basic 功能](https://support.shapr3d.com/hc/en-us/articles/7872024839452-Shapr3D-Basic)、[特征历史](https://support.shapr3d.com/hc/en-us/articles/11567903089180-History)。

### 与已有 Shapr3D MCP 的区别可以明确验收

`Alfredoalv13/shapr3d-mcp` 使用 build123d/OpenCascade 建模，通过 STEP 与 Shapr3D 交换，并提供 macOS 启动和截图桥接。其说明明确指出参数化历史不能通过 STEP 往返保留，应用内草图和导出还需要用户或计算机操作。这是可用的外部建模思路，但没有验证我们要研究的原生业务调用。[项目说明](https://github.com/Alfredoalv13/shapr3d-mcp)。

reverse-cli 的新增价值应当是：Agent 在 Shapr3D 内创建和修改草图、特征、实体，保留原生项目状态，读回结果并由应用导出。若最终只实现外部生成 STEP 后导入，就应如实称为文件交换适配，不应算作原生建模逆向成功。

### 初始验证可以控制成本

Basic 免费版允许两个项目，提供草图、约束和实体建模，但只允许低精度 STL/3MF 导出。首轮可以验证一个小型模型及其参数修改；不要把 STEP、高精度网格或所有原生格式导出写成免费版已具备的条件。[Basic 方案](https://support.shapr3d.com/hc/en-us/articles/7872024839452-Shapr3D-Basic)、[格式与方案限制](https://support.shapr3d.com/hc/en-us/articles/7874523890076-Supported-file-types)。

## 首个演示与拟议 CLI

演示任务：**根据安装尺寸制作双孔固定板，再按反馈修改并导出。**

1. 新建毫米单位项目，创建 80 × 40 mm 草图，拉伸为 4 mm 厚实体。
2. 添加两个直径 5 mm 的贯穿孔，中心距 60 mm，并将其对称布置。
3. 读取尺寸、实体数量和特征参数，输出原生预览。
4. 接收修改要求：孔距变为 50 mm，板厚改为 6 mm；修改同一项目中的相关参数。
5. 原生保存、关闭重开；导出 STL/3MF，外部检查模型尺寸和拓扑。

这个小案例能展示“创建—观察—修改—保留编辑性—交付”的完整流程。首次只处理平面、矩形、圆与拉伸/切除；圆角、装配和复杂曲面后续扩展。官方 Extrude 支持新建实体与布尔操作，History 可修改特征参数，证明任务符合应用的功能范围。[Extrude](https://support.shapr3d.com/hc/en-us/articles/7874453786908-Extrude)、[History](https://support.shapr3d.com/hc/en-us/articles/11567903089180-History)。

以下是拟议命令组，**尚未实现，也不代表已发现对应函数**：

| 命令组 | 首轮范围 | 返回与验收重点 |
| --- | --- | --- |
| `project` | create/open/save/close/inspect | 项目 ID、单位、保存状态、草图/实体/特征对象 |
| `sketch` | 在指定平面创建矩形、圆和必要尺寸约束 | 稳定对象 ID、尺寸、闭合轮廓、约束状态 |
| `feature` | 拉伸、贯穿切除；按特征 ID 更新厚度/位置参数 | 操作记录、实体变化、读回参数 |
| `model` | 测量、查询与原生 undo/redo | 包围盒、体积、拓扑信息和撤销后的状态差异 |
| `output` | 原生视图预览、导出可用的 STL/3MF | 应用生成的画面/文件、导出结果、独立几何校验 |

原生测量和原生撤销是否可调用均待验证；不要提前承诺固定撤销层数。输出记录必须说明使用的方案、网格精度和单位，不能把低精度三角网格的圆孔尺寸当作精确曲面参数。

## 实现前的可行性关卡

沿用 [通用 SOP](../SOP.md)，但不假设 Shapr3D 与 CapCut 使用相同架构或可复制同一组偏移。

| 关卡 | 要得到的证据 | 不足以判定通过的结果 |
| --- | --- | --- |
| 0. 版本与环境 | 正常安装/运行，锁定程序版本与哈希，确认账号、Basic 能力、存储位置 | 下载成功或仅能启动 |
| 1. 只读原生状态 | 从实际程序恢复项目、草图或实体对象的读接口及线程/生命周期要求 | 只得到窗口标题、截图或字符串表 |
| 2. 最小业务修改 | 通过原生路径完成一个草图/拉伸或参数修改；读回结果，验证撤销 | 外部内核生成模型，或只改了内存数值却没有业务效果 |
| 3. 持久化与输出 | 应用保存、重开后同一模型仍可编辑，原生导出几何一致 | 一次截图看似正确，保存后丢失修改 |
| 4. Agent 任务 | 上述固定板流程无鼠标执行；回执、状态、预览、导出测量能对齐 | 单个函数调用成功或 JSON 返回 `ok` |

逆向时先检查发行包、模块、元数据、资源、已有内部命令或 IPC，再决定 REA 静态分析与运行时观测的切入点。重点是恢复应用的业务命令及对象生命周期；直接调用几何内核但不进入项目历史，可能产生不能保存或撤销的“孤立实体”，不能据此宣称控制了编辑器。

通过关卡 2 后再扩展五个命令组。若原生建模入口不可达、只能靠逐次鼠标操作，或无法保持项目一致性，应记录阻塞点并重评候选，而非继续堆叠没有业务效果的 CLI。

## 验收标准

- **业务状态**：一个有效实体；两个贯穿孔；修改前后尺寸与参数符合任务。记录单位与允许误差。
- **原生编辑性**：相关草图与特征可查询，修改进入应用状态；原生撤销/重做与保存重开分别验证，不假设历史栈跨会话保留。
- **输出**：原生预览可见尺寸变化；导出网格可解析、闭合，包围盒与板厚正确；孔距、体积与原生测量相互核对，误差按实际网格精度设定。
- **Agent 可恢复性**：提供对象 ID、操作后读回、错误分类；超时和结果未知时先检查状态，不盲目重放创建命令。
- **证据**：固定版本/哈希、完整 CLI 记录、前后状态、原生预览、导出哈希和独立几何检查。验收通过后才新增 `shapr3d-cli/` 的已支持索引。

## Windows 与 D 盘安排

本次从官方分发地址读取的 `.appinstaller` 清单标记版本 **26.180.11926.0**，指向 x64 `.msixbundle`，并列出 VCLibs、UI.Xaml 和 .NET Native 依赖。这只是分发清单证据，不能据此推断完整建模内核架构；后续以实际取得的包及哈希锁定目标。[官方安装清单](https://download.shapr3d.com/windows/Shapr3D.Package.appinstaller)。

官方要求 Windows 10 2004 或更新；Intel/AMD 平台需 AVX2，简单设计建议 16 GB 内存。安装前应核对当前设备和图形环境。[兼容设备](https://www.shapr3d.com/compatible-devices)。

计划将下载放到 `D:\Installers\Shapr3D`，研究项目放到 `D:\ChatGPT\reverse-cli\shapr3d-cli`，可配置缓存放到 `D:\Caches\Shapr3D`。MSIX 由 Windows 部署，**安装到 D 盘的可行方式和实际目录仍需核验**，不能承诺它像普通安装器一样使用 `D:\Apps\Shapr3D`；应用管理的用户状态也要实际检查。现有软件和数据不为此迁移或删除。

## 对 reverse-cli 的定位建议

CLI-Anything 当前也包含商业软件案例。因此公开说明应突出本项目从发行程序恢复业务入口、管理原生状态并验收真实产物的技术路线；不宜声称所有闭源软件都没有 API，或已经能自动为任意软件生成 CLI。[CLI-Anything 仓库](https://github.com/HKUDS/CLI-Anything)。

CapCut 已验证视频编辑。若 Shapr3D 通过上述验收，第二个案例将验证参数化几何、约束和特征历史，使通用 SOP 有跨领域证据。当前 [机器索引](../../registry.json) 仍只把 CapCut 标记为已验收。
