"""Release Policy: v1 launch-contract artifacts are valid and enforceable.

Validates the machine-readable release factory contract under release/v1/:

- Schemas (task/result/candidate-manifest) are valid JSON Schema drafts.
- The launch contract references journey files, gates, and harness scripts
  that actually exist, so no agent can claim readiness against a phantom gate.
- Every task file conforms to task.schema.json, references only existing
  make targets / scripts / test paths, and the dependency graph is acyclic.
- Architecture invariants map to existing enforcement or to a tracked task.

Design principles (matching this suite):
- Structural parsing of machine-readable policy files, no live services.
- Fail closed: a dangling reference is a release-policy failure.
"""

from __future__ import annotations

import json
import re
import shlex
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RELEASE_V1 = REPO_ROOT / "release" / "v1"
MAKEFILE = REPO_ROOT / "Makefile"

TASK_SCHEMA_PATH = RELEASE_V1 / "schemas" / "task.schema.json"
RESULT_SCHEMA_PATH = RELEASE_V1 / "schemas" / "result.schema.json"
MANIFEST_SCHEMA_PATH = RELEASE_V1 / "schemas" / "candidate-manifest.schema.json"
RISK_SCHEMA_PATH = RELEASE_V1 / "schemas" / "risk-register.schema.json"
LAUNCH_CONTRACT_PATH = RELEASE_V1 / "launch-contract.yaml"
INVARIANTS_PATH = RELEASE_V1 / "architecture-invariants.yaml"
RISK_REGISTER_YAML = REPO_ROOT / "production-readiness" / "risk_register.yaml"
RISK_REGISTER_MD = REPO_ROOT / "production-readiness" / "risk_register.md"
TASKS_DIR = RELEASE_V1 / "tasks"
JOURNEYS_DIR = RELEASE_V1 / "journeys"


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path} must be a YAML mapping"
    return data


def _make_targets() -> set[str]:
    targets = set()
    for line in MAKEFILE.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+):", line)
        if match:
            targets.add(match.group(1))
    return targets


def _command_references_exist(command: str) -> str | None:
    """Return an error string if the command references a missing target/path."""
    parts = shlex.split(command)
    if not parts:
        return f"empty command: {command!r}"
    if parts[0] == "make":
        targets = _make_targets()
        for target in parts[1:]:
            if target.startswith("-"):
                continue
            if target not in targets:
                return f"make target {target!r} not found in Makefile ({command!r})"
    elif parts[0] in {"python", "python3", "bash", "sh"} and len(parts) > 1:
        if not (REPO_ROOT / parts[1]).exists():
            return f"script {parts[1]!r} does not exist ({command!r})"
    elif parts[0] == "pytest":
        skip_next = False
        for arg in parts[1:]:
            if skip_next:
                skip_next = False
                continue
            if arg in {"-m", "-k", "-n", "-p", "--junitxml"}:
                skip_next = True
                continue
            if arg.startswith("-") or "::" in arg:
                continue
            if not (REPO_ROOT / arg).exists():
                return f"pytest path {arg!r} does not exist ({command!r})"
    return None


class TestSchemasAreValid:
    @pytest.mark.parametrize(
        "schema_path",
        [TASK_SCHEMA_PATH, RESULT_SCHEMA_PATH, MANIFEST_SCHEMA_PATH, RISK_SCHEMA_PATH],
        ids=lambda p: p.name,
    )
    def test_schema_is_valid_draft7(self, schema_path: Path) -> None:
        assert schema_path.exists(), f"missing schema: {schema_path}"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft7Validator.check_schema(schema)

    def test_manifest_schema_forbids_in_flight_remediation(self) -> None:
        schema = json.loads(MANIFEST_SCHEMA_PATH.read_text(encoding="utf-8"))
        remediation = schema["properties"]["certification"]["properties"][
            "remediation_during_certification"
        ]
        assert remediation.get("const") is False, (
            "The candidate manifest must structurally forbid remediation during "
            "certification (fail-closed certifier rule)."
        )


class TestLaunchContract:
    def test_launch_contract_parses_and_is_frozen(self) -> None:
        contract = _load_yaml(LAUNCH_CONTRACT_PATH)
        assert contract["schema_version"] == 1
        assert contract["release"] == "v1"
        assert contract["status"] == "frozen"

    def test_layer2_5_signal_refinery_has_an_explicit_scope_decision(self) -> None:
        """services/layer2-5-signal-refinery exists in the repo and is built by
        `make docker-build`; it must not be implicitly deployed yet absent from
        the certified path — the launch contract must record an explicit
        Core-GA in/out decision."""
        assert (REPO_ROOT / "services" / "layer2-5-signal-refinery").is_dir()
        contract = _load_yaml(LAUNCH_CONTRACT_PATH)
        decision = contract["scope_decisions"].get("layer2_5_signal_refinery_in_scope")
        assert decision is not None, (
            "launch contract must record an explicit scope decision for "
            "layer2-5-signal-refinery (in scope -> journeys/invariants/image "
            "inventory; out of scope -> recorded decision requiring "
            "server-disabled evidence)"
        )
        assert decision["decision"] in {
            "in-scope-for-core-ga",
            "out-of-scope-for-core-ga",
        }
        if decision["decision"] == "in-scope-for-core-ga":
            journey = _load_yaml(JOURNEYS_DIR / "j02-core-value-case.yaml")
            assert "layer2-5-signal-refinery" in json.dumps(journey), (
                "in-scope layer2-5-signal-refinery must appear in journey j02"
            )

    def test_journey_files_exist_and_are_well_formed(self) -> None:
        contract = _load_yaml(LAUNCH_CONTRACT_PATH)
        journeys = contract["critical_journeys"]
        assert len(journeys) == 5, "launch contract defines exactly 5 v1 journeys (j01-j05)"
        for entry in journeys:
            journey_path = REPO_ROOT / entry["file"]
            assert journey_path.exists(), f"missing journey file: {entry['file']}"
            journey = _load_yaml(journey_path)
            assert journey["id"] == entry["id"], f"journey id mismatch in {entry['file']}"
            for key in (
                "title",
                "priority",
                "required_outcome",
                "steps",
                "allowed_behavior",
                "denied_behavior",
                "evidence",
            ):
                assert key in journey, f"journey {entry['id']} missing key {key!r}"
            assert journey["priority"] in {"P0", "P1"}
            assert journey["allowed_behavior"], f"journey {entry['id']} needs allowed behavior"
            assert journey["denied_behavior"], f"journey {entry['id']} needs denied behavior"

    def test_journey_evidence_paths_exist(self) -> None:
        for journey_file in sorted(JOURNEYS_DIR.glob("*.yaml")):
            journey = _load_yaml(journey_file)
            for test_path in journey["evidence"].get("existing_tests", []):
                assert (REPO_ROOT / test_path).exists(), (
                    f"journey {journey['id']} cites nonexistent evidence path {test_path!r}"
                )

    def test_canonical_gates_exist_in_makefile(self) -> None:
        contract = _load_yaml(LAUNCH_CONTRACT_PATH)
        targets = _make_targets()
        for name, command in contract["canonical_gates"].items():
            parts = command.split()
            assert parts[0] == "make", f"canonical gate {name} must be a make target"
            assert parts[1] in targets, (
                f"canonical gate {name} references missing make target {parts[1]!r}"
            )

    def test_harness_schemas_and_scripts_exist(self) -> None:
        contract = _load_yaml(LAUNCH_CONTRACT_PATH)
        harness = contract["harness"]
        for key in (
            "task_schema",
            "result_schema",
            "candidate_manifest_schema",
            "risk_register_schema",
            "tasks_dir",
        ):
            assert (REPO_ROOT / harness[key]).exists(), f"missing harness path: {harness[key]}"
        for name, script in harness["scripts"].items():
            script_path = REPO_ROOT / script
            assert script_path.exists(), f"missing harness script {name}: {script}"
            assert script_path.suffix == ".py", (
                f"harness must be the thin Python orchestrator, not shell: {script}"
            )
        targets = _make_targets()
        for name, command in harness["make_targets"].items():
            parts = command.split()
            assert parts[0] == "make" and parts[1] in targets, (
                f"harness make target {name} references missing target: {command!r}"
            )

    def test_no_shell_harness_remains(self) -> None:
        strays = sorted((REPO_ROOT / "scripts" / "release").glob("*.sh"))
        assert not strays, (
            f"shell harness scripts must be replaced by the Python orchestrator: {strays}"
        )


class TestArchitectureInvariants:
    def test_invariants_map_to_existing_enforcement_or_task(self) -> None:
        data = _load_yaml(INVARIANTS_PATH)
        task_ids = {path.stem for path in TASKS_DIR.glob("*.yaml")}
        targets = _make_targets()
        seen_ids: set[str] = set()
        for invariant in data["invariants"]:
            inv_id = invariant["id"]
            assert inv_id not in seen_ids, f"duplicate invariant id {inv_id}"
            seen_ids.add(inv_id)
            assert invariant["enforcement"] in {"existing", "task"}
            if invariant["enforcement"] == "existing":
                checks = invariant.get("checks", [])
                assert checks, f"invariant {inv_id} claims existing enforcement but lists no checks"
                for check in checks:
                    if check["type"] == "make":
                        assert check["target"] in targets, (
                            f"invariant {inv_id} references missing make target {check['target']!r}"
                        )
                    else:
                        assert (REPO_ROOT / check["path"]).exists(), (
                            f"invariant {inv_id} references missing path {check['path']!r}"
                        )
            else:
                assert invariant["task"] in task_ids, (
                    f"invariant {inv_id} references missing task {invariant['task']!r}"
                )


class TestTaskGraph:
    def _tasks(self) -> dict[str, dict]:
        tasks = {}
        for task_file in sorted(TASKS_DIR.glob("*.yaml")):
            task = _load_yaml(task_file)
            assert task_file.stem == task["id"], (
                f"task file name {task_file.name} must match its id {task['id']!r}"
            )
            tasks[task["id"]] = task
        assert tasks, "release/v1/tasks must contain at least one task"
        return tasks

    def test_tasks_conform_to_schema(self) -> None:
        schema = json.loads(TASK_SCHEMA_PATH.read_text(encoding="utf-8"))
        validator = Draft7Validator(schema)
        for task_id, task in self._tasks().items():
            errors = sorted(validator.iter_errors(task), key=lambda e: list(e.path))
            assert not errors, f"task {task_id} violates task.schema.json: " + "; ".join(
                e.message for e in errors
            )

    def test_task_acceptance_commands_reference_existing_targets(self) -> None:
        for task_id, task in self._tasks().items():
            for command in task["acceptance_tests"]:
                error = _command_references_exist(command)
                assert error is None, f"task {task_id}: {error}"

    def test_task_dependency_graph_is_acyclic_and_closed(self) -> None:
        tasks = self._tasks()
        for task_id, task in tasks.items():
            for dep in task.get("depends_on", []):
                assert dep in tasks, f"task {task_id} depends on unknown task {dep!r}"

        state: dict[str, int] = {}

        def visit(node: str, stack: tuple[str, ...]) -> None:
            if state.get(node) == 2:
                return
            assert state.get(node) != 1, f"dependency cycle: {' -> '.join(stack + (node,))}"
            state[node] = 1
            for dep in tasks[node].get("depends_on", []):
                visit(dep, stack + (node,))
            state[node] = 2

        for task_id in tasks:
            visit(task_id, ())


class TestCanonicalRiskRegister:
    """production-readiness/risk_register.yaml is the single canonical risk
    register; the .md file is a human view that must stay reconciled."""

    def test_risk_register_conforms_to_schema(self) -> None:
        schema = json.loads(RISK_SCHEMA_PATH.read_text(encoding="utf-8"))
        data = _load_yaml(RISK_REGISTER_YAML)
        errors = sorted(
            Draft7Validator(schema).iter_errors(data), key=lambda e: list(e.path)
        )
        assert not errors, "risk_register.yaml violates risk-register.schema.json: " + "; ".join(
            e.message for e in errors
        )

    def test_risk_register_task_links_exist(self) -> None:
        data = _load_yaml(RISK_REGISTER_YAML)
        task_ids = {path.stem for path in TASKS_DIR.glob("*.yaml")}
        for risk in data["risks"]:
            for task in risk.get("tasks", []):
                assert task in task_ids, (
                    f"risk {risk['id']} references missing task {task!r}"
                )

    def test_markdown_view_does_not_drift_from_canonical_yaml(self) -> None:
        data = _load_yaml(RISK_REGISTER_YAML)
        md_text = RISK_REGISTER_MD.read_text(encoding="utf-8")
        yaml_ids = {risk["id"] for risk in data["risks"]}
        md_ids = set(re.findall(r"PRR-\d+", md_text))
        assert yaml_ids == md_ids, (
            "risk register drift: PRR ids differ between risk_register.yaml "
            f"and risk_register.md (yaml-only={sorted(yaml_ids - md_ids)}, "
            f"md-only={sorted(md_ids - yaml_ids)})"
        )
        for risk in data["risks"]:
            row = next(
                (line for line in md_text.splitlines() if risk["id"] in line and line.startswith("|")),
                None,
            )
            assert row is not None, f"{risk['id']} missing from markdown table"
            assert risk["status"] in row, (
                f"risk register drift: {risk['id']} status {risk['status']!r} "
                "not reflected in risk_register.md row"
            )
            assert risk["severity"] in row, (
                f"risk register drift: {risk['id']} severity {risk['severity']!r} "
                "not reflected in risk_register.md row"
            )

    def test_no_second_risk_register_inside_release_v1(self) -> None:
        strays = [
            p
            for p in RELEASE_V1.rglob("*")
            if p.is_file() and "risk" in p.name and p.suffix in {".yaml", ".yml", ".md"}
        ]
        assert not strays, (
            "release/v1 must not contain a risk register (canonical register is "
            f"production-readiness/risk_register.yaml): {strays}"
        )

    def test_no_committed_generated_state_in_release_v1(self) -> None:
        contract = _load_yaml(LAUNCH_CONTRACT_PATH)
        forbidden_names = {
            "release-readiness.yaml",
            "current-state.yaml",
            "dependency-graph.yaml",
            "journey-coverage.yaml",
            "candidate-manifest.yaml",
        }
        strays = [p for p in RELEASE_V1.rglob("*") if p.name in forbidden_names]
        assert not strays, (
            f"generated candidate state must live under artifacts/release/<sha>/, not release/v1: {strays}"
        )
        assert "generated_never_committed" in contract["artifact_policy"]
