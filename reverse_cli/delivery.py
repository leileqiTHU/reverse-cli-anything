"""Generate agent documentation and self-contained Skill bundles without loading targets."""
import json
import os
import re
import uuid
from pathlib import Path

from . import config, registry
from .research import save_new, sha256


def _text_new(path, text):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def _cell(value):
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def generate_docs(manifest_path, output):
    """Read saved data only: never import a hook or infer native verification."""
    manifest_path = Path(manifest_path).resolve(strict=True)
    entry = registry.manifest(manifest_path)
    root = Path(entry["_root"])
    destination = Path(output).resolve()
    if not destination.is_relative_to(root) or destination == root:
        raise ValueError("Generated documents must use a new subdirectory of the adapter root")
    catalog_path = registry.reference(entry, "toolSchema")
    catalog = registry.read(catalog_path)
    if catalog.get("adapter") != entry["id"] or not isinstance(catalog.get("tools"), list):
        raise ValueError("Mismatched or invalid saved tool catalog")
    coverage, sources = {}, [manifest_path, catalog_path]
    if entry.get("acceptance"):
        coverage_path = registry.reference(entry, "acceptance")
        document = registry.read(coverage_path)
        if document.get("adapter") != entry["id"]:
            raise ValueError("Coverage belongs to another adapter")
        for item in document.get("tools", []):
            if item["name"] in coverage:
                raise ValueError("Duplicate coverage entry")
            coverage[item["name"]] = item
        sources.append(coverage_path)
    names = set()
    for tool in catalog["tools"]:
        name = tool.get("name", "")
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. -]{0,127}", name):
            raise ValueError("Unsupported tool name for command documentation")
        if name in names or type(tool.get("mutates")) is not bool:
            raise ValueError("Duplicate tool or missing mutation classification")
        names.add(name)
        if not isinstance(tool.get("inputSchema"), dict) or not isinstance(tool.get("outputSchema"), dict):
            raise ValueError("Each tool needs saved input and output schemas")

    def relative(path):
        return Path(os.path.relpath(path, destination)).as_posix()

    lines = ["# " + entry["name"] + " command reference", "",
             "Generated from the saved catalog. No adapter hook or native command ran.", "",
             "Declared coverage is historical metadata, not fresh validation. Read the target's native notes before mutation.", "",
             "[Manifest](<" + relative(manifest_path) + ">) · [Tool schemas](<" + relative(catalog_path) + ">)", "",
             "Register that manifest with your selected framework before calling the tools.", "",
             "| Tool | Writes state | Provenance | Declared coverage |",
             "| --- | --- | --- | --- |"]
    for tool in catalog["tools"]:
        item = coverage.get(tool["name"], {})
        lines.append("| " + " | ".join(_cell(value) for value in (
            tool["name"], tool["mutates"], tool.get("provenance", "unspecified"), item.get("coverage", "not-run"))) + " |")
    for tool in catalog["tools"]:
        item = coverage.get(tool["name"], {})
        lines.extend(["", "## " + tool["name"], "", tool.get("description", "Consult the input contract and native implementation notes."), "",
                      "Run from the selected framework directory, after writing validated inputs to request.json:", "", "```text",
                      "python -B reverse-cli-anything.py call " + entry["id"] + " " + json.dumps(tool["name"]) + " --args @request.json", "```", "",
                      "Input schema:", "", "```json", json.dumps(tool["inputSchema"], ensure_ascii=False, indent=2), "```", "",
                      "Output schema (references resolve from the source catalog):", "", "```json",
                      json.dumps(tool["outputSchema"], ensure_ascii=False, indent=2), "```", "",
                      "Declared scope: " + str(item.get("scope", "No native coverage declared.")), "",
                      "Declared evidence: " + json.dumps(item.get("evidence", []), ensure_ascii=False)])
    native_links = []
    for field in ("readme", "skill", "acceptance"):
        if entry.get(field):
            native_links.append("- [" + field + "](<" + relative(registry.reference(entry, field)) + ">)")
    skill = ("---\nname: " + json.dumps(entry["id"]) + "\ndescription: " +
             json.dumps("Use the registered CLI for " + entry["name"] + "; inspect build constraints and declared coverage before operations.", ensure_ascii=False) +
             "\n---\n\n# " + entry["name"] + " CLI\n\n"
             "Read [commands and contracts](COMMANDS.md), then the source native notes below. "
             "This generated Skill describes saved metadata; generation did not verify native behavior.\n\n" +
             "\n".join(native_links) + "\n\n"
             "Use the selected framework to register the linked manifest and inspect readiness. "
             "Bind calls to the correct target, inputs and applicable execution context. Query native state before and after writes. "
             "On partial or unknown outcomes, inspect the retained operation before retrying. "
             "Follow the source Skill for target-specific lifecycle, units, constraints and recovery.\n")
    destination.mkdir(parents=True, exist_ok=False)
    _text_new(destination / "COMMANDS.md", "\n".join(lines) + "\n")
    _text_new(destination / "SKILL.md", skill)
    save_new(destination / "sources.json", {
        "schemaVersion": 1, "adapter": entry["id"], "nativeValidationRun": False,
        "sources": [{"path": relative(path), "sha256": sha256(path)} for path in sources]})
    return {"ok": True, "directory": str(destination), "tools": len(names), "nativeValidationRun": False}


def bundle_sources(root):
    files = []
    for pattern in ("reverse_cli/*.py", "schemas/*.schema.json", "templates/research/*", "docs/guides/*.md", "tests_shared/*.py", "tests_development/*.py"):
        files.extend(root.glob(pattern))
    documents = ("HARNESS", "SOP", "workflows", "development-tools", "install", "runtime", "adapter-contract", "architecture")
    for stem in documents:
        files.extend(root / "docs" / (stem + suffix + ".md") for suffix in ("", ".zh-CN"))
    for name in ("reverse-cli-anything.py", "reverse-cli-anything.ps1", "reverse-cli.py", "reverse-cli.ps1",
                 "reverse-cli.config.example.json", "requirements-dev.txt", "CONTRIBUTING.md", "CONTRIBUTING.zh-CN.md",
                 "skills/reverse-cli-anything/SKILL.md", "acceptance/README.md", "acceptance/README.zh-CN.md",
                 "tools/rea/README.md", "tools/rea/README.zh-CN.md"):
        files.append(root / name)
    for name in ("setup.py", "resolve-python.ps1", "research.py", "generate-docs.py", "install-skill.py", "build-catalog.py",
                 "check-contracts.py", "check-layout.py", "run-tests.py", "smoke-portable.py", "regress-native.py"):
        files.append(root / "tools" / name)
    for path in sorted(set(files)):
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError("Missing or unsafe bundle source: " + str(path))
    return sorted(set(files))


def install_skill(destination):
    """Stage an allowlisted resource bundle; do not alter host settings or existing skills."""
    root = config.ROOT.resolve()
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Refusing to replace an existing Skill: " + str(destination))
    destination = destination.resolve()
    sources = bundle_sources(root)
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = destination.parent / (".reverse-cli-anything-" + uuid.uuid4().hex)
    staging.mkdir()
    # Both resolved paths stay within the explicitly selected destination parent.
    if not staging.resolve().is_relative_to(destination.parent) or destination.parent != staging.parent:
        raise ValueError("Invalid staging location")
    for source in sources:
        target = staging / "framework" / source.relative_to(root)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    save_new(staging / "framework/registry.json", {"schemaVersion": 1, "project": "reverse-cli-anything", "adapters": []})
    skill = (root / "skills/reverse-cli-anything/SKILL.md").read_text(encoding="utf-8")
    _text_new(staging / "SKILL.md", skill.replace("(../../", "(framework/"))
    _text_new(staging / "framework/README.md", "# reverse-cli-anything\n\n## Quick start: install with your agent\n\n"
              "This is the self-contained framework resource bundle. Read the [installed Skill](../SKILL.md), "
              "[installation guide](docs/install.md) and [engineering manual](docs/HARNESS.md).\n")
    _text_new(staging / "framework/README.zh-CN.md", "# reverse-cli-anything\n\n## 最简安装：复制给你的 Agent\n\n"
              "这是独立框架资源包，请读取[已安装 Skill](../SKILL.md)、[安装指南](docs/install.zh-CN.md)和[工程手册](docs/HARNESS.zh-CN.md)。\n")
    records = [{"path": p.relative_to(staging).as_posix(), "sha256": sha256(p)}
               for p in sorted(staging.rglob("*")) if p.is_file()]
    save_new(staging / "bundle.json", {"schemaVersion": 1, "name": "reverse-cli-anything", "files": records,
             "scope": "Generic method, templates and framework only; no adapters, application binaries or local settings"})
    if destination.exists() or destination.is_symlink():
        raise FileExistsError("Destination appeared during installation; staged files retained at " + str(staging))
    staging.rename(destination)
    return {"ok": True, "skill": str(destination / "SKILL.md"), "framework": str(destination / "framework"),
            "files": len(records), "hostConfigurationChanged": False,
            "discovery": "Use the host's supported Skill directory and reload mechanism; installation does not confirm host discovery"}
