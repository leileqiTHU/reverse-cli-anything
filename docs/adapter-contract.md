# Adapter contract

[中文](adapter-contract.zh-CN.md) · [Runtime](runtime.md) · [SOP](SOP.md)

An adapter is an independently registered directory. Its native implementation is selected by a manifest, not a core software-name branch. Create a shell with `init`, implement the target-specific work and register its manifest.

Use the [engineering manual](HARNESS.md) to recover the native operation behind this contract. Once the saved catalog is maintained, [generate command documentation](development-tools.md#generate-target-instructions) and supplement its target-specific lifecycle semantics. Documentation generation does not establish native compatibility.

## Minimal manifest

```json
{
  "schemaVersion": 1,
  "id": "my-app",
  "name": "My application",
  "entrypoint": "cli.py",
  "toolSchema": "tools.json",
  "skill": "SKILL.md",
  "acceptance": "acceptance.json",
  "testedBuilds": []
}
```

Paths are relative to the manifest directory, or to its explicit `root`. References must remain inside that declared root. IDs are lowercase letters/digits/hyphens, start with a letter and exclude Windows reserved names. Registration is local, retains the manifest path and refuses a different manifest with an existing ID. A manifest and hook are trusted executable configuration: review their code before registering third-party adapters.

The [manifest schema](../schemas/adapter.schema.json) describes fields. `entrypoint` is currently a Python program; it may launch another implementation. The core requires Python, not a particular target technology. Optional `regression` is an argv list whose first item is a Python acceptance script relative to the declared root. `tools/regress-native.py <adapter> ...` dispatches it only when explicitly requested.

## Default transport and tool catalog

```text
python cli.py <tool-name> --input <JSON-object>
```

A catalog has `schemaVersion`, `adapter` and `tools`. Every tool declares a unique `name`, `inputSchema`, `outputSchema`, boolean `mutates` and an honest `provenance`. Output schema references resolve relative to the catalog. Use `mutates: true` for operations that change target or session state; read classification determines gateway locking.

Write exactly one JSON response to stdout; diagnostics go to stderr. Use `ok: true` with exit code 0 for successful completion. A failed command should report its known outcome: `not-submitted`, `partially-applied`, or an error whose native outcome remains unknown. A write error alone does not prove rollback.

Inputs are validated before dispatch. Native semantic checks, build pins and actual completion remain the adapter's responsibility. Define units, state prerequisites and identity precisely in the tool schema and target Skill.

## Optional compatibility hook

A manifest may declare `runtime: "adapter_runtime.py"`. This local module can supply only the functions it needs:

| Hook | Result |
| --- | --- |
| `preflight(argv)` | `(tool_name, parsed_arguments)` after validating legacy arguments |
| `command(tool, arguments)` | Legacy argv for validated structured arguments |
| `tools()` | Generated catalog, checked against the saved schema |
| `app_path()`, `native_tools()`, `ffmpeg()` | Target defaults or dependency paths |
| `child_env()` | Target-specific environment additions |
| `doctor_checks(pid, inventory)` | Read-only diagnostic check objects |
| `prepare(argv, operation_id)` | Correlate native requests without executing them |
| `successful(tool, response, exit_code)` | Recognize an existing successful result convention |
| `evidence(response)` | Native evidence path descriptors |

Hooks must not launch applications or mutate targets during import, discovery, argument validation or `doctor`. Inspecting a catalog alone does not import the hook. Hooks are trusted and this rule is a contract, not a sandbox.

The core does not know the target's ABI, native command names, object types or process executable. Keep those in the adapter. Prefer the default transport for new adapters; use hooks for actual compatibility needs.

## Evidence and scope

The per-tool coverage file follows [acceptance.schema.json](../schemas/acceptance.schema.json). A native workflow report follows [acceptance-report.schema.json](../schemas/acceptance-report.schema.json). A scaffold starts with `not-run` coverage and `nativeImplemented: false`. Registering it does not change those claims.

Run `tools/check-contracts.py --adapter <id>` after implementation. Application-specific tests and artifact verifiers belong to the adapter; report their exact tested build and workflow. See [generic acceptance](../acceptance/README.md).
