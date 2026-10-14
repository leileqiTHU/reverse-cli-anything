# Axure RP 11.0.0.4150 入口与证据

## 目标身份

- Windows x64，`AxureRP11.dll`，16,314,368 字节。
- SHA-256：`dae5748f6be3e69c063ef117bab0b400586d94adf119f5a9ba260df59dc4e4a7`。
- 官方主程序签名：Axure Software Solutions, Inc，验证为 Valid。
- 安装包：官方 `https://axure.cachefly.net/AxureRP-Setup.zip`，SHA-256 `f9f374412306629dadb78cbd5db643353df83fb7c2d7a7e987687865b876dfe0`。
- 随包运行时配置：.NET 10.0.10、WindowsDesktop、ASP.NET Core。

## REA 使用情况与明确边界

使用 `reverse-engineer-anything` 技能的托管程序集分析路线，调用 REA `inspect_managed_artifact`。保留完整[REA 原始证据](evidence/rea-artifact.json)，Evidence ID：

```text
ev_e29c588cceaa189a8c3d87f9dd7a5e28e7bd8a65bf8773ddb6a485e6f18273e8
```

REA 观察到 PE32+、CLI 头、ReadyToRun 签名及程序集哈希。完整元数据表示超过该解析器的 64 MiB 上限，返回 `coverage=partial`；不能把它描述为 REA 已完整反编译了 Axure。

后续用 ILSpy `ICSharpCode.Decompiler 9.1.0.7988` 对同一哈希的发行程序集做定向反编译，先从未混淆的官方 MCP 文档服务追踪活动客户端，再追踪编辑事务、保存和生成器。原始反编译材料仅保存在忽略的 `.runtime/`。可复用的入口签名与 token 记录在 [保存/导出证据](evidence/static-save-export.json)和[文字事务 token](evidence/static-text-tokens.json)中。

## 已验证的调用链

| 能力 | 入口和语义 |
| --- | --- |
| 活动客户端 | `W30.M3m.vRo()` |
| 当前文件 / 编辑器 | `client.XIXf()` / `client.Editor` |
| 控件稳定 ID | `widget.Mtn3()` 返回 GUID |
| 文本构造 | `tSmX.rSma.lSmU(text, widget.AttributedString.VIvs())`，与原生纯文本编辑采用相同样式来源 |
| 原生文本编辑对象 | `djCv.ljCy.HjCQ(widget, replacement)` |
| 原生事务提交 | `editor.yFZi(edit, false)` → `Workspace.QIml` → `Client.CImW` |
| 撤销 / 重做 | `client.Undo(client.Workspace)` / `Redo(...)`，避免焦点控件截获 |
| 测试控件创建 | `VectorShape(document, Shape.Paragraph, ...)` → `editor.oFYd(widget, true)` |
| 保存前提交 | `client.CommitOuterObject(true)`，与原生保存菜单一致 |
| 保存 / 另存为 | `file.Save()` / `file.INR4(path, out error)` |
| 新建空白文档 | `client.vImH(DesignDocumentType.Standard, false)` |
| 打开 / 关闭 | `client.OpenDocument(path, false)` / `client.CloseClient()` |
| 可写 / 脏状态 | `client.LImL()` / `client.TIX7()`，只读取状态做保护 |
| 原生 HTML | `new LSr8.GSrn(file.DNET())` 配置 → `new OJF5.cJFt(config).Generate(file, null, null, null)` |
| 输出目录 / 全部页面 | `config.HSFG(path)`、`ESFS(false)`、`jSFg(true)` |
| 生成成功 | `result.zJFb()`，并独立检查文件与浏览器渲染 |
| 缓存偏好 | 原生偏好存储的 `AppTemporaryPath` 键；保存后重启生效 |
| 页面创建 | `ESDL.lSDD(AddNode)` 与 `RenameNode` → `BS11.pS1H` 组合事务 → `Workspace.QIml`；精确命名、一次撤销 |
| 页面列表 / 切换 | 内置 `SitemapMapper.MapSitemap(client.nIXw())` / `client.TImN(pageId, Guid.Empty, false)` |
| Pages 面板通知 | `Sitemap.UNrz(EventArgs.Empty)` 通知原生订阅者重建侧栏；创建及撤销/重做后调用 |
| 按钮 / 输入框 | `Axure.DocumentModel.Objects.Button(doc)` / `TextBox(doc)`，再走原生 add-object 事务 |
| 位置尺寸 | `QSc5.kSct` 快照 → `FSW9` 连接器更新作用域 → `YJ0S(Rect, EditAllAdaptive)` → `YSWI` → `Workspace.zImy` |
| 点击事件树 | `gJuG(doc, widget)` → `lJu3(OnClick)` → `TNFt` 插入 `IxCase` 和动作；自动维护所属交互表 |
| 交互提交 | `uSgI.ESg1(widget, oldMap, newMap, emptyIdMap, null, false, ...)` → `editor.yFZi`，进入原生历史 |
| 文本条件 | `BinaryExpr(Equals/And/Or)`、`FCall(GetWidgetText)`、`DiagramObjectPathLiteral`、`StringLiteral` |
| 设置文字动作 | `IxActionSetFunction` + `SetWidgetFormText` / `SetWidgetRichText`，通过 `QNyH` 安装表达式 |
| 跳页动作 | `IxLinkWindowAction(LinkType.Current)`，`TargetType.Page` 和稳定 `TargetPagePackageId` |

类型名和 token 均仅绑定当前构建。CLI 在启动和应用进程内双重验证程序集哈希。

## 执行与验收

自编写的 startup hook 通过 .NET 支持的进程启动入口装载。桥接在 Axure 的 WinForms UI 线程上调用上述业务函数。正式桥接没有任意反射调用或代码执行接口，使用当前用户专属命名管道，保存请求结果；开发期反射探针位于 `.runtime/`，不参与正式启动。

真实验收验证了 A → B → Undo A → Redo B、原生保存、切换文件后重开、进程退出后冷启动重开、同一 GUID 控件继续可编辑。HTML 由 Axure 原生生成器输出，另由 Chrome 渲染检查。详细结果见[完整命令记录](evidence/native-text-acceptance.json)和[浏览器检查](evidence/native-html-render.json)。

扩展证据：[页面事务](evidence/page-native-entrypoints.json)、[侧栏通知 token](evidence/page-refresh-entrypoints.json)、[控件及几何 token](evidence/widget-native-entrypoints.json)、[交互树](evidence/interaction-tree-native-entrypoints.json)、[表达式 token](evidence/interaction-expression-entrypoints.json)。本轮复用相同程序集的既有 REA 身份证据，新增入口使用定向 ILSpy 与发行包原生 JavaScript 运行时辅助分析，没有把 ILSpy 结果冒称为 REA 完整反编译输出。

[登录表单验收](evidence/native-login-acceptance.json)验证稳定页面/控件 ID、原生条件树、几何、事务撤销及保存/冷启动持久化。[浏览器验收](evidence/native-login-browser.json)执行 Axure 导出的 JavaScript，使用空值、错误值、正确演示凭据、清空和返回分支，不注入实现这些业务行为的自定义 JavaScript。[过程录制](evidence/login-recording.json)保留真实原生窗口与导出页录制、章节和完整解码证据。

静态入口在运行验收前仅为候选。动态面板、其他事件、任意已有交互替换和复杂自适应布局仍未验收。
