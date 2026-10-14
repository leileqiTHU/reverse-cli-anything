# 公共运行层

[English](runtime.md) · [安装](install.zh-CN.md) · [适配器契约](adapter-contract.zh-CN.md) · [验收](../acceptance/README.zh-CN.md)

研究记录、文件指纹、目录生成说明及 Skill 打包由独立的[开发助手](development-tools.zh-CN.md)提供，这些文件操作不向目标软件派发命令。

运行层负责发现已注册目标、校验 JSON、调用入口和保存操作证据。初始注册表为空，核心运行不需要任何展示软件。

## 命令

这些是 Agent 开发或使用适配器时执行的内部工具。用户通过对话提出软件和操作需求，由 Agent 按需完成配置、脚手架、注册与调用步骤。

```powershell
python -B reverse-cli-anything.py doctor
python -B reverse-cli-anything.py list
python -B reverse-cli-anything.py init my-app --output ../my-app-cli
python -B reverse-cli-anything.py register ../my-app-cli/adapter.json
python -B reverse-cli-anything.py tools my-app
python -B reverse-cli-anything.py call my-app status --args '{}' --operation-id inspect-001
python -B reverse-cli-anything.py operation get inspect-001
```

脚手架 status 只报告基础设施状态，完成原生实现和验收后才能宣称支持软件。转发已有参数用 `run <adapter> -- <arguments>`；检查适配器环境用 `doctor <adapter>`，不带目标的 `doctor` 仅检查核心。

`list --examples` 额外读取可选展示注册表。旧案例命令仍可通过显式指定 ID 调用；核心命令不依赖展示注册表或对应软件文件。

## 配置

优先级为环境变量、被忽略的 `reverse-cli.local.json`、默认值。`REVERSE_CLI_CONFIG` 可指定其他配置文件。

持久配置使用绝对路径，确保从其他工作目录也能使用同一安装。在选定框架中运行 `tools/setup.py --configure`，创建缺失的配置并将实际上下文记录到 `<stateDir>/installation.json`，已有配置不会覆盖。显式指定 `REVERSE_CLI_CONFIG` 时，后续进程仍须提供该变量；也可使用默认本机配置文件。Skill 资源包和原仓库各有自己的配置与注册表。

| 字段 | 环境变量 | 含义 |
| --- | --- | --- |
| `python` | `REVERSE_CLI_PYTHON` | 解释器；直接 Python 调用默认使用自身，PowerShell 无配置时使用 PATH |
| `registry` | `REVERSE_CLI_REGISTRY` | 基础注册表，默认为仓库 registry.json |
| `cacheDir` | `REVERSE_CLI_CACHE_DIR` | 有 D 盘时默认 D:/Caches/reverse-cli-anything，否则仓库 .runtime/cache |
| `stateDir` | `REVERSE_CLI_STATE_DIR` | 仓库 .reverse-cli，保存操作、锁和本机注册 |
| `outputDir` | `REVERSE_CLI_OUTPUT_DIR` | 仓库 outputs/reverse-cli-anything |
| `nativeTools` | `REVERSE_CLI_NATIVE_TOOLS` | 可选依赖目录，仅供选中的适配器使用 |
| `ffmpeg` | `REVERSE_CLI_FFMPEG` | 可选媒体工具，核心不需要 |

目标配置位于 `adapters.<id>`，可提供 `appPath` 和 `nativeTools`。其他旧设置由对应适配器 Hook 解释。[配置示例](../reverse-cli.config.example.json)。读取配置不会迁移现有软件或数据。

子进程使用配置的临时目录和可选适配器环境。软件依赖由选中的适配器安装；核心仅依赖标准库，开发 schema 检查另有可选依赖。

## 回执与恢复

`run` 和 `call` 返回公共结果：`ok`、`operationId`、`state`、原始 `response`、回执路径及 `replayed`；直接调用适配器保留原接口。

| 状态 | 含义 |
| --- | --- |
| `not-submitted` | 参数、锁或已知原生拒绝阻止本次请求应用 |
| `running` | 已跨过进程提交边界，尚未记录完成 |
| `completed` | 已观察到适配器终态，还需检查 ok 和独立证据 |
| `partially-applied` | 适配器明确报告只完成了部分修改 |
| `unknown` | 现有证据不足以确认原生最终结果 |

操作 ID 绑定参数及受支持的文件输入哈希。复用只读取历史，返回 `freshStateVerified: false`，不会再次提交；更换输入会被拒绝。这是防重复执行机制，不是通用原生事务。

同一状态目录内按适配器串行公共写入。读取可以绕过公共写锁，但目标软件仍可能阻塞读取；直接调用和其他状态目录不受此锁约束。

超时保留子进程和锁；控制进程退出后，残留 running 状态转为 unknown。不要自动重试写入，可使用：

```powershell
python -B reverse-cli-anything.py operation list
python -B reverse-cli-anything.py operation get <operation-id>
python -B reverse-cli-anything.py operation refresh <operation-id>
python -B reverse-cli-anything.py operation resolve <operation-id> --evidence <recovery.json>
```

Refresh 仅观察迟到的成功响应或精确匹配的请求结果文件，不重新执行。显式恢复要求控制与工作进程已退出，证据包含同一操作 ID、`nativeWorkFinished: true`、终态 `state`、布尔 `ok`、非空且通过的具名 `checks` 与带哈希的 `evidenceFiles`。保留原失败响应，并记录调用方核验；哈希证明文件完整性，不证明调用方原生断言本身为真。

公共回执的验证标记初始为 false。原生状态、持久化与产物事实需要目标专属检查；仅有核心回执不能证明有用的原生流程已经验收。
