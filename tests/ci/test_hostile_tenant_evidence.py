"""Test the hostile tenant evidence verification script."""

from __future__ import annotations

from pathlib import Path
import pytest

from scripts.ci.check_hostile_tenant_evidence import verify_hostile_evidence


def test_hostile_evidence_passes_on_repo(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[2]
    assert verify_hostile_evidence(repo_root) is True


def test_hostile_evidence_detects_missing_contracts(tmp_path: Path):
    # Setup dummy repo with missing contract
    tests_dir = tmp_path / "tests" / "tenancy"
    tests_dir.mkdir(parents=True)
    fixture_file = tests_dir / "hostile_fixtures.py"
    fixture_file.write_text("def assert_foreign_resource_exists(): pass", encoding="utf-8")

    test_file = tests_dir / "test_hostile_tenancy_contracts.py"
    test_file.write_text("def test_signed_url_replay_and_expiration_denial(): pass", encoding="utf-8")

    assert verify_hostile_evidence(tmp_path) is False
