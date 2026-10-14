# Verification and state observation
[中文](verification-and-observation.zh-CN.md) · [Manual](../HARNESS.md) · [Acceptance](../../acceptance/README.md)

## Design a falsifiable check

For every requested operation specify the expected data, computation or state change and applicable unaffected state before executing it. Use stable identities where available, not only counts. A command returning zero, a nonempty output file and a matching screenshot are individually insufficient for many tasks.

Select only applicable layers: request, state, persistence, artifact and recovery. Read-only inspection need not invent a save/export test. Same-session reopen, a fresh process and a new machine are distinct scopes. An app's normal license or platform limitations remain explicit.

Bind each result to the target build, input, configuration and execution time. Preserve evidence of rejection, partial completion and uncertainty alongside successful results.

## Small diagnostic fixtures, then realistic inputs

Construct a small fixture with known values, distinguishable inputs or objects, and an explicit expected result. Vary one relevant condition at a time. Include boundary values, empty input, invalid references and encoding differences where they affect the contract.

Derive tolerances from native units, numerical precision and serialization rules. Record the conversion between caller and native representations, including rounding and coordinate or reference systems. Reject discrepancies outside that bound.

Then exercise representative inputs with realistic size, structure, metadata and dependencies. Preserve the original input and record preprocessing so a successful conversion is distinguishable from native handling of the original format.

Check both the operation's structural result and the task's semantic result. Attribute each transformation to the component that performs it: target application, file operation or external helper.

## Independent output checks

| Property | Meaningful checks |
| --- | --- |
| Identity and completeness | Expected request, output path, format and complete decode/parse; exclude stale or partially written files |
| Structured values | Required fields, types, IDs, relationships and preservation of unrelated values |
| Quantitative results | Units, ranges, dimensions and numerical error within the defined tolerance |
| Executable behavior | Required branches, side effects, invalid input and terminal outcomes in the intended runtime |
| Persistence | Reacquired objects, saved values and continued operation after the supported reload lifecycle |
| Rendered representation | Expected content and transformation, using a view derived from the correct source revision |

Check before, during and after affected boundaries. Validate unchanged objects and relevant other documents/contexts. After export, inspect source state as well as the final artifact.

## Observation contract

Use the [observation template](../../templates/research/observation.json) to record:

- producing operation/request ID and exact native target;
- capture timestamp and source revision/fingerprint, when obtainable;
- kind: native query, native render/export, saved-file inspection, external helper or screen recording;
- artifacts with paths, hashes, media types and known scope;
- whether temporary state was modified/restored and whether the capture may be stale.

Distinguish native state queries, persisted data, generated representations and visible application state in tool descriptions and results. Provide compact state queries for choosing the next operation; retain detailed artifacts when needed to inspect content.

Cache reuse requires matching source identity and relevant options. If source revision cannot be established, say freshness is unknown or obtain a fresh observation. No generic cache key can establish native correctness by itself.

## Correlate execution and observation

Retain the command arguments, operation ID, submission/completion timestamps and resulting object or artifact IDs. Link subsequent observations to that operation and source revision. When a result arrives late, reconcile it with the original request before deciding whether another write is needed.

An execution log establishes submission and reported completion. An independent observation establishes the resulting state. Keep both when the operation's correctness depends on them.
