# 适配器契约

[English](adapter-contract.md) · [运行层](runtime.zh-CN.md) · [SOP](SOP.zh-CN.md)

适配器是独立注册的目录，通过清单选择原生实现，核心中不增加软件名称分支。先用 `init` 生成骨架，再实现目标能力并注册清单。

先按[工程手册](HARNESS.zh-CN.md)恢复契约背后的原生操作。维护工具目录后，[生成调用说明](development-tools.zh-CN.md#生成目标说明)，再补充目标专属的生命周期语义；生成文档不代表已验证原生兼容性。

## 最小清单

```json
{
  "schemaVersion": 1,
  "id": "my-app",
  "name": "My application",
  "entrypoint": "cli.py",
  "toolSchema": "tools.json",
  "skill": "SKILL.md",
  "acceptance": "acceptance.json",
  "testedBuilds": []
}
```

路径相对于清单目录，或显式 `root` 指定的根目录，引用必须位于声明的根目录内。ID 使用小写字母、数字、连字符，以字母开头，排除 Windows 保留名称。本机注册保存清单路径，拒绝不同清单占用同一个 ID。清单及 Hook 属于受信任的可执行配置，注册第三方适配器前应检查其代码。

字段见[清单 schema](../schemas/adapter.schema.json)。`entrypoint` 目前是 Python 程序，可以再启动其他语言实现；框架要求 Python，不要求目标采用特定技术。`regression` 为可选参数数组，第一项是相对声明根目录的 Python 验收脚本；显式运行 `tools/regress-native.py <adapter> ...` 时才调用。

## 默认传输与工具目录

```text
python cli.py <tool-name> --input <JSON-object>
```

工具目录包含 `schemaVersion`、`adapter` 和 `tools`。每个工具声明唯一 `name`、`inputSchema`、`outputSchema`、布尔 `mutates` 和真实 `provenance`。输出 schema 引用相对于目录文件。会改变目标或会话状态的操作用 `mutates: true`；读写分类决定公共入口是否加锁。

标准输出仅写一个 JSON 响应，诊断写标准错误。成功完成用 `ok: true` 和退出码 0。失败应记录已知结果：`not-submitted`、`partially-applied`，或原生结果仍未知的错误。写入报错本身不能证明回滚。

输入在提交前校验，原生语义、版本固定和真实完成判断由适配器负责。工具 schema 和目标 Skill 应明确单位、状态前提和对象身份。

## 可选兼容 Hook

清单可声明 `runtime: "adapter_runtime.py"`，只需提供用得上的函数：

| Hook | 返回内容 |
| --- | --- |
| `preflight(argv)` | 校验旧命令后返回 `(tool_name, parsed_arguments)` |
| `command(tool, arguments)` | 已校验结构化输入对应的旧命令参数 |
| `tools()` | 生成的工具目录，用于与已保存 schema 比较 |
| `app_path()`、`native_tools()`、`ffmpeg()` | 目标默认路径或依赖路径 |
| `child_env()` | 目标环境变量 |
| `doctor_checks(pid, inventory)` | 只读诊断检查项 |
| `prepare(argv, operation_id)` | 关联原生请求，不执行操作 |
| `successful(tool, response, exit_code)` | 识别既有成功响应约定 |
| `evidence(response)` | 原生证据路径描述 |

导入、发现、参数校验和 `doctor` 阶段不能启动或修改目标；仅读取工具目录不会导入 Hook。Hook 是受信任代码，这属于开发契约而非沙箱隔离。

核心不知道具体 ABI、原生命令名、对象类型或进程名，这些均由适配器维护。新适配器优先采用默认传输，确有兼容需求时再用 Hook。

## 证据与范围

逐工具覆盖见 [acceptance.schema.json](../schemas/acceptance.schema.json)，原生流程报告见 [acceptance-report.schema.json](../schemas/acceptance-report.schema.json)。脚手架初始为 `not-run`，并返回 `nativeImplemented: false`；注册不会改变这些结论。

实现后运行 `tools/check-contracts.py --adapter <id>`。软件测试和产物验证器属于适配器，明确记录实测版本及工作流，遵循[通用验收说明](../acceptance/README.zh-CN.md)。
