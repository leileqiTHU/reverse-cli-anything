# Agent task modes

[中文](workflows.zh-CN.md) · [Engineering manual](HARNESS.md)

Choose the mode from the conversation; the user does not need to type a mode command. Existing authorization and constraints carry forward. Mode changes do not authorize unrelated installation, publishing or target mutations.

## Install

Follow [installation](install.md), install the complete Skill resources into the chosen agent's supported Skill location, and verify the copied resources. Preserve storage preferences. Report the installed path and any host reload requirement. Stop before selecting or investigating an application unless separately requested.

## Build an operation set

1. Follow [target-task startup](SOP.md#start-a-target-task). Read the manual and relevant technical guides; translate the goal into operations, dependencies and observable results.
2. Discover existing adapters and public coverage. Establish build identity and initialize a research workspace for the gaps.
3. Prove one requested operation with known input and an independent observation; record failed candidates as well as successful calls. Select write, undo and persistence checks only for operations with those semantics.
4. Complete the remaining operations and combined workflow, including lifecycle and recovery.
5. Generate instructions from the actual catalog, supplement native semantics and deliver scoped evidence.

Output: adapter, catalog, target Skill, usage, version constraints, research decisions and operation-level coverage. A scaffold is progress, not completion. Ask about a blocker only when available context and independent research cannot resolve it.

## Extend an existing adapter

Read its Skill, catalog, version map and previous evidence. List the requested additions, existing supporting commands and compatibility commitments. A new operation often needs new observation fields or lifecycle support before its mutator.

Keep existing command names and semantics unless the user requests a breaking change. Use narrow patches and record shared-layer changes. Plan checks for new behavior, relevant old behavior and composed workflows; choose execution according to the user's current scope. Do not regenerate handwritten documentation over existing content.

Output: coverage delta, implementation, updated generated instructions, known limitations and which checks actually ran. Historical evidence remains historical.

## Recover a partial or unknown operation

Read the receipt and target identity before any mutation. Determine whether the original worker/native task remains alive, whether a terminal result arrived late and whether the affected resource or session is still the intended one. Query created IDs and completed steps. Use [recovery](guides/state-and-recovery.md) to choose observation, safe continuation or explicit restoration.

Output: a resolved or still-unknown record, evidence, remaining changes and next action. An error message, dead Python worker or elapsed deadline does not prove rollback. Do not invent a new operation ID to bypass an unresolved write lock.

## Support another build

Fingerprint the candidate modules and compare the supported version map. Revisit entry locations, signatures, layouts and object acquisition separately; metadata matches alone do not establish ABI compatibility. Use a separate build profile and verify a requested operation plus its applicable lifecycle and output checks.

Output: a new supported profile with evidence, or a researched but unverified profile. Keep previous pins intact. Details: [delivery and maintenance](guides/delivery.md).

## Validate or review

Select the requested level before acting:

| Level | Work | Does not establish |
| --- | --- | --- |
| Documentation/contract review | Check links, schemas, generated instructions, evidence references and limits | Current native execution |
| Tooling verification | Test framework helpers against isolated synthetic files | Compatibility with an application |
| Native operation verification | Execute selected tools against the pinned target, observe results | Untested commands or other builds |
| Workflow/portability verification | Run the requested full workflow, required reopen, output and fresh installation checks | Universal software support |

Record the selected validation level and the checks actually executed. Unexecuted checks remain `not-run`; report them separately from failures and inapplicable checks.

## Use existing tools

For ordinary work, read the target Skill and inspect readiness/current state. Execute the task through existing supported CLI tools and verify the result. Switch to extension or upgrade only for an actual gap. The user remains in conversation; internal research and framework commands stay the agent's responsibility.
