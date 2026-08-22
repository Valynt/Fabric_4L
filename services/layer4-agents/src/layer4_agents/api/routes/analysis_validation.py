from __future__ import annotations

"""Validation seeding sub-router for Layer 4 analysis API.

Provides non-production endpoints for seeding auth contexts, issuing browser
validation sessions, and seeding deterministic business case lifecycle states.
"""

import asyncio
import logging
import os
import re
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Response,
)
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    ValidationError,
    ValueFabricException,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.jwt import encode_jwt
from value_fabric.shared.identity.policy_registry import authorize_action

from ...config.settings import get_settings
from ...engine.executor import WorkflowExecutor
from ...models.agent_state import (
    BusinessCaseAgentState,
    WorkflowStatus,
)
from ...services.account_service import AccountService
from ...services.business_case_service import BusinessCaseService
from ...tenants.models.api_key import APIKey
from ...tenants.models.tenant import IsolationTier, Tenant, TenantStatus
from ...tenants.models.user import User
from ..common.audit import emit_and_persist_audit
from ..common.db import get_route_db
from ..security.csrf import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, issue_csrf_token
from .analysis_schemas import (
    BusinessCaseLifecycleSeedRequest,
    ValidationAuthContextSeedRequest,
    ValidationSeededApiKey,
    ValidationSessionRequest,
)

logger = logging.getLogger(__name__)

from ...test_support.seed_runtime_config import (
    SEED_AUTH_SOURCE,
    SEED_PRIVILEGED_REASON,
    SEED_SERVICE_ACCOUNT_ID,
    SEED_VALIDATION_USER_IDS,
)

VALIDATION_USERS = [
    {
        "id": SEED_VALIDATION_USER_IDS["admin"],
        "email": "validation-admin@valuefabric.test",
        "display_name": "Validation Admin",
        "role": "super_admin",
    },
    {
        "id": SEED_VALIDATION_USER_IDS["reviewer"],
        "email": "validation-reviewer@valuefabric.test",
        "display_name": "Validation Reviewer",
        "role": "analyst",
    },
    {
        "id": SEED_VALIDATION_USER_IDS["read_only"],
        "email": "validation-readonly@valuefabric.test",
        "display_name": "Validation Read Only",
        "role": "read_only",
    },
    {
        "id": SEED_VALIDATION_USER_IDS["sales"],
        "email": "validation-sales@valuefabric.test",
        "display_name": "Validation Sales",
        "role": "analyst",
    },
]

VALIDATION_ACCOUNT_MAPPINGS = [
    {
        "provider_record_id": "acct-meridian-001",
        "backend_uuid": os.environ.get(
            "E2E_MERIDIAN_ACCOUNT_UUID", "00000000-0000-4000-e2e0-000000000101"
        ),
        "label": "Meridian Automotive",
    }
]


def require_validation_seed_allowed(
    http_request: Request,
    context: RequestContext,
    *,
    settings_provider: Callable[[], Any] | None = None,
) -> None:
    """Fail closed unless this is an authenticated, non-production seed request."""
    current_settings = settings_provider() if settings_provider else get_settings()
    if current_settings.environment == "production":
        raise AuthorizationError(message="Validation seeding is disabled in production")
    if not context.tenant_id:
        raise AuthorizationError(message="Validation seeding requires tenant context")
    reason = http_request.headers.get("X-Privileged-Reason", "").strip()
    if reason != SEED_PRIVILEGED_REASON:
        raise AuthorizationError(
            message="Validation seeding requires privileged reason"
        )


def context_tenant_uuid(context: RequestContext) -> UUID:
    """Return the authenticated tenant UUID or fail closed."""
    authorize_action("layer4.analysis.roi", context)
    try:
        return UUID(str(context.tenant_id))
    except (TypeError, ValueError) as exc:
        raise ValidationError(
            message="Validation seeding requires UUID tenant context"
        ) from exc


async def upsert_validation_tenant(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    tenant_name: str,
    tenant_slug: str,
    actor: str | None,
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    now = datetime.now(UTC)
    settings_payload = {
        "isolation_tier": IsolationTier.SHARED.value,
        "seeded": True,
        "seed_source": SEED_AUTH_SOURCE,
        "backend_integrated_validation": True,
    }
    if tenant is None:
        tenant = Tenant(
            id=tenant_id,
            name=tenant_name,
            slug=tenant_slug,
            status=TenantStatus.ACTIVE.value,
            settings=settings_payload,
            status_changed_at=now,
            status_reason="backend-integrated validation seed",
            status_changed_by=actor or SEED_SERVICE_ACCOUNT_ID,
        )
        db.add(tenant)
    else:
        tenant.name = tenant_name
        tenant.slug = tenant_slug
        tenant.status = TenantStatus.ACTIVE.value
        tenant.settings = {**(tenant.settings or {}), **settings_payload}
        tenant.updated_at = now
    return tenant


async def upsert_validation_users(
    db: AsyncSession, *, tenant_id: UUID
) -> list[dict[str, str]]:
    seeded: list[dict[str, str]] = []
    now = datetime.now(UTC)
    for user_data in VALIDATION_USERS:
        user_id = user_data["id"]
        user = await db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                tenant_id=tenant_id,
                email=str(user_data["email"]),
                display_name=str(user_data["display_name"]),
                role=str(user_data["role"]),
                status="active",
            )
            db.add(user)
        else:
            if user.tenant_id != tenant_id:
                raise ConflictError(message=f"Seeded user tenant mismatch: {user_id}")
            user.email = str(user_data["email"])
            user.display_name = str(user_data["display_name"])
            user.role = str(user_data["role"])
            user.status = "active"
            user.updated_at = now
        seeded.append(
            {
                "id": str(user_id),
                "email": str(user_data["email"]),
                "role": str(user_data["role"]),
                "status": "active",
            }
        )
    return seeded


async def upsert_validation_api_key(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    service_account_id: str,
    api_key_payload: ValidationSeededApiKey,
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", api_key_payload.key_hash):
        raise ValidationError(message="Seeded API key hash must be HMAC-SHA256 hex")

    metadata = {
        **api_key_payload.metadata,
        "seeded": True,
        "seed_source": SEED_AUTH_SOURCE,
        "service_account_id": service_account_id,
        "raw_secret_persisted": False,
    }
    key = await db.get(APIKey, api_key_payload.key_id)
    if key is None:
        key = APIKey(
            key_id=api_key_payload.key_id,
            tenant_id=tenant_id,
            user_id=None,
            name=api_key_payload.name,
            key_hash=api_key_payload.key_hash,
            prefix=api_key_payload.prefix,
            role=api_key_payload.role,
            permissions=api_key_payload.permissions or None,
            enabled=True,
            metadata_=metadata,
        )
        db.add(key)
    else:
        if key.tenant_id != tenant_id:
            raise ConflictError(message=f"Seeded API key tenant mismatch: {key.key_id}")
        key.name = api_key_payload.name
        key.key_hash = api_key_payload.key_hash
        key.prefix = api_key_payload.prefix
        key.role = api_key_payload.role
        key.permissions = api_key_payload.permissions or None
        key.enabled = True
        key.metadata_ = metadata

    return {
        "key_id": key.key_id,
        "prefix": key.prefix,
        "role": key.role,
        "permissions": key.permissions or [],
        "raw_secret_persisted": False,
    }


def seeded_business_case_output(
    *,
    case_id: str,
    account_id: UUID,
    tenant_id: str,
    lifecycle_status: str,
    document_url: str | None,
) -> dict[str, Any]:
    """Build canonical workflow output for deterministic business-case lifecycle evidence."""
    approved = lifecycle_status == "approved"
    title = (
        "Meridian Automation Business Case"
        if approved
        else "Draft Meridian Business Case"
    )
    approval_history = [
        {
            "event": "submitted",
            "actor": "e2e-admin-user",
            "timestamp": datetime.now(UTC).isoformat(),
            "outcome": "pending_approval",
        }
    ]
    if approved:
        approval_history.append(
            {
                "event": "approved",
                "actor": "e2e-reviewer-user",
                "timestamp": datetime.now(UTC).isoformat(),
                "outcome": "approved",
            }
        )

    recommendations = [
        "Approve phased automation rollout for Meridian Automotive with ROI governance checkpoints.",
        "Use traceable claims and linked evidence before executive export.",
        "Push approved ROI summary to CRM for sales follow-up.",
        "Convert approved business case into post-sale realization action plan and track outcomes.",
    ]

    return {
        "assemble_document": {
            "title": title,
            "executive_summary": (
                "Executive summary: Meridian Automotive can capture validated automation value "
                "through a governed rollout with evidence-backed claims, approval history, "
                "CRM follow-up, and post-sale realization tracking."
            ),
            "total_estimated_value": 1_850_000.0 if approved else 0.0,
            "implementation_cost_estimate": 420_000.0 if approved else 0.0,
            "roi_ratio": 4.4 if approved else 0.0,
            "payback_months": 9 if approved else 0,
            "confidence_score": 0.86 if approved else 0.42,
            "recommendations": recommendations if approved else recommendations[:2],
            "status": lifecycle_status,
            "document_url": document_url,
            "page_count": 12 if approved else 0,
            "file_size_bytes": 245_760 if approved else 0,
            "truth_references": [
                {
                    "truth_object_id": "truth-meridian-automation-001",
                    "claim": "Automation reduces quote-to-cash cycle time",
                    "source": "Meridian validation workspace evidence",
                    "confidence": 0.88,
                }
            ],
            "remediation_items": (
                []
                if approved
                else [
                    {
                        "code": "APPROVAL_REQUIRED",
                        "message": "Draft must be approved before export",
                    }
                ]
            ),
            "case_metadata": {
                "tenant_id": tenant_id,
                "account_id": str(account_id),
                "approval_history": approval_history,
                "export_allowed": approved,
                "crm_push_available": approved,
                "realization_conversion_available": approved,
                "seed_source": SEED_PRIVILEGED_REASON,
            },
        },
        "verify_truth_requirements": {
            "passed": approved,
            "truth_references": [
                {
                    "truth_object_id": "truth-meridian-automation-001",
                    "claim": "Automation reduces quote-to-cash cycle time",
                }
            ],
            "remediation_items": (
                []
                if approved
                else [{"code": "APPROVAL_REQUIRED", "message": "Approval is required"}]
            ),
        },
        "generate_sdes": {
            "status": "seeded",
            "lineage": {
                "case_id": case_id,
                "account_id": str(account_id),
                "tenant_id": tenant_id,
            },
        },
        "synthesize_narrative": {
            "narrative": "Approved value case with renewal narrative and realization action plan."
        },
    }


def build_validation_seed_router(
    *,
    get_executor: Callable[[], WorkflowExecutor],
    get_settings_fn: Callable[[], Any] | None = None,
    require_tenant_account_fn: (
        Callable[[AsyncSession, UUID, RequestContext], Any] | None
    ) = None,
) -> APIRouter:
    router = APIRouter()

    @router.post("/validation/seed/auth-context")
    async def seed_validation_auth_context(
        payload: ValidationAuthContextSeedRequest,
        http_request: Request,
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, Any]:
        """Seed deterministic auth context for backend-integrated validation."""
        authorize_action("layer4.analysis.seed_auth_context", context)
        require_validation_seed_allowed(
            http_request, context, settings_provider=get_settings_fn
        )
        tenant_id = context_tenant_uuid(context)
        if payload.tenant_id is not None and payload.tenant_id != tenant_id:
            raise AuthorizationError(message="Validation seed tenant mismatch")

        await upsert_validation_tenant(
            db,
            tenant_id=tenant_id,
            tenant_name=payload.tenant_name,
            tenant_slug=payload.tenant_slug,
            actor=context.service_account_id
            or str(context.user_id or SEED_SERVICE_ACCOUNT_ID),
        )
        seeded_users = await upsert_validation_users(db, tenant_id=tenant_id)
        seeded_api_key = None
        if payload.api_key is not None:
            seeded_api_key = await upsert_validation_api_key(
                db,
                tenant_id=tenant_id,
                service_account_id=payload.service_account_id,
                api_key_payload=payload.api_key,
            )

        await db.flush()
        return {
            "seeded": True,
            "tenant": {
                "id": str(tenant_id),
                "slug": payload.tenant_slug,
                "name": payload.tenant_name,
                "status": TenantStatus.ACTIVE.value,
            },
            "users": seeded_users,
            "role_bindings": [
                {
                    "user_id": user["id"],
                    "role": user["role"],
                    "tenant_id": str(tenant_id),
                }
                for user in seeded_users
            ],
            "service_account": {
                "id": payload.service_account_id,
                "tenant_id": str(tenant_id),
                "auth_source": "service_account",
                "metadata_seeded": True,
            },
            "api_key": seeded_api_key,
            "account_mappings": payload.account_mappings,
            "raw_secret_persisted": False,
        }

    @router.post("/validation/session")
    async def issue_validation_session(
        payload: ValidationSessionRequest,
        response: Response,
        http_request: Request,
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, Any]:
        """Issue a non-production browser session for backend-integrated Playwright validation."""
        authorize_action("layer4.analysis.create_validation_session", context)
        require_validation_seed_allowed(
            http_request, context, settings_provider=get_settings_fn
        )

        token = encode_jwt(
            tenant_id=context.tenant_id,
            user_id=payload.user_id,
            roles=[payload.role],
            expires_in_seconds=payload.expires_in_seconds,
        )
        csrf_token = issue_csrf_token()
        secure_cookie = http_request.url.scheme == "https"

        response.set_cookie(
            key=SESSION_COOKIE_NAME,
            value=token,
            httponly=True,
            secure=secure_cookie,
            samesite="strict",
            max_age=payload.expires_in_seconds,
            path="/",
        )
        response.set_cookie(
            key=CSRF_COOKIE_NAME,
            value=csrf_token,
            httponly=False,
            secure=secure_cookie,
            samesite="strict",
            max_age=payload.expires_in_seconds,
            path="/",
        )

        return {
            "authenticated": True,
            "expires_in": payload.expires_in_seconds,
            "user": {
                "id": payload.user_id,
                "email": payload.email,
                "role": payload.role,
                "tenantId": str(context.tenant_id),
                "tenantSlug": payload.tenant_slug,
            },
            "tenant_id": str(context.tenant_id),
        }

    @router.post("/validation/seed/business-case-lifecycle")
    async def seed_business_case_lifecycle(
        payload: BusinessCaseLifecycleSeedRequest,
        http_request: Request,
        executor: WorkflowExecutor = Depends(get_executor),
        db: AsyncSession = Depends(get_route_db),
        context: RequestContext = Depends(require_authenticated),
    ) -> dict[str, Any]:
        """Seed deterministic business-case lifecycle state for non-production E2E validation."""
        authorize_action("layer4.analysis.seed_case_lifecycle", context)
        require_validation_seed_allowed(
            http_request, context, settings_provider=get_settings_ref
        )
        if require_tenant_account_fn:
            await require_tenant_account_fn(db, payload.account_id, context)
        else:
            account = await AccountService(db).get_account(
                payload.account_id, tenant_id=str(context.tenant_id)
            )
            if not account:
                raise NotFoundError(message=f"Account not found: {payload.account_id}")

        tenant_id = str(context.tenant_id)
        now = datetime.now(UTC)
        cases = [
            {
                "case_id": payload.draft_case_id,
                "status": "draft",
                "document_url": None,
            },
            {
                "case_id": payload.approved_case_id,
                "status": "approved",
                "document_url": "/exports/meridian-business-case.pdf",
            },
        ]
        for alias_case_id in payload.approved_case_aliases:
            if alias_case_id and alias_case_id not in {
                str(case["case_id"]) for case in cases
            }:
                cases.append(
                    {
                        "case_id": alias_case_id,
                        "status": "approved",
                        "document_url": "/exports/meridian-business-case.pdf",
                    }
                )

        business_case_service = BusinessCaseService(db)
        seeded_cases: list[dict[str, Any]] = []
        audit_events_requested = 0

        for case in cases:
            case_id = str(case["case_id"])
            lifecycle_status = str(case["status"])
            document_url = case["document_url"]
            output_data = seeded_business_case_output(
                case_id=case_id,
                account_id=payload.account_id,
                tenant_id=tenant_id,
                lifecycle_status=lifecycle_status,
                document_url=document_url,
            )
            metadata = {
                "workflow_id": case_id,
                "workflow_type": "business_case",
                "tenant_id": tenant_id,
                "user_id": context.user_id,
                "account_id": str(payload.account_id),
                "seeded": True,
                "seed_source": SEED_PRIVILEGED_REASON,
                "lifecycle_status": lifecycle_status,
            }

            await business_case_service.upsert_case_record(
                case_id=case_id,
                workflow_id=case_id,
                account_id=payload.account_id,
                opportunity_id=None,
                status=lifecycle_status,
                document_url=document_url,
                tenant_id=tenant_id,
            )

            state = BusinessCaseAgentState(
                workflow_id=case_id,
                tenant_id=tenant_id,
                status=WorkflowStatus.COMPLETED,
                current_node="seeded_validation_lifecycle",
                input_data={"account_id": str(payload.account_id)},
                output_data=output_data,
                metadata=metadata,
                started_at=now,
                completed_at=now,
                document_url=document_url,
            )
            await executor.state_manager.save_state(case_id, state)
            if hasattr(executor, "_workflow_metadata"):
                executor._workflow_metadata[case_id] = metadata

            audit_actions = [
                AuditAction.BUSINESS_CASE_GENERATED,
                AuditAction.WORKFLOW_COMPLETED,
            ]
            if lifecycle_status == "approved":
                audit_actions.append(AuditAction.BUSINESS_CASE_APPROVED)

            for audit_action in audit_actions:
                try:
                    await emit_and_persist_audit(
                        action=audit_action,
                        context=context,
                        resource_type="BusinessCase",
                        resource_id=case_id,
                        details={
                            "case_id": case_id,
                            "account_id": str(payload.account_id),
                            "lifecycle_status": lifecycle_status,
                            "seed_source": SEED_PRIVILEGED_REASON,
                        },
                    )
                    audit_events_requested += 1
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception(
                        "Seed lifecycle audit emission failed for case %s", case_id
                    )

            seeded_cases.append(
                {
                    "case_id": case_id,
                    "workflow_id": case_id,
                    "status": lifecycle_status,
                    "document_url": document_url,
                    "account_id": str(payload.account_id),
                }
            )

        return {
            "seeded": True,
            "tenant_id": tenant_id,
            "cases": seeded_cases,
            "audit_events_requested": audit_events_requested,
            "required_seed_rows_blocked": [],
        }

    return router
