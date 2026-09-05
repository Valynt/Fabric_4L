"""Resource projections: typed, server-side snapshots of a resource's authz facts.

A projection answers "what does the PDP need to know about this resource right
now?" — its tenant, current revision, state, owners, relationships. Projections
are produced server-side (never from the client) and drive the attribute resolver.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ResourceProjection:
    """Minimal, immutable authz projection for one resource."""

    resource_type: str
    resource_id: str
    tenant_id: str
    revision: str | None = None
    attributes: dict = field(default_factory=dict)
    relationships: dict = field(default_factory=dict)

    def as_resource(self) -> dict:
        return {
            "type": self.resource_type,
            "id": self.resource_id,
            "tenant_id": self.tenant_id,
        }

    def facts(self) -> dict:
        return {
            "attributes": dict(self.attributes),
            "relationships": dict(self.relationships),
        }


def claim_projection(
    *,
    claim_id: str,
    tenant_id: str,
    author_id: str | None,
    account_id: str | None = None,
    revision: str | None = None,
    validation_complete: bool = False,
    has_open_dispute: bool = False,
    impact_amount: float | None = None,
    approval_ceiling: float | None = None,
    current_state: str | None = None,
    approved_model_version: str | None = None,
    relationships: dict | None = None,
) -> ResourceProjection:
    """Build the authz projection for a claim (server-side state)."""
    return ResourceProjection(
        resource_type="value_claim",
        resource_id=claim_id,
        tenant_id=tenant_id,
        revision=revision,
        attributes={
            "author_id": author_id or "",
            "account_id": account_id or "",
            "validation_complete": bool(validation_complete),
            "has_open_dispute": bool(has_open_dispute),
            "impact_amount": impact_amount,
            "approval_ceiling": approval_ceiling,
            "current_state": current_state,
            "approved_model_version": approved_model_version,
        },
        relationships=relationships or {},
    )


def exception_projection(
    *,
    exception_id: str,
    tenant_id: str,
    requester_id: str | None,
    current_state: str | None = None,
    target_state: str | None = None,
    is_expired: bool = False,
    in_scope: bool = True,
    relationships: dict | None = None,
) -> ResourceProjection:
    return ResourceProjection(
        resource_type="exception",
        resource_id=exception_id,
        tenant_id=tenant_id,
        revision=None,
        attributes={
            "requester_id": requester_id or "",
            "current_state": current_state,
            "target_state": target_state,
            "is_expired": bool(is_expired),
            "in_scope": bool(in_scope),
        },
        relationships=relationships or {},
    )


def opportunity_projection(
    *,
    opportunity_id: str,
    tenant_id: str,
    is_locked: bool = False,
    relationships: dict | None = None,
) -> ResourceProjection:
    return ResourceProjection(
        resource_type="opportunity",
        resource_id=opportunity_id,
        tenant_id=tenant_id,
        revision=None,
        attributes={"is_locked": bool(is_locked)},
        relationships=relationships or {},
    )