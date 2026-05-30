from __future__ import annotations

import pytest
from fastapi import HTTPException

from src.api.app_monolith import _resolve_ingest_tenant_id


def test_ingest_tenant_resolution_requires_authenticated_context() -> None:
    with pytest.raises(HTTPException):
        _resolve_ingest_tenant_id("", None, None, allow_tenant_hints=False)


def test_ingest_tenant_resolution_rejects_hints_for_unauthorized_principal() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _resolve_ingest_tenant_id("tenant-a", "tenant-a", None, allow_tenant_hints=False)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Tenant hints are not allowed for this principal"


def test_ingest_tenant_resolution_rejects_forged_body_tenant() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _resolve_ingest_tenant_id("tenant-a", None, "tenant-b", allow_tenant_hints=True)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Request tenant_id does not match authenticated tenant context"


@pytest.mark.parametrize(
    ("header_tenant_id", "body_tenant_id", "expected"),
    [
        ("tenant-a", None, "tenant-a"),
        (" tenant-a ", None, "tenant-a"),
        (None, "tenant-a", "tenant-a"),
        ("tenant-a", "tenant-a", "tenant-a"),
    ],
)
def test_ingest_tenant_resolution_accepts_matching_hints_when_explicitly_authorized(
    header_tenant_id: str | None,
    body_tenant_id: str | None,
    expected: str,
) -> None:
    assert (
        _resolve_ingest_tenant_id("tenant-a", header_tenant_id, body_tenant_id, allow_tenant_hints=True)
        == expected
    )
