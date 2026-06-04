"""Regression coverage for Layer 1 monolith tenant fail-closed behavior."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
APP_MONOLITH = REPO_ROOT / "services/layer1-ingestion/src/layer1_ingestion/api/app_monolith.py"


def test_app_monolith_does_not_trust_x_organization_id_without_context() -> None:
    source = APP_MONOLITH.read_text(encoding="utf-8")
    get_tenant_id_body = source.split("def get_tenant_id", 1)[1].split(
        "def get_current_user_id", 1
    )[0]

    assert "governance_context" in get_tenant_id_body
    assert "X-Organization-ID" not in get_tenant_id_body
    assert 'AuthenticationError(message = "Authentication required")' in get_tenant_id_body

