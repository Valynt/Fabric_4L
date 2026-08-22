"""Unit and regression tests for prospects_helpers extracted functions."""

from __future__ import annotations

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from layer4_agents.api.routes.prospects_helpers import (
    infer_buyer_role_from_title,
    resolve_enrichment_and_crm_status,
    trigger_prospect_workflow,
)


def test_infer_buyer_role_from_title():
    # None or empty title
    assert infer_buyer_role_from_title(None) == ("unavailable", None, None, "missing_title")
    assert infer_buyer_role_from_title("") == ("unavailable", None, None, "missing_title")

    # Executive titles
    status, role, conf, src = infer_buyer_role_from_title("VP of Engineering")
    assert status == "pending"
    assert role == "Economic Buyer"
    assert conf == 0.6
    assert src == "title_heuristic"

    status_cfo, role_cfo, conf_cfo, _ = infer_buyer_role_from_title("Chief Financial Officer")
    assert status_cfo == "pending"
    assert role_cfo == "Economic Buyer"

    # Non-executive title
    status_dev, role_dev, conf_dev, src_dev = infer_buyer_role_from_title("Software Developer")
    assert status_dev == "pending"
    assert role_dev is None
    assert conf_dev is None
    assert src_dev == "title_not_executive_pattern"


def test_resolve_enrichment_and_crm_status():
    enr, crm_st, crm_src, msg = resolve_enrichment_and_crm_status("Acme Corp", "Initial msg")
    assert enr in ["queued", "unavailable"]
    assert crm_st == "unavailable"
    assert crm_src in ["crm_service_unavailable", "crm_module_not_loaded"]


@pytest.mark.asyncio
async def test_trigger_prospect_workflow_no_executor():
    prospect_uuid = uuid.uuid4()
    mock_setup = MagicMock()
    mock_setup.company_name = "Acme"
    mock_setup.contact_name = "Jane Doe"
    mock_setup.contact_title = "CTO"
    mock_setup.primary_objective = "growth"
    mock_setup.buyer_role_confirmed = False
    mock_setup.company_confirmed = False
    mock_setup.crm_reviewed = False

    w_id, status, msg = await trigger_prospect_workflow(
        executor=None,
        prospect_uuid=prospect_uuid,
        setup_data=mock_setup,
        workflow_type="prospect_analysis",
        priority_str="NORMAL",
        tenant_id="tenant-123",
        user_id="user-456",
    )
    assert w_id is None
    assert status == "degraded"
    assert "unavailable" in msg


@pytest.mark.asyncio
async def test_trigger_prospect_workflow_with_executor():
    prospect_uuid = uuid.uuid4()
    mock_setup = MagicMock()
    mock_setup.company_name = "Acme"
    mock_setup.contact_name = "Jane Doe"
    mock_setup.contact_title = "CTO"
    mock_setup.primary_objective = "growth"
    mock_setup.buyer_role_confirmed = False
    mock_setup.company_confirmed = False
    mock_setup.crm_reviewed = False

    mock_executor = MagicMock()
    mock_result = MagicMock()
    mock_result.workflow_id = "wf-789"
    mock_executor.execute_workflow = AsyncMock(return_value=mock_result)

    w_id, status, msg = await trigger_prospect_workflow(
        executor=mock_executor,
        prospect_uuid=prospect_uuid,
        setup_data=mock_setup,
        workflow_type="prospect_analysis",
        priority_str="HIGH",
        tenant_id="tenant-123",
        user_id="user-456",
    )
    assert w_id == "wf-789"
    assert status == "started"
    assert "wf-789" in msg


@pytest.mark.asyncio
async def test_trigger_prospect_workflow_executor_failure():
    prospect_uuid = uuid.uuid4()
    mock_setup = MagicMock()
    mock_setup.company_name = "Acme"
    mock_setup.contact_name = "Jane Doe"
    mock_setup.contact_title = "CTO"
    mock_setup.primary_objective = "growth"
    mock_setup.buyer_role_confirmed = False
    mock_setup.company_confirmed = False
    mock_setup.crm_reviewed = False

    mock_executor = MagicMock()
    mock_executor.execute_workflow = AsyncMock(side_effect=RuntimeError("Cluster offline"))

    w_id, status, msg = await trigger_prospect_workflow(
        executor=mock_executor,
        prospect_uuid=prospect_uuid,
        setup_data=mock_setup,
        workflow_type="prospect_analysis",
        priority_str="NORMAL",
        tenant_id="tenant-123",
        user_id="user-456",
    )
    assert w_id is None
    assert status == "degraded"
    assert "Cluster offline" in msg
