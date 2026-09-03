"""Regression tests for H-07 Dependabot stale-entry detection."""

from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "ci" / "validate_dependabot_coverage.py"


def load_validator_module():
    spec = importlib.util.spec_from_file_location("validate_dependabot_coverage", VALIDATOR_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stale_dependabot_entries_fail_for_missing_and_wrong_ecosystem_dirs(tmp_path, monkeypatch):
    validator = load_validator_module()
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    service_dir = tmp_path / "services" / "api"
    service_dir.mkdir(parents=True)
    (service_dir / "pyproject.toml").write_text("[project]\nname = 'api'\n", encoding="utf-8")
    (service_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")

    packages = validator.discover_packages()
    entries = {
        "pip": {"services/api", "services/obsolete-api"},
        "npm": {"services/api"},
        "docker": {"services/api"},
        "github-actions": {"missing-actions-root"},
    }

    stale_entries = validator.validate_stale_dependabot_entries(packages, entries)

    assert "pip: services/obsolete-api (directory does not exist)" in stale_entries
    assert "npm: services/api (no active npm manifest found)" in stale_entries
    assert "github-actions: missing-actions-root (directory does not exist)" in stale_entries
    assert all(not item.startswith("docker: services/api") for item in stale_entries)


def test_validate_coverage_reports_stale_entries_separately(tmp_path, monkeypatch):
    validator = load_validator_module()
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    package_dir = tmp_path / "apps" / "web"
    package_dir.mkdir(parents=True)
    (package_dir / "package.json").write_text('{"name":"web"}\n', encoding="utf-8")

    packages = validator.discover_packages()
    entries = {
        "pip": set(),
        "npm": {"apps/web", "frontend"},
        "docker": set(),
        "github-actions": set(),
    }
    codeowners = "/apps/web/ @services/frontend\n"

    missing_dependabot, missing_ownership, stale_dependabot = validator.validate_coverage(
        packages, entries, codeowners
    )

    assert missing_dependabot == []
    assert missing_ownership == []
    assert stale_dependabot == ["npm: frontend (directory does not exist)"]


def test_discover_packages_excludes_codex_worktrees(tmp_path, monkeypatch):
    validator = load_validator_module()
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    canonical_dir = tmp_path / "services" / "api"
    canonical_dir.mkdir(parents=True)
    (canonical_dir / "pyproject.toml").write_text("[project]\nname = 'api'\n", encoding="utf-8")

    linked_worktree_dir = tmp_path / ".codex-worktrees" / "old-branch" / "services" / "api"
    linked_worktree_dir.mkdir(parents=True)
    (linked_worktree_dir / "pyproject.toml").write_text(
        "[project]\nname = 'old-api'\n", encoding="utf-8"
    )

    packages = validator.discover_packages()

    assert packages["pip"] == {Path("services/api")}


def test_discover_packages_excludes_archived_dependency_snapshots(tmp_path, monkeypatch):
    validator = load_validator_module()
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)

    archived_dir = tmp_path / "docs" / "archive" / "frontend-snapshot"
    archived_dir.mkdir(parents=True)
    (archived_dir / "package.json").write_text('{"name":"historical-frontend"}\n', encoding="utf-8")

    live_dir = tmp_path / "apps" / "web"
    live_dir.mkdir(parents=True)
    (live_dir / "package.json").write_text('{"name":"web"}\n', encoding="utf-8")

    packages = validator.discover_packages()

    assert packages["npm"] == {Path("apps/web")}
