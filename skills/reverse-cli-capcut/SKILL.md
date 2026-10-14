---
name: reverse-cli-capcut
description: Operate the validated reverse-cli CapCut adapter to inspect projects, edit timelines, add audio and captions, and preview or export through CapCut native interfaces. Use for actual local CapCut editing through this adapter, not generic video editing with FFmpeg.
---

# CapCut through reverse-cli

Locate the `reverse-cli` checkout and use its `capcut-cli/capcut_agent.py` or `capcut-cli/capcut-agent.ps1`. The tested target is Windows x64, CapCut 9.5.0.4050; the adapter pins module hashes. Run `capabilities` and `help --topic editor` to discover the actual command syntax.

Prefer the additive shared gateway for recorded execution: `python -B reverse-cli.py doctor capcut --pid <pid>`, then `tools capcut --name <tool>`. Use `run capcut --operation-id <id> -- <legacy arguments>` or `call capcut <tool> --args @request.json`. Schema names use dots, such as `editor.set-clip`; JSON argument keys use underscores. The full native response remains under `response`. Legacy calls still work but do not acquire the shared lock; never mix concurrent writers.

For setup and command details read [the adapter README](../../capcut-cli/README.md) and [command semantics](../../capcut-cli/docs/commands.md). Paths here are repository-relative; if this skill is installed separately, locate the checkout before executing.

## Target identity

Resolve the current main process PID; historical PIDs are not reusable. Use `project list` to identify the current project. Prefer stable `projectId` for lifecycle commands and use `projectPath` returned after open, because the application can rename draft directories. Bind editor calls to an explicit active `timelineId`; `switch-timeline` waits for readiness.

The caller's editing request authorizes its necessary operations. Do not ask for redundant permission for ordinary reversible edits within that scope. Work in a separate test project for exploratory probes or destructive verification.

## Execution

- The running desktop application is required for native edits, but mouse and keyboard UI events are unnecessary.
- Parse UTF-8 JSON stdout, check `ok`, and retain returned object IDs and logs. Do not infer success from exit text or file existence alone.
- `project import-media` imports local video into a closed project's media bin; `editor add-video` separately places it on a timeline.
- Time values are integer microseconds. `trim` retains an absolute interval in the pre-edit timeline; `split` points are relative to the clip start. Check returned `targetUs/sourceUs` after magnetic snapping.
- `add-track` means a new video layer containing its first clip. It does not create an empty track. An independent timeline uses `add-timeline`.
- `captions-import` consumes supplied SRT/JSON; speech recognition and translation are upstream tasks. Inspect a native frame to verify actual text layout.
- `media frame/preview` examines files with FFmpeg; `editor frame/preview/export` uses the real native timeline/renderer. Do not substitute one while claiming the other.
- Outputs and caches in this implementation are on D:. Reuse existing environments rather than relocating them merely to satisfy that preference.

## Failures and verification

Serialize writes to each PID. For the three newer editing tools, use a stable `--request-id` for one logical operation. A partial result contains created IDs and completed steps: inspect them and resume only missing work. An unknown result or timeout is not proof of cancellation. Do not remove a live worker's lock or blindly repeat a mutation.

Shared operation ID reuse returns a historical receipt with `freshStateVerified: false`; it does not re-execute or verify current state. Use `operation get/refresh <id>` and fresh `editor.inspect` to observe uncertain outcomes. Reads can pass the shared write lock, but native backend locks may still block them. Explicit `operation resolve` requires verified terminal work and hashed evidence; it is caller attestation, not automatic native verification. Preserve failed evidence. See [runtime/recovery](../../docs/runtime.md) and [per-tool acceptance](../../acceptance/capcut.json).

MP3 artwork can make the native probe classify music as video; the tested workaround is decoding to WAV through CLI before native audio import. Native caption time fields may round by one microsecond; larger timing errors remain failures.

Verify state after edits, reopen dedicated acceptance projects when appropriate, and independently decode/export-check meaningful artifacts. Preserve source attribution and distinguish actual runtime evidence from untested assumptions. See [the real-media example](../../capcut-cli/examples/real-media.md) for a completed workflow and its known incidents.
