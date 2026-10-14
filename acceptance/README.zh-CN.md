# 通用验收标准

[English](README.md) · [SOP](../docs/SOP.zh-CN.md) · [适配器契约](../docs/adapter-contract.zh-CN.md)

框架安装与目标验收分开。安装核心不需要真实应用、特定文档类型或任何展示工作流。

## 核心验收

执行 `tools/setup.py`、`tools/run-tests.py core` 和 `tools/smoke-portable.py`，检查配置、空注册表、新适配器注册、参数校验、调用、回执、并发和恢复。隔离冒烟副本不包含任何案例代码或原生依赖，合成适配器仅证明基础设施行为。

开发时通过 `tools/check-contracts.py` 校验 schema。零适配器时检查通用 schema，以零工具通过。指定 `--adapter <id>` 检查该目标清单、工具契约和覆盖；`--examples` 才额外纳入可选展示案例。

## 原生流程验收

根据用户任务和真实软件选择断言。所有报告需要交代以下层次，不限定具体导出格式、对象模型或 UI 技术。

| 层次 | 证据要求 |
| --- | --- |
| `request` | 正确目标和请求身份、输入、可关联的完成信号。 |
| `state` | 正确的返回数据、计算结果或原生状态，并按任务检查无关内容保留。 |
| `persistence` | 任务要求的保存重载行为，区分同会话与冷启动。 |
| `artifact` | 任务所需原生产物，以及独立的实际内容检查。 |
| `recovery` | 相关拒绝、部分完成、不确定结果及支持的恢复行为。 |

每条断言标记为 `passed`、`failed`、`not-run` 或 `not-applicable`。通过项必须有证据路径及 SHA-256；不适用必须说明原因，请求与状态不可省略。未执行或失败项阻止验收通过。具体原生检查和任务断言由适配器实现。

`init` 生成尚未执行的 `acceptance-plan.json`。实际运行后补齐目标版本、任务、断言及证据，按 [acceptance-report.schema.json](../schemas/acceptance-report.schema.json) 保存报告。

```powershell
python -B reverse-cli-anything.py acceptance "<report.json>"
python -B tools/regress-native.py my-app <适配器专属参数>
```

第一条命令只检查报告完整性和证据哈希，不重新执行任务、不识别任意产物内容，也不独立证明调用方断言。第二条委托适配器声明的验收脚本，需要显式目标及其前提条件；不存在适用于全部软件的原生测试动作序列。

## 逐工具覆盖

[acceptance.schema.json](../schemas/acceptance.schema.json) 分别记录每条命令。`current-native` 表示在限定原生流程中执行过，`historical-workflow` 引用旧证据，`not-run` 不作执行声明；均不代表覆盖全部参数组合。发现和脚手架命令不构成原生编辑能力证明。

保留失败尝试及成功恢复，并标明版本、运行环境和范围。软件专属样本、验证器和媒体属于适配器或可选案例。

[验证指南](../docs/guides/verification-and-observation.zh-CN.md)说明独立观察、内容检查与证据时效。每项结果记录目标构建及执行范围。
