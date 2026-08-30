"""Typed authorization models: request, decision, environment, obligations.

The decision shape is the stable output contract. Every decision is
explainable (reason_codes), versioned (policy_version), auditable
(decision_id correlated to the resulting domain event), and carries a
resource revision for optimistic concurrency / stale-input rejection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .errors import AuthorizationDeniedError

DECISION_SCHEMA_VERSION = "fabric.authz.decision.v1"


class Obligation(BaseModel):
    """A mandatory downstream step coupled to an allowed decision.

    Examples: ``audit``, ``mask_external_scope``, ``require_secondary_approval``,
    ``persist_decision``. Obligations are enforced by the caller; the decision
    is only fully "honored" once its obligations are met.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: str
    detail: dict[str, Any] = Field(default_factory=dict)


class AuthzEnvironment(BaseModel):
    """Request-time (ABAC) facts resolved server-side by the PIP.

    Per principle 3, none of these may be trusted when supplied by the client;
    the attribute resolver populates them from server-owned state.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    now: datetime = Field(default_factory=lambda: datetime.now(UTC))
    # Resource attributes (state, ownership, version, amounts, risk, etc.)
    resource_attributes: dict[str, Any] = Field(default_factory=dict)
    # Relationship / ReBAC facts.
    relationships: dict[str, Any] = Field(default_factory=dict)
    # environment/context facts.
    environment: dict[str, Any] = Field(default_factory=dict)


class AuthzRequest(BaseModel):
    """A single authorization check.

    ``principal`` and ``resource`` may be supplied as raw dicts (in which case
    they are wrapped) or as ``PrincipalContext``/resource-projection objects
    (normalised to dicts). The attribute resolver enriches ``environment``.
    """

    model_config = ConfigDict(extra="forbid")

    action: str
    principal: Any
    resource: dict[str, Any] = Field(default_factory=dict)
    environment: AuthzEnvironment = Field(default_factory=AuthzEnvironment)
    requested_resource_revision: str | None = None

    def input_fingerprint(self) -> str:
        """Deterministic fingerprint of the decision input for audit."""
        payload = {
            "action": self.action,
            "principal": _canonical(self.principal),
            "resource": _canonical(self.resource),
            "attributes": _canonical(self.environment.resource_attributes),
            "relationships": _canonical(self.environment.relationships),
        }
        return _stable_hash(payload)


class AuthzDecision(BaseModel):
    """The stable decision object returned by ``authorize``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = DECISION_SCHEMA_VERSION
    allowed: bool
    decision_id: str = Field(default_factory=lambda: str(uuid4()))
    policy_version: str
    reason_codes: list[str] = Field(default_factory=list)
    deny_code: str | None = Field(default=None)
    obligations: list[Obligation] = Field(default_factory=list)
    bundle_digest: str | None = Field(default=None)
    input_fingerprint: str | None = Field(default=None)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resource_revision: str | None = Field(default=None)
    cache_ttl_ms: int = 0

    def require_allowed(self, *, action: str | None = None) -> None:
        """Fail closed: raise if not allowed."""
        if not self.allowed:
            raise AuthorizationDeniedError(
                " ".join(self.reason_codes) or "access denied",
                action=action or None,
                details={"decision_id": self.decision_id, "deny_code": self.deny_code},
            )


# ---------------------------------------------------------------------------
# Serialization + fingerprint helpers (kept dependency-free)
# ---------------------------------------------------------------------------
def _canonical(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return _canonical(value.model_dump())
    if hasattr(value, "to_dict"):
        return _canonical(value.to_dict())
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_canonical(v) for v in value]
    if isinstance(value, (UUID, datetime)):
        return str(value)
    return value


def _stable_hash(payload: Any) -> str:
    try:
        import hashlib

        serialized = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    except Exception:  # pragma: no cover - non-fatal
        return str(uuid4())