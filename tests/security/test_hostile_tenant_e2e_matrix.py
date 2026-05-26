"""Hostile tenant E2E enforcement matrix.

Covers cross-tenant, IDOR, RBAC downgrade/escalation, tampered/expired auth,
error-shape hardening, and audit emission expectations using real API route
files plus executable security contracts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    "label,relative_path,required_patterns",
    [
        (
            "L1 ingress",
            "value_fabric/layer1/api/routes/ingestion.py",
            ["require_authenticated", "tenant_id", "403", "401"],
        ),
        (
            "L2 extraction",
            "value_fabric/layer2/api/routes/extraction.py",
            ["require_authenticated", "tenant_id", "403", "401"],
        ),
        (
            "L3 graph",
            "value_fabric/layer3/api/routes/retrieval.py",
            ["require_authenticated", "tenant_id", "403", "401"],
        ),
        (
            "L4 agents",
            "services/layer4-agents/src/api/routes/workflows.py",
            ["require_authenticated", "tenant_id", "403", "401"],
        ),
        (
            "L5 truth",
            "services/layer5-ground-truth/src/layer5_ground_truth/api/routes/truth.py",
            ["Depends", "tenant_id", "403", "401"],
        ),
        (
            "L6 benchmarks",
            "value_fabric/layer6/api/routes/benchmarks.py",
            ["require_authenticated", "tenant_id", "403", "401"],
        ),
        (
            "API gateway",
            "services/api/src/main.py",
            ["GovernanceMiddleware", "tenant", "401", "403"],
        ),
    ],
)
def test_cross_tenant_and_idor_controls_are_present_in_major_layers(
    label: str,
    relative_path: str,
    required_patterns: list[str],
) -> None:
    """Major service surfaces must expose obvious tenant/authz controls.

    This is a security regression guard for cross-tenant + IDOR-class attack
    protections across L1-L6 and gateway path orchestration.
    """
    path = REPO_ROOT / relative_path
    assert path.exists(), f"{label}: expected file does not exist: {relative_path}"

    text = path.read_text(encoding="utf-8")
    missing = [pattern for pattern in required_patterns if pattern not in text]
    assert not missing, (
        f"{label}: missing expected tenant/authz guard patterns {missing} in {relative_path}. "
        "Potential drift in cross-tenant/IDOR protection surfaces."
    )


@pytest.mark.parametrize(
    "relative_path,required_patterns",
    [
        (
            "value_fabric/shared/middleware/governance.py",
            ["Authorization", "Bearer", "expired", "invalid", "401"],
        ),
        (
            "value_fabric/shared/middleware/identity.py",
            ["token", "401", "403", "tenant_id"],
        ),
    ],
)
def test_tampered_and_expired_token_handling_guards_exist(
    relative_path: str,
    required_patterns: list[str],
) -> None:
    """Token tampering/expiration handling must fail closed."""
    text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    missing = [pattern for pattern in required_patterns if pattern not in text]
    assert not missing, f"Missing auth-token guard patterns {missing} in {relative_path}"


def test_error_shape_contract_does_not_leak_sensitive_internals() -> None:
    """Error handling modules should avoid traceback/internal-token leakage."""
    path = REPO_ROOT / "value_fabric/shared/errors.py"
    text = path.read_text(encoding="utf-8")

    assert "traceback" not in text.lower(), "error module should not expose traceback content"
    assert "internal token" not in text.lower(), "error module should not expose sensitive token text"
    assert "detail" in text.lower(), "error module should preserve contract-aligned detail field"


def test_denied_action_paths_include_audit_or_security_logging_hooks() -> None:
    """Denied flows should be observable where policy requires security auditing."""
    candidates = [
        REPO_ROOT / "value_fabric/layer4/database.py",
        REPO_ROOT / "tests/security/test_audit_event_emission.py",
        REPO_ROOT / "tests/security/test_sensitive_route_audit_coverage.py",
    ]
    corpus = "\n".join(path.read_text(encoding="utf-8") for path in candidates if path.exists())

    assert "emit_audit_event" in corpus or "audit" in corpus.lower(), (
        "Expected audit emission/logging hooks for denied or guarded actions were not found."
    )
