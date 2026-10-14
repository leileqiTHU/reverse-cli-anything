# Shared runtime

[中文](runtime.zh-CN.md) · [Installation](install.md) · [Adapter contract](adapter-contract.md) · [Acceptance](../acceptance/README.md)

The runtime discovers registered targets, validates JSON, launches their entry points and retains operation evidence. The initial registry is empty; core operation requires no example software.

Research records, file fingerprints, catalog-derived documentation and Skill packaging live in separate [development helpers](development-tools.md). Those file-only operations do not dispatch target commands.

## Commands

These commands are internal tools for the agent developing or using an adapter. The user names the application and desired operations through conversation; the agent runs the setup, scaffolding, registration and invocation steps as needed.

```powershell
python -B reverse-cli-anything.py doctor
python -B reverse-cli-anything.py list
python -B reverse-cli-anything.py init my-app --output ../my-app-cli
python -B reverse-cli-anything.py register ../my-app-cli/adapter.json
python -B reverse-cli-anything.py tools my-app
python -B reverse-cli-anything.py call my-app status --args '{}' --operation-id inspect-001
python -B reverse-cli-anything.py operation get inspect-001
```

The scaffold's status reports infrastructure only. Implement and verify native operations before claiming support. To forward an adapter's existing arguments, use `run <adapter> -- <arguments>`. To inspect its environment, use `doctor <adapter>`; plain `doctor` checks only the core.

`list --examples` additionally reads the optional showcase registry. Existing named example calls remain compatible through explicit ID selection. Core commands do not require that registry or its application files.

## Configuration

Environment variables take precedence over ignored `reverse-cli.local.json`, followed by defaults. `REVERSE_CLI_CONFIG` selects another config file.

Use absolute paths in persistent settings so the same installation works from another working directory. From the selected framework, `tools/setup.py --configure` creates missing settings and records the effective context in `<stateDir>/installation.json`; an existing settings file is preserved. An explicit `REVERSE_CLI_CONFIG` override must remain available in future processes, or use the default local file. The Skill bundle and original checkout have separate configurations and registries.

| Field | Environment | Meaning |
| --- | --- | --- |
| `python` | `REVERSE_CLI_PYTHON` | Interpreter; direct Python invocation defaults to its own interpreter, PowerShell otherwise uses PATH |
| `registry` | `REVERSE_CLI_REGISTRY` | Base manifest registry, default checkout `registry.json` |
| `cacheDir` | `REVERSE_CLI_CACHE_DIR` | D:/Caches/reverse-cli-anything when available; otherwise checkout .runtime/cache |
| `stateDir` | `REVERSE_CLI_STATE_DIR` | Checkout .reverse-cli; operations, locks and local registrations |
| `outputDir` | `REVERSE_CLI_OUTPUT_DIR` | Checkout outputs/reverse-cli-anything |
| `nativeTools` | `REVERSE_CLI_NATIVE_TOOLS` | Optional dependency directory used only by selected adapters |
| `ffmpeg` | `REVERSE_CLI_FFMPEG` | Optional media-helper executable; not required by the core |

Target configuration lives under `adapters.<id>`, with optional `appPath` and `nativeTools`. Additional legacy settings are interpreted only by their adapter hooks. [Example config](../reverse-cli.config.example.json). Reading config does not migrate existing software or data.

Child processes receive configured temporary/cache paths and optional adapter environment settings. Dependency installation belongs to the selected adapter. The core uses the standard library; development schema checks have separate optional requirements.

## Receipts and recovery

`run` and `call` return a shared envelope: `ok`, `operationId`, `state`, original `response`, receipt path and `replayed`. Direct adapter invocation retains its own interface.

| State | Meaning |
| --- | --- |
| `not-submitted` | Validation, locking or known native rejection prevented application of this request |
| `running` | Dispatch crossed the process boundary; completion not yet recorded |
| `completed` | A terminal adapter response was observed; inspect `ok` and independent evidence |
| `partially-applied` | The adapter explicitly reports incomplete mutation |
| `unknown` | Available evidence cannot establish the final native outcome |

An operation ID binds request arguments and supported file-input hashes. Reusing it returns history without dispatch, with `freshStateVerified: false`; different input is rejected. This is replay prevention, not a universal native transaction.

Gateway writers serialize per adapter and state directory. Reads can bypass the gateway write lock, but the native application may still block them. Direct clients and other state roots are not covered.

A timeout leaves the child and lock intact. A dead controller changes a retained running record to unknown. Do not retry the write automatically. Use:

```powershell
python -B reverse-cli-anything.py operation list
python -B reverse-cli-anything.py operation get <operation-id>
python -B reverse-cli-anything.py operation refresh <operation-id>
python -B reverse-cli-anything.py operation resolve <operation-id> --evidence <recovery.json>
```

Refresh observes late successful responses or a matching request-result file; it never re-executes a command. Explicit resolution requires the controller and child to have exited, the same operation ID, `nativeWorkFinished: true`, terminal `state`, boolean `ok`, nonempty passing named `checks` and hashed `evidenceFiles`. It preserves the original failed response and records caller verification. File hashes establish integrity, not the truth of the caller's native assertions.

Shared receipt verification flags start false. Target-specific state, persistence and artifact checks establish those facts separately. No core receipt alone proves that a useful native workflow passed.
