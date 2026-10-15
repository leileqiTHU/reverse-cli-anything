# Closed-source software automation: frequently asked questions

[中文](faq.zh-CN.md) · [Project overview](../README.md) · [Installation](install.md)

## What is reverse-cli-anything?

reverse-cli-anything is an open-source toolkit for building AI-agent-friendly command-line interfaces for closed-source software through reverse engineering. It supplies a research method, adapter framework, Agent Skill and verification tools. A coding agent investigates the selected application, implements missing operations and tests the resulting workflow. See [how it works](../README.md#how-it-works).

## How can an AI agent automate software without a public API?

See the [desktop automation guide](desktop-automation.md) for route selection and [native application examples](native-automation-examples.md) for verified workflows.

When existing interfaces lack the required operations, the agent can investigate shipped binaries, managed assemblies, embedded scripts or runtime behavior to recover internal entry points. It then wraps the verified operations in CLI commands. The appropriate technique depends on the target, and each operation needs actual application testing. See the [research workflow](SOP.md) and [artifact investigation guide](guides/reconnaissance.md).

## How is this different from a CLI, API, MCP server or GUI automation?

CLI and API interfaces expose operations; MCP lets agents discover and call tools. reverse-cli-anything helps create missing command-line interfaces by investigating an application's internals. Its documented examples invoke recovered internal operations rather than replaying mouse clicks. Public interfaces should be checked first, and the repository does not claim every application can be automated this way. See the [interface recovery details](../README.md#how-the-example-interfaces-were-recovered).

## Can I automate CapCut video editing, Axure prototyping or Shapr3D CAD?

The repository contains version-specific examples, with recorded workflows and evidence:

| Application | Demonstrated workflow | Scope and evidence |
| --- | --- | --- |
| CapCut | Import footage, edit a timeline, add music and editable captions, export native video. | [Commands and supported version](../capcut-cli/README.md); [26 recorded checks](../capcut-cli/evidence/recorded-real-media-20261014.json). Speech recognition and translation are external helpers. |
| Axure RP | Create pages and widgets, install click interactions, save/reopen and generate interactive HTML. | [Commands and supported version](../axure-cli/README.md); [native checks](../axure-cli/evidence/native-login-acceptance.json) and [browser checks](../axure-cli/evidence/native-login-browser.json). |
| Shapr3D | Build and edit the demonstrated mounting plate, make a through-hole and export native project/STL. | [Commands and supported version](../shapr3d-cli/README.md); [78 geometry checks](../shapr3d-cli/evidence/recorded-demo-english-20261014.json). This is a scoped modeling pilot. |

These are examples of the method, not a guarantee of support for other versions or arbitrary operations. See the [recording sources](demos/README.md).

## Does it work with any application or operating system?

New applications require investigation and verification. The three recorded adapters were tested on Windows x64; their documentation identifies exact application versions and limitations. The core framework uses Python 3.11+, but that does not establish that an application's native adapter works on macOS or Linux. See [installation](install.md) and [acceptance criteria](../acceptance/README.md).

## Do I need to write commands or install all three example applications?

No. Give a coding agent the [installation prompt](../README.md#quick-start-install-with-your-agent), then describe the software and operations you need. The agent handles setup, implementation and verification. Framework installation does not require the showcase applications. A later target task needs that application's environment and relevant dependencies.

## How do I know a generated CLI really works?

Check operation-level evidence and end-to-end application results, including save/reopen, export and recovery where applicable. A discovered symbol or a successful wrapper return alone does not prove the requested result. The framework's [acceptance criteria](../acceptance/README.md) and [verification guide](guides/verification-and-observation.md) explain what to retain.

## How is reverse-cli-anything related to REA and CLI-Anything?

The source repository is [leileqiTHU/reverse-cli-anything](https://github.com/leileqiTHU/reverse-cli-anything). It provides the method and framework for delivering verified agent CLIs from closed-source application operations. [morluto/rea](https://github.com/morluto/rea) is a separate project whose analysis tools were used in the investigations; [HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything) is a separate project credited for inspiration. These names identify different repositories. See the [acknowledgments](../README.md#acknowledgments) and [this repository's native implementations](native-automation-examples.md).

## Is reverse-cli-anything open source?

The project's original code and documentation use the [MIT License](../LICENSE). Target applications, third-party tools and demo media retain their own licenses. See [acknowledgments](../README.md#acknowledgments) and [media credits](demos/CREDITS.md).
