"""Executable contract for the mandatory security regression merge control."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_CHECK = REPO_ROOT / "scripts" / "ci" / "check_mandatory_security_gate_contract.py"
ENFORCEMENT_CHECK = REPO_ROOT / "scripts" / "ci" / "validate_mandatory_security_gate_enforcement.py"


def test_mandatory_security_gate_contract_is_enforced_locally() -> None:
    """The checked-in workflow, policy, and owners must expose one stable gate."""
    result = subprocess.run(
        [sys.executable, str(CONTRACT_CHECK)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )

    assert result.returncode == 0, result.stderr or result.stdout


def _enforcement_result(tmp_path: Path, protection: dict, rulesets: list[dict]) -> subprocess.CompletedProcess[str]:
    protection_path = tmp_path / "protection.json"
    rulesets_path = tmp_path / "rulesets.json"
    protection_path.write_text(json.dumps(protection), encoding="utf-8")
    rulesets_path.write_text(json.dumps(rulesets), encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(ENFORCEMENT_CHECK),
            "--branch-protection-file",
            str(protection_path),
            "--ruleset-file",
            str(rulesets_path),
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )


def test_effective_enforcement_accepts_only_the_governed_context(tmp_path: Path) -> None:
    protection = {
        "required_status_checks": {
            "strict": True,
            "checks": [{"context": "mandatory-security-regression", "app_id": 15368}],
        },
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "require_code_owner_reviews": True,
            "required_approving_review_count": 1,
        },
        "required_conversation_resolution": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }
    rulesets = [{"name": "Protect", "enforcement": "active", "bypass_actors": []}]

    result = _enforcement_result(tmp_path, protection, rulesets)

    assert result.returncode == 0, result.stderr or result.stdout


def test_effective_enforcement_rejects_ruleset_bypass_actors(tmp_path: Path) -> None:
    protection = {
        "required_status_checks": {
            "strict": True,
            "checks": [{"context": "mandatory-security-regression", "app_id": 15368}],
        },
        "enforce_admins": {"enabled": True},
        "required_pull_request_reviews": {
            "require_code_owner_reviews": True,
            "required_approving_review_count": 1,
        },
        "required_conversation_resolution": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }
    rulesets = [
        {
            "name": "Protect",
            "enforcement": "active",
            "bypass_actors": [{"actor_id": 1}],
        }
    ]

    result = _enforcement_result(tmp_path, protection, rulesets)

    assert result.returncode != 0
    assert "bypass actors" in result.stderr


def test_effective_enforcement_rejects_administrator_bypass(tmp_path: Path) -> None:
    protection = {
        "required_status_checks": {
            "strict": True,
            "checks": [{"context": "mandatory-security-regression", "app_id": 15368}],
        },
        "enforce_admins": {"enabled": False},
        "required_pull_request_reviews": {
            "require_code_owner_reviews": True,
            "required_approving_review_count": 1,
        },
        "required_conversation_resolution": {"enabled": True},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
    }

    result = _enforcement_result(tmp_path, protection, [])

    assert result.returncode != 0
    assert "enforce administrators" in result.stderr
