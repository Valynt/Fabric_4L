from __future__ import annotations

import importlib.util
import json
import re
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


WORKFLOW_REGISTRY_DOC = ROOT / ".github" / "workflows" / "WORKFLOW_REGISTRY.md"
WORKFLOW_README = ROOT / ".github" / "workflows" / "README.md"
WORKFLOW_REGISTRY_JSON = ROOT / ".github" / "workflows" / "workflow-registry.json"


def load_repository_registry_entries() -> dict[str, dict[str, object]]:
    data = json.loads(WORKFLOW_REGISTRY_JSON.read_text(encoding="utf-8"))
    return {str(entry["path"]): entry for entry in data["workflows"]}


def workflow_inventory_rows() -> dict[str, dict[str, str]]:
    source = WORKFLOW_REGISTRY_DOC.read_text(encoding="utf-8")
    start = source.index("## Inventory")
    end = source.index("## Overlap Register", start)
    rows: dict[str, dict[str, str]] = {}

    for line in source[start:end].splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 5:
            continue
        workflow = cells[0].strip("`")
        rows[workflow] = {
            "owner": cells[1].strip("`"),
            "blocking": cells[2],
            "triggers": cells[3].strip("`"),
            "local_validation": cells[4].strip("`"),
        }

    return rows


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


class WorkflowRegistryDocumentationTests(unittest.TestCase):
    def test_markdown_inventory_matches_json_workflow_paths(self) -> None:
        registry_paths = set(load_repository_registry_entries())
        markdown_paths = set(workflow_inventory_rows())

        self.assertEqual(markdown_paths, registry_paths)

    def test_markdown_inventory_fields_match_json_source_of_truth(self) -> None:
        registry_entries = load_repository_registry_entries()
        markdown_rows = workflow_inventory_rows()
        mismatches: list[str] = []

        for path, entry in registry_entries.items():
            row = markdown_rows.get(path)
            if row is None:
                mismatches.append(f"{path}: missing markdown row")
                continue

            expected_blocking = "yes" if entry["blocking"] else "no"
            expected_triggers = ", ".join(entry["trigger"])
            expected_command = str(entry["local_validation_command"])

            if row["owner"] != entry["owner"]:
                mismatches.append(f"{path}: owner {row['owner']} != {entry['owner']}")
            if row["blocking"] != expected_blocking:
                mismatches.append(f"{path}: blocking {row['blocking']} != {expected_blocking}")
            if row["triggers"] != expected_triggers:
                mismatches.append(f"{path}: triggers {row['triggers']} != {expected_triggers}")
            if row["local_validation"] != expected_command:
                mismatches.append(f"{path}: command {row['local_validation']} != {expected_command}")

        self.assertFalse(mismatches, "\n".join(mismatches))

    def test_workflow_readme_count_matches_current_workflow_files(self) -> None:
        source = WORKFLOW_README.read_text(encoding="utf-8")
        match = re.search(r"currently contains \*\*(\d+)\*\* GitHub Actions workflow files", source)

        self.assertIsNotNone(match, "workflow README must document the current workflow count")
        assert match is not None
        expected_count = len(verify_workflow_registry.workflow_files(ROOT / ".github" / "workflows"))

        self.assertEqual(int(match.group(1)), expected_count)


if __name__ == "__main__":
    unittest.main()
