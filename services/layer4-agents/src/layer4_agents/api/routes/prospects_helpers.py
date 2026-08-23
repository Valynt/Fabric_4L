"""Helper functions for prospect analysis route orchestration.

Decomposes the start_prospect_analysis hotspot into testable pure & async helpers:
- Buyer role heuristic inference
- Enrichment and CRM integration status resolution
- Prospect account record creation and update
- Workflow executor dispatch and error mapping
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.account import Account

if TYPE_CHECKING:
    from .prospects import (
        ProspectSetupData,
    )

logger = logging.getLogger(__name__)


def infer_buyer_role_from_title(title: str | None) -> tuple[str, str | None, float | None, str]:
    """Infer buyer role from contact title heuristic.

    Returns:
        tuple of (status_val, role, confidence, source)
    """
    if not title:
        return ("unavailable", None, None, "missing_title")

    title_lower = title.lower()
    executive_indicators = ["vp", "vice president", "director", "chief", "cfo", "cto", "ceo"]
    if any(ind in title_lower for ind in executive_indicators):
        return ("pending", "Economic Buyer", 0.6, "title_heuristic")

    return ("pending", None, None, "title_not_executive_pattern")


def resolve_enrichment_and_crm_status(
    company_name: str,
    initial_message: str | None = None,
) -> tuple[str, str, str, str | None]:
    """Resolve module availability for enrichment and CRM services.

    Returns:
        tuple of (enrichment_status_val, crm_status_val, crm_source, message)
    """
    enrichment_status = "unavailable"
    message = initial_message

    try:
        __import__("layer4_agents.services.enrichment_orchestrator", fromlist=["EnrichmentOrchestrator"])
        enrichment_status = "queued"
        message = message or f"Enrichment queued for {company_name}"
    except ImportError:
        enrichment_status = "unavailable"

    crm_status = "unavailable"
    try:
        __import__("layer4_agents.services.crm_sync_service", fromlist=["CRMSyncService"])
        crm_source = "crm_service_unavailable"
    except ImportError:
        crm_source = "crm_module_not_loaded"

    return enrichment_status, crm_status, crm_source, message


async def create_or_update_prospect_account(
    db: AsyncSession,
    prospect_uuid: uuid.UUID,
    setup_data: ProspectSetupData,
) -> Account:
    """Create a new prospect account or update existing account with setup data."""
    result = await db.execute(
        select(Account).where(
            Account.id == prospect_uuid,
            Account.provider == "value_fabric",  # Internal prospects
        )
    )
    existing_account = result.scalar_one_or_none()

    if existing_account:
        existing_account.name = setup_data.company_name
        existing_account.stage = "prospect"
        existing_account.contacts = existing_account.contacts or []
        primary_contact = {
            "provider_contact_id": str(uuid.uuid4()),
            "name": setup_data.contact_name,
            "title": setup_data.contact_title,
            "is_primary": True,
            "last_synced_at": datetime.now(UTC).isoformat(),
        }
        existing_account.contacts = [
            c for c in existing_account.contacts if not c.get("is_primary")
        ]
        existing_account.contacts.append(primary_contact)
        existing_account.updated_at = datetime.now(UTC)
        account = existing_account
    else:
        account = Account(
            id=prospect_uuid,
            provider="value_fabric",
            provider_record_id=f"vf_prospect_{prospect_uuid.hex[:8]}",
            name=setup_data.company_name,
            normalized_name=setup_data.company_name.lower().strip(),
            stage="prospect",
            contacts=[
                {
                    "provider_contact_id": str(uuid.uuid4()),
                    "name": setup_data.contact_name,
                    "title": setup_data.contact_title,
                    "is_primary": True,
                    "last_synced_at": datetime.now(UTC).isoformat(),
                }
            ],
            opportunities=[],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(account)

    await db.flush()
    await db.refresh(account)
    return account


async def trigger_prospect_workflow(
    executor: object | None,
    prospect_uuid: uuid.UUID,
    setup_data: ProspectSetupData,
    workflow_type: str,
    priority_str: str,
    tenant_id: str,
    user_id: str | None,
) -> tuple[str | None, str, str | None]:
    """Trigger the analysis workflow via executor if available.

    Returns:
        tuple of (workflow_id, overall_status_val, message)
    """
    if not executor:
        return (
            None,
            "degraded",
            "Prospect saved. Workflow executor unavailable - analysis queued for retry.",
        )

    try:
        from ...engine.types import TaskPriority

        priority_map = {
            "CRITICAL": TaskPriority.CRITICAL,
            "HIGH": TaskPriority.HIGH,
            "NORMAL": TaskPriority.NORMAL,
            "LOW": TaskPriority.LOW,
        }
        priority = priority_map.get(priority_str.upper(), TaskPriority.NORMAL)

        workflow_result = await executor.execute_workflow(
            workflow_type=workflow_type,
            input_data={
                "prospect_id": str(prospect_uuid),
                "company_name": setup_data.company_name,
                "contact_name": setup_data.contact_name,
                "contact_title": setup_data.contact_title,
                "primary_objective": setup_data.primary_objective,
                "buyer_role_confirmed": setup_data.buyer_role_confirmed,
                "company_confirmed": setup_data.company_confirmed,
                "crm_reviewed": setup_data.crm_reviewed,
            },
            tenant_id=tenant_id,
            user_id=user_id,
            priority=priority,
        )

        workflow_id = workflow_result.workflow_id
        return (
            workflow_id,
            "started",
            f"Workflow {workflow_id} started for prospect analysis",
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        return (
            None,
            "degraded",
            f"Prospect saved but workflow trigger failed: {e!r}",
        )
