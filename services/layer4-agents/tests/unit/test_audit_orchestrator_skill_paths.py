"""Unit tests for audit_orchestrator skill-path resolution after the
.agent/skills -> agents/skills promotion (Slice S).

These tests exercise the dual-layout resolution: the canonical
``agents/skills`` path is preferred, the legacy ``.agent/skills`` path is a
fallback, and an absent layout is handled gracefully.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from layer4_agents.agents.audit_orchestrator.analyzers import catalog_checks


def _make_repo_audit(root: Path, skills_root: Path) -> None:
    skill = skills_root / "repo-audit"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# repo-audit\n", encoding="utf-8")
    (skill / "config.yaml").write_text("{}", encoding="utf-8")


@pytest.mark.unit
def test_resolve_skills_root_prefers_canonical(tmp_path: Path) -> None:
    (tmp_path / "agents" / "skills").mkdir(parents=True)
    (tmp_path / ".agent" / "skills").mkdir(parents=True)
    assert catalog_checks._resolve_skills_root(tmp_path) == tmp_path / "agents" / "skills"


@pytest.mark.unit
def test_resolve_skills_root_falls_back_to_legacy(tmp_path: Path) -> None:
    (tmp_path / ".agent" / "skills").mkdir(parents=True)
    assert catalog_checks._resolve_skills_root(tmp_path) == tmp_path / ".agent" / "skills"


@pytest.mark.unit
def test_resolve_skills_root_none_when_absent(tmp_path: Path) -> None:
    assert catalog_checks._resolve_skills_root(tmp_path) is None


@pytest.mark.unit
def test_missing_repo_audit_skill_detects_canonical(tmp_path: Path) -> None:
    _make_repo_audit(tmp_path, tmp_path / "agents" / "skills")
    result = catalog_checks._check_missing_repo_audit_skill(tmp_path, None)
    assert result["triggered"] is False
    assert result["repo_audit_skill_present"] is True


@pytest.mark.unit
def test_missing_repo_audit_skill_detects_legacy(tmp_path: Path) -> None:
    _make_repo_audit(tmp_path, tmp_path / ".agent" / "skills")
    result = catalog_checks._check_missing_repo_audit_skill(tmp_path, None)  # type: ignore[arg-type]
    assert result["triggered"] is False
    assert result["repo_audit_skill_present"] is True


@pytest.mark.unit
def test_missing_repo_audit_skill_triggers_when_absent(tmp_path: Path) -> None:
    result = catalog_checks._check_missing_repo_audit_skill(tmp_path, None)  # type: ignore[arg-type]
    assert result["triggered"] is True
    assert result["repo_audit_skill_present"] is False
