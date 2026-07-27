from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.policy_registry import authorize_action

from ...engine.executor import WorkflowExecutor
from ...models.business_case_record import BusinessCaseRecord
from ...models.workspace_tab_data import WorkspaceTabData
from ...services.tenant_cypher import fetch_tenant_validated_records
from ..common.db import get_route_db
from .analysis_schemas import WorkspaceEvidenceItem, WorkspaceEvidenceResponse

VALID_WORKSPACE_TABS = {
    "signals",
    "drivers",
    "evidence",
    "stakeholders",
    "action-plan",
    "value-model",
    "narrative",
    "intake",
    "evidence-links",
}


def build_workspace_router(
    *,
    get_executor: Callable[[], WorkflowExecutor],
    get_neo4j_driver: Callable[[Request], Any],
) -> APIRouter:
    router = APIRouter()

    @router.get("/cases/{case_id}/workspace/evidence", response_model=WorkspaceEvidenceResponse)
    async def get_workspace_evidence(
        case_id: str,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> WorkspaceEvidenceResponse:
        authorize_action("layer4.analysis.read_case", context)
        tenant_id = str(context.tenant_id)
        result = await db.execute(
            select(WorkspaceTabData).where(
                WorkspaceTabData.case_id == case_id,
                WorkspaceTabData.tab_key == "evidence",
                WorkspaceTabData.tenant_id == tenant_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return WorkspaceEvidenceResponse(evidence=[])
        payload = record.data if isinstance(record.data, dict) else {}
        evidence_items = payload.get("evidence", [])
        if not isinstance(evidence_items, list):
            raise ServiceUnavailableError(message="Invalid persisted evidence payload shape")
        normalized_items: list[dict[str, Any]] = []
        for item in evidence_items:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    **item,
                    "title": item.get("title") or item.get("claim") or item.get("id") or "Evidence",
                    "type": item.get("type") or "evidence",
                    "verification": item.get("verification")
                    or item.get("validation_status")
                    or "unverified",
                    "linkedSignals": item.get("linkedSignals") or item.get("linked_signals") or [],
                    "excerpt": item.get("excerpt") or item.get("claim") or "",
                }
            )
        return WorkspaceEvidenceResponse(
            evidence=[WorkspaceEvidenceItem.model_validate(item) for item in normalized_items]
        )

    @router.get("/cases/{case_id}/workspace/{tab_key}")
    async def get_workspace_tab(
        case_id: str,
        tab_key: str,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, Any]:
        """Get persisted workspace tab data."""
        authorize_action("layer4.analysis.read_case", context)
        if tab_key not in VALID_WORKSPACE_TABS:
            raise ValidationError(
                message=str(f"Invalid tab_key. Must be one of: {VALID_WORKSPACE_TABS}")
            )

        tenant_id = str(context.tenant_id)
        result = await db.execute(
            select(WorkspaceTabData).where(
                WorkspaceTabData.case_id == case_id,
                WorkspaceTabData.tab_key == tab_key,
                WorkspaceTabData.tenant_id == tenant_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            return {tab_key: []}
        data = record.data if isinstance(record.data, dict) else {"data": record.data}
        return data or {tab_key: []}

    @router.put("/cases/{case_id}/workspace/{tab_key}")
    async def update_workspace_tab(
        case_id: str,
        tab_key: str,
        payload: dict[str, Any],
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, Any]:
        """Update persisted workspace tab data."""
        authorize_action("layer4.analysis.write_case", context)
        if tab_key not in VALID_WORKSPACE_TABS:
            raise ValidationError(
                message=str(f"Invalid tab_key. Must be one of: {VALID_WORKSPACE_TABS}")
            )

        tenant_id = str(context.tenant_id)
        result = await db.execute(
            select(WorkspaceTabData).where(
                WorkspaceTabData.case_id == case_id,
                WorkspaceTabData.tab_key == tab_key,
                WorkspaceTabData.tenant_id == tenant_id,
            )
        )
        record = result.scalar_one_or_none()
        if record is None:
            record = WorkspaceTabData(
                case_id=case_id,
                tab_key=tab_key,
                tenant_id=tenant_id,
                data=payload,
            )
            db.add(record)
        else:
            record.data = payload

        return {"case_id": case_id, "tab": tab_key, "updated": True, "data": payload}

    @router.post("/cases/{case_id}/workspace/generate")
    async def generate_workspace_intelligence(
        case_id: str,
        request: Request,
        executor: WorkflowExecutor = Depends(get_executor),
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, Any]:
        """Generate workspace intelligence data for a case.

        Lightweight generation that surfaces existing Neo4j data (signals,
        hypotheses) for the account. No LLM call — just exposes graph data
        the frontend currently can't see.
        """
        authorize_action("layer4.analysis.write_case", context)
        record = await db.get(BusinessCaseRecord, case_id)
        if not record:
            raise NotFoundError(message=str(f"Case {case_id} not found"))

        if not context.tenant_id:
            raise AuthorizationError(
                message="Tenant context is required for workspace intelligence generation"
            )
        tenant_id = str(context.tenant_id)
        account_id = str(record.account_id)

        driver = get_neo4j_driver(request)

        signal_query = """
        MATCH (ps:PainSignal {account_id: $account_id, tenant_id: $tenant_id})
        RETURN ps {.id, .name, .category, .confidence_score, .impact_value, .trend} AS signal
        LIMIT 50
        """
        signals = []
        signal_records = await fetch_tenant_validated_records(
            driver=driver,
            query=signal_query,
            params={"account_id": account_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            operation="analysis.get_account_intelligence.signals",
        )
        for record_row in signal_records:
            signal = record_row["signal"]
            if signal:
                signals.append(
                    {
                        "id": signal.get("id", ""),
                        "name": signal.get("name", ""),
                        "category": signal.get("category", "Unknown"),
                        "confidence": int((signal.get("confidence_score") or 0.5) * 100),
                        "impact": signal.get("impact_value", "medium"),
                        "trend": signal.get("trend", "stable"),
                    }
                )

        hypothesis_query = """
        MATCH (vh:ValueHypothesis {account_id: $account_id, tenant_id: $tenant_id})
        RETURN vh {.id, .hypothesis_text, .confidence_score, .value_path_category, .status, .capability_name} AS hypothesis
        LIMIT 50
        """
        hypotheses = []
        hypothesis_records = await fetch_tenant_validated_records(
            driver=driver,
            query=hypothesis_query,
            params={"account_id": account_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            operation="analysis.get_account_intelligence.hypotheses",
        )
        for record_row in hypothesis_records:
            hypothesis = record_row["hypothesis"]
            if hypothesis:
                hypotheses.append(
                    {
                        "id": hypothesis.get("id", ""),
                        "hypothesis_text": hypothesis.get("hypothesis_text", ""),
                        "confidence": hypothesis.get("confidence_score", 0.5),
                        "value_path_category": hypothesis.get("value_path_category"),
                        "status": hypothesis.get("status", "draft"),
                        "capability_name": hypothesis.get("capability_name", ""),
                    }
                )

        tab_data: dict[str, dict[str, Any]] = {
            "signals": {"signals": signals},
            "drivers": {"drivers": hypotheses},
            "evidence": {"evidence": []},
            "stakeholders": {"stakeholders": []},
            "action-plan": {"recommendations": []},
            "value-model": {"value_models": []},
            "narrative": {"narratives": []},
        }

        tab_keys = list(tab_data.keys())
        existing_tabs = {}
        if tab_keys:
            result = await db.execute(
                select(WorkspaceTabData).where(
                    WorkspaceTabData.case_id == case_id,
                    WorkspaceTabData.tab_key.in_(tab_keys),
                    WorkspaceTabData.tenant_id == tenant_id,
                )
            )
            existing_tabs = {tab.tab_key: tab for tab in result.scalars().all()}

        for tab_key, data in tab_data.items():
            existing = existing_tabs.get(tab_key)
            if existing:
                existing.data = data
            else:
                db.add(
                    WorkspaceTabData(
                        case_id=case_id,
                        tab_key=tab_key,
                        tenant_id=tenant_id,
                        data=data,
                    )
                )

        return {
            "case_id": case_id,
            "account_id": account_id,
            "generated": True,
            "stats": {
                "signals": len(signals),
                "drivers": len(hypotheses),
                "evidence": 0,
                "stakeholders": 0,
            },
        }

    return router
