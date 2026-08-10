"""Static contract for executable visual regression coverage."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "apps" / "web" / "e2e" / "visual" / "regression.spec.ts"
WORKFLOW = ROOT / ".github" / "workflows" / "visual-regression.yml"


def test_visual_suite_uses_canonical_routed_pages() -> None:
    source = SPEC.read_text(encoding="utf-8")

    for route in (
        "/home",
        "/t/demo/accounts",
        "/t/demo/context",
        "/t/demo/governance",
        "/settings/profile",
    ):
        assert f'path: "{route}"' in source

    for obsolete in (
        'path: "/dashboard"',
        'path: "/workflows"',
        'path: "/knowledge-graph"',
        'path: "/tenant-admin"',
        "/storybook/iframe.html",
    ):
        assert obsolete not in source


def test_snapshot_refresh_uploads_reviewable_baselines() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["test"]["steps"]
    upload = next(
        step for step in steps if step.get("name") == "Upload generated baseline screenshots"
    )

    assert "inputs.update_snapshots" in upload["if"]
    assert upload["with"]["if-no-files-found"] == "error"
    assert upload["with"]["path"] == "apps/web/e2e/visual/**/*-snapshots/*.png"
