"""Guard the canonical Layer 4 v1 application factory and runtime entrypoint."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LAYER4 = ROOT / "services" / "layer4-agents"
CANONICAL_ENTRYPOINT = "layer4_agents.api.main:app"


def test_layer4_main_constructs_app_only_through_release_factory() -> None:
    main_path = LAYER4 / "src" / "layer4_agents" / "api" / "main.py"
    module = ast.parse(main_path.read_text(encoding="utf-8"))

    app_assignments = [
        node
        for node in module.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "app"
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
        )
    ]

    assert len(app_assignments) == 1
    assignment = app_assignments[0]
    value = assignment.value
    assert isinstance(value, ast.Call)
    assert isinstance(value.func, ast.Name)
    assert value.func.id == "create_app"
    assert value.args == []
    assert value.keywords == []


def test_layer4_deployable_bootstraps_use_canonical_release_entrypoint() -> None:
    dockerfiles = [
        LAYER4 / "Dockerfile",
        LAYER4 / "Dockerfile.full",
        LAYER4 / "Dockerfile.uv",
    ]

    for path in dockerfiles:
        content = path.read_text(encoding="utf-8")
        assert CANONICAL_ENTRYPOINT in content, f"{path} bypasses the Layer 4 v1 entrypoint"
        assert "src.api.main:app" not in content

    for name in ("docker-compose.dev.yml", "docker-compose.e2e.yml"):
        path = ROOT / "infra" / "compose" / name
        layer4_service = path.read_text(encoding="utf-8").split("\n  layer4:", 1)[1]
        layer4_service = re.split(r"\n  \S", layer4_service, maxsplit=1)[0]
        assert CANONICAL_ENTRYPOINT in layer4_service
        assert "src.api.main:app" not in layer4_service

    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    dev_command = package["scripts"]["dev:layer4"]
    assert CANONICAL_ENTRYPOINT in dev_command
    assert "services.layer4-agents" not in dev_command


def test_layer4_factory_is_only_production_app_constructor() -> None:
    production_files = (LAYER4 / "src" / "layer4_agents").rglob("*.py")
    constructors = [
        path.relative_to(ROOT)
        for path in production_files
        if "create_fabric_app(" in path.read_text(encoding="utf-8")
    ]

    assert constructors == [
        Path("services/layer4-agents/src/layer4_agents/api/app_factory.py")
    ]
