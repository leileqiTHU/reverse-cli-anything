# Generic acceptance criteria

[中文](README.zh-CN.md) · [SOP](../docs/SOP.md) · [Adapter contract](../docs/adapter-contract.md)

Framework installation and target acceptance are separate. Installing the core does not require a real application, a particular document type or any showcase workflow.

The [verification guide](../docs/guides/verification-and-observation.md) describes independent observations, content checks and evidence freshness. Record the target build and execution scope for each result.

## Core acceptance

Run `tools/setup.py`, `tools/run-tests.py core` and `tools/smoke-portable.py`. They check configuration, an empty registry, new adapter registration, argument validation, dispatch, receipts, concurrency and recovery. The isolated smoke copy excludes all example code and native dependencies. Its synthetic adapter proves infrastructure behavior only.

Development schema validation uses `tools/check-contracts.py`. With no adapters registered, it validates the generic schemas and succeeds with zero tools. Selecting `--adapter <id>` checks that target's manifest, tool schemas and coverage. `--examples` explicitly adds the optional showcase catalogs.

## Native workflow acceptance

Choose assertions from the task and actual software. All reports must address these layers; no particular export format, object model or UI technology is prescribed.

| Layer | Required evidence |
| --- | --- |
| `request` | Correct target/request identity, input and correlated completion. |
| `state` | Correct returned data, computation or native state, with unrelated content preserved as applicable. |
| `persistence` | Save/reload behavior required by the task; identify same-session versus cold startup. |
| `artifact` | The requested native output, checked independently for actual content. |
| `recovery` | Relevant rejection, partial completion, uncertainty and supported restoration behavior. |

Each assertion has `passed`, `failed`, `not-run` or `not-applicable` status. Passing assertions require evidence paths and SHA-256 hashes. Inapplicable layers require a reason; request and state cannot be omitted. Unrun or failed checks prevent acceptance. The adapter implements actual native verification and decides task-specific assertions.

`init` creates an unfinished `acceptance-plan.json`. Complete its target/build, workflow, assertions and evidence after actual execution, then save a report following [acceptance-report.schema.json](../schemas/acceptance-report.schema.json).

```powershell
python -B reverse-cli-anything.py acceptance "<report.json>"
python -B tools/regress-native.py my-app <adapter-specific-options>
```

The first command checks report completeness and evidence integrity. It does not re-execute the task, recognize arbitrary output content or independently prove caller assertions. The second delegates to the adapter's declared regression script; it requires an explicit target and its own prerequisites. There is no universal native test sequence.

## Per-tool coverage

[acceptance.schema.json](../schemas/acceptance.schema.json) records each command separately. `current-native` means that command ran in a scoped native workflow; `historical-workflow` refers to older evidence; `not-run` makes no execution claim. None of these implies exhaustive parameter coverage. Discovery and scaffold commands do not establish native editing support.

Maintain original failed attempts alongside successful recovery and label build/runtime scope. Application-specific fixtures, verifiers and media belong to their adapters or optional examples.

