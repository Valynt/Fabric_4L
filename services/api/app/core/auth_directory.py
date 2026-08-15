"""In-memory identity directory backing the Clerk webhook handler.

This is a lightweight, process-local store that keeps Fabric4L identity tables
in sync with Clerk webhooks.  In production deployments it is expected to be
replaced by or backed by a persistent directory service; the interface remains
the same.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass

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
        self._processed_events: set[str] = set()
        self._tenant_entitlements: dict[str, set[str]] = {}
        self._tenant_entitlement_valid_until: dict[str, int | None] = {}
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
            user_id = id or (existing.id if existing else clerk_user_id)
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

    def delete_user(self, *, clerk_user_id: str) -> None:
        with self._lock:
            self._users.pop(clerk_user_id, None)
            # Also revoke any memberships for this user.
            self._memberships = {
                key: membership
                for key, membership in self._memberships.items()
                if membership.clerk_user_id != clerk_user_id
            }
            self._projection_version += 1

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
            tenant_id = id or (existing.id if existing else uuid.uuid4().hex)
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

    def delete_tenant(self, *, clerk_org_id: str) -> None:
        with self._lock:
            self._tenants.pop(clerk_org_id, None)
            self._memberships = {
                key: membership
                for key, membership in self._memberships.items()
                if membership.clerk_org_id != clerk_org_id
            }
            self._projection_version += 1

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

    def revoke_membership(self, *, clerk_org_id: str, clerk_user_id: str) -> None:
        with self._lock:
            self._memberships.pop((clerk_org_id, clerk_user_id), None)
            self._projection_version += 1

    def get_active_membership(
        self, *, clerk_org_id: str, clerk_user_id: str
    ) -> DirectoryMembership | None:
        with self._lock:
            membership = self._memberships.get((clerk_org_id, clerk_user_id))
            if membership is None or membership.status != "active":
                return None
            return membership

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
    # Webhook idempotency
    # ------------------------------------------------------------------
    def has_processed_event(self, event_id: str) -> bool:
        with self._lock:
            return event_id in self._processed_events

    def mark_event_processed(self, event_id: str, _event_type: str | None = None) -> None:
        with self._lock:
            self._processed_events.add(event_id)


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
