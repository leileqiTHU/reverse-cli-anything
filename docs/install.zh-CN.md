# 安装 reverse-cli-anything

[English](install.md) · [运行层](runtime.zh-CN.md) · [通用 Skill](../skills/reverse-cli-anything/SKILL.md)

本文供负责安装的 Agent 执行。用户发送 [README 中的安装提示词](../README.zh-CN.md#最简安装复制给你的-agent)，Agent 完成下面的步骤并报告结果，用户无须手动运行这些命令。

安装阶段只准备框架，不选择、安装、激活、分析或修改任何目标软件。核心检查不需要展示案例、案例依赖、Frida 或反编译引擎。

## 选择执行目录

1. 从用户提供的地址克隆仓库，或使用指定的本地目录，解析绝对路径并遵循存储配置。
2. 找到 Python 3.11 及以上版本，记录解释器绝对路径。优先复用，缺少时再安装。框架及核心检查使用标准库；下列命令中的 `python` 指已核实的解释器，不能假定 PATH 中一定存在。
3. 读取[通用 Skill](../skills/reverse-cli-anything/SKILL.md)，选择一种安装模式：

| 模式 | 安装动作 | 后续统一使用的执行目录 |
| --- | --- | --- |
| 安装 Skill | 确认宿主支持的 Skill 目录，从仓库执行 `python -B tools/install-skill.py --destination "<新的Skill目录>"`。 | 安装器返回的绝对 `framework` 路径，位于已安装 Skill 内。 |
| 使用仓库 | 保留源码目录，向 Agent 提供其中的 Skill 路径。 | 仓库绝对路径。 |

已安装 Skill 包含独立的框架副本。注册适配器前先配置这份副本，源码目录的配置和注册状态不会自动复制。一个流程持续使用同一目录。[资源包说明](development-tools.zh-CN.md#安装完整通用-skill)包含升级与资源检查方法。

## 配置并检查选定目录

进入选定执行目录，先通过[配置](runtime.zh-CN.md#配置)确定存储位置。持久配置使用绝对路径。`--configure` 按生效的解释器与目录生成缺失的本机配置，保留已有配置文件。环境变量优先级更高，只保留有意设置的覆盖。

```powershell
python -B tools/setup.py --configure
python -B reverse-cli-anything.py doctor
python -B reverse-cli-anything.py list
python -B tools/run-tests.py core
python -B tools/smoke-portable.py
```

Setup 检查必需的方法文档、脚本、模板及其本地引用。成功配置后，在状态目录保存 `installation.json`，记录执行目录、解释器、设置、注册表和资源位置。`python -B tools/setup.py` 只检查已有安装，不创建设置。

冒烟检查安装完整临时 Skill 包，在不继承框架环境变量的新进程中验证研究记录、合成适配器注册与调用、文档生成，不操作目标软件。报告和临时文件使用配置的输出及缓存目录。

另开不带临时安装变量的终端或进程，在选定目录重新执行 setup 和 `list`，确认仍使用相同解释器和状态目录。指定目标之前，适配器列表为空是正常状态。

## 衔接后续对话

安装 Skill 时，按宿主支持的方式重新加载，确认能够读取已安装 `SKILL.md` 及一份引用资源。无法测试宿主发现时，将发现状态标为待确认，并提供 Skill 绝对路径供直接读取。仓库模式也需要在新对话中提供该路径。

报告执行目录、Skill 路径、安装记录位置、检查及发现状态。安装记录随框架保留，后续目标任务沿用其中的配置和注册表。所选目录中的资源及解释器可用，表示框架安装完成；Skill 自动发现另行确认。

开发时如需完整 JSON Schema 检查，在开发环境安装 [requirements-dev.txt](../requirements-dev.txt)，执行 `python -B tools/check-contracts.py`。正常运行核心无需这些开发依赖。

安装完成后，等待用户指定软件和操作。按 [SOP](SOP.zh-CN.md#开始目标任务)确认目标访问、预期结果和现有接口覆盖，再选择研究工具或创建适配器。[研究工具说明](../tools/rea/README.zh-CN.md)用于确认分析器就绪；目标依赖、平台、构建与激活要求由适配器记录。

规范入口为 `reverse-cli-anything.py` 和 `reverse-cli-anything.ps1`。原来的 `reverse-cli.py` / `.ps1`、`REVERSE_CLI_*` 配置名称和本机状态格式继续兼容，不迁移已有安装。
