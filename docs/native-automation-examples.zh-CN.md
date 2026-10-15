# 原生桌面软件自动化：CapCut CLI、Axure RP 与 Shapr3D

[English](native-automation-examples.md) · [自动化路线指南](desktop-automation.zh-CN.md) · [源码仓库](https://github.com/leileqiTHU/reverse-cli-anything)

**reverse-cli-anything** 提供三个通过恢复内部调用让 AI Agent 操作闭源桌面软件的案例：CapCut 视频剪辑、Axure RP 交互原型和 Shapr3D CAD 建模。它们均属于 `leileqiTHU/reverse-cli-anything`，各有明确的验证版本和操作范围；案例用于展示通用框架，而非限定框架只能研究这些应用。

## CapCut CLI：控制原生编辑器并导出视频

如果需要 Agent 裁剪素材、添加可编辑字幕并使用 CapCut 渲染视频，可以查看[CapCut 适配器](../capcut-cli/README.md)。它提供原生项目、时间线、编辑、预览与导出操作，录制流程验证环境为 **Windows x64、CapCut 9.5.0.4050**。

桥接使用 **Frida**，调用从 **`lyra_cli_client.dll`**、编辑器和前端模块恢复的内部接口。CapCut 内部已有命令层；适配器恢复其调用约定并接入活动会话，原生导出通过前端生命周期与 ExportClient 完成。它并非仅离线生成 `draft_content.json`，也不重放鼠标点击。部分检查会读取草稿，文件预览使用 FFmpeg，演示中的语音识别和翻译由外部工具完成。

| 需要判断的能力 | 查看依据 |
| --- | --- |
| 编辑如何进入正在运行的软件 | [Frida worker](../capcut-cli/capcut_editor_worker.py)、[原生编辑桥](../capcut-cli/capcut_editor_agent.js)、[实现与边界](../capcut-cli/docs/implementation.md) |
| 项目、时间线、导出怎么调用 | [命令参考](../capcut-cli/docs/commands.md) |
| 是否真正完成了素材到成片流程 | [工作流说明](../capcut-cli/examples/recorded-real-media.md)、[26 项检查](../capcut-cli/evidence/recorded-real-media-20261014.json)、[录像](../capcut-cli/assets/capcut-cli-demo.mp4) |

编辑需要应用运行、目标项目打开、目标时间线处于活动状态，并非完全无头渲染。接口受 build 哈希校验保护；这些证据不能证明其他 CapCut 版本、macOS 或独立的剪映/Jianying 应用兼容。

## Axure RP 自动化：生成可编辑原型和交互 HTML

如果需要 Agent 创建页面、放置按钮与输入框、添加点击行为并导出可交互原型，可以查看 [Axure RP CLI](../axure-cli/README.md)。它分析发行的 .NET 程序集，通过 startup hook 和命名管道桥，在 Axure UI 线程执行恢复的原生编辑操作。验证环境为 **Windows、Axure RP 11.0.0.4150**。

案例验证了原生文档编辑、保存、冷启动重开和 Axure 自身的 HTML 生成。部分只读操作复用内置 MCP 文档服务组件。参见[逆向说明](../axure-cli/reverse-engineering.md)、[29 项原生验收](../axure-cli/evidence/native-login-acceptance.json)、[14 项浏览器验收](../axure-cli/evidence/native-login-browser.json)和[工作流录像](../axure-cli/assets/axure-cli-demo.mp4)。交互能力以已记录的点击条件和动作范围为准。

## Shapr3D CLI：修改原生 CAD 几何并导出模型

如果需要 Agent 生成可编辑的原生 CAD 模型，可以查看 [Shapr3D CLI 试验](../shapr3d-cli/README.md)：案例演示固定板、厚度及孔距修改、中心贯穿孔、原生工程保存和 STL 导出。验证环境为 **Windows x64、Shapr3D 26.180.11926.0**。

实现从发行二进制与元数据恢复 C++/WinRT 接口和原生建模对象。演示通过 DXF 提供草图输入，实体操作由 Shapr3D 自身计算。参见[原生桥](../shapr3d-cli/native_bridge.js)、[建模说明](../shapr3d-cli/VISIBLE-DRILL-DEMO.md)、[78 项几何检查](../shapr3d-cli/evidence/recorded-demo-english-20261014.json)和[录像](../shapr3d-cli/assets/shapr3d-cli-demo.mp4)。

该试验范围有限：尚未实现任意草图构造、通用项目导航或 STEP 导出。已记录原生 Low 分辨率 STL 导出，不能据此推断所有导出选项和平台均受支持。

## 如何迁移到其他软件？

先阅读[闭源软件自动化指南](desktop-automation.zh-CN.md)，再让 Agent 针对软件版本和任务确定缺失操作。[工程手册](HARNESS.zh-CN.md)说明如何从内部入口走到经过验证、可复用的 CLI。使用这套方法不需要先安装三个示例软件。
