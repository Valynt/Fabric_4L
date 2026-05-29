from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.interfaces.formula_governance import FormulaStatus
from layer4_agents.interfaces.value_pack_service import (
    PackExecutionRequest,
    PackStatus,
    ValuePack,
)
from layer4_agents.services.formula_governance_service import Neo4jFormulaGovernanceService
from layer4_agents.services.value_pack_service import Neo4jValuePackService


@pytest.mark.asyncio
async def test_value_pack_get_pack_enforces_tenant_filter():
    driver = MagicMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session
    result = AsyncMock()
    result.single = AsyncMock(return_value=None)
    session.run = AsyncMock(return_value=result)

    svc = Neo4jValuePackService(driver)
    pack = await svc.get_pack("pack-1", tenant_id="tenant-a")

    assert pack is None
    _, kwargs = session.run.call_args
    assert kwargs["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_formula_governance_cross_tenant_formula_not_visible():
    driver = MagicMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session
    result = AsyncMock()
    result.single = AsyncMock(return_value=None)
    session.run = AsyncMock(return_value=result)

    svc = Neo4jFormulaGovernanceService(driver)
    governance = await svc.get_governance("formula-b", tenant_id="tenant-a")

    assert governance is None
    _, kwargs = session.run.call_args
    assert kwargs["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_formula_id_in_tenant_b_not_visible_from_tenant_a_regression():
    driver = MagicMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session

    check_result = AsyncMock()
    check_result.single = AsyncMock(return_value=None)
    session.run = AsyncMock(return_value=check_result)

    svc = Neo4jFormulaGovernanceService(driver)
    resp = await svc.activate(
        request=type("Req", (), {"formula_id": "shared-formula", "version": "1.0.0", "requested_by": "u1", "effective_date": None})(),
        tenant_id="tenant-a",
    )

    assert resp.success is False
    assert resp.new_status == FormulaStatus.DRAFT
    _, kwargs = session.run.call_args
    assert kwargs["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_execute_pack_ignores_crafted_variables_tenant_id():
    driver = MagicMock()
    session = AsyncMock()
    driver.session.return_value.__aenter__.return_value = session
    session.run = AsyncMock()

    svc = Neo4jValuePackService(driver)
    svc.get_pack = AsyncMock(  # type: ignore[method-assign]
        return_value=ValuePack(
            pack_id="pack-shared",
            name="Shared Pack",
            description="",
            industry="saas",
            segment=None,
            status=PackStatus.PUBLISHED,
            version="1.0.0",
            formulas=[],
        )
    )

    request = PackExecutionRequest(
        pack_id="pack-shared",
        workspace_id="ws-1",
        variables={"tenant_id": "tenant-b", "arr": 1000},
        user_id="user-a",
    )
    await svc.execute_pack(request=request, tenant_id="tenant-a")

    svc.get_pack.assert_awaited_once_with("pack-shared", "tenant-a")
    for call in session.run.call_args_list:
        assert call.kwargs["tenant_id"] == "tenant-a"
