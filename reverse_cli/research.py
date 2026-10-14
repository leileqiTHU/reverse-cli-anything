"""File-only research helpers; no target attachment, execution or inferred verification."""
import copy
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .registry import adapter_id, read

STATUSES = {"planned", "researching", "implemented", "verified", "blocked"}


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_new(path, value):
    """Exclusive creation prevents accidental replacement of research or evidence."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def fingerprint(files):
    observations = []
    for name in files:
        path = Path(name).resolve(strict=True)
        if not path.is_file():
            raise ValueError("Expected a file: " + str(path))
        before = path.stat()
        digest = sha256(path)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
            raise ValueError("File changed during fingerprinting: " + str(path))
        observations.append({"path": str(path), "bytes": after.st_size, "sha256": digest})
    if not observations:
        raise ValueError("At least one explicit file is required")
    return {"schemaVersion": 1, "capturedAt": datetime.now(timezone.utc).isoformat(),
            "scope": "File identity only; no native compatibility claim", "files": observations}


def initialize(adapter, application, goal, operation_ids, output):
    adapter_id(adapter)
    if not application.strip() or not goal.strip():
        raise ValueError("Application and goal must be nonempty")
    if not operation_ids or len(set(operation_ids)) != len(operation_ids):
        raise ValueError("Provide distinct requested operation IDs")
    for name in operation_ids:
        adapter_id(name)
    source = config.ROOT / "templates/research"
    task = read(source / "task.json")
    task.update(adapter=adapter, application=application, goal=goal)
    task["workflow"] = list(operation_ids)
    operations = read(source / "operations.json")
    item = operations["operations"][0]
    operations["operations"] = []
    for name in operation_ids:
        entry = copy.deepcopy(item)
        entry.update(id=name, description=name)
        operations["operations"].append(entry)
    build = read(source / "build-map.json")
    build["adapter"] = adapter
    root = Path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / "entrypoints").mkdir()
    (root / "experiments").mkdir()
    (root / "evidence").mkdir()
    for name, data in (("task.json", task), ("operations.json", operations), ("build-map.json", build)):
        save_new(root / name, data)
    return {"ok": True, "directory": str(root), "operations": len(operation_ids),
            "stage": "research-planned", "nativeImplemented": False}


def inspect(workspace):
    root = Path(workspace).resolve(strict=True)
    task, operations = read(root / "task.json"), read(root / "operations.json")
    adapter_id(task["adapter"])
    entries = operations["operations"]
    if task.get("schemaVersion") != 1 or operations.get("schemaVersion") != 1:
        raise ValueError("Unsupported research record version")
    if not isinstance(entries, list) or not entries:
        raise ValueError("No requested operations")
    ids = [entry["id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate operation IDs")
    for name in ids:
        adapter_id(name)
    problems, references, counts = [], 0, Counter()
    dependency_map = {}
    for entry in entries:
        name, state = entry["id"], entry["status"]
        if state not in STATUSES:
            raise ValueError("Unknown operation status: " + str(state))
        counts[state] += 1
        if state == "blocked" and not entry.get("blocker"):
            problems.append(name + ": blocked operation needs a reason")
        dependencies = entry.get("dependsOn", [])
        if not isinstance(dependencies, list):
            raise ValueError("dependsOn must be a list")
        dependency_map[name] = dependencies
        for dependency in dependencies:
            if dependency not in ids:
                problems.append(name + ": unknown dependency " + str(dependency))
        for field in ("entrypoints", "experiments"):
            for relative in entry.get(field, []):
                path = (root / relative).resolve()
                if not path.is_relative_to(root) or not path.is_file():
                    problems.append(name + ": invalid " + field + " reference " + relative)
                else:
                    record = read(path)
                    if record.get("operation") != name:
                        problems.append(name + ": mismatched operation in " + relative)
        evidence = entry.get("acceptanceEvidence", [])
        if not isinstance(evidence, list):
            raise ValueError("acceptanceEvidence must be a list")
        if state == "verified" and not evidence:
            problems.append(name + ": verified claim has no acceptance evidence")
        for item in evidence:
            path = (root / item["path"]).resolve()
            expected = item.get("sha256", "")
            if not re.fullmatch(r"[0-9a-f]{64}", expected):
                problems.append(name + ": invalid evidence digest")
            elif not path.is_file() or sha256(path) != expected:
                problems.append(name + ": missing or changed evidence " + item["path"])
            else:
                references += 1

    def visit(name, active, finished):
        if name in active:
            raise ValueError("Cyclic operation dependencies: " + name)
        if name in finished or name not in dependency_map:
            return
        active.add(name)
        for dependency in dependency_map[name]:
            visit(dependency, active, finished)
        active.remove(name)
        finished.add(name)

    finished = set()
    for name in ids:
        visit(name, set(), finished)
    return {"ok": not problems, "adapter": task["adapter"], "goal": task["goal"],
            "declaredCounts": {key: counts[key] for key in sorted(STATUSES)},
            "evidenceHashesChecked": references, "problems": problems,
            "scope": "Declared research progress and reference integrity only; native assertions are not executed"}
