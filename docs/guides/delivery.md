# Delivery, installation and maintenance
[中文](delivery.zh-CN.md) · [Manual](../HARNESS.md) · [Development tools](../development-tools.md)

## Three different installations

1. **Framework:** Python, shared runtime and development resources. No application or decompiler is required for core installation.
2. **Agent Skill:** the installed discovery entry plus its complete method and helper resources. Copying only a Skill with broken relative references is insufficient.
3. **Target adapter:** the native runtime dependencies, build profile and target instructions needed to execute supported operations.

Use the [Skill installer](../development-tools.md) for a self-contained resource bundle in the chosen agent's supported Skill directory. The installer requires an explicit destination, refuses an existing directory and records file hashes. Resolve installation and cache locations from the user's configuration. Check host discovery separately from copying files.

The included framework snapshot can run independently of the original checkout. It has an empty adapter registry. It contains no showcase code, binary, credentials, local configuration, application cache or analysis engine. Update by installing to a fresh location, reviewing it and using the host's normal replacement mechanism; do not overwrite unknown existing skills.

## Generate instructions from actual tools

Run the documentation helper on the saved adapter manifest. It reads data without importing runtime hooks or launching the app. Generated output includes the exact tool list, input/output contracts and declared coverage. It explicitly distinguishes declared evidence from a fresh verification.

Keep generated documents in a new output directory and preserve handwritten native notes. Use the generated Skill as a starting artifact or link it from the maintained target Skill. Regenerate after command changes and review units, state prerequisites, async semantics and error handling that schemas cannot fully express.

The helper is not a native implementation generator. It must not invent a successful example invocation for required arguments it does not know. A missing coverage declaration is unverified, not implicitly supported.

## Deliverable checklist

- Runnable adapter with one clear entry point and machine-readable results.
- Manifest, catalog and target-specific dependencies/configuration.
- Build map: hashes, supported architecture, bindings and evidence.
- Requested-operation coverage and limitations, including unverified modes.
- State inspection, error/outcome interpretation and recovery instructions.
- Native assertions and artifact verifiers appropriate to the target.
- Target Skill, command reference and a meaningful combined workflow.
- Research handoff: failed candidates, current decisions and unresolved blockers.

Packaging as a Python distribution is useful when it improves installation, but not a universal requirement. If distributing an installed executable, test that executable from outside the checkout when such validation is in scope. A source-directory smoke check does not prove installed-package portability.

## Upgrade deliberately

Fingerprint new modules and diff the build map. Reconfirm metadata tokens/RVAs, signatures, layouts and ownership. Do not automatically change a hash guard while preserving old addresses. Maintain separate supported and candidate profiles.

Verify one requested operation and its relevant lifecycle/output checks on the new build. Include a bounded write only for mutation tools. Evidence from an older build can guide the investigation but cannot certify the new one. Record crashes and uncertain outcomes; keep the last supported profile usable.

## Agent handoff

Provide the framework/Skill location, installation record, adapter manifest, supported builds, readiness query and requested workflow. Include applicable input/job/session identity and unresolved operation IDs when continuing work. The receiving agent must be able to determine prerequisites, select commands and interpret outcomes from these resources.

## Attribution and release

Include dependency versions, licenses and required notices in the distribution. Keep source references with any code or assets that require attribution.

Public release should contain bounded implementation and publishable evidence, not installers, private application binaries, dumps, account data or entire research caches. Public publication and registry submission require the user's requested release scope.
