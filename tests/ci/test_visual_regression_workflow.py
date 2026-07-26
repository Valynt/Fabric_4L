from __future__ import annotations

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "visual-regression.yml"

EXPECTED_FRONTEND_ROUTE_ENV = {
    "VITE_API_BASE": "/api/v1",
    "VITE_L1_PREFIX": "/ingest",
    "VITE_L2_PREFIX": "/extract",
    "VITE_L2_5_PREFIX": "/signals",
    "VITE_L3_PREFIX": "/graph",
    "VITE_L4_PREFIX": "/agents",
    "VITE_L5_PREFIX": "/truths",
    "VITE_L6_PREFIX": "/benchmarks",
    "VITE_L7_PREFIX": "/billing",
}


def _workflow() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_visual_preview_server_has_production_api_route_defaults() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["test"]["steps"]
    preview_step = next(step for step in steps if step.get("name") == "Start preview server")

    assert preview_step.get("env") == EXPECTED_FRONTEND_ROUTE_ENV


def test_visual_workflow_uses_valid_playwright_snapshot_mode() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["test"]["steps"]
    visual_step = next(step for step in steps if step.get("name") == "Run visual regression tests")

    assert "--update-snapshots=${{ inputs.update_snapshots && 'all' || 'none' }}" in visual_step["run"]
    assert "--update-snapshots=false" not in visual_step["run"]


def test_visual_workflow_uses_existing_apps_web_playwright_project() -> None:
    workflow = _workflow()
    matrix = workflow["jobs"]["test"]["strategy"]["matrix"]

    assert matrix["project"] == ["journeys"]
