"""Check complete framework resources and retain installation settings for later sessions."""
import json
import os
from pathlib import Path
import re

from . import config, registry
from .delivery import bundle_sources
from .journal import write


def resources():
    root = config.ROOT.resolve()
    files = set(bundle_sources(root))
    required = files | {root / "README.md", root / "README.zh-CN.md", root / "registry.json"}
    bundled = root.name == "framework" and (root.parent / "bundle.json").is_file()
    if bundled:
        required.add(root.parent / "SKILL.md")
        files.update({root.parent / "SKILL.md", root / "README.md", root / "README.zh-CN.md"})

    def label(path):
        return os.path.relpath(path, root)

    failures = [label(path) for path in sorted(required) if not path.is_file()]
    links = 0
    for path in sorted(files):
        if path.suffix != ".md" or not path.is_file():
            continue
        for raw in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', path.read_text(encoding="utf-8")):
            target = raw.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            links += 1
            resolved = (path.parent / target).resolve()
            if resolved not in required or not resolved.is_file():
                failures.append(label(path) + ": " + target)
    for path in (root / "templates/research").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    return {"passed": not failures, "files": len(required), "localLinks": links, "failures": failures}


def configure():
    """Create missing settings only; existing configuration remains user-owned."""
    path = Path(os.environ.get("REVERSE_CLI_CONFIG", config.ROOT / "reverse-cli.local.json")).resolve()
    if path.exists():
        config.settings()  # Reject invalid JSON, without replacing the user's file.
        return {"path": str(path), "created": False}
    settings = {"python": config.python(), **{kind + "Dir": str(config.directory(kind)) for kind in ("cache", "state", "output")}, "adapters": {}}
    # Persist an explicit registry override too, so dropping temporary variables
    # does not switch the registration context in the next process.
    if os.environ.get("REVERSE_CLI_REGISTRY"):
        settings["registry"] = str(registry.registry_path())
    python = Path(settings["python"])
    if not python.is_absolute():
        import shutil
        resolved = shutil.which(settings["python"])
        if not resolved:
            raise ValueError("Cannot resolve the configured Python executable")
        settings["python"] = str(Path(resolved).resolve())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(settings, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"path": str(path), "created": True}


def record():
    root = config.ROOT.resolve()
    bundled = root.name == "framework" and (root.parent / "bundle.json").is_file()
    skill = root.parent / "SKILL.md" if bundled else root / "skills/reverse-cli-anything/SKILL.md"
    path = config.directory("state") / "installation.json"
    result = {
        "schemaVersion": 1, "frameworkRoot": str(root), "skill": str(skill),
        "python": config.python(), "configPath": str(Path(os.environ.get("REVERSE_CLI_CONFIG", root / "reverse-cli.local.json")).resolve()),
        "registry": str(registry.registry_path()),
        "directories": {kind: str(config.directory(kind)) for kind in ("cache", "state", "output")},
        "environmentOverrides": sorted(key for key in os.environ if key.startswith("REVERSE_CLI_")),
        "hostDiscovery": "not-verified",
    }
    write(path, result)
    return {**result, "recordPath": str(path)}
