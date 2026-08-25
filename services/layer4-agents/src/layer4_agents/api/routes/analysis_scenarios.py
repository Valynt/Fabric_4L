from __future__ import annotations

"""Saved scenarios sub-router for Layer 4 business cases.

Provides CRUD endpoints for persisted business-case what-if scenarios
scoped strictly by tenant context.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import NotFoundError
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.policy_registry import authorize_action

from ...models.saved_scenario import SavedBusinessCaseScenario
from ..common.db import get_route_db
from .analysis_schemas import (
    SavedScenarioDetail,
    SavedScenarioSummary,
    SaveScenarioRequest,
)


def build_scenarios_router() -> APIRouter:
    router = APIRouter()

    @router.get("/cases/{case_id}/scenarios", response_model=list[SavedScenarioSummary])
    async def list_saved_scenarios(
        case_id: str,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> list[SavedScenarioSummary]:
        """List saved scenario metadata for a business case."""
        authorize_action("layer4.analysis.read_case", context)
        tenant_id = str(context.tenant_id)
        result = await db.execute(
            select(SavedBusinessCaseScenario)
            .where(
                SavedBusinessCaseScenario.case_id == case_id,
                SavedBusinessCaseScenario.tenant_id == tenant_id,
            )
            .order_by(SavedBusinessCaseScenario.created_at.desc())
        )
        records = result.scalars().all()
        return [
            SavedScenarioSummary(
                id=record.scenario_id,
                name=record.name,
                created_at=record.created_at.isoformat(),
            )
            for record in records
        ]

    @router.post(
        "/cases/{case_id}/scenarios",
        response_model=SavedScenarioDetail,
        status_code=status.HTTP_201_CREATED,
    )
    async def save_scenario(
        case_id: str,
        request: SaveScenarioRequest,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> SavedScenarioDetail:
        """Persist a business-case what-if scenario server-side."""
        authorize_action("layer4.analysis.write_case", context)
        now = datetime.now(UTC)
        record = SavedBusinessCaseScenario(
            scenario_id=f"scenario_{uuid4().hex}",
            case_id=case_id,
            tenant_id=str(context.tenant_id),
            name=request.name,
            adjustments=request.adjustments,
            created_at=now,
        )
        db.add(record)
        return SavedScenarioDetail(
            id=record.scenario_id,
            name=record.name,
            adjustments=request.adjustments,
            created_at=now.isoformat(),
        )

    @router.get(
        "/cases/{case_id}/scenarios/{scenario_id}", response_model=SavedScenarioDetail
    )
    async def get_saved_scenario(
        case_id: str,
        scenario_id: str,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> SavedScenarioDetail:
        """Fetch a saved scenario with sensitive adjustments from server storage."""
        authorize_action("layer4.analysis.read_case", context)
        result = await db.execute(
            select(SavedBusinessCaseScenario).where(
                SavedBusinessCaseScenario.case_id == case_id,
                SavedBusinessCaseScenario.scenario_id == scenario_id,
                SavedBusinessCaseScenario.tenant_id == str(context.tenant_id),
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            raise NotFoundError(message="Saved scenario not found")
        return SavedScenarioDetail(
            id=record.scenario_id,
            name=record.name,
            adjustments=record.adjustments,
            created_at=record.created_at.isoformat(),
        )

    @router.delete(
        "/cases/{case_id}/scenarios/{scenario_id}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    async def delete_saved_scenario(
        case_id: str,
        scenario_id: str,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> None:
        """Delete a saved scenario only within the authenticated tenant scope."""
        authorize_action("layer4.analysis.write_case", context)
        result = await db.execute(
            delete(SavedBusinessCaseScenario).where(
                SavedBusinessCaseScenario.case_id == case_id,
                SavedBusinessCaseScenario.scenario_id == scenario_id,
                SavedBusinessCaseScenario.tenant_id == str(context.tenant_id),
            )
        )
        if getattr(result, "rowcount", 0) == 0:
            raise NotFoundError(message="Saved scenario not found")

    return router
