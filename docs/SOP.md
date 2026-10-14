# From any target program to an agent-friendly CLI

[中文](SOP.zh-CN.md) · [Architecture](architecture.md) · [Adapter contract](adapter-contract.md) · [Acceptance](../acceptance/README.md)

This workflow starts with a user-selected application and task. No particular software, artifact format, operating system, editing model or export type is a framework prerequisite. Installation is separate: follow [setup](install.md) and wait for the user's target before investigating it.

Use this page as the phase checklist. The [engineering manual](HARNESS.md) supplies detailed decisions and deliverables; [workflow modes](workflows.md) distinguish building, extending, recovering and adapting to upgrades. [Development helpers](development-tools.md) and [research templates](../templates/research/README.md) turn the method into retained working records.

## Start a target task

1. Resolve the execution directory from the installed Skill or supplied checkout. Read its local configuration and installation record, then inspect the registry with `list`. Keep research and registration bound to this directory.
2. Identify the named application, platform, build and available artifact or endpoint. Locate the actual installation or obtain the required distribution when target setup is part of the task. Record a concrete access blocker if the target cannot be obtained; do not substitute another application.
3. Describe each requested operation's inputs, result, side effects and dependencies. Classify the execution model (interactive process, service, batch executable, library or offline format), state lifetime (persistent, session or stateless) and operation effect (observation, computation or mutation).
4. Check public interfaces and existing adapters for this exact operation set. Reuse adequate coverage; initialize a research workspace for gaps with `tools/research.py init` as documented in [development helpers](development-tools.md).
5. Verify the chosen analyzer can inspect the relevant artifact, then trace one requested operation to a callable entry point. Use the [engineering manual](HARNESS.md) and the matching runtime guide. Record unsupported or unknown bindings instead of generating speculative native calls.

The research directory holds hypotheses and evidence. The adapter directory holds the reusable implementation and manifest. Add recovered operations to its entry point and saved tool catalog, register that manifest in the selected framework, then exercise the operations through `call`. The [adapter contract](adapter-contract.md) defines this connection. Installation, research-record creation and adapter scaffolding are separate steps.

## Define the requested operation set

Accept a conversational request naming the application and required operations, or derive the operation set from the user's work goal. Record each operation's input, expected output, target version and observable success criteria, along with the workflow connecting them. Identify the native objects involved and which state must remain editable or persistent. Track requested, implemented, verified and blocked operations so the first successful call does not replace the full requested scope.

The agent owns environment setup, investigation, CLI implementation, registration and verification. The user need not design commands or run framework plumbing. Deliver a reusable tool set for the requested work; a scaffold or list of internal functions is not the deliverable.

Inspect existing public automation and installed adapters. Recover missing internal operations where needed. Record the provenance of each tool: public interface, recovered internal entry, file-format operation, external helper or adapter infrastructure.

## Investigate according to the artifact

| Evidence available | Candidate approach | What still needs runtime proof |
| --- | --- | --- |
| Native binaries, symbols or type metadata | Targeted disassembly/decompilation, imports/exports, cross-references and runtime observation | Calling convention, ownership, thread, object identity and completion |
| Managed assemblies | Types, call chains, transactions, serializers and service discovery | Active object ownership, dispatch and persistence |
| Packaged scripts or embedded runtimes | Bundle/resource analysis, internal messages and runtime inspection | Actual business handler, supported state and side effects |
| IPC, local services or file formats | Trace and recover protocol/schema semantics and lifecycle | Request identity, live state synchronization and native acceptance |

Use REA or suitable equivalent tools, selecting backends for the actual artifact. Retain target hashes and tool versions; distinguish static inference from an observed native call. Do not require every backend or copy one example's injection technique to unrelated software.

## Build and prove

1. **Baseline:** identify the artifact/build, applicable process or endpoint, inputs and relevant state. Preserve affected data before writes; a stateless task does not require a document or running editor.
2. **Recover lifecycle:** establish argument types and units, prerequisites, native object origin, thread/dispatcher, ownership/release, completion and failure signals.
3. **Prove a bounded call:** execute one requested operation with known input and an independent result check. For mutations, retain a baseline and verify applicable restoration/persistence behavior. For observations or stateless computations, verify the returned data and absence of unintended side effects.
4. **Create the adapter:** use `init`, implement commands and register its manifest. Keep application-specific paths, ABI and dependencies in the adapter. The scaffold's status command does not prove native support.
5. **Expose contracts:** supply validated JSON inputs, object identity, provenance, mutation classification and discoverable results. Preserve structured failures and explicit limitations.
6. **Handle uncertainty:** retain request IDs, timestamps and evidence around dispatch. A timeout does not cancel native work; inspect partial/unknown outcomes before another mutation.
7. **Accept independently:** check the applicable layers below with target-specific assertions. Save successful and failed evidence.
8. **Deliver:** CLI, manifest, tool schema, target Skill, build constraints, acceptance report and usage examples. Register the adapter without editing core application lists.

Repeat the implementation and verification steps until all requested operations and their combined workflow have been covered, or concrete blockers prevent further progress. Report any remaining gaps explicitly, distinguishing unimplemented, implemented but unverified, and verified capabilities. Later conversational tasks should reuse the generated CLI and target Skill rather than restart development.

## Generic acceptance layers

| Layer | Question | Examples of evidence |
| --- | --- | --- |
| Request | Was the intended request dispatched to the correct target, with a correlated completion? | IDs, input digest, response, native request log |
| State / result | Did the operation return the correct data or produce the intended state, with unrelated state preserved? | Independent queries, known-result computations, native state diff |
| Persistence | Did the change survive the required save/reopen lifecycle? | Reopened object state; distinguish same-session and cold startup |
| Artifact | Does the native output contain the intended result? | Independent file decoding, document content, rendered content or geometry assertions |
| Recovery | Are rejected, partial and unknown operations handled without blind replay? | Rejection tests, timeout evidence, supported undo or restoration |

The task decides which layers apply. Read-only operations may not need export or persistence; explain such exclusions explicitly. Missing evidence is `not-run`, not a pass. See [acceptance](../acceptance/README.md) for the generic report and evidence-integrity validator.

## Framework boundary

The core owns discovery, JSON validation, dispatch, receipts and evidence bookkeeping. Adapters own native execution, application-specific readiness, transactions, artifact verification and recovery semantics. Tool choice, desktop requirements and export mechanics are target-dependent.
