from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "verify_workflow_registry",
    ROOT / "scripts" / "ci" / "verify_workflow_registry.py",
)
verify_workflow_registry = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(verify_workflow_registry)


class WorkflowRegistryVerifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.workflows_dir = self.root / ".github" / "workflows"
        self.workflows_dir.mkdir(parents=True)
        (self.root / "scripts" / "ci").mkdir(parents=True)
        (self.root / "scripts" / "ci" / "check_workflow_targets_and_artifacts.py").write_text(
            "print('ok')\n",
            encoding="utf-8",
        )
        (self.root / "package.json").write_text('{"scripts": {}}\n', encoding="utf-8")
        (self.root / "Makefile").write_text("noop:\n\t@echo ok\n", encoding="utf-8")
        self.registry_path = self.workflows_dir / "workflow-registry.json"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def write_workflow(self, filename: str, *, extra: str = "") -> None:
        (self.workflows_dir / filename).write_text(
            "\n".join(
                [
                    "name: Test Workflow",
                    "on:",
                    "  push:",
                    "jobs:",
                    "  test:",
                    "    runs-on: ubuntu-latest",
                    "    steps:",
                    "      - run: echo ok",
                    extra,
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def entry(self, filename: str, **overrides: object) -> dict[str, object]:
        data: dict[str, object] = {
            "path": f".github/workflows/{filename}",
            "name": "Test Workflow",
            "owner": "@value-fabric/sre-leads",
            "trigger": ["push"],
            "trigger_purpose": f"{filename.replace('-', '_')} validates test workflow",
            "blocking": True,
            "required_secrets": [],
            "produced_artifacts": [],
            "runtime_budget_minutes": 30,
            "local_validation_command": "python scripts/ci/check_workflow_targets_and_artifacts.py",
            "deprecation_status": "active",
        }
        data.update(overrides)
        return data

    def write_registry(self, entries: list[dict[str, object]], duplicate_groups: list[dict[str, object]] | None = None) -> None:
        self.registry_path.write_text(
            json.dumps(
                {
                    "version": 1,
                    "schema_version": "test",
                    "last_audited": "test",
                    "duplicate_groups": duplicate_groups or [],
                    "workflows": entries,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    def errors(self) -> list[str]:
        return verify_workflow_registry.validate_registry(
            root=self.root,
            workflows_dir=self.workflows_dir,
            registry_path=self.registry_path,
        )

    def test_missing_workflow_registry_entry_fails(self) -> None:
        self.write_workflow("a.yml")
        self.write_workflow("b.yml")
        self.write_registry([self.entry("a.yml")])
        self.assertTrue(any("b.yml: workflow file is missing" in error for error in self.errors()))

    def test_stale_registry_entry_fails(self) -> None:
        self.write_workflow("a.yml")
        self.write_registry([self.entry("a.yml"), self.entry("stale.yml")])
        self.assertTrue(any("stale.yml: registry entry points to a missing workflow file" in error for error in self.errors()))

    def test_missing_owner_fails(self) -> None:
        self.write_workflow("a.yml")
        self.write_registry([self.entry("a.yml", owner="")])
        self.assertTrue(any("`owner` must be a non-empty string" in error for error in self.errors()))

    def test_missing_secret_metadata_fails(self) -> None:
        self.write_workflow("a.yml", extra="      - run: echo ${{ secrets.TEST_TOKEN }}")
        self.write_registry([self.entry("a.yml")])
        self.assertTrue(any("required_secrets" in error and "TEST_TOKEN" in error for error in self.errors()))

    def test_missing_artifact_metadata_fails(self) -> None:
        self.write_workflow(
            "a.yml",
            extra="\n".join(
                [
                    "      - uses: actions/upload-artifact@v4",
                    "        with:",
                    "          name: test",
                    "          path: artifacts/out.json",
                ]
            ),
        )
        self.write_registry([self.entry("a.yml")])
        self.assertTrue(any("produced_artifacts" in error and "artifacts/out.json" in error for error in self.errors()))

    def test_unregistered_duplicate_overlap_fails(self) -> None:
        self.write_workflow("a.yml")
        self.write_workflow("b.yml")
        self.write_registry(
            [
                self.entry("a.yml", trigger_purpose="shared gate a"),
                self.entry("b.yml", trigger_purpose="shared gate b"),
            ]
        )
        self.assertTrue(any("overlapping workflows require a duplicate_groups entry" in error for error in self.errors()))

    def test_deprecated_workflow_without_replacement_fails(self) -> None:
        self.write_workflow("a.yml")
        self.write_registry([self.entry("a.yml", deprecation_status="deprecated")])
        self.assertTrue(any("non-active workflow must declare" in error for error in self.errors()))


if __name__ == "__main__":
    unittest.main()
