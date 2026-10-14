# File-only development helpers

[中文](development-tools.zh-CN.md) · [Manual](HARNESS.md) · [Templates](../templates/research/README.md)

These internal tools use Python's standard library. They do not launch, attach to or mutate target applications. Run them from the framework root with the user's interpreter and storage preferences.

## Research records and file identity

```powershell
python -B tools/research.py init my-app --application "<selected application>" --goal "<requested outcome>" --operation "<operation-id>" --output ../my-app-research
python -B tools/research.py status ../my-app-research
python -B tools/research.py fingerprint "<module-path>" --output ../my-app-research/evidence/build.json
```

Initialization creates a new directory with task, operations and build-map records, plus empty entrypoints, experiments and evidence directories. It generates no native integration. Copy applicable templates when an actual entry-point card or experiment is needed.

Replace the placeholders with the user's target and derived operation IDs; repeat `--operation` for additional operations. Classify execution and state lifetime in `task.json` and effects in `operations.json` before choosing native checks.

Update operation descriptions, public-interface gaps, postconditions and dependencies as research progresses. Entry-point/experiment references are workspace-relative. Acceptance evidence uses `{"path":"evidence/result.json","sha256":"<64 lowercase hex characters>"}`; explicitly supplied absolute evidence paths are supported.

Status checks unique IDs, known statuses, dependency cycles, record ownership and evidence hashes. Blocked items need a reason; verified claims need hashed evidence. It reports **declared progress and integrity**, not native correctness, and never promotes status automatically.

Fingerprinting streams explicit files and checks for size/mtime changes during reading. It records resolved paths, bytes and SHA-256; it does not discover binaries, infer architecture or certify compatibility. Existing output files are not replaced.

## Generate target instructions

```powershell
python -B tools/generate-docs.py ../my-app-cli/adapter.json --output ../my-app-cli/agent-docs
```

The output must be a **new subdirectory of the adapter root** so relative references survive moving the adapter. The helper reads saved data without importing hooks or executing commands. It creates:

- `COMMANDS.md`: exact tools, schemas, provenance and declared coverage.
- `SKILL.md`: routing to contracts and existing native notes.
- `sources.json`: source paths relative to the output and hashes for detecting stale instructions.

Handwritten files are preserved. Unknown required arguments and successful examples are not invented. Schema references resolve from the original catalog. Review units, readiness, async and recovery semantics; then deliberately update the maintained target Skill or manifest. Generation does not register anything or re-verify historical evidence.

## Install a complete generic Skill

```powershell
python -B tools/install-skill.py --destination "<skill-directory>/reverse-cli-anything"
```

Resolve the host's supported Skill directory and reload procedure before replacing `<skill-directory>`. Use the configured storage locations for working data and caches. Installing to an arbitrary directory does not make a Skill discoverable.

The installer requires a nonexistent destination, stages under its parent and renames when complete. It allowlists generic code, contracts, guides, templates and helpers; rewrites the outer Skill's links to the included `framework/`; and records hashes in `bundle.json`. The inner framework retains a source-form Skill for redistribution and starts with an empty registry.

The bundle contains no showcases, proprietary binaries, local settings, credentials, research caches or analysis engines. It does not change host settings or confirm discovery. Failed staging remains available for inspection. For an upgrade, install a fresh bundle, review it and use the host's normal replacement mechanism.

Framework helpers work without the original checkout. Change to the installer's returned `framework` directory and follow [configuration and verification](install.md#configure-and-verify-the-selected-directory), including `tools/setup.py --configure`. Keep using that execution directory and its installation record. Register target manifests explicitly; another checkout's settings and registrations are not migrated.

## Helper verification

`tests_development/` checks synthetic research files, no-hook execution, overwrite refusal, dependency cycles, tampered evidence, incomplete installations and persistent installation settings. It does not invoke application adapters or native workflows. Run it when changing these helpers; report those checks separately from native acceptance.

```powershell
python -B -m unittest discover -s tests_development -v
```

Fixtures are retained under the configured cache directory for inspection. This command runs only helper tests; it does not run the existing CLI regression suites.
