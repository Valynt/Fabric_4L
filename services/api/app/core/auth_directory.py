"""In-memory identity directory backing the Clerk webhook handler.

This is a lightweight, process-local store that keeps Fabric4L identity tables
in sync with Clerk webhooks.  In production deployments it is expected to be
replaced by or backed by a persistent directory service; the interface remains
the same.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass, replace

from app.core.clerk_provisioner import fabric_tenant_id_for, fabric_user_id_for

logger = logging.getLogger(__name__)

_USER_NOT_FOUND = "user_not_found"
_TENANT_NOT_FOUND = "tenant_not_found"


@dataclass(frozen=True)
class DirectoryUser:
    """A user record derived from Clerk ``user.*`` events."""

    id: str
    clerk_user_id: str
    email: str | None
    display_name: str | None
    status: str


@dataclass(frozen=True)
class DirectoryTenant:
    """A tenant/organization record derived from Clerk ``organization.*`` events."""

    id: str
    clerk_org_id: str
    name: str
    slug: str | None
    status: str


@dataclass(frozen=True)
class DirectoryMembership:
    """A user↔organization membership record from Clerk ``organizationMembership.*`` events."""

    clerk_org_id: str
    clerk_user_id: str
    clerk_membership_id: str
    role: str
    status: str


@dataclass(frozen=True)
class DirectoryInvitation:
    """An organization invitation record from Clerk ``organizationInvitation.*`` events."""

    clerk_invitation_id: str
    clerk_org_id: str
    email: str
    role: str
    status: str
    created_at: int | None = None


class AuthDirectory:
    """Process-local identity directory with basic tenant/user/membership tracking."""

    def __init__(
        self,
        *,
        account_authorizer: Callable[[str, str, str], bool] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._users: dict[str, DirectoryUser] = {}
        self._tenants: dict[str, DirectoryTenant] = {}
        self._memberships: dict[tuple[str, str], DirectoryMembership] = {}
        self._invitations: dict[str, DirectoryInvitation] = {}
        self._tenant_entitlements: dict[str, set[str]] = {}
        self._tenant_entitlement_valid_until: dict[str, int | None] = {}
        self._revoked_sessions: set[str] = set()
        self._user_revoked_before: dict[str, int] = {}
        # Account ownership is resolved by the canonical account repository,
        # not duplicated in this process-local Clerk identity projection.
        self._account_authorizer = account_authorizer or (lambda _tenant, _user, _account: False)
        self._projection_version = 0

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def upsert_user(
        self,
        *,
        id: str | None = None,
        clerk_user_id: str,
        email: str | None,
        display_name: str | None,
        status: str,
    ) -> DirectoryUser:
        with self._lock:
            existing = self._users.get(clerk_user_id)
            user_id = id or (existing.id if existing else fabric_user_id_for(clerk_user_id))
            user = DirectoryUser(
                id=user_id,
                clerk_user_id=clerk_user_id,
                email=email,
                display_name=display_name,
                status=status,
            )
            self._users[clerk_user_id] = user
            self._projection_version += 1
            return user

    def deactivate_user(self, *, clerk_user_id: str) -> bool:
        """Soft-deactivate a user (deny access immediately).

        The user record and its memberships are retained so re-provisioning the
        same Clerk user maps back to the same immutable Fabric identity, and so
        a later ``user.created`` for the same clerk id can safely reactivate.
        """
        with self._lock:
            user = self._users.get(clerk_user_id)
            if user is None:
                return False
            self._users[clerk_user_id] = replace(user, status="deactivated")
            self._memberships = {
                key: (replace(m, status="deactivated") if m.clerk_user_id == clerk_user_id else m)
                for key, m in self._memberships.items()
            }
            self._projection_version += 1
            return True

    def get_user_by_clerk(self, clerk_user_id: str) -> DirectoryUser | None:
        with self._lock:
            return self._users.get(clerk_user_id)

    # ------------------------------------------------------------------
    # Tenants
    # ------------------------------------------------------------------
    def upsert_tenant(
        self,
        *,
        id: str | None = None,
        clerk_org_id: str,
        name: str,
        slug: str | None,
        status: str,
    ) -> DirectoryTenant:
        with self._lock:
            existing = self._tenants.get(clerk_org_id)
            tenant_id = id or (existing.id if existing else fabric_tenant_id_for(clerk_org_id))
            tenant = DirectoryTenant(
                id=tenant_id,
                clerk_org_id=clerk_org_id,
                name=name,
                slug=slug,
                status=status,
            )
            self._tenants[clerk_org_id] = tenant
            self._projection_version += 1
            return tenant

    def deactivate_tenant(self, *, clerk_org_id: str) -> bool:
        """Soft-deactivate a tenant/organization (deny access immediately).

        The tenant record and its memberships are retained so a recreated
        organization maps back to the same immutable Fabric tenant id.
        """
        with self._lock:
            tenant = self._tenants.get(clerk_org_id)
            if tenant is None:
                return False
            self._tenants[clerk_org_id] = replace(tenant, status="deactivated")
            self._memberships = {
                key: (replace(m, status="deactivated") if m.clerk_org_id == clerk_org_id else m)
                for key, m in self._memberships.items()
            }
            self._projection_version += 1
            return True

    def get_tenant_by_clerk_org(self, clerk_org_id: str) -> DirectoryTenant | None:
        with self._lock:
            return self._tenants.get(clerk_org_id)

    # ------------------------------------------------------------------
    # Memberships
    # ------------------------------------------------------------------
    def upsert_membership(
        self,
        *,
        clerk_org_id: str,
        clerk_user_id: str,
        clerk_membership_id: str,
        role: str,
        status: str,
    ) -> DirectoryMembership:
        with self._lock:
            if clerk_user_id not in self._users:
                raise KeyError(_USER_NOT_FOUND)
            if clerk_org_id not in self._tenants:
                raise KeyError(_TENANT_NOT_FOUND)

            membership = DirectoryMembership(
                clerk_org_id=clerk_org_id,
                clerk_user_id=clerk_user_id,
                clerk_membership_id=clerk_membership_id,
                role=role,
                status=status,
            )
            self._memberships[(clerk_org_id, clerk_user_id)] = membership
            self._projection_version += 1
            return membership

    def deactivate_membership(self, *, clerk_org_id: str, clerk_user_id: str) -> bool:
        """Soft-deactivate a membership (deny access immediately).

        The membership record is retained (keyed by clerk org+user) so replay
        and re-creation of the same membership remain idempotent.
        """
        with self._lock:
            key = (clerk_org_id, clerk_user_id)
            membership = self._memberships.get(key)
            if membership is None:
                return False
            self._memberships[key] = replace(membership, status="deactivated")
            self._projection_version += 1
            return True

    def get_active_membership(
        self, *, clerk_org_id: str, clerk_user_id: str
    ) -> DirectoryMembership | None:
        with self._lock:
            membership = self._memberships.get((clerk_org_id, clerk_user_id))
            if membership is None or membership.status != "active":
                return None
            return membership

    # ------------------------------------------------------------------
    # Invitations
    # ------------------------------------------------------------------
    def upsert_invitation(
        self,
        *,
        clerk_invitation_id: str,
        clerk_org_id: str,
        email: str,
        role: str,
        status: str,
        created_at: int | None = None,
    ) -> DirectoryInvitation:
        with self._lock:
            invitation = DirectoryInvitation(
                clerk_invitation_id=clerk_invitation_id,
                clerk_org_id=clerk_org_id,
                email=email,
                role=role,
                status=status,
                created_at=created_at,
            )
            self._invitations[clerk_invitation_id] = invitation
            self._projection_version += 1
            return invitation

    def get_invitation(self, clerk_invitation_id: str) -> DirectoryInvitation | None:
        with self._lock:
            return self._invitations.get(clerk_invitation_id)

    def list_invitations_for_org(self, clerk_org_id: str) -> list[DirectoryInvitation]:
        with self._lock:
            return [
                inv
                for inv in self._invitations.values()
                if inv.clerk_org_id == clerk_org_id and inv.status == "pending"
            ]

    def revoke_invitation(self, clerk_invitation_id: str) -> None:
        with self._lock:
            if clerk_invitation_id in self._invitations:
                current = self._invitations[clerk_invitation_id]
                self._invitations[clerk_invitation_id] = DirectoryInvitation(
                    clerk_invitation_id=current.clerk_invitation_id,
                    clerk_org_id=current.clerk_org_id,
                    email=current.email,
                    role=current.role,
                    status="revoked",
                    created_at=current.created_at,
                )
                self._projection_version += 1

    def set_tenant_entitlements(
        self, tenant_id: str, entitlements: set[str], *, valid_until: int | None = None
    ) -> None:
        """Replace the tenant entitlement projection atomically."""
        with self._lock:
            self._tenant_entitlements[tenant_id] = set(entitlements)
            # None explicitly means the canonical entitlement grant is non-expiring.
            self._tenant_entitlement_valid_until[tenant_id] = valid_until
            self._projection_version += 1

    def read_authorization_projection(
        self, *, clerk_org_id: str, clerk_user_id: str, account_id: str | None
    ) -> dict[str, object] | None:
        """Read identity, membership, entitlements, and account grant under one lock.

        The projection version makes this a concrete consistent-read boundary for
        the process-local development adapter. Production adapters must provide
        the equivalent from one database snapshot or one materialized version.
        """
        with self._lock:
            user = self._users.get(clerk_user_id)
            tenant = self._tenants.get(clerk_org_id)
            membership = self._memberships.get((clerk_org_id, clerk_user_id))
            if (
                user is None
                or user.status != "active"
                or tenant is None
                or tenant.status != "active"
                or membership is None
                or membership.status != "active"
            ):
                return None
            account_allowed = account_id is None or self._account_authorizer(
                tenant.id, user.id, account_id
            )
            return {
                "version": self._projection_version,
                "user": user,
                "tenant": tenant,
                "membership": membership,
                "entitlements": tuple(sorted(self._tenant_entitlements.get(tenant.id, set()))),
                "membership_valid_until": None,
                "permission_policy_valid_until": None,
                "entitlement_valid_until": self._tenant_entitlement_valid_until.get(tenant.id),
                "account_allowed": account_allowed,
            }

    # ------------------------------------------------------------------
    # Session Management & Revocation
    # ------------------------------------------------------------------
    def _redis(self):
        try:
            from app.core.redis_client import get_redis_client
            return get_redis_client()
        except Exception:
            return None

    def revoke_session(self, sid: str) -> None:
        """Denylist an active session discriminator across memory and Redis."""
        with self._lock:
            self._revoked_sessions.add(sid)
            self._projection_version += 1
        r = self._redis()
        if r is not None:
            try:
                r.setex(f"auth:clerk:revoked_session:{sid}", 604800, "revoked")
            except Exception as exc:
                logger.warning("Redis revoke_session write failed: %s", exc)

    def is_session_revoked(self, sid: str) -> bool:
        """Check if an individual session is explicitly revoked in memory or Redis."""
        with self._lock:
            if sid in self._revoked_sessions:
                return True
        r = self._redis()
        if r is not None:
            try:
                if r.get(f"auth:clerk:revoked_session:{sid}") is not None:
                    with self._lock:
                        self._revoked_sessions.add(sid)
                    return True
            except Exception as exc:
                logger.warning("Redis is_session_revoked read failed: %s", exc)
        return False

    def revoke_user_sessions(
        self, clerk_user_id: str, *, revoked_before: int | None = None
    ) -> None:
        """Force sign-out all sessions for a user issued before the timestamp across memory and Redis."""
        import time
        cutoff = revoked_before if revoked_before is not None else int(time.time())
        with self._lock:
            self._user_revoked_before[clerk_user_id] = cutoff
            self._projection_version += 1
        r = self._redis()
        if r is not None:
            try:
                r.setex(f"auth:clerk:user_revoked_before:{clerk_user_id}", 604800, str(cutoff))
            except Exception as exc:
                logger.warning("Redis revoke_user_sessions write failed: %s", exc)

    def is_user_session_revoked(
        self, clerk_user_id: str, token_iat: int | None = None
    ) -> bool:
        """Check if tokens for this user issued at token_iat have been revoked in memory or Redis."""
        with self._lock:
            cutoff = self._user_revoked_before.get(clerk_user_id)
        if cutoff is None:
            r = self._redis()
            if r is not None:
                try:
                    val = r.get(f"auth:clerk:user_revoked_before:{clerk_user_id}")
                    if val is not None:
                        cutoff = int(val)
                        with self._lock:
                            self._user_revoked_before[clerk_user_id] = cutoff
                except Exception as exc:
                    logger.warning("Redis is_user_session_revoked read failed: %s", exc)
        if cutoff is None:
            return False
        if token_iat is None:
            return True
        return token_iat <= cutoff

# Process-level singleton.  Production deployments may replace this with a
# service-backed directory retrieved from dependency injection.
_directory: AuthDirectory | None = None
_directory_lock = threading.Lock()


def get_auth_directory() -> AuthDirectory:
    """Return the shared ``AuthDirectory`` singleton."""
    global _directory
    if _directory is None:
        with _directory_lock:
            if _directory is None:
                from app.core.database import db

                _directory = AuthDirectory(
                    account_authorizer=lambda tenant_id, _user_id, account_id: (
                        db.accounts.get(account_id, tenant_id=tenant_id) is not None
                    )
                )
    return _directory


def reset_auth_directory() -> None:
    """Reset the shared directory; intended for tests."""
    global _directory
    with _directory_lock:
        _directory = None
