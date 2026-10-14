# 研究记录模板

[English](README.md) · [工程手册](../../docs/HARNESS.zh-CN.md) · [助手](../../docs/development-tools.zh-CN.md)

按当前需要复制记录。unknown 表示刻意保留的未知，不能默认已验证；工作记录不替代工具契约或验收报告。

在 `task.execution` 记录执行模型、状态寿命与就绪条件，在 `operations` 记录各项操作属于观察、计算还是修改。目标没有事务、回调等机制时，相应字段注明不适用及原因。交付记录保存选定框架、配置和研究目录的位置，使后续 Agent 无须会话历史即可继续工作。

| 文件 | 用途 |
| --- | --- |
| [task.json](task.json) | 目标、约束、身份、流程与交接 |
| [operations.json](operations.json) | 操作集合、依赖、状态和证据 |
| [entrypoint.json](entrypoint.json) | 候选绑定、ABI、寿命及业务语义 |
| [experiment.json](experiment.json) | 假设、基线、调用、观察与决策 |
| [build-map.json](build-map.json) | 候选/支持构建、模块及绑定证据 |
| [observation.json](observation.json) | 关联状态/预览、来源、新鲜度与恢复 |
| [delivery.json](delivery.json) | 交付、已验证/未验证范围及历史证据 |

接口卡和实验注明所属操作；状态助手检查相对引用和带哈希验收证据。转储、完整反编译及私有程序放入忽略目录，公开有限观察与过程，不分发私有产物。

实验 observed 时，持久化和输出可能仍未验证；支持的构建只覆盖已证明的操作及生命周期。
