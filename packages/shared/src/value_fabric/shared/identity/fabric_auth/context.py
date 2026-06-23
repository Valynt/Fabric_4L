"""Canonical AuthContext carried inside the Fabric4L internal envelope.

The model is frozen; downstream services must treat it as an immutable
verified identity. Only the gateway (services/api) constructs an
AuthContext from external Clerk claims; L1–L6 only ever *receive* one
that has been signed by the gateway.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, FrozenSet

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _load_canonical_defaults() -> dict[str, Any]:
    """Load the canonical auth defaults from the platform-contract JSON file."""
    marker_names = {".git", "package.json", "pnpm-workspace.yaml", "pnpm-lock.yaml"}
    start = Path(__file__).resolve()
    for parent in (start, *start.parents):
        if any((parent / marker).exists() for marker in marker_names):
            candidate = parent / "packages" / "platform-contract" / "src" / "clerk_defaults.json"
            if candidate.exists():
                return json.loads(candidate.read_text(encoding="utf-8"))
        candidate = parent / "packages" / "platform-contract" / "src" / "clerk_defaults.json"
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    # Fallback to hardcoded defaults if the JSON is not found (e.g., installed package).
    return {
        "fabric": {
            "authIssuer": "fabric4l-gateway",
            "authAudience": "fabric4l-internal",
        }
    }


_CANONICAL_DEFAULTS = _load_canonical_defaults()
_FABRIC_DEFAULTS = _CANONICAL_DEFAULTS.get("fabric", {})

DEFAULT_ISSUER = _FABRIC_DEFAULTS.get("authIssuer", "fabric4l-gateway")
DEFAULT_AUDIENCE = _FABRIC_DEFAULTS.get("authAudience", "fabric4l-internal")


class AuthContext(BaseModel):
    """Verified identity envelope passed between Fabric4L services.

    Notes:
        - ``tenant_id`` is the *only* trusted source of tenant scope. Any
          header or URL slug must match this value or be rejected.
        - ``permissions`` and ``roles`` are populated from Clerk org claims
          at the gateway. Domain-level RBAC (account access, workflow,
          entitlements) is enforced separately in Fabric4L.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    # Identity
    clerk_user_id: str = Field(..., min_length=1, max_length=128)
    clerk_org_id: str | None = Field(default=None, max_length=128)
    user_id: str = Field(..., min_length=1, max_length=64)
    tenant_id: str = Field(..., min_length=1, max_length=64)

    # Authorization hints (Clerk-org-level only; not the final word)
    roles: FrozenSet[str] = Field(default_factory=frozenset)
    permissions: FrozenSet[str] = Field(default_factory=frozenset)

    # Envelope metadata
    request_id: str = Field(..., min_length=1, max_length=128)
    iat: int = Field(..., description="Issued-at, unix seconds")
    exp: int = Field(..., description="Expiry, unix seconds")
    nbf: int | None = Field(default=None, description="Not-before, unix seconds")
    iss: str = Field(default=DEFAULT_ISSUER, max_length=128)
    aud: str = Field(default=DEFAULT_AUDIENCE, max_length=128)
    kid: str = Field(..., min_length=1, max_length=64)

    @field_validator("roles", "permissions", mode="before")
    @classmethod
    def _coerce_to_frozenset(cls, value: Any) -> FrozenSet[str]:
        if value is None:
            return frozenset()
        if isinstance(value, frozenset):
            return value
        if isinstance(value, (list, tuple, set)):
            return frozenset(str(v) for v in value)
        raise TypeError("roles/permissions must be an iterable of strings")

    @field_validator("exp")
    @classmethod
    def _exp_after_iat(cls, exp: int, info: Any) -> int:
        iat = info.data.get("iat")
        if iat is not None and exp <= iat:
            raise ValueError("exp must be greater than iat")
        return exp

    def has_permission(self, permission: str) -> bool:
        """Convenience for callers; not a substitute for backend RBAC."""
        return permission in self.permissions

    def has_role(self, role: str) -> bool:
        return role in self.roles

    def is_expired(self, *, now: int | None = None) -> bool:
        current = now if now is not None else int(datetime.now(timezone.utc).timestamp())
        return current >= self.exp

    def to_jwt_claims(self) -> dict[str, Any]:
        """Serialize to a JWT claim dict suitable for ``sign_envelope``."""
        return {
            "iss": self.iss,
            "aud": self.aud,
            "iat": self.iat,
            "exp": self.exp,
            "nbf": self.nbf if self.nbf is not None else self.iat,
            "request_id": self.request_id,
            "clerk_user_id": self.clerk_user_id,
            "clerk_org_id": self.clerk_org_id,
            "user_id": self.user_id,
            "tenant_id": self.tenant_id,
            "roles": sorted(self.roles),
            "permissions": sorted(self.permissions),
        }

    @classmethod
    def from_jwt_claims(cls, claims: dict[str, Any], *, kid: str) -> "AuthContext":
        return cls(
            clerk_user_id=claims["clerk_user_id"],
            clerk_org_id=claims.get("clerk_org_id"),
            user_id=claims["user_id"],
            tenant_id=claims["tenant_id"],
            roles=claims.get("roles") or [],
            permissions=claims.get("permissions") or [],
            request_id=claims["request_id"],
            iat=int(claims["iat"]),
            exp=int(claims["exp"]),
            nbf=int(claims["nbf"]) if claims.get("nbf") is not None else None,
            iss=claims.get("iss", DEFAULT_ISSUER),
            aud=claims.get("aud", DEFAULT_AUDIENCE),
            kid=kid,
        )
