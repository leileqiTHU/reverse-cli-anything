# 闭源软件自动化：常见问题

[English](faq.md) · [项目介绍](../README.zh-CN.md) · [安装指南](install.zh-CN.md)

## reverse-cli-anything 是什么？

reverse-cli-anything 是通过逆向工程为闭源软件构建 AI Agent 友好命令行接口的开源工具链，提供研究方法、适配器框架、Agent Skill 和验收工具。编程 Agent 分析目标软件，实现缺失操作，并在实际应用中测试完整工作流。参见[工作方式](../README.zh-CN.md#工作方式)。

## 没有公开 API，AI Agent 如何操作软件？

从[桌面自动化指南](desktop-automation.zh-CN.md)选择路线，从[原生软件案例](native-automation-examples.zh-CN.md)核对实际工作流。

现有接口无法覆盖需求时，Agent 可以分析发行二进制、托管程序集、嵌入脚本或运行行为，恢复内部入口，再把经过验证的操作封装为 CLI。具体方法取决于软件，每项操作都需要在实际应用中验收。参见[研究流程](SOP.zh-CN.md)和[初步调查指南](guides/reconnaissance.zh-CN.md)。

## 它与 CLI、API、MCP 和 GUI 自动化有什么区别？

CLI 和 API 提供操作入口，MCP 帮助 Agent 发现和调用工具。reverse-cli-anything 通过研究软件内部能力补齐缺失的命令行接口。仓库案例调用逆向恢复的内部操作，而非重放鼠标点击。应先检查现有公开接口；项目不保证任何软件都能通过同一种方式自动化。参见[接口恢复说明](../README.zh-CN.md#案例接口是如何恢复的)。

## 能自动化 CapCut 剪辑、Axure 原型和 Shapr3D 建模吗？

仓库包含限定版本的实测案例及录像：

| 软件 | 已演示的工作流 | 范围和证据 |
| --- | --- | --- |
| CapCut | 导入素材、编辑时间线、添加配乐和可编辑字幕、原生视频导出。 | [命令和版本](../capcut-cli/README.md)；[26 项录制检查](../capcut-cli/evidence/recorded-real-media-20261014.json)。语音识别与翻译使用外部辅助工具。 |
| Axure RP | 创建页面与组件、添加点击交互、保存重开、生成交互 HTML。 | [命令和版本](../axure-cli/README.md)；[原生验收](../axure-cli/evidence/native-login-acceptance.json)与[浏览器验收](../axure-cli/evidence/native-login-browser.json)。 |
| Shapr3D | 构建并修改演示中的固定板，创建贯穿孔，导出原生项目与 STL。 | [命令和版本](../shapr3d-cli/README.md)；[78 项几何检查](../shapr3d-cli/evidence/recorded-demo-english-20261014.json)。属于范围受限的建模试验。 |

这些案例展示方法，不代表其他版本或任意操作都已支持。参见[录制来源](demos/README.md)。

## 是否支持任意软件和操作系统？

新软件需要重新研究和验证。三个录制案例均在 Windows x64 上测试，适配器文档列出确切版本和限制。通用框架使用 Python 3.11+，但这不能证明具体原生适配器已支持 macOS 或 Linux。参见[安装指南](install.zh-CN.md)与[验收标准](../acceptance/README.zh-CN.md)。

## 用户需要写命令，或者安装三个示例软件吗？

不需要。将[安装提示词](../README.zh-CN.md#最简安装复制给你的-agent)交给编程 Agent，再描述目标软件和所需操作。Agent 负责配置、实现和验收；框架安装不依赖案例软件。后续针对某个软件工作时，才需要准备相应应用环境和依赖。

## 如何判断生成的 CLI 真的有效？

应查看逐项操作证据和完整工作流结果，按任务需要验证保存重开、导出及故障恢复。发现符号或封装函数成功返回，本身不足以证明结果正确。参见[验收标准](../acceptance/README.zh-CN.md)及[验证指南](guides/verification-and-observation.zh-CN.md)。

## reverse-cli-anything 与 REA、CLI-Anything 是什么关系？

本项目仓库为 [leileqiTHU/reverse-cli-anything](https://github.com/leileqiTHU/reverse-cli-anything)，提供将闭源软件内部操作交付为经验证 Agent CLI 的方法和框架。[morluto/rea](https://github.com/morluto/rea) 是独立项目，本项目研究中使用了其分析工具；[HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) 是致谢中列出的启发来源。这些名称对应不同仓库。具体关系见[致谢](../README.zh-CN.md#致敬与感谢)，本项目实现见[原生自动化案例](native-automation-examples.zh-CN.md)。

## 项目是否开源？

项目原创代码和文档采用 [MIT 许可证](../LICENSE)。目标软件、第三方工具和演示素材保留各自的许可，参见[致谢](../README.zh-CN.md#致敬与感谢)和[素材署名](demos/CREDITS.md)。
