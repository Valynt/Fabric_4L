from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from fastapi import HTTPException, status
from value_fabric.shared.audit.emitter import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome


class ArtifactStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass(frozen=True)
class ArtifactAccessRequest:
    tenant_id: UUID
    actor_id: str
    request_id: str
    policy_id: str
    artifact_id: str
    artifact_kind: str  # formula | benchmark
    artifact_status: ArtifactStatus
    actor_scopes: set[str]
    required_scope: str


_BLOCKED_STATUSES: set[ArtifactStatus] = {
    ArtifactStatus.DRAFT,
    ArtifactStatus.DEPRECATED,
    ArtifactStatus.ARCHIVED,
}


def _emit_policy_decision(req: ArtifactAccessRequest, *, allowed: bool, reason: str) -> None:
    emit_audit_event(
        action=AuditAction.POLICY_DECISION,
        outcome=AuditOutcome.SUCCESS if allowed else AuditOutcome.DENIED,
        tenant_id=req.tenant_id,
        user_id=req.actor_id,
        request_id=req.request_id,
        resource_type=req.artifact_kind,
        resource_id=req.artifact_id,
        details={
            "policy_id": req.policy_id,
            "required_scope": req.required_scope,
            "actor_scopes": sorted(req.actor_scopes),
            "artifact_status": req.artifact_status.value,
            "decision": "allow" if allowed else "deny",
            "reason": reason,
        },
    )


def enforce_formula_benchmark_runtime_policy(req: ArtifactAccessRequest) -> None:
    if req.required_scope not in req.actor_scopes:
        _emit_policy_decision(req, allowed=False, reason="missing_scope")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission scope for artifact resolution.",
        )

    if req.artifact_status != ArtifactStatus.APPROVED:
        _emit_policy_decision(req, allowed=False, reason="not_approved")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Artifact must be approved for runtime use.",
        )

    if req.artifact_status in _BLOCKED_STATUSES:
        _emit_policy_decision(req, allowed=False, reason="blocked_status")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Artifact status is not permitted for runtime use.",
        )

    _emit_policy_decision(req, allowed=True, reason="policy_pass")
