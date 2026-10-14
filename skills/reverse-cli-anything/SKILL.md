---
name: reverse-cli-anything
description: Install reverse-cli-anything or develop reusable CLI tools for operations missing from a user-selected application's public CLI, API or MCP. Use for investigating shipped artifacts, building or extending adapters, recovering uncertain operations and reviewing build compatibility. For ordinary supported operations, use the target adapter's Skill.
---

# Reverse CLI Anything

The user names software and an operation set through conversation, or describes a goal from which you derive the operations. Own the research and development; do not ask the user to design native calls, scaffold an adapter or translate a task into commands. Deliver the requested tool set and a meaningful combined workflow with honest verification scope.

## Find your resources

Resolve references from this Skill's location. In an installed bundle, the framework is the adjacent `framework/` directory. In a repository checkout it is two directories above this file. Confirm that the chosen root contains `reverse-cli-anything.py`. Run helper commands from that root, using the user's interpreter and storage preferences.

The installed bundle includes its own generic framework, guides and templates. It does not include target software, analysis engines, user adapters or personal settings. Never assume adapters registered in a different checkout are registered here.

Use the selected framework's local configuration and `installation.json` in its state directory. Run setup there if installation is incomplete. Keep subsequent research, registration and calls on that same framework; [installation](../../docs/install.md) explains how to persist this context across sessions.

## Select the task mode

| User intent | Read / perform |
| --- | --- |
| Install the repository or Skill | [Installation](../../docs/install.md); choose the execution directory, install complete resources, configure and check that copy, then wait for a target request |
| Build missing CLI operations | [Start a target task](../../docs/SOP.md#start-a-target-task), [engineering manual](../../docs/HARNESS.md), then relevant technical guides |
| Add capabilities to an existing adapter | Its Skill and catalog, [extend mode](../../docs/workflows.md#extend-an-existing-adapter), then guides for the actual gaps |
| Recover a timeout or partial write | Original receipt and target state, [recovery guide](../../docs/guides/state-and-recovery.md) |
| Support a new application build | [Upgrade mode](../../docs/workflows.md#support-another-build) and [delivery guide](../../docs/guides/delivery.md) |
| Review or validate | [Validation modes](../../docs/workflows.md#validate-or-review); execute only the requested level |
| Perform work using supported tools | Target Skill, readiness and native state; reuse existing commands |

Installation is separately scoped. Do not choose, install or investigate a target application merely because this Skill was installed. A request to develop a target does authorize its normal necessary development work; do not repeatedly ask permission for internal implementation steps.

## Development invariants

- Map the full operation set and inspect public coverage first. Select techniques from the target's artifacts and runtime.
- Preserve tool provenance: public interface, recovered internal entry, file-format operation, external helper or framework infrastructure. Report partial REA coverage and alternative tools accurately.
- Bind native calls to exact builds, real business objects and the correct thread/lifecycle. Function names, metadata and returned success do not prove useful native behavior.
- Classify the target's execution model, state lifetime and operation effects. Read-only and stateless tasks do not require a document, GUI, edit, undo or save cycle. Prove one requested operation, then complete the operation set and its combined workflow.
- Keep production bridges narrow. Research probes, app binaries, local account information and raw dumps are not distribution artifacts.
- Preserve request identity and observed state. On partial or unknown execution, inspect before retrying; a timeout does not cancel queued native work.
- Separate native state, visible editor synchronization, persistence, output and recovery evidence. Keep same-session and cold-start reopen claims distinct.
- Record the build, inputs and execution evidence for each validation result. Keep unexecuted checks distinct from passed checks and declared compatibility.

## Technical routing

Use [reconnaissance](../../docs/guides/reconnaissance.md) to choose a route from actual artifacts. Use REA if available and appropriate; record the tools actually used. Read only relevant guides:

- [Native commands, ABI, embedded runtimes and protocols](../../docs/guides/native-runtime.md)
- [Managed assemblies, edit transactions and notifications](../../docs/guides/managed-transactions.md)
- [WinMD, COM, dispatch and object lifecycle](../../docs/guides/winrt-lifecycle.md)
- [State and recovery](../../docs/guides/state-and-recovery.md)
- [Verification and state observation](../../docs/guides/verification-and-observation.md)

## Working tools and delivery

[Development helpers](../../docs/development-tools.md) initialize research records, fingerprint explicit files, check declared progress, generate instructions from saved tool schemas and install complete Skill resources. They do not recover native functions automatically or certify behavior. Use the [record templates](../../templates/research/README.md) for entry-point cards, experiments, builds and observations.

Use the [adapter contract](../../docs/adapter-contract.md) and [shared runtime](../../docs/runtime.md) when implementing and registering tools. Keep application-specific ABI, dependencies, readiness and assertions in the adapter. Apply [acceptance criteria](../../acceptance/README.md) at the requested verification level.

Deliver runnable tools, matching contracts, a target Skill, supported builds, coverage and recovery instructions. Follow [delivery and maintenance](../../docs/guides/delivery.md). Report blocked and unverified operations separately. Provide enough context for another agent to continue without the research conversation; do not claim cross-session discovery until the host has loaded the installed Skill.
