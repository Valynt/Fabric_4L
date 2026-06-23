"""Regression coverage for demo seed password handling."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
API_APP = REPO_ROOT / "services/api/app"
SEED_DATA = API_APP / "services/seed_data.py"


def test_api_production_tree_has_no_literal_seed_passwords() -> None:
    offenders: list[Path] = []
    for path in API_APP.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if "SeedAdmin" in source or "SeedAnalyst" in source:
            offenders.append(path.relative_to(REPO_ROOT))

    assert offenders == []


def test_seed_users_requires_explicit_dev_seed_password_env_vars() -> None:
    source = SEED_DATA.read_text(encoding="utf-8")

    assert "DEV_SEED_ADMIN_PASSWORD" in source
    assert "DEV_SEED_ANALYST_PASSWORD" in source
    assert 'hash_password("SeedAdmin' not in source
    assert 'hash_password("SeedAnalyst' not in source

