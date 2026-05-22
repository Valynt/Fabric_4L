"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Formula Governance API routes for Layer 3.

Provides endpoints for formula versioning, lifecycle, and governance.

All Cypher queries are tenant-scoped via `create_neo4j_tenant_session`.
"""

import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from logging_config import get_logger

from ...api.dependencies_tenant_secured import create_neo4j_tenant_session
from ...api.routes._utils import get_tenant_id_from_api_key, semver_key
from ...auth.api_keys import APIKey
from ...auth.middleware import get_current_api_key, require_admin_role

logger = get_logger(__name__)


def _get_authenticated_tenant_id(api_key: APIKey) -> str:
    """Resolve tenant ID from authenticated API-key context; fail closed if absent.

    Delegates to the shared get_tenant_id_from_api_key helper in _utils.
    """
    return get_tenant_id_from_api_key(api_key)


# Status constants for Formula Governance
STATUS_DRAFT = "draft"
STATUS_UNDER_REVIEW = "under_review"
STATUS_APPROVED = "approved"
STATUS_ACTIVE = "active"
STATUS_DEPRECATED = "deprecated"
STATUS_RETIRED = "retired"

# Default configuration constants
DEFAULT_REVIEW_CYCLE_DAYS = 90

router = APIRouter()


# Pydantic Models


class FormulaVersionResponse(BaseModel):
    """Formula version response."""

    version: str
    formula_id: str
    status: str
    created_at: str
    created_by: str
    change_summary: str
    previous_version: str | None


class FormulaGovernanceResponse(BaseModel):
    """Formula governance metadata response."""

    formula_id: str
    current_version: str
    status: str
    owner: str | None
    department: str | None
    review_cycle_days: int
    approved_by: str | None
    approved_at: str | None
    last_reviewed_at: str | None
    next_review_at: str | None
    versions: list[FormulaVersionResponse]


VALID_FORMULA_STATUSES = [
    STATUS_DRAFT,
    STATUS_UNDER_REVIEW,
    STATUS_APPROVED,
    STATUS_ACTIVE,
    STATUS_DEPRECATED,
    STATUS_RETIRED,
]


class CreateVersionRequest(BaseModel):
    """Request to create new formula version."""

    version: str = Field(
        ...,
        pattern=r"^\d+\.\d+\.\d+(-[a-zA-Z0-9.-]+)?(\+[a-zA-Z0-9.-]+)?$",
        description="Semver version (e.g., 1.2.3)",
    )
    change_summary: str
    created_by: str


class SubmitForReviewRequest(BaseModel):
    """Request to submit formula for review."""

    version: str
    submitted_by: str


class ApproveRequest(BaseModel):
    """Request to approve formula."""

    version: str
    approved_by: str
    comments: str | None = None


class RejectRequest(BaseModel):
    """Request to reject formula."""

    version: str
    rejected_by: str
    reason: str


class ActivateRequest(BaseModel):
    """Request to activate formula version."""

    version: str
    requested_by: str
    justification: str
    effective_date: datetime | None = None


class DeprecateRequest(BaseModel):
    """Request to deprecate formula."""

    reason: str
    requested_by: str
    deprecation_date: datetime
    replacement_formula_id: str | None = None


class TransitionResponse(BaseModel):
    """Governance transition result."""

    success: bool
    formula_id: str
    old_status: str
    new_status: str
    error_message: str | None
    requires_approval: bool = False


class DependencyResponse(BaseModel):
    """Formula dependency response."""

    source_formula_id: str
    target_formula_id: str
    dependency_type: str


class ValidationResponse(BaseModel):
    """Validation result for activation."""

    can_activate: bool
    errors: list[str]
    warnings: list[str]


# API Endpoints


class ApprovalQueueItem(BaseModel):
    """Pending approval queue entry."""

    id: str
    formula_id: str
    formula_name: str
    submitted_by: str
    submitted_at: str
    change_summary: str
    previous_version: str
    status: Literal["pending", "approved", "rejected"] = "pending"


@router.get("/formulas/approvals/pending", response_model=list[ApprovalQueueItem])
async def list_pending_approvals(
    api_key: APIKey = Depends(get_current_api_key),
):
    """List all formulas currently pending review/approval."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    query = """
    MATCH (f:Formula)
    WHERE f.status = 'under_review'
      AND f.tenant_id = $tenant_id
    OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion)
    WITH f, fv
    ORDER BY fv.createdAt DESC
    WITH f, head(collect(fv)) AS latest_version
    RETURN f, latest_version
    ORDER BY f.submittedAt DESC
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, tenant_id=tenant_id)
        records = await result.data()

        return [
            ApprovalQueueItem(
                id=r["f"]["id"],
                formula_id=r["f"]["id"],
                formula_name=r["f"].get("name", ""),
                submitted_by=r["f"].get("submittedBy", ""),
                submitted_at=r["f"].get("submittedAt", ""),
                change_summary=r["latest_version"].get("changeSummary", "")
                if r.get("latest_version")
                else "",
                previous_version=r["latest_version"].get("previousVersion", "")
                if r.get("latest_version")
                else "",
                status="pending",
            )
            for r in records
        ]


@router.get(
    "/formulas/{formula_id}/versions", response_model=list[FormulaVersionResponse]
)
async def list_formula_versions(
    formula_id: str,
    include_retired: bool = Query(False, description="Include retired versions"),
    api_key: APIKey = Depends(get_current_api_key),
):
    """List all versions of a formula."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    query = """
    MATCH (f:Formula {id: $formula_id})-[:HAS_VERSION]->(fv:FormulaVersion)
    WHERE ($include_retired OR fv.status <> 'retired')
      AND f.tenant_id = $tenant_id
    RETURN fv
    ORDER BY fv.createdAt DESC
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            formula_id=formula_id,
            include_retired=include_retired,
            tenant_id=tenant_id,
        )
        records = await result.data()

        return [
            FormulaVersionResponse(
                version=r["fv"]["version"],
                formula_id=formula_id,
                status=r["fv"].get("status", "draft"),
                created_at=r["fv"].get("createdAt", datetime.now(UTC).isoformat()),
                created_by=r["fv"].get("createdBy", "system"),
                change_summary=r["fv"].get("changeSummary", ""),
                previous_version=r["fv"].get("previousVersion"),
            )
            for r in records
        ]


@router.get(
    "/formulas/{formula_id}/governance", response_model=FormulaGovernanceResponse
)
async def get_formula_governance(
    formula_id: str,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Get governance metadata for a formula."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion)
    RETURN f,
           collect(DISTINCT fv) as versions
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, formula_id=formula_id, tenant_id=tenant_id)
        record = await result.single()

        if not record or not record["f"]:
            raise HTTPException(status_code=404, detail="Formula not found")

        f = record["f"]
        versions_data = record["versions"]

        versions = [
            FormulaVersionResponse(
                version=v["version"],
                formula_id=formula_id,
                status=v.get("status", "draft"),
                created_at=v.get("createdAt", datetime.now(UTC).isoformat()),
                created_by=v.get("createdBy", "system"),
                change_summary=v.get("changeSummary", ""),
                previous_version=v.get("previousVersion"),
            )
            for v in versions_data
            if v
        ]

        # Sort by semver (descending) using shared utility
        versions.sort(key=lambda v: semver_key(v.version), reverse=True)

        return FormulaGovernanceResponse(
            formula_id=formula_id,
            current_version=f.get("version", "1.0.0"),
            status=f.get("status", "draft"),
            owner=f.get("owner"),
            department=f.get("department"),
            review_cycle_days=f.get("reviewCycleDays", DEFAULT_REVIEW_CYCLE_DAYS),
            approved_by=f.get("approvedBy"),
            approved_at=f.get("approvedAt"),
            last_reviewed_at=f.get("lastReviewedAt"),
            next_review_at=f.get("nextReviewAt"),
            versions=versions,
        )


@router.post(
    "/formulas/{formula_id}/versions",
    response_model=FormulaVersionResponse,
    status_code=201,
)
async def create_formula_version(
    formula_id: str,
    request: CreateVersionRequest,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Create a new formula version. Requires authentication."""
    tenant_id = _get_authenticated_tenant_id(api_key)

    # Check formula exists
    check_query = "MATCH (f:Formula {id: $formula_id}) WHERE f.tenant_id = $tenant_id RETURN f"
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(check_query, formula_id=formula_id, tenant_id=tenant_id)
        if not await result.single():
            raise HTTPException(status_code=404, detail="Formula not found")

    now = datetime.now(UTC).isoformat()
    version_id = str(uuid.uuid4())

    # Get current version as previous
    prev_query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    RETURN f.version as current_version
    """
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(prev_query, formula_id=formula_id, tenant_id=tenant_id)
        record = await result.single()
        previous_version = record["current_version"] if record else None

    # Create version
    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    CREATE (fv:FormulaVersion {
        id: $version_id,
        version: $version,
        formulaId: $formula_id,
        status: 'draft',
        createdAt: $created_at,
        createdBy: $created_by,
        changeSummary: $change_summary,
        previousVersion: $previous_version,
        tenant_id: $tenant_id
    })
    CREATE (f)-[:HAS_VERSION]->(fv)
    SET f.version = $version,
        f.status = 'draft',
        f.updatedAt = $created_at
    RETURN fv
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            formula_id=formula_id,
            version_id=version_id,
            version=request.version,
            created_at=now,
            created_by=request.created_by,
            change_summary=request.change_summary,
            previous_version=previous_version,
            tenant_id=tenant_id,
        )
        record = await result.single()

        if not record:
            raise HTTPException(status_code=500, detail="Failed to create version")

        fv = record["fv"]

        return FormulaVersionResponse(
            version=fv["version"],
            formula_id=formula_id,
            status=fv["status"],
            created_at=fv["createdAt"],
            created_by=fv["createdBy"],
            change_summary=fv["changeSummary"],
            previous_version=fv.get("previousVersion"),
        )


@router.post("/formulas/{formula_id}/submit", response_model=TransitionResponse)
async def submit_for_review(
    formula_id: str,
    request: SubmitForReviewRequest,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Submit formula for review. Requires authentication."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    # Check current status
    check_query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    RETURN f.status as status
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(check_query, formula_id=formula_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Formula not found")

        current_status = record["status"] or "draft"

        if current_status != "draft":
            return TransitionResponse(
                success=False,
                formula_id=formula_id,
                old_status=current_status,
                new_status=current_status,
                error_message=f"Formula must be in draft status to submit for review, currently {current_status}",
            )

    now = datetime.now(UTC).isoformat()

    # Atomic query: check status and update in single operation to prevent TOCTOU race
    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.status = 'draft'
      AND f.tenant_id = $tenant_id
    MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
    SET f.status = 'under_review',
        f.submittedAt = $submitted_at,
        f.submittedBy = $submitted_by,
        fv.status = 'under_review'
    RETURN f.status as new_status
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            formula_id=formula_id,
            version=request.version,
            submitted_at=now,
            submitted_by=request.submitted_by,
            tenant_id=tenant_id,
        )
        record = await result.single()

        if not record:
            # Formula not found, not in draft status, or version doesn't exist
            return TransitionResponse(
                success=False,
                formula_id=formula_id,
                old_status=current_status,
                new_status=current_status,
                error_message="Failed to submit for review: formula must be in draft status with matching version",
            )

        # Audit log the governance action
        logger.info(
            "formula_submitted_for_review",
            extra={
                "formula_id": formula_id,
                "version": request.version,
                "submitted_by": request.submitted_by,
                "actor_key_id": api_key.key_id if api_key else None,
            },
        )

        return TransitionResponse(
            success=True,
            formula_id=formula_id,
            old_status="draft",
            new_status="under_review",
        )


@router.post("/formulas/{formula_id}/approve", response_model=TransitionResponse)
async def approve_formula(
    formula_id: str,
    request: ApproveRequest,
    api_key: APIKey = Depends(require_admin_role),
):
    """Approve formula (admin only)."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    now = datetime.now(UTC).isoformat()

    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
    SET f.status = 'approved',
        f.approvedAt = $approved_at,
        f.approvedBy = $approved_by,
        f.approvalComments = $comments,
        fv.status = 'approved'
    RETURN f
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            formula_id=formula_id,
            version=request.version,
            approved_at=now,
            approved_by=request.approved_by,
            comments=request.comments,
            tenant_id=tenant_id,
        )
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Formula or version not found")

        # Audit log the governance action
        logger.info(
            "formula_approved",
            extra={
                "formula_id": formula_id,
                "version": request.version,
                "approved_by": request.approved_by,
                "actor_key_id": api_key.key_id if api_key else None,
            },
        )

        return TransitionResponse(
            success=True,
            formula_id=formula_id,
            old_status="under_review",
            new_status="approved",
        )


@router.post("/formulas/{formula_id}/activate", response_model=TransitionResponse)
async def activate_formula(
    formula_id: str,
    request: ActivateRequest,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Activate a formula version. Requires authentication."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    now = datetime.now(UTC).isoformat()
    effective_date = (request.effective_date or datetime.now(UTC)).isoformat()

    # Check current status
    check_query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    RETURN f.status as status
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(check_query, formula_id=formula_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Formula not found")

        old_status = record["status"] or "draft"

        if old_status == "active":
            return TransitionResponse(
                success=False,
                formula_id=formula_id,
                old_status=old_status,
                new_status=old_status,
                error_message="Formula is already active",
            )

    # Perform activation
    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
    SET f.status = 'active',
        f.activatedAt = $activated_at,
        f.activatedBy = $activated_by,
        f.effectiveDate = $effective_date,
        f.justification = $justification,
        fv.status = 'active'
    RETURN f
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            formula_id=formula_id,
            version=request.version,
            activated_at=now,
            activated_by=request.requested_by,
            effective_date=effective_date,
            justification=request.justification,
            tenant_id=tenant_id,
        )
        record = await result.single()

        if not record:
            raise HTTPException(status_code=500, detail="Failed to activate formula")

        # Audit log the governance action
        logger.info(
            "formula_activated",
            extra={
                "formula_id": formula_id,
                "version": request.version,
                "activated_by": request.requested_by,
                "actor_key_id": api_key.key_id if api_key else None,
            },
        )

        return TransitionResponse(
            success=True,
            formula_id=formula_id,
            old_status=old_status,
            new_status="active",
        )


@router.post("/formulas/{formula_id}/deprecate", response_model=TransitionResponse)
async def deprecate_formula(
    formula_id: str,
    request: DeprecateRequest,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Deprecate a formula. Requires authentication."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    # Check current status
    check_query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    RETURN f.status as status
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(check_query, formula_id=formula_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Formula not found")

        old_status = record["status"] or "draft"

        if old_status in ["deprecated", "retired"]:
            return TransitionResponse(
                success=False,
                formula_id=formula_id,
                old_status=old_status,
                new_status=old_status,
                error_message=f"Formula is already {old_status}",
            )

    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    SET f.status = 'deprecated',
        f.deprecatedAt = $deprecated_at,
        f.deprecatedBy = $deprecated_by,
        f.deprecationReason = $reason,
        f.replacementFormulaId = $replacement_id
    RETURN f
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            formula_id=formula_id,
            deprecated_at=request.deprecation_date.isoformat(),
            deprecated_by=request.requested_by,
            reason=request.reason,
            replacement_id=request.replacement_formula_id,
            tenant_id=tenant_id,
        )
        record = await result.single()

        if not record:
            raise HTTPException(status_code=500, detail="Failed to deprecate formula")

        # Audit log the governance action
        logger.info(
            "formula_deprecated",
            extra={
                "formula_id": formula_id,
                "old_status": old_status,
                "deprecated_by": request.requested_by,
                "actor_key_id": api_key.key_id if api_key else None,
            },
        )

        return TransitionResponse(
            success=True,
            formula_id=formula_id,
            old_status=old_status,
            new_status="deprecated",
        )


@router.get(
    "/formulas/{formula_id}/dependencies", response_model=list[DependencyResponse]
)
async def get_formula_dependencies(
    formula_id: str,
    direction: str = Query(
        "both", description="Dependency direction: outgoing, incoming, or both"
    ),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Get formula dependencies."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    deps = []

    if direction in ["outgoing", "both"]:
        outgoing_query = """
        MATCH (f:Formula {id: $formula_id})-[:DEPENDS_ON]->(dep:Formula)
        WHERE f.tenant_id = $tenant_id
        RETURN dep.id as dep_id
        """
        async with await create_neo4j_tenant_session(tenant_id) as neo4j:
            result = await neo4j.run(outgoing_query, formula_id=formula_id, tenant_id=tenant_id)
            records = await result.data()
            for r in records:
                deps.append(
                    DependencyResponse(
                        source_formula_id=formula_id,
                        target_formula_id=r["dep_id"],
                        dependency_type="uses",
                    )
                )

    if direction in ["incoming", "both"]:
        incoming_query = """
        MATCH (other:Formula)-[:DEPENDS_ON]->(f:Formula {id: $formula_id})
        WHERE other.tenant_id = $tenant_id
        RETURN other.id as other_id
        """
        async with await create_neo4j_tenant_session(tenant_id) as neo4j:
            result = await neo4j.run(incoming_query, formula_id=formula_id, tenant_id=tenant_id)
            records = await result.data()
            for r in records:
                deps.append(
                    DependencyResponse(
                        source_formula_id=r["other_id"],
                        target_formula_id=formula_id,
                        dependency_type="uses",
                    )
                )

    return deps


@router.post("/formulas/{formula_id}/validate", response_model=ValidationResponse)
async def validate_activation(
    formula_id: str,
    version: str = Query(..., description="Version to validate"),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Validate if formula can be activated."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    query = """
    MATCH (f:Formula {id: $formula_id})
    WHERE f.tenant_id = $tenant_id
    OPTIONAL MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion {version: $version})
    OPTIONAL MATCH (f)-[:DEPENDS_ON]->(dep:Formula)
    WHERE dep.status <> 'active'
    RETURN f.status as status,
           fv IS NOT NULL as version_exists,
           count(dep) as inactive_deps
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, formula_id=formula_id, version=version, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            return ValidationResponse(
                can_activate=False,
                errors=["Formula not found"],
                warnings=[],
            )

        errors = []
        warnings = []

        if not record["version_exists"]:
            errors.append(f"Version {version} does not exist")

        current_status = record["status"] or "draft"
        if current_status == "active":
            warnings.append("Formula is already active")
        elif current_status == "retired":
            errors.append("Cannot activate retired formula")

        inactive_deps = record["inactive_deps"]
        if inactive_deps > 0:
            warnings.append(f"Formula has {inactive_deps} inactive dependencies")

        return ValidationResponse(
            can_activate=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )
