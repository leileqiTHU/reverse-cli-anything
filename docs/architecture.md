# Architecture

[中文](architecture.zh-CN.md) · [SOP](SOP.md) · [Adapter contract](adapter-contract.md)

`reverse-cli-anything` separates a target-neutral framework from independently registered adapters. The framework installs and passes its core checks with zero adapters and no application binaries.

```text
User: install framework → core setup and self-test → wait for target task
User: software + task
  → Agent + generic Skill + SOP
  → artifact analysis / runtime investigation using suitable tools
  → adapter manifest + native implementation + tool schema + acceptance
  → shared CLI: discover → validate → journal → dispatch → observe
  → target-specific native state / persistence / artifact verification
```

| Component | Responsibility | Does not assume |
| --- | --- | --- |
| Agent method | Operation scope, research routes, experiments, lifecycle and delivery decisions | A fixed target list or automatic recovery of arbitrary binaries |
| File-only research and delivery helpers | Research records, identity hashes, reference checks, catalog-derived docs and complete Skill bundles | Native correctness or host Skill discovery |
| Core config and doctor | Interpreter, configured directories, registry and optional adapter diagnostics | A particular application, desktop OS or native dependency |
| Manifest registry | Load registered adapters and trusted optional hooks | A fixed application list |
| Catalog and schema validation | Discover tools, validate JSON and translate arguments | An application-specific command hierarchy |
| Dispatch and journal | Process execution, write serialization, retained receipts and explicit recovery | Universal native undo, cancellation or exactly-once execution |
| Scaffold | Create a standalone adapter shell and unfinished acceptance plan | That native interfaces have already been recovered |
| Acceptance validator | Required evidence layers, result classification and evidence hashes | Semantic correctness of arbitrary software output |
| Adapter | Build pins, native ABI, object lifecycle, completion, native assertions and artifact verifier | The runtime model of any other adapter |

## Extension boundary

The [manual](HARNESS.md), [workflow modes](workflows.md) and focused [research guides](guides/reconnaissance.md) direct the agent's development work. The [helpers](development-tools.md) retain evidence and package instructions; they do not run an adapter during research-status checks, documentation generation or Skill installation.

Register an `adapter.json`; a new application does not require editing the core. The default transport invokes a Python entry point with a tool name and JSON input. An optional adapter-owned Python hook supports existing CLI syntax, native environment checks and result conventions. Hooks are trusted local code and load only when that adapter is selected. See the [contract](adapter-contract.md).

The core registry starts empty. Optional showcase metadata lives in `examples/registry.json`. `list --examples` includes it explicitly. Selecting a bundled example by its exact ID remains a compatibility path; normal installation and core diagnostics never load it. Removing all showcase directories leaves the core usable.

## Layout

```text
reverse-cli-anything.py / .ps1     canonical launchers
reverse_cli/                      target-neutral runtime
registry.json                     empty base registry; optional example index
schemas/*.schema.json             generic manifest, receipt and acceptance contracts
skills/reverse-cli-anything/       generic install / target investigation Skill
docs/                             manual, guides, workflow modes, contracts and architecture
templates/research/               task, operation, entry-point, experiment and delivery records
tests_development/                isolated file-helper checks; no native execution
tests_shared/                     synthetic adapter tests; no showcase dependencies
tools/                            core setup, checks and generic adapter dispatch
<target>-cli/                     optional adapter implementation and manifest
examples/                         showcase registry, compatibility glue and historical runners
```

`completed` / `ok: true` record adapter completion, not independent native acceptance. Unknown writes retain their lock until observed or explicitly resolved. Direct clients and different state roots are outside a gateway lock's scope. The core provides no universal binary-to-CLI compiler, native transaction or MCP server; agents perform the investigation using the shared method and contracts.
