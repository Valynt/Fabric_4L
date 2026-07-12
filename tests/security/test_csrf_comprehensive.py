"""Comprehensive CSRF double-submit coverage for browser-cookie auth."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from layer4_agents.api.security.csrf import validate_double_submit
from layer4_agents.tenants.api.routes import oidc
from layer4_agents.tenants.api.routes import tenants as tenant_routes
from value_fabric.shared.error_handling import register_exception_handlers

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_COMPAT_SOURCE = (
    REPO_ROOT
    / "services"
    / "layer4-agents"
    / "src"
    / "layer4_agents"
    / "api"
    / "routes"
    / "frontend_compat.py"
)


def test_double_submit_rejects_missing_cookie_and_header() -> None:
    with pytest.raises(Exception) as exc:
        validate_double_submit(None, None)
    assert getattr(exc.value, "status_code", 403) == 403
    assert "missing" in str(getattr(exc.value, "detail", exc.value)).lower()


def test_double_submit_rejects_missing_header() -> None:
    with pytest.raises(Exception) as exc:
        validate_double_submit("csrf-token", None)
    assert getattr(exc.value, "status_code", 403) == 403


def test_double_submit_rejects_mismatch() -> None:
    with pytest.raises(Exception) as exc:
        validate_double_submit("csrf-token", "attacker-token")
    assert getattr(exc.value, "status_code", 403) == 403
    assert "mismatch" in str(getattr(exc.value, "detail", exc.value)).lower()


def test_double_submit_accepts_matching_ajax_header_and_cookie() -> None:
    assert validate_double_submit("csrf-token", "csrf-token") is None


def test_route_level_csrf_dependency_accepts_ajax_header_and_cookie() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/mutate")
    async def mutate(_csrf_ok: None = Depends(validate_double_submit)):
        return {"ok": True}

    client = TestClient(app)

    accepted = client.post(
        "/mutate",
        cookies={"vf_csrf_token": "csrf-token"},
        headers={"X-CSRF-Token": "csrf-token"},
    )
    rejected = client.post(
        "/mutate",
        cookies={"vf_csrf_token": "csrf-token"},
        headers={"X-CSRF-Token": "wrong-token"},
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 403


def _has_csrf_dependency(fn) -> bool:
    signature = inspect.signature(fn)
    return any(
        getattr(parameter.default, "dependency", None) is validate_double_submit
        for parameter in signature.parameters.values()
    )


def test_browser_cookie_session_mutation_routes_require_csrf() -> None:
    assert _has_csrf_dependency(oidc.auth_refresh)
    assert _has_csrf_dependency(oidc.auth_logout)


def test_tenant_settings_and_registration_mutation_routes_require_csrf() -> None:
    assert _has_csrf_dependency(tenant_routes.api_update_current_tenant_settings)
    source = FRONTEND_COMPAT_SOURCE.read_text(encoding="utf-8")
    assert "async def update_current_tenant_settings" in source
    assert "async def register_tenant_frontend_alias" in source
    assert source.count("Depends(validate_double_submit)") >= 2
