# 仅处理文件的开发助手

[English](development-tools.md) · [工程手册](HARNESS.zh-CN.md) · [模板](../templates/research/README.zh-CN.md)

这些内部工具只使用 Python 标准库，不启动、附加或修改目标软件。命令从框架根目录运行，遵循用户解释器及存储偏好。

## 研究记录与文件身份

```powershell
python -B tools/research.py init my-app --application "<指定的软件>" --goal "<请求的结果>" --operation "<操作ID>" --output ../my-app-research
python -B tools/research.py status ../my-app-research
python -B tools/research.py fingerprint "<module-path>" --output ../my-app-research/evidence/build.json
```

初始化创建全新目录，包含任务、操作和构建映射，以及空的 entrypoints、experiments、evidence 子目录，不生成原生接入。真正需要接口卡或实验时再复制相应模板。

将占位内容替换为用户目标和拆解出的操作 ID；更多操作重复传入 `--operation`。选择原生检查前，在 `task.json` 记录执行方式和状态寿命，在 `operations.json` 记录操作效果。

随着研究填写操作描述、公开接口缺口、后置条件和依赖。接口卡/实验使用相对研究目录路径；验收证据格式为 `{"path":"evidence/result.json","sha256":"<64 位小写十六进制>"}`，也支持显式绝对证据路径。

状态助手检查 ID 唯一性、状态、依赖环、记录归属与证据哈希。受阻项需要原因，verified 声明需要带哈希证据。它只报告**声明的进度与完整性**，不证明原生正确，也不自动提升状态。

指纹助手流式读取指定文件，检查读取期间大小/mtime 是否变化，记录解析路径、大小和 SHA-256；不发现二进制、不推断架构、不证明兼容性。已有输出不覆盖。

## 生成目标说明

```powershell
python -B tools/generate-docs.py ../my-app-cli/adapter.json --output ../my-app-cli/agent-docs
```

输出必须是**适配器根目录内的新子目录**，使适配器整体移动后相对引用仍有效。助手只读已保存数据，不导入 hook、不执行命令。生成：

- `COMMANDS.md`：准确工具、schema、来源及声明的覆盖。
- `SKILL.md`：指向契约和既有原生说明。
- `sources.json`：相对输出目录的源路径及哈希，用于检查说明是否过期。

保留手写文件，不猜未知必填参数或编造成功示例，schema 引用仍按原工具目录解析。审阅单位、就绪、异步和恢复语义后，再有意更新维护中的 Skill 或清单。生成不会注册任何内容，也不重新验证历史证据。

## 安装完整通用 Skill

```powershell
python -B tools/install-skill.py --destination "<skill-directory>/reverse-cli-anything"
```

先确认宿主支持的 Skill 目录及重新加载方式，再替换 `<skill-directory>`。工作数据和缓存采用已配置的存储位置；复制到任意目录不代表 Skill 会被发现。

安装器要求目标不存在，在父目录暂存后重命名。按清单复制通用代码、契约、指南、模板和助手，将外层 Skill 链接改为包内 `framework/`，在 `bundle.json` 记录哈希。内部框架保留可再分发的源码形式 Skill，注册表为空。

资源包不包含案例、私有程序、本机设置、凭据、研究缓存或分析引擎；不修改宿主配置，也不确认已经被发现。失败时保留暂存目录；升级先生成新包，审阅后按宿主正常机制替换。

助手可脱离原仓库运行。进入安装器返回的 `framework` 目录，按[安装说明](install.zh-CN.md)配置并验证，其中包含 `tools/setup.py --configure`。后续持续使用该执行目录和安装记录。目标清单显式注册，其他仓库的配置与注册状态不会迁移。

## 助手验证

`tests_development/` 检查合成研究文件、不加载 hook、拒绝覆盖、依赖环、证据篡改、安装资源缺失及安装配置持久化，不调用应用适配器或原生工作流。只在改动助手时运行，并与原生验收分别报告。

```powershell
python -B -m unittest discover -s tests_development -v
```

检查样本保留在配置的缓存目录中，便于复核。此命令只运行助手测试，不执行已有 CLI 回归套件。
