---
name: reverse-cli-shapr3d
description: Operate the version-pinned reverse-cli Shapr3D pilot for native project sessions, history parameters, the scoped XY mounting-plate modeling workflow, and native SHAPR or STL export. Use for verified Shapr3D operations, not arbitrary CAD modeling or generic mesh generation.
---

# Shapr3D through reverse-cli

Locate the checkout. Target Windows x64 Shapr3D 26.180.11926.0, normal login/onboarding and export permissions. Read [setup and limits](../../shapr3d-cli/README.md), [visible modeling](../../shapr3d-cli/VISIBLE-DRILL-DEMO.md), [runtime](../../docs/runtime.md) and [acceptance](../../acceptance/shapr3d.json).

Run `python -B reverse-cli.py doctor shapr3d --pid <pid>` and `tools shapr3d`. Doctor verifies environment, not editable state. Reuse a valid public pilot session if available; otherwise `run shapr3d -- start --pid <pid>` returns its session directory. Do not create competing hosts for the same application state.

Use `call shapr3d history --args @request.json`, where the object includes the current `session`, or `run shapr3d -- call --session <path> --json <payload>`. Native operation payloads retain their legacy format. Inspect current history/status and use returned names, language-dependent labels and IDs; do not reuse example pointers or numeric IDs. Native integer IDs may exceed JavaScript's exact numeric range and must remain strings.

## Workflow and scope

- Native calls use recovered C++/WinRT objects, application dispatcher and COM lifetimes. Never bypass the coordinated close/reopen or callback cleanup paths.
- The current visible geometry tools support the demonstrated XY mounting plate, not arbitrary sketches, topology or universal CAD operations. DXF supplies sketch input; Shapr3D computes the bodies and cuts.
- Read `history` before `history-set`; use explicit unit expressions such as `-4 mm`. Native numeric distance values are meters. Inspect history/errors after edits.
- Back up to native SHAPR and STL before scoped destructive tests. `model-clear-demo` requires the adapter's explicit backup, expected-history and confirmation inputs; do not broaden it.
- `project-reopen` requires a supported access object retained by the same session. It does not promise cold restart, universal project listing or restoring a handle after session exit.
- Export through native `export-shapr` / `export-stl`, with a basename and writable application-accessible staging directory. Verify its resolved location on D:, then byte-copy and hash-check final artifacts. Existing files must not be overwritten.
- Validate geometry independently: dimensions, volume, holes, mesh connectivity and before/after differences. Native completion/file existence alone cannot prove geometry.

## Recovery

Serialize edits. Shared operation ID reuse returns the old receipt, with no fresh state guarantee; direct legacy calls are outside shared locking. An unknown result or deadline does not cancel native work. Inspect the pilot queue, native callback state and `operation get/refresh` before proceeding. Explicit resolution is a caller-verified, hashed evidence record, not an automatic native attestation.

Session close must wait for callback release. Keep the application and session alive for any outstanding operation. Prefer configured D-drive cache/output locations without migrating existing installations. The user's task authorizes its necessary reversible edits; exploratory acceptance belongs in a dedicated model or verified backup.
