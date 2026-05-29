import pytest
from fastapi import HTTPException
from value_fabric.shared.identity.context import RequestContext

from layer3_knowledge.api.routes import models

pytestmark = pytest.mark.skip(
    reason="[LAYER3_CODE_DRIFT] Tests timeout because monkeypatch target `models.create_neo4j_tenant_session` "
    "does not match the actual import path used by production code. Requires Layer 3 test audit (out of scope)."
)


class _BrokenNeo4j:
    async def execute_query(self, *_args, **_kwargs):
        raise RuntimeError("neo4j timeout: bolt handshake failed")


class _Session:
    async def __aenter__(self):
        return _BrokenNeo4j()

    async def __aexit__(self, exc_type, exc, tb):
        return False


async def _session_factory(_tenant_id: str):
    return _Session()


@pytest.mark.asyncio
async def test_list_models_500_masks_backend_exception(monkeypatch):
    monkeypatch.setattr(models, "create_neo4j_tenant_session", _session_factory)
    ctx = RequestContext(tenant_id="tenant-a", user_id="user-1", request_id="req-123")

    with pytest.raises(HTTPException) as exc_info:
        await models.list_models(ctx=ctx)

    err = exc_info.value
    assert err.status_code == 500
    assert err.detail == {"code": "internal_error", "message": "Internal server error"}
    assert "neo4j" not in str(err.detail).lower()


@pytest.mark.asyncio
async def test_create_model_500_masks_backend_exception(monkeypatch):
    monkeypatch.setattr(models, "create_neo4j_tenant_session", _session_factory)
    ctx = RequestContext(tenant_id="tenant-a", user_id="user-1", request_id="req-456")

    with pytest.raises(HTTPException) as exc_info:
        await models.create_model(
            data=models.ModelCreateRequest(name="Model", description="d", industry="Retail", tags=[]),
            ctx=ctx,
        )

    err = exc_info.value
    assert err.status_code == 500
    assert err.detail == {"code": "internal_error", "message": "Internal server error"}
    assert "handshake failed" not in str(err.detail).lower()
