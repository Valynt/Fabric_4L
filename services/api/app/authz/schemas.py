"""Pydantic models for the ``fabric.authz.request.v1`` / ``fabric.authz.decision.v1`` contracts.

These models are the stable, versioned wire contracts consumed by the policy
decision plane. They mirror design Section 10.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.authz.constants import DenyCode, ReasonCode

REQUEST_SCHEMA_VERSION = "fabric.authz.request.v1"
DECISION_SCHEMA_VERSION = "fabric.authz.decision.v1"


class Principal(BaseModel):
    """The acting principal in an authorization request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., min_length=1)
    type: Literal["human", "agent", "service", "external_viewer", "system_control"] = "human"
    tenant_id: str = Field(..., min_length=1)
    status: Literal["active", "inactive", "suspended"] = "active"
    platform_roles: frozenset[str] = Field(default_factory=frozenset)
    workflow_roles: frozenset[str] = Field(default_factory=frozenset)
    membership_revision: int | None = None
    approval_ceiling_usd: float | None = None
    authn_assurance: str | None = None
    is_agent: bool = Field(default=False, description="True when the principal is an agent.")


class Resource(BaseModel):
    """The resource being acted upon."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str = Field(..., min_length=1)
    id: str = Field(..., min_length=1)
    tenant_id: str = Field(..., min_length=1)
    authz_revision: int = Field(default=0, ge=0)
    attributes: dict[str, Any] = Field(default_factory=dict)
    relationships: frozenset[str] = Field(default_factory=frozenset)


class AuthzContext(BaseModel):
    """Request-time evaluation context."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    now: datetime = Field(default_factory=datetime.utcnow)
    channel: str = "api"
    requested_model_version: str | None = None
    trace_id: str | None = None
    ip_risk: str | None = None
    break_glass_grant_id: str | None = None


class Obligation(BaseModel):
    """A returned obligation the enforcement point must satisfy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    type: str = Field(..., min_length=1)
    parameters: dict[str, Any] = Field(default_factory=dict)

    def __hash__(self) -> int:
        # Rectifies the auto-generated hash for frozen models whose fields
        # contain unhashable values (parameters is a dict), so obligations can
        # be carried in frozensets.
        return hash((self.type, json.dumps(self.parameters, sort_keys=True)))


class AuthzRequest(BaseModel):
    """A ``fabric.authz.request.v1`` authorization request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["fabric.authz.request.v1"] = REQUEST_SCHEMA_VERSION
    request_id: str = Field(..., min_length=1)
    principal: Principal
    action: str = Field(..., min_length=1)
    resource: Resource
    context: AuthzContext = Field(default_factory=AuthzContext)
    delegation: dict[str, Any] | None = None


class AuthzDecision(BaseModel):
    """A ``fabric.authz.decision.v1`` authorization decision."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["fabric.authz.decision.v1"] = DECISION_SCHEMA_VERSION
    decision_id: str = Field(..., min_length=1)
    allow: bool
    reason_codes: frozenset[ReasonCode] = Field(default_factory=frozenset)
    deny_code: DenyCode | None = None
    policy_version: str = Field(..., min_length=1)
    bundle_digest: str | None = None
    input_fingerprint: str = Field(..., min_length=32)
    obligations: frozenset[Obligation] = Field(default_factory=frozenset)
    cache_ttl_ms: int = Field(default=0, ge=0)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
