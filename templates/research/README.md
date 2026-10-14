# Research record templates

[中文](README.zh-CN.md) · [Manual](../../docs/HARNESS.md) · [Helpers](../../docs/development-tools.md)

Copy only the records needed now. Unknown fields are deliberate, not implicitly verified. These working records do not replace tool contracts or acceptance reports.

Record the execution model, state lifetime and readiness in `task.execution`, and each operation's observation/computation/mutation effect in `operations`. Mark target-specific fields such as transactions or callbacks as not applicable with a reason when absent. Delivery records retain the selected framework, configuration and research locations so a later agent can continue without session history.

| File | Use |
| --- | --- |
| [task.json](task.json) | Goal, constraints, target identity, workflow and handoff |
| [operations.json](operations.json) | Requested operations, dependencies, status and evidence |
| [entrypoint.json](entrypoint.json) | Candidate binding, ABI, lifetime and business semantics |
| [experiment.json](experiment.json) | Hypothesis, baseline, call, observations and decision |
| [build-map.json](build-map.json) | Candidate/supported builds, module and binding evidence |
| [observation.json](observation.json) | Correlated state/preview, source, freshness and restoration |
| [delivery.json](delivery.json) | Tool handoff, verified/unverified scope and historical evidence |

Entry-point and experiment records name their owning operation. The status helper checks workspace-relative references and hashed acceptance evidence. Keep raw dumps, full decompilations and proprietary binaries in ignored local storage. Publish scoped observations and procedures rather than private artifacts.

An observed experiment can still lack persistence or artifact verification. A supported build is supported only for its demonstrated operations and lifecycles.
