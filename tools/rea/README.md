# Research tools

[中文](README.zh-CN.md) · [SOP](../../docs/SOP.md) · [Install the framework](../../docs/install.md)

[REA](https://github.com/morluto/rea) is a research tool used to inspect shipped artifacts and recover internal operations. It is not a dependency of generic framework installation or every generated CLI.

After the user selects a target, follow REA's upstream setup for the agent environment. Choose the analysis backend from the artifact: native disassembly/decompilation, managed decompilation, packaged-script inspection or runtime/protocol observation. Install only the required engines and record versions and target hashes. An adapter's ordinary runtime dependencies are a separate concern.

Before relying on an analyzer, discover the tools actually exposed to the current agent, check their documented inputs and configured backend, and inspect a small relevant part of the selected artifact. Retain that query, tool/backend version, coverage and output as the readiness evidence. A registered connector or installed executable alone does not prove the required analysis works. If an engine is missing, configure it from its current upstream instructions and repeat this bounded check. If access or coverage is still blocked, retain the blocker and choose an appropriate fallback; do not guess tool names, signatures or native entry points.

Use the configured installation/cache locations and preserve existing data. Do not publish machine-specific registration files as universal setup scripts. If REA is unavailable, name the equivalent tools actually used and retain their evidence instead of labeling all findings as REA output.

Use the [artifact routing and fallback guide](../../docs/guides/reconnaissance.md) for bounded analysis. A tool reporting a size limit or partial result is not proof that a type or entry point is absent. Retain the failed query, narrow the module/type/function, and record the actual fallback tool. Keep build hashes, ABI and lifecycle findings in the [entry-point and build templates](../../templates/research/README.md); do not transfer addresses or vtable slots across builds without evidence.
