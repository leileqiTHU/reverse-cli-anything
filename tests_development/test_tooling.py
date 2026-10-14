"""Synthetic file-helper checks. No framework calls, adapter imports or native work."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reverse_cli import config, delivery, research


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def broken_links(root):
    failures = []
    for document in root.rglob("*.md"):
        for link in re.findall(r'!?\[[^\]]*\]\(([^)]+)\)', document.read_text(encoding="utf-8")):
            target = link.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            path = (document.parent / target).resolve()
            if not path.is_relative_to(root) or not path.exists():
                failures.append(str(document.relative_to(root)) + ": " + target)
    return failures


class FileHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = config.directory("cache") / "development-checks"
        cache.mkdir(parents=True, exist_ok=True)
        # Keep scoped fixtures for inspection; do not delete existing user paths.
        cls.root = Path(tempfile.mkdtemp(prefix="file-helpers-", dir=cache))
        cls.bundle = cls.root / "installed-skill"
        cls.install_result = delivery.install_skill(cls.bundle)
        print("Helper fixtures: " + str(cls.root), flush=True)

    def setUp(self):
        self.directory = self.root / self._testMethodName
        self.directory.mkdir()

    def workspace(self):
        result = research.initialize("sample-app", "Sample application", "Create and edit", ["create", "edit"], self.directory / "research")
        self.assertFalse(result["nativeImplemented"])
        return Path(result["directory"])

    def change_operations(self, root, change):
        path = root / "operations.json"
        value = json.loads(path.read_text(encoding="utf-8"))
        change(value["operations"])
        write_json(path, value)

    def adapter(self):
        root = self.directory / "sample adapter"
        root.mkdir()
        sentinel = "raise RuntimeError('TARGET CODE MUST NEVER EXECUTE')\n"
        (root / "entry.py").write_text(sentinel, encoding="utf-8")
        (root / "hooks.py").write_text(sentinel, encoding="utf-8")
        (root / "README.md").write_text("# Native semantics\n", encoding="utf-8")
        (root / "SKILL.md").write_text("# Maintained native lifecycle\n", encoding="utf-8")
        catalog = {"schemaVersion": 1, "adapter": "sample-app", "tools": [
            {"name": "object edit", "description": "Change a native object", "mutates": True,
             "provenance": "recovered-internal", "inputSchema": {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}},
             "outputSchema": {"type": "object"}}]}
        write_json(root / "tools.json", catalog)
        write_json(root / "acceptance.json", {"schemaVersion": 1, "adapter": "sample-app", "tools": [
            {"name": "object edit", "coverage": "historical-workflow", "scope": "An older build only", "evidence": []}]})
        manifest = {"schemaVersion": 1, "id": "sample-app", "name": "Sample application", "entrypoint": "entry.py", "runtime": "hooks.py",
                    "toolSchema": "tools.json", "readme": "README.md", "skill": "SKILL.md", "acceptance": "acceptance.json"}
        write_json(root / "adapter.json", manifest)
        return root

    def test_research_initialization_is_unverified(self):
        root = self.workspace()
        result = research.inspect(root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["declaredCounts"]["planned"], 2)
        self.assertEqual(result["declaredCounts"]["verified"], 0)
        self.assertIn("native assertions are not executed", result["scope"])

    def test_duplicate_operation_does_not_create_workspace(self):
        with self.assertRaises(ValueError):
            research.initialize("sample-app", "app", "goal", ["edit", "edit"], self.directory / "new")
        self.assertFalse((self.directory / "new").exists())

    def test_existing_research_preserved(self):
        root = self.workspace()
        digest = research.sha256(root / "task.json")
        with self.assertRaises(FileExistsError):
            research.initialize("another-app", "app", "goal", ["edit"], root)
        self.assertEqual(digest, research.sha256(root / "task.json"))

    def test_unknown_dependency_rejected(self):
        root = self.workspace()
        self.change_operations(root, lambda items: items[1].update(dependsOn=["missing"]))
        self.assertIn("unknown dependency", " ".join(research.inspect(root)["problems"]))

    def test_dependency_cycle_rejected(self):
        root = self.workspace()
        self.change_operations(root, lambda items: (items[0].update(dependsOn=["edit"]), items[1].update(dependsOn=["create"])))
        with self.assertRaisesRegex(ValueError, "Cyclic"):
            research.inspect(root)

    def test_blocked_needs_reason(self):
        root = self.workspace()
        self.change_operations(root, lambda items: items[0].update(status="blocked"))
        self.assertFalse(research.inspect(root)["ok"])

    def test_verified_needs_evidence(self):
        root = self.workspace()
        self.change_operations(root, lambda items: items[0].update(status="verified"))
        self.assertIn("no acceptance evidence", " ".join(research.inspect(root)["problems"]))

    def test_evidence_hash_and_tampering(self):
        root = self.workspace()
        path = root / "evidence/result.json"
        path.write_text('{"historical":true}', encoding="utf-8")
        self.change_operations(root, lambda items: items[0].update(status="verified", acceptanceEvidence=[{"path": "evidence/result.json", "sha256": research.sha256(path)}]))
        result = research.inspect(root)
        self.assertTrue(result["ok"])
        self.assertEqual(result["evidenceHashesChecked"], 1)
        path.write_text("changed", encoding="utf-8")
        self.assertFalse(research.inspect(root)["ok"])

    def test_reference_ownership_and_workspace_boundary(self):
        root = self.workspace()
        write_json(root / "entrypoints/candidate.json", {"operation": "edit"})
        self.change_operations(root, lambda items: items[0].update(entrypoints=["entrypoints/candidate.json"]))
        self.assertIn("mismatched operation", " ".join(research.inspect(root)["problems"]))
        write_json(self.directory / "outside.json", {"operation": "create"})
        self.change_operations(root, lambda items: items[0].update(entrypoints=["../outside.json"]))
        self.assertIn("invalid entrypoints", " ".join(research.inspect(root)["problems"]))

    def test_explicit_absolute_evidence_allowed(self):
        root = self.workspace()
        evidence = self.directory / "outside-evidence.json"
        evidence.write_bytes(b"published source")
        self.change_operations(root, lambda items: items[0].update(acceptanceEvidence=[{"path": str(evidence), "sha256": research.sha256(evidence)}]))
        self.assertEqual(research.inspect(root)["evidenceHashesChecked"], 1)

    def test_file_identity_and_overwrite_refusal(self):
        path = self.directory / "素材.bin"
        content = b"known bytes\x00\xff"
        path.write_bytes(content)
        result = research.fingerprint([path])
        self.assertEqual(result["files"][0]["sha256"], hashlib.sha256(content).hexdigest())
        self.assertEqual(result["files"][0]["bytes"], len(content))
        research.save_new(self.directory / "identity.json", result)
        with self.assertRaises(FileExistsError):
            research.save_new(self.directory / "identity.json", {})

    def test_generated_docs_do_not_execute_hooks(self):
        root = self.adapter()
        result = delivery.generate_docs(root / "adapter.json", root / "agent-docs")
        self.assertTrue(result["ok"])
        self.assertFalse(result["nativeValidationRun"])
        commands = (root / "agent-docs/COMMANDS.md").read_text(encoding="utf-8")
        self.assertIn("historical-workflow", commands)
        self.assertIn('"required": [', commands)
        self.assertIn('call sample-app "object edit" --args @request.json', commands)
        self.assertEqual(broken_links(root), [])

    def test_generated_source_hashes_survive_adapter_move(self):
        root = self.adapter()
        delivery.generate_docs(root / "adapter.json", root / "agent-docs")
        moved = self.directory / "moved adapter"
        # Both paths are known children of this test's dedicated fixture directory.
        self.assertEqual(root.resolve().parent, self.directory.resolve())
        self.assertEqual(moved.resolve().parent, self.directory.resolve())
        root.rename(moved)
        sources = json.loads((moved / "agent-docs/sources.json").read_text(encoding="utf-8"))
        for record in sources["sources"]:
            self.assertFalse(Path(record["path"]).is_absolute())
            self.assertEqual(research.sha256(moved / "agent-docs" / record["path"]), record["sha256"])
        self.assertEqual(broken_links(moved), [])

    def test_generated_docs_preserve_handwritten_output(self):
        root = self.adapter()
        output = root / "agent-docs"
        output.mkdir()
        (output / "SKILL.md").write_text("maintained", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            delivery.generate_docs(root / "adapter.json", output)
        self.assertEqual((output / "SKILL.md").read_text(encoding="utf-8"), "maintained")

    def test_generated_docs_reject_outside_root(self):
        root = self.adapter()
        with self.assertRaisesRegex(ValueError, "subdirectory"):
            delivery.generate_docs(root / "adapter.json", self.directory / "outside")

    def test_catalog_identity_mismatch_rejected(self):
        root = self.adapter()
        path = root / "tools.json"
        catalog = json.loads(path.read_text(encoding="utf-8"))
        catalog["adapter"] = "wrong-app"
        write_json(path, catalog)
        with self.assertRaisesRegex(ValueError, "Mismatched"):
            delivery.generate_docs(root / "adapter.json", root / "agent-docs")

    def test_missing_coverage_is_not_run(self):
        root = self.adapter()
        write_json(root / "acceptance.json", {"adapter": "sample-app", "tools": []})
        delivery.generate_docs(root / "adapter.json", root / "agent-docs")
        self.assertIn("not-run", (root / "agent-docs/COMMANDS.md").read_text(encoding="utf-8"))

    def test_bundle_hashes_and_resource_links(self):
        manifest = json.loads((self.bundle / "bundle.json").read_text(encoding="utf-8"))
        for record in manifest["files"]:
            self.assertEqual(research.sha256(self.bundle / record["path"]), record["sha256"])
        self.assertEqual(broken_links(self.bundle), [])

    def test_bundle_excludes_settings_and_unlisted_directories(self):
        paths = [path.relative_to(self.bundle).as_posix() for path in self.bundle.rglob("*")]
        for excluded in ("reverse-cli.local.json", ".reverse-cli", "__pycache__"):
            self.assertFalse(any(excluded in Path(path).parts for path in paths), excluded)
        allowed = {"reverse_cli", "schemas", "templates", "docs", "skills", "acceptance", "tools", "tests_shared", "tests_development"}
        actual = {path.name for path in (self.bundle / "framework").iterdir() if path.is_dir()}
        self.assertLessEqual(actual, allowed)
        registry = json.loads((self.bundle / "framework/registry.json").read_text(encoding="utf-8"))
        self.assertEqual(registry["adapters"], [])
        self.assertNotIn("examples", registry)
        self.assertFalse(self.install_result["hostConfigurationChanged"])
        self.assertNotIn("(../../", (self.bundle / "SKILL.md").read_text(encoding="utf-8"))

    def test_existing_skill_never_replaced(self):
        digest = research.sha256(self.bundle / "SKILL.md")
        with self.assertRaises(FileExistsError):
            delivery.install_skill(self.bundle)
        self.assertEqual(digest, research.sha256(self.bundle / "SKILL.md"))

    def test_installed_research_helper_runs_without_checkout(self):
        framework = self.bundle / "framework"
        script = framework / "tools/research.py"
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH" and not key.startswith("REVERSE_CLI_")}
        env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONIOENCODING="utf-8")
        command = [sys.executable, "-B", str(script), "init", "detached-app", "--application", "Detached app", "--goal", "Only records", "--operation", "edit", "--output", str(self.directory / "research")]
        result = subprocess.run(command, cwd=self.directory, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["nativeImplemented"])
        status = subprocess.run([sys.executable, "-B", str(script), "status", str(self.directory / "research")], cwd=self.directory, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(json.loads(status.stdout)["declaredCounts"]["planned"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
