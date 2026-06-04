from unittest.mock import MagicMock

import pytest

from src.services.competitive_intel_service import (
    CompetitiveIntelService,
    _get_tenant_id as get_competitive_tenant,
)
from src.services.product_service import (
    ProductService,
    _get_tenant_id as get_product_tenant,
)


def test_product_service_requires_context_tenant(monkeypatch):
    monkeypatch.setattr(
        'src.services.product_service.require_context',
        lambda: (_ for _ in ()).throw(RuntimeError('no context')),
    )
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        get_product_tenant()


def test_competitive_service_requires_context_tenant(monkeypatch):
    monkeypatch.setattr(
        'src.services.competitive_intel_service.require_context',
        lambda: (_ for _ in ()).throw(RuntimeError('no context')),
    )
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        get_competitive_tenant()


@pytest.mark.asyncio
async def test_product_run_cypher_requires_tenant_id():
    service = ProductService(MagicMock())
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        await service._run_cypher(MagicMock(), 'MATCH (p:Product) RETURN p', {})


@pytest.mark.asyncio
async def test_competitive_run_cypher_requires_tenant_id():
    service = CompetitiveIntelService(MagicMock())
    with pytest.raises(RuntimeError, match='tenant_id is required'):
        await service._run_cypher(MagicMock(), 'MATCH (c:Competitor) RETURN c', {})
