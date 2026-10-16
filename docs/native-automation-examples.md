# Native desktop automation: CapCut CLI, Axure RP and Shapr3D

[中文](native-automation-examples.zh-CN.md) · [Automation route guide](desktop-automation.md) · [Project repository](https://github.com/leileqiTHU/reverse-cli-anything)

**reverse-cli-anything** includes three examples of AI agents operating closed-source desktop applications through recovered internal calls: CapCut video editing, Axure RP interactive prototyping and Shapr3D CAD modeling. These adapters belong to `leileqiTHU/reverse-cli-anything`; each has a tested build and a bounded operation set. They illustrate the general framework rather than define its application coverage.

## CapCut CLI: control the native editor and export video

For an agent that needs to trim footage, add editable captions and render video in CapCut, the repository's [CapCut adapter](../capcut-cli/README.md) exposes native project, timeline, editing, preview and export operations. The recorded workflow was verified on **Windows x64, CapCut 9.5.0.4050**.

The bridge uses **Frida** and recovered calls involving **`lyra_cli_client.dll`**, the editor and frontend modules. CapCut already contains an internal command layer; the adapter recovers the calling conventions and connects commands to active sessions. Native export uses the frontend lifecycle and ExportClient. It is not just an offline `draft_content.json` generator, and it does not replay mouse clicks. Some inspection and save checks read draft data; file previews use FFmpeg, while speech recognition and translation in the demo use external helpers.

| Evaluate the capability | Inspect this evidence |
| --- | --- |
| How editing reaches the running application | [Frida worker](../capcut-cli/capcut_editor_worker.py), [native editor bridge](../capcut-cli/capcut_editor_agent.js), [implementation boundaries](../capcut-cli/docs/implementation.md) |
| How to call project, timeline and export operations | [Command reference](../capcut-cli/docs/commands.md) |
| Whether a complete media workflow was recorded | [Workflow walkthrough](../capcut-cli/examples/recorded-real-media.md), [26 checks](../capcut-cli/evidence/recorded-real-media-20261014.json), [video](../capcut-cli/assets/capcut-cli-demo.mp4) |

Editing needs a running application, an open target project and the intended active timeline; this is not a fully headless renderer. Build hashes are checked. Other CapCut versions, macOS and the separate Jianying/剪映 application are not established as compatible by this evidence.

## Axure RP automation: generate editable prototypes and interactive HTML

For an agent that needs to create pages, place buttons and inputs, add click behavior and export a working prototype, the [Axure RP CLI](../axure-cli/README.md) uses recovered native editing operations from shipped .NET assemblies. A startup hook and named-pipe bridge dispatch work on the Axure UI thread. The tested application is **Axure RP 11.0.0.4150 on Windows**.

The example verifies editable native document operations and Axure's own HTML generation, including save and cold reopen. Some read-only operations reuse built-in MCP document-service components. See [reverse-engineering notes](../axure-cli/reverse-engineering.md), [29 native checks](../axure-cli/evidence/native-login-acceptance.json), [14 browser checks](../axure-cli/evidence/native-login-browser.json) and the [recorded prototype workflow](../axure-cli/assets/axure-cli-demo.mp4). The documented click conditions and actions define the supported scope.

## Shapr3D CLI: edit native CAD geometry and export a model

For an agent that needs an editable native CAD model, the [Shapr3D CLI pilot](../shapr3d-cli/README.md) demonstrates a mounting plate, thickness and hole-spacing changes, a center through-hole, native project saving and STL export. It was tested on **Windows x64, Shapr3D 26.180.11926.0**.

The implementation recovers C++/WinRT interfaces and native modeling objects from shipped binaries and metadata. DXF supplies the demonstrated sketch input; Shapr3D performs the native modeling operations. Inspect the [native bridge](../shapr3d-cli/native_bridge.js), [modeling walkthrough](../shapr3d-cli/VISIBLE-DRILL-DEMO.md), [78 geometry checks](../shapr3d-cli/evidence/recorded-demo-english-20261014.json) and [recorded demo](../shapr3d-cli/assets/shapr3d-cli-demo.mp4).

This is a scoped pilot: arbitrary sketch construction, general project navigation and STEP export are not implemented. Native Low-resolution STL export is documented; this is not evidence of every export option or platform.

## From a user task to a verified native result

For video editors, the useful unit is a complete footage-to-video workflow: import media, trim the timeline, add editable captions, retain the project and export MP4. For prototype designers, it is a native document that reopens and generates interactive HTML. For CAD users, it is a bounded parameter change whose saved model and exported geometry agree. The recordings above provide examples of these acceptance targets; they do not establish unattended batch processing or arbitrary operation coverage.

If you arrive looking for Python scripting, a CLI or an MCP tool, first identify the native result you need. The agent-facing interface and the application's execution backend are separate choices. Use the [route selection guide](desktop-automation.md#cli-mcp-and-gui-automation-separate-the-interface-from-the-backend) to choose between an existing public interface, project-file editing, GUI automation and recovered internal calls.

## Apply the method to another application

Start with the [closed-source automation guide](desktop-automation.md), then ask an agent to identify the missing operations for your application and version. The [engineering manual](HARNESS.md) explains how to move from internal entry points to verified, reusable CLI tools. Reusing this method does not require installing the three example applications.
