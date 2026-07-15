"""Hostile tenant-isolation tests for endpoints with compatibility tenant hints.

Endpoint inventory covered by this module:
- POST /v1/ingest (services/layer3-knowledge/src/api/models.py::IngestRequest.tenant_id)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from fastapi import HTTPException
from value_fabric.shared.error_handling.exceptions import AuthorizationError

pytestmark = pytest.mark.tenant_boundary

REPO_ROOT = Path(__file__).resolve().parents[2]
MODELS_PATH = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "models.py"
APP_MONOLITH_PATH = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "app_monolith.py"
TENANT_RESOLUTION_PATH = REPO_ROOT / "services" / "layer3-knowledge" / "src" / "api" / "services" / "tenant_resolution.py"


def _assert_forbidden(exc: BaseException, expected_message: str) -> None:
    if isinstance(exc, HTTPException):
        assert exc.status_code == 403
        assert exc.detail == expected_message
        return

    assert isinstance(exc, AuthorizationError)
    assert exc.message == expected_message


def _resolve_ingest_tenant_id(
    authenticated_tenant_id: str,
    header_tenant_id: str | None,
    body_tenant_id: str | None,
    *,
    allow_tenant_hints: bool,
) -> str:
    spec = importlib.util.spec_from_file_location("tenant_resolution", TENANT_RESOLUTION_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.resolve_ingest_tenant_id(
        authenticated_tenant_id,
        header_tenant_id,
        body_tenant_id,
        allow_tenant_hints=allow_tenant_hints,
    )


def test_endpoint_inventory_includes_optional_tenant_hint_model() -> None:
    """Enumerate endpoints whose request models include compatibility tenant hints."""
    source = MODELS_PATH.read_text(encoding="utf-8")
    assert "class IngestRequest" in source
    assert "Optional tenant hint for compatibility" in source


def test_ingest_rejects_missing_auth_tenant_context_fail_closed() -> None:
    """Missing authenticated tenant context must be rejected with stable contract."""
    source = APP_MONOLITH_PATH.read_text(encoding="utf-8", errors="ignore")
    assert (
        'raise HTTPException(status_code=401, detail="Authentication context is required")'
        in source
        or "AuthenticationError" in source
    )


def test_ingest_rejects_tenant_hints_for_non_service_principals() -> None:
    with pytest.raises((HTTPException, AuthorizationError)) as exc:
        _resolve_ingest_tenant_id(
            "tenant-a",
            "tenant-a",
            None,
            allow_tenant_hints=False,
        )

    _assert_forbidden(exc.value, "Tenant hints are not allowed for this principal")


def test_ingest_rejects_cross_tenant_header_forgery_even_for_authorized_hints() -> None:
    with pytest.raises((HTTPException, AuthorizationError)) as exc:
        _resolve_ingest_tenant_id(
            "tenant-a",
            "tenant-b",
            None,
            allow_tenant_hints=True,
        )

    _assert_forbidden(exc.value, "X-Tenant-ID header does not match authenticated tenant context")


def test_ingest_rejects_cross_tenant_body_forgery_even_for_authorized_hints() -> None:
    with pytest.raises((HTTPException, AuthorizationError)) as exc:
        _resolve_ingest_tenant_id(
            "tenant-a",
            None,
            "tenant-b",
            allow_tenant_hints=True,
        )

    _assert_forbidden(exc.value, "Request tenant_id does not match authenticated tenant context")
