# Install reverse-cli-anything

[中文](install.zh-CN.md) · [Runtime](runtime.md) · [Generic Skill](../skills/reverse-cli-anything/SKILL.md)

This guide is for the agent performing installation. The user supplies the [README installation prompt](../README.md#quick-start-install-with-your-agent); the agent executes the steps below and reports the result. The user does not need to run these commands manually.

Installation prepares the framework. It does not select, install, activate, analyze or modify a target application. No showcase application, example dependency, Frida installation or decompiler is required for the core checks.

## Choose the execution directory

1. Clone the repository from the address supplied by the user, or use the supplied local checkout. Resolve an absolute path and respect the user's storage configuration.
2. Locate Python 3.11 or newer and record its absolute executable path. Reuse a compatible interpreter or install one if needed. The framework and core checks use the standard library. In the commands below, `python` means that verified interpreter, not an assumed PATH entry.
3. Read [the generic Skill](../skills/reverse-cli-anything/SKILL.md) and choose one installation mode:

| Mode | Installation action | Execution directory for all later commands |
| --- | --- | --- |
| Installed Skill | Determine the host's supported Skill directory. From the checkout, run `python -B tools/install-skill.py --destination "<new-skill-directory>"`. | The absolute `framework` path returned by the installer, inside the installed Skill. |
| Checkout | Keep the checkout and provide its Skill path to the agent. | The absolute checkout path. |

The installed Skill contains a separate framework copy. Configure that copy before registering adapters; checkout configuration and registrations are not copied into it. Avoid switching between copies during one workflow. The [bundle guide](development-tools.md#install-a-complete-generic-skill) describes upgrades and resource verification.

## Configure and verify the selected directory

Change to the chosen execution directory. Select storage paths through [configuration](runtime.md#configuration) before running setup. Use absolute paths in persistent configuration. `--configure` creates missing local settings from the effective interpreter and directories; it preserves an existing settings file. Environment variables take precedence and should be retained only when intentional.

```powershell
python -B tools/setup.py --configure
python -B reverse-cli-anything.py doctor
python -B reverse-cli-anything.py list
python -B tools/run-tests.py core
python -B tools/smoke-portable.py
```

Setup verifies the required method, scripts, templates and their local references. A successful configuration also writes `installation.json` into the configured state directory, recording the execution directory, interpreter, settings, registry and resource locations. `python -B tools/setup.py` checks an existing installation without creating settings.

The smoke check installs a complete temporary Skill bundle, starts fresh processes without inherited framework variables, and exercises research records, synthetic adapter registration/calls and documentation generation. It performs no target application work. Reports and temporary files use the configured output/cache directories.

Start a fresh terminal or process without temporary installation variables and run setup and `list` again from the selected directory. Confirm the same interpreter and state paths. An empty adapter list is valid before a target has been selected.

## Make the installation available to the next conversation

For installed Skills, use the host's supported reload mechanism and confirm it can load the installed `SKILL.md` and a referenced resource. If host discovery cannot be tested, report it as pending and provide the absolute Skill path for direct reading. Checkout mode similarly requires that path to be available in the new conversation.

Report the execution directory, Skill path, installation-record path, checks and discovery status. Keep this installation record with the framework; target work should use its configuration and registry. Installation is complete when the resources and interpreter work from the chosen directory; automatic Skill discovery is a separate host check.

For development-time JSON Schema checks, install [requirements-dev.txt](../requirements-dev.txt) in your development environment and run `python -B tools/check-contracts.py`. These packages are optional for normal core operation.

After installation, wait for the user to name a software target and operations. Start with [the SOP](SOP.md#start-a-target-task): establish target access, requested postconditions and existing interface coverage before selecting research tools or creating an adapter. [Research tool guidance](../tools/rea/README.md) covers analyzer readiness; target dependencies, platforms, builds and activation belong to the adapter.

The canonical launchers are `reverse-cli-anything.py` and `reverse-cli-anything.ps1`. The earlier `reverse-cli.py` / `.ps1`, `REVERSE_CLI_*` configuration names and local state format remain compatible. Existing installations are not moved.
