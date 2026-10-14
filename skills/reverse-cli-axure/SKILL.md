---
name: reverse-cli-axure
description: Operate the reverse-cli Axure RP adapter to create pages and widgets, edit text and bounds, set supported click interactions, save and reopen projects, and export native HTML. Use for actual Axure editing through the recovered native bridge, not static HTML generation.
---

# Axure RP through reverse-cli

Locate the checkout. Target Windows x64 Axure RP 11.0.0.4150 with normal activation; the assembly hash is pinned. Read [setup and commands](../../axure-cli/README.md), [runtime/recovery](../../docs/runtime.md) and [acceptance](../../acceptance/axure.json).

Run `python -B reverse-cli.py doctor axure`, then `tools axure` or `tools axure --name widget.create`. Doctor is read-only and does not prove login or bridge readiness. Use the existing build/launch procedure only when required, then query `status`, `inspect` and `page.list` for current document/page/widget identities.

Execute `run axure --operation-id <id> -- <legacy arguments>` or `call axure <tool> --args @request.json`. JSON argument keys come from the schema. The original result remains under `response`. The legacy `axure_cli.py`/PowerShell entry points remain supported; avoid simultaneous writers through both paths.

## Native workflow

1. Inspect the active project and dirty state. Use a dedicated project for acceptance; preserve the prior document.
2. Create/open the project and root-level page; bind subsequent edits to the correct current page.
3. Create supported paragraph/button/input widgets, record returned IDs, set text and bounds, inspect readback.
4. Install click rules only on widgets with an empty interaction map. Supported conditions are widget text equality, any/all; supported actions are setText and navigate. Read the current schema and adapter contract for exact payloads.
5. Exercise native undo/redo where appropriate. Save, reopen, inspect persisted state, export with the native HTML generator.
6. Validate exported browser behavior independently. Browser DOM/keyboard acceptance is evidence about the exported artifact, not how the Axure project was edited.

Writes use UI-thread transactions recovered from shipped .NET assemblies. Some reads reuse packaged document-service components. Plain-text replacement retains first-run formatting; this is not a general rich-text editor or arbitrary interaction API.

## Recovery and storage

Use one shared operation ID for one request. Reuse returns a retained receipt, not fresh execution. Unknown/partial results retain the shared write lock; timeout is not cancellation. Query `operation get/refresh <id>` and the exact Axure request journal before another mutation. A late successful request journal can resolve a disconnected client. Cold launch may repeat read-only readiness checks; never replay a timed-out write to test readiness.

Explicit resolution requires caller-verified terminal work and hashed evidence; do not force-unlock a live operation. Native completion does not independently prove save/reopen or HTML behavior.

Configure `AXURE_APP`, shared D-drive cache/output paths, and supported native cache settings. Do not relocate existing data implicitly. Perform necessary reversible work within the user's scope without redundant confirmation; use test documents for probes.
