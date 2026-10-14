# Reconnaissance and evidence
[中文](reconnaissance.zh-CN.md) · [Manual](../HARNESS.md)

## Identify the gap before the technique

Start from the requested operation, its input and the expected native state. Inventory published CLI/API/MCP coverage and any existing adapter. Public read access may expose a useful route to the active document while leaving editing unavailable. An internal component reused through recovered calls is not automatically a supported public API.

Inventory the installed artifact, not only the installer: executable, modules, runtime configuration, metadata, resources, bundled scripts and local protocol endpoints. Record architecture and streaming SHA-256 hashes for relevant files with the fingerprint helper. Do not hash every cache or publish proprietary binaries. Preserve actual resolved installation/storage paths and configuration precedence.

## Route selection

| Observation | First investigation | Next proof |
| --- | --- | --- |
| Exported functions, command strings, Qt metadata | Imports/exports, command registration, targeted cross-references | Receiver, ABI, session mode and dispatch |
| CLR header, assemblies, runtime config, ReadyToRun | Managed inventory, targeted type/method decompilation | Runtime/receiver initialization, call context, result and applicable transaction semantics |
| WinMD and C++/WinRT components | Interfaces, GUIDs, signatures, enum values, candidate vtable slots | ABI layout, ownership, dispatcher and object acquisition |
| Packaged JavaScript/Electron or embedded scripting | Bundle handlers, command registry, internal messages | Handler reaches the intended business operation and produces the requested result |
| IPC/local service | Endpoint identity, message correlation and state transitions | Real request/response semantics in the intended process |
| Data or project files | Format structure, reader/writer call paths and controlled input/output comparisons | Correct interpretation, native acceptance of writes, and concurrent access where applicable |

These are branches, not installation prerequisites. Choose the smallest useful toolchain. Inspect what REA actually supports in the current environment; do not invent tool names or interpret a registered backend as a successfully analyzed target.

## Make static work targeted

1. Use a recognizable behavior as an anchor: user-visible error, command name, property, save action or export service.
2. Follow references to the receiver and downstream business operation. Record why this candidate fits the user task.
3. Inspect callers to recover preconditions and cleanup, not only the callee's body.
4. Write one experiment that can falsify the candidate, with a known baseline and expected observation.
5. Keep rejected candidates and reasons so another agent does not repeat them.

For large binaries, begin with symbols, metadata and a small address range. If whole-program analysis times out, narrow the analysis or change backend. Record partial parser coverage, timeouts and tool versions. A failed all-module decompile is not a reason to claim the software cannot be automated.

## Evidence ladder

Use separate labels: static candidate → runtime observation → verified requested operation → applicable lifecycle verification → workflow coverage. A query or stateless computation does not require a mutation stage. Record evidence paths, tool, target hash and experiment ID at each transition. Imported metadata, a callable pointer, a successful bridge return and an independently checked result are different claims.

The helper templates deliberately start uninvestigated or not-run. No automatic fingerprint or status report upgrades a capability to verified. Normal CLI usage should load a verified build profile, not rerun decompilation.

## When the route fails

Distinguish missing environment (login, initialization, filesystem access) from an incorrect technical hypothesis. Continue independent static work while a user-only step is pending. Do not turn one machine's proxy configuration or one application's activation flow into a universal installation step. Report the specific condition that blocks the requested native operation.
