# Contribute a target or improve the framework

[中文](CONTRIBUTING.zh-CN.md) · [SOP](docs/SOP.md) · [Adapter contract](docs/adapter-contract.md)

The framework serves user-selected software. Existing showcases demonstrate results; adding a target must not require hardcoding its name, executable, ABI or verification logic in the core.

1. Define a useful task, expected native result and known public-interface gaps.
2. Use the [manual](docs/HARNESS.md) and [workflow modes](docs/workflows.md) to investigate the shipped artifact and native lifecycle. Retain an operation matrix, complete entry-point cards, bounded experiments and failed hypotheses with the [research helpers](docs/development-tools.md).
3. Create an independent adapter with `init`; implement its native commands, schemas and Skill. Keep platform dependencies, version pins and domain-specific verifiers in that adapter.
4. Register its manifest. Use the default JSON transport, or an optional hook for real compatibility requirements.
5. Add task-specific assertions under the generic request/state/persistence/artifact/recovery criteria. Explain inapplicable layers and retain failures. Separate native observations from static inference, synthetic tests and historical evidence.
6. Match validation to the changed behavior. Adapter behavior changes require contract checks and relevant native regression; runtime changes require core-only tests. Documentation and file-helper changes use link, template and isolated helper checks. Record check inputs, builds and results.
7. Add an optional showcase entry and demo if useful. Update English/Chinese documentation and sources. A new example does not become an installation prerequisite.

Do not commit proprietary application binaries, dumps, personal documents, account configuration or bulk recordings. Publish scoped evidence and reproducible procedures; retain third-party attribution. Public APIs and external helpers may be useful parts of an adapter, but identify their provenance accurately.

