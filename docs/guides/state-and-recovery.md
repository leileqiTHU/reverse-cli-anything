# State, asynchronous work and recovery
[中文](state-and-recovery.zh-CN.md) · [Manual](../HARNESS.md) · [Runtime receipts](../runtime.md)

## Bind the operation to its real context

Capture build/module identity, process lifetime, bridge/session generation, document ID, subordinate context and selected objects as applicable. Recheck immediately before dispatch. A title or filename alone can match the wrong open document; a pointer is only meaningful within its owning lifetime.

Distinguish application state, bridge state and the framework receipt. A retained successful receipt proves what was recorded then, not that the current native state is unchanged. Queries that read autosaved files must report that source and synchronize with native identity/save completion.

## Plan multi-step writes

Validate the whole input before the first mutation. Record intended steps, prior state and input digest. After each completed step retain created object IDs and a postcondition. If adding ten objects fails at number six, do not report an atomic failure or repeat all ten.

Prefer native transactions when their semantics are known. Compensation is separate: deleting a newly created object or restoring an old value can itself fail and may not restore history, selection or external effects. Report compensation as an observed action, not an assumed rollback.

Command/request IDs identify submission attempts. Reusing one ID with changed parameters must fail. Before returning a prior result for a logically repeated request, decide whether the caller needs fresh object-state verification. Two different IDs can still represent the same harmful duplicate operation; infrastructure deduplication alone does not solve semantic idempotency.

## State decisions

| Observation | Classification / next step |
| --- | --- |
| Validation or known pre-submit rejection | not-submitted; explain the rejected input/state |
| Correct correlated terminal result and postcondition | completed; retain native evidence separately |
| Some known steps changed state | partially-applied; preserve IDs and remaining steps |
| Deadline, lost response or ambiguous native error | unknown; observe before any conflicting write |
| Late matching terminal result | reconcile the original request; never resubmit just to obtain a response |

Do not release a mutation lock while unknown native work may still be executing. The shared gateway serializes its own writers, not arbitrary clients or other state directories. State the lock's scope. A dead controller/worker does not establish that work queued in the target stopped.

When the process has crashed, preserve logs and scoped dumps locally, identify the last known mutation, and inspect the saved state before reopening or recovering. A backup does not prove the active document has been restored.

## Temporary settings and previews

A preview may temporarily change range, resolution, selection, camera, export path or active context. Snapshot the exact affected fields and identity. Restore only if the same operation still owns those settings and the native job no longer needs them. Avoid overwriting intervening user changes.

Record capture failure and restoration failure independently. A good preview plus failed restoration is still a partial result. Re-query after cleanup; later events can modify state after the apparent main operation finishes.

## Recovery handoff

Leave a compact record: operation ID; target identity; last confirmed step; created/changed objects; worker/native liveness; evidence locations; allowed read-only observations; and what condition permits continuation. Expose those facts through status/inspection where possible. Do not require a new agent to infer them from a long console transcript.
