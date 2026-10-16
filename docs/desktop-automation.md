# Automating closed-source desktop software without a public API

[中文](desktop-automation.zh-CN.md) · [reverse-cli-anything](../README.md) · [Native examples](native-automation-examples.md)

An AI agent may need to edit a document, change a CAD parameter or export a video in an application that has no suitable public API. **reverse-cli-anything** helps a coding agent investigate the missing operations and build a verified CLI from the application's shipped artifacts and runtime. The deliverable is a reusable tool for the requested workflow; support for a new application must be established by investigation and testing.

## Who is this for?

- **Agent builders and automation developers:** your agent can run commands, but the desktop application does not expose the operation it needs.
- **People working in creative or engineering software:** you need an editable native project and the application's own output, with a repeatable workflow you can request through conversation.
- **Reverse engineers:** you have located an internal function or command and need to establish its calling convention, session, state and verification before delivering a usable interface.
- **Tool maintainers:** an application update broke an adapter, or another agent needs to continue the investigation without repeating it.

## Choose an automation route

| Route | When it fits | What to verify |
| --- | --- | --- |
| Public CLI, SDK, scripting API or existing MCP tool | The required operations are already exposed. | Coverage, supported versions and the actual output. Use these interfaces first. |
| Project-file editing | The goal can be expressed in a documented or understood file format. | Whether the application opens it correctly, preserves editability and renders the intended output. Writing JSON alone does not establish live editor control. |
| GUI automation or RPA | The workflow is accessible through the user interface. | Focus, dialogs, timing and whether the application actually saved or exported the result. |
| Reverse-engineered native control | Public interfaces lack needed operations and investigation can recover the application's internal business operations. | ABI, threading, object lifetime, active project/session, version identity and end-to-end results. This is reverse-cli-anything's main engineering use case. |

These routes can coexist in a workflow. Native control does not automatically mean headless execution: the CapCut example needs a running application and an active editing session. Likewise, a CLI's JSON input/output describes its external contract, not whether its implementation edits files or calls the application.

## How do I give an AI agent a CLI for a new application?

Start with the [installation prompt](../README.md#quick-start-install-with-your-agent), then describe the native result you need:

```text
Use reverse-cli-anything to build CLI tools for <application and version>.
I need to open <input>, perform <specific edits>, save an editable native
project, and export <format>. Check existing public interfaces first.
Investigate missing operations and verify the complete workflow in the
application, including reopening the saved project where applicable.
```

The agent should first identify the operation gap and target build. It then selects analysis tools for native binaries, managed assemblies, embedded scripts or protocols, recovers a bounded call contract, and tests the operation before expanding the workflow. The [engineering manual](HARNESS.md) provides the full method; the [reconnaissance guide](guides/reconnaissance.md) covers choosing the research route.

## How does a recovered function become a reliable tool?

A function address is only a starting point. The wrapper must know which object to call, on which thread, with which units and ownership rules, and how to detect completion. For mutations, verify the native state and the saved or exported artifact. Retain the target version, evidence and recovery instructions with the tool.

The framework supplies [adapter contracts](adapter-contract.md), [structured calls and receipts](runtime.md), and [delivery guidance](guides/delivery.md). An MCP integration can call a delivered CLI, but the framework does not claim to generate a ready-made MCP server for every target.

## What happens when the application updates?

Internal calls can change across builds. Recheck build identity, investigate changed entry points and repeat affected workflow acceptance before claiming compatibility. Use the [upgrade workflow](workflows.md) and [state and recovery guide](guides/state-and-recovery.md). The existence of a working adapter for one version does not establish support for another.

## Where can I see working examples?

See [CapCut native editing and export, Axure RP prototype generation, and Shapr3D native CAD modeling](native-automation-examples.md). Each example links the implementation, supported version, recorded workflow and verification evidence so you can judge whether it fits your task.

## CLI, MCP and GUI automation: separate the interface from the backend

When evaluating an open-source desktop automation repository, ask two questions: how does the agent call it, and how does it change the application? A shell command with JSON results and an MCP tool are agent-facing interfaces. The implementation behind either interface can edit project files, operate UI controls or invoke recovered internal functions. Choosing MCP alone does not determine which application operations are available.

For an agent with terminal access, start with the delivered CLI and its documented arguments and results. For an MCP-only client, an integration would need to expose the selected CLI operations as tools, validate arguments, preserve errors and enforce the same session and version requirements. This repository's [runtime contract](runtime.md) and [adapter contract](adapter-contract.md) describe the reusable CLI side; a universal MCP server is not included.

## How do I evaluate an open-source desktop automation tool?

Use a small task that produces an editable native result and an exported artifact. Check the backend and evidence before assuming that a successful command completed the task.

| Need | Acceptance question | Starting point |
| --- | --- | --- |
| Video editing | Did the running editor retain the timeline and captions, and did its own renderer produce the video? | [CapCut workflow and evidence](native-automation-examples.md#capcut-cli-control-the-native-editor-and-export-video) |
| Prototype generation | Does the saved document reopen, and do exported buttons and inputs behave as specified? | [Axure RP native and browser checks](native-automation-examples.md#axure-rp-automation-generate-editable-prototypes-and-interactive-html) |
| CAD parameter editing | Are the intended dimensions retained in the native model and reflected in the exported geometry? | [Shapr3D mounting-plate pilot](native-automation-examples.md#shapr3d-cli-edit-native-cad-geometry-and-export-a-model) |
| Reusable agent integration | Can another session discover the operations, interpret failures and reproduce the verified workflow? | [Delivery guidance](guides/delivery.md) |
| Updates and recovery | Is the target build identified, and can affected operations be retested after a change? | [Build, recover and upgrade workflows](workflows.md) |

For Windows RPA or GUI automation comparisons, evaluate the specific operation gap: focus and screen layout matter for UI control; calling conventions, UI-thread dispatch and object lifetime matter for native control. Neither route establishes universal coverage. Preserve the test input, application build, native output and acceptance record so another developer can reproduce the result.
