"""Static ownership contracts for the Phase B task-runner manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "tools/fabric-cli/tasks.json"
PROJECT_PATHS = (
    ROOT / "tools/fabric-cli/project.json",
    ROOT / "apps/web/project.json",
    ROOT / "packages/platform-contract/project.json",
    ROOT / "services/layer1-ingestion/project.json",
    ROOT / "services/layer4-agents/project.json",
)

EXPECTED_NX_ROUTES = {
    "build": "web:build",
    "check-conflict-markers": "fabric-task-runner:check-conflict-markers",
    "check-no-nul-bytes": "fabric-task-runner:check-no-nul-bytes",
    "lint-layer1": "layer1-ingestion:lint",
    "lint-layer4": "layer4-agents:lint",
    "platform-contract:typecheck": "platform-contract:typecheck",
    "test-frontend": "web:test",
    "test-layer1": "layer1-ingestion:test",
    "typecheck-layer1": "layer1-ingestion:typecheck",
    "typecheck-layer4": "layer4-agents:typecheck",
    "web:typecheck": "web:typecheck",
}
EXPECTED_MAKE_ROUTES = {
    "check-health-ratchets": "check-health-ratchets",
    "contract-tests": "contract-tests",
    "down": "down",
    "lint": "lint",
    "migrate": "migrate",
    "test": "test",
    "typecheck": "typecheck",
    "up": "up",
    "verify": "verify",
}


def _load(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), path
    return document


def _projects() -> dict[str, dict[str, object]]:
    projects = {_load(path)["name"]: _load(path) for path in PROJECT_PATHS}
    assert len(projects) == len(PROJECT_PATHS)
    return projects


def test_manifest_is_the_sorted_bounded_phase_b_surface() -> None:
    manifest = _load(MANIFEST_PATH)
    assert manifest["schema_version"] == 1
    tasks = manifest["tasks"]

    assert list(tasks) == sorted(tasks)
    assert len(tasks) == 20
    assert {
        task: route["target"]
        for task, route in tasks.items()
        if route["kind"] == "nx"
    } == EXPECTED_NX_ROUTES
    assert {
        task: route["target"]
        for task, route in tasks.items()
        if route["kind"] == "make_delegate"
    } == EXPECTED_MAKE_ROUTES


def test_every_native_route_has_one_uncached_leaf_owner() -> None:
    projects = _projects()

    for route, reference in EXPECTED_NX_ROUTES.items():
        project_name, target_name = reference.split(":", maxsplit=1)
        assert project_name in projects, route
        target = projects[project_name]["targets"][target_name]

        assert target["executor"] == "nx:run-commands", route
        assert target["cache"] is False, route
        assert target["options"]["cwd"], route
        assert target["options"]["forwardAllArgs"] is True, route

        command = target["options"]["command"]
        assert not re.search(r"(^|\s)(?:make|fabric)(?:\s|$)", command), (
            f"{route} delegates to another orchestration owner: {command}"
        )


def test_nx_is_local_offline_and_ignored_by_git() -> None:
    nx_config = _load(ROOT / "nx.json")
    package = _load(ROOT / "package.json")
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

    assert nx_config == {
        "$schema": "./node_modules/nx/schemas/nx-schema.json",
        "defaultBase": "main",
        "neverConnectToCloud": True,
        "plugins": [],
    }
    assert package["devDependencies"]["nx"] == "23.1.2"
    assert package["scripts"]["fabric"] == "node tools/fabric-cli/bin/fabric.mjs"
    assert package["scripts"]["test:fabric-cli"] == (
        "node --test tools/fabric-cli/tests/*.test.mjs"
    )
    assert ".nx/" in gitignore
