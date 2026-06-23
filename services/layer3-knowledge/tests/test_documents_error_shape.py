from __future__ import annotations

from types import SimpleNamespace

import pytest
from value_fabric.shared.error_handling.exceptions import ServiceUnavailableError

from src.api.models import DocumentExportRequest
from src.api.routes.documents import export_document


@pytest.mark.asyncio
async def test_export_document_returns_stable_error_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BrokenClient:
        async def __aenter__(self):
            raise RuntimeError("db://secret")

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("src.api.routes.documents.httpx.AsyncClient", lambda *a, **k: _BrokenClient())

    with pytest.raises(ServiceUnavailableError) as raised:
        await export_document(
            DocumentExportRequest(business_case_id="bc-1", format="pdf", document_type="business_case"),
            app_state=SimpleNamespace(),
            http_request=SimpleNamespace(
                state=SimpleNamespace(
                    request_id="req-l3-1",
                    governance_context=SimpleNamespace(tenant_id="tenant-a"),
                )
            ),
        )

    assert raised.value.status_code == 503
    assert raised.value.message == "Document export failed"
    assert raised.value.details["error_code"] == "L3_DOCUMENT_EXPORT_FAILED"
    assert raised.value.details["request_id"] == "req-l3-1"
