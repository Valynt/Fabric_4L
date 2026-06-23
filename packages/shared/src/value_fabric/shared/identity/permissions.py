"""Canonical Role and Permission definitions for Value Fabric.

Replaces the layer-specific Role/Permission enums in:
- layer3-knowledge/src/auth/api_keys.py (Role.DEVELOPER removed, renamed to match business roles)
- (layer4 had no formal Permission enum)

Design decisions:
- Roles map to business personas, not technical roles (no "developer").
- Permissions use colon-namespaced strings for easy JWT claim embedding.
- ROLE_PERMISSIONS is the single source of truth; each layer reads this
  to enforce access without re-defining its own mapping.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Iterable


class Permission(str, Enum):
    """Fine-grained permissions enforced at endpoint level."""

    # ── Read permissions ───────────────────────────────────────────────────
    READ_HEALTH = "read:health"
    READ_METRICS = "read:metrics"
    READ_SCHEMA = "read:schema"
    READ_SEARCH = "read:search"
    READ_GRAPHRAG = "read:graphrag"
    READ_ANALYTICS = "read:analytics"
    READ_INGESTION = "read:ingestion"
    READ_AGENTS = "read:agents"

    # ── Model registry permissions ─────────────────────────────────────────
    READ_MODELS = "read:models"
    WRITE_MODELS = "write:models"
    ADMIN_MODELS = "admin:models"

    # ── Write permissions ──────────────────────────────────────────────────
    WRITE_INGESTION = "write:ingestion"
    WRITE_EXTRACTION = "write:extraction"
    WRITE_SCHEMA = "write:schema"
    WRITE_ANALYTICS = "write:analytics"
    WRITE_AGENTS = "write:agents"

    # ── Admin permissions ──────────────────────────────────────────────────
    ADMIN_API_KEYS = "admin:api_keys"
    ADMIN_USERS = "admin:users"
    ADMIN_TENANTS = "admin:tenants"
    ADMIN_SYSTEM = "admin:system"


class Role(str, Enum):
    """Business roles used across all layers.

    Hierarchy (highest → lowest):
        super_admin > tenant_admin > content_admin > analyst > read_only

    The ``system`` role is reserved for internal service-to-service calls.
    """

    SUPER_ADMIN = "super_admin"
    TENANT_ADMIN = "tenant_admin"
    CONTENT_ADMIN = "content_admin"
    ANALYST = "analyst"
    READ_ONLY = "read_only"
    SYSTEM = "system"


# Legacy claim aliases are intentionally narrow and resolve only to canonical
# business roles. Runtime callers decide whether this compatibility path is
# enabled; RBAC checks continue to evaluate only canonical role values.
LEGACY_ROLE_ALIASES: dict[str, str] = {
    "admin": Role.TENANT_ADMIN.value,
}


def normalize_role_claim(role: Role | Any) -> str:
    """Return a canonical role string for a single role-like claim value."""
    raw_role = role.value if isinstance(role, Role) else str(role)
    normalized_key = raw_role.strip().lower()
    return LEGACY_ROLE_ALIASES.get(normalized_key, raw_role.strip())


def normalize_role_claims(roles: Iterable[Role | Any] | None) -> list[str]:
    """Normalize role claim values while preserving unknown roles as inert strings."""
    if roles is None:
        return []
    return [normalized for role in roles if (normalized := normalize_role_claim(role))]


@dataclass(frozen=True)
class RolePermissions:
    """Immutable role → permission mapping."""

    permissions: FrozenSet[Permission]
    description: str


# ---------------------------------------------------------------------------
# Single source-of-truth permission mapping
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[Role, RolePermissions] = {
    Role.READ_ONLY: RolePermissions(
        permissions=frozenset(
            {
                Permission.READ_HEALTH,
                Permission.READ_METRICS,
                Permission.READ_SCHEMA,
                Permission.READ_SEARCH,
                Permission.READ_GRAPHRAG,
            }
        ),
        description="Read-only access to search and value trees",
    ),
    Role.ANALYST: RolePermissions(
        permissions=frozenset(
            {
                Permission.READ_HEALTH,
                Permission.READ_METRICS,
                Permission.READ_SCHEMA,
                Permission.READ_SEARCH,
                Permission.READ_GRAPHRAG,
                Permission.READ_ANALYTICS,
                Permission.READ_INGESTION,
                Permission.READ_AGENTS,
                Permission.READ_MODELS,
                Permission.WRITE_ANALYTICS,
                Permission.WRITE_AGENTS,
            }
        ),
        description="Read KG, run queries, generate ROI / business cases (L4)",
    ),
    Role.CONTENT_ADMIN: RolePermissions(
        permissions=frozenset(
            {
                Permission.READ_HEALTH,
                Permission.READ_METRICS,
                Permission.READ_SCHEMA,
                Permission.READ_SEARCH,
                Permission.READ_GRAPHRAG,
                Permission.READ_ANALYTICS,
                Permission.READ_INGESTION,
                Permission.READ_AGENTS,
                Permission.READ_MODELS,
                Permission.WRITE_MODELS,
                Permission.WRITE_INGESTION,
                Permission.WRITE_EXTRACTION,
                Permission.WRITE_SCHEMA,
                Permission.WRITE_ANALYTICS,
                Permission.WRITE_AGENTS,
            }
        ),
        description="Ingest docs (L1), trigger extractions (L2), manage KG (L3)",
    ),
    Role.TENANT_ADMIN: RolePermissions(
        permissions=frozenset(
            {
                Permission.READ_HEALTH,
                Permission.READ_METRICS,
                Permission.READ_SCHEMA,
                Permission.READ_SEARCH,
                Permission.READ_GRAPHRAG,
                Permission.READ_ANALYTICS,
                Permission.READ_INGESTION,
                Permission.READ_AGENTS,
                Permission.READ_MODELS,
                Permission.WRITE_MODELS,
                Permission.ADMIN_MODELS,
                Permission.WRITE_INGESTION,
                Permission.WRITE_EXTRACTION,
                Permission.WRITE_SCHEMA,
                Permission.WRITE_ANALYTICS,
                Permission.WRITE_AGENTS,
                Permission.ADMIN_API_KEYS,
                Permission.ADMIN_USERS,
            }
        ),
        description="Manage users, API keys, tenant settings",
    ),
    Role.SUPER_ADMIN: RolePermissions(
        permissions=frozenset(p for p in Permission),
        description="Platform-wide admin: all tenants, billing, global config",
    ),
    Role.SYSTEM: RolePermissions(
        permissions=frozenset(p for p in Permission),
        description="Internal service-to-service; never issued to humans",
    ),
}


# ---------------------------------------------------------------------------
# Role hierarchy for escalation guard (F-11)
# ---------------------------------------------------------------------------

# An inviter may only grant roles strictly below their own rank.
# Higher rank = more privilege.
ROLE_RANK: dict[str, int] = {
    Role.SUPER_ADMIN.value: 100,
    Role.TENANT_ADMIN.value: 80,
    Role.CONTENT_ADMIN.value: 60,
    Role.ANALYST.value: 40,
    Role.READ_ONLY.value: 20,
}


def get_role_rank(role: str | Role) -> int:
    """Return the rank for a role string or enum. Unknown roles resolve to 0."""
    raw = role.value if isinstance(role, Role) else role
    return ROLE_RANK.get(raw, 0)


def can_grant_role(inviter_role: str | Role, invitee_role: str | Role) -> bool:
    """Return True if *inviter_role* may grant *invitee_role*.

    An inviter may only grant roles with a rank **strictly lower** than their
    own.  Unrecognised roles resolve to rank 0 and are always blocked.
    """
    inviter_rank = get_role_rank(inviter_role)
    invitee_rank = get_role_rank(invitee_role)
    return inviter_rank > 0 and invitee_rank > 0 and invitee_rank < inviter_rank


def get_role_permissions(role: Role) -> FrozenSet[Permission]:
    """Return the canonical permission set for a role."""
    return ROLE_PERMISSIONS[role].permissions


def role_has_permission(role: Role, permission: Permission) -> bool:
    """Check whether *role* includes *permission*."""
    return permission in ROLE_PERMISSIONS[role].permissions
