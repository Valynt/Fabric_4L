"""In-memory identity directory backing the Clerk webhook handler.

This is a lightweight, process-local store that keeps Fabric4L identity tables
in sync with Clerk webhooks.  In production deployments it is expected to be
replaced by or backed by a persistent directory service; the interface remains
the same.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass

_USER_NOT_FOUND = "user_not_found"
_TENANT_NOT_FOUND = "tenant_not_found"


@dataclass(frozen=True)
class DirectoryUser:
    """A user record derived from Clerk ``user.*`` events."""

    clerk_user_id: str
    email: str | None
    display_name: str | None
    status: str


@dataclass(frozen=True)
class DirectoryTenant:
    """A tenant/organization record derived from Clerk ``organization.*`` events."""

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

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._users: dict[str, DirectoryUser] = {}
        self._tenants: dict[str, DirectoryTenant] = {}
        self._memberships: dict[tuple[str, str], DirectoryMembership] = {}
        self._processed_events: set[str] = set()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------
    def upsert_user(
        self,
        *,
        clerk_user_id: str,
        email: str | None,
        display_name: str | None,
        status: str,
    ) -> DirectoryUser:
        with self._lock:
            user = DirectoryUser(
                clerk_user_id=clerk_user_id,
                email=email,
                display_name=display_name,
                status=status,
            )
            self._users[clerk_user_id] = user
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

    def get_user_by_clerk(self, clerk_user_id: str) -> DirectoryUser | None:
        with self._lock:
            return self._users.get(clerk_user_id)

    # ------------------------------------------------------------------
    # Tenants
    # ------------------------------------------------------------------
    def upsert_tenant(
        self,
        *,
        clerk_org_id: str,
        name: str,
        slug: str | None,
        status: str,
    ) -> DirectoryTenant:
        with self._lock:
            tenant = DirectoryTenant(
                clerk_org_id=clerk_org_id,
                name=name,
                slug=slug,
                status=status,
            )
            self._tenants[clerk_org_id] = tenant
            return tenant

    def delete_tenant(self, *, clerk_org_id: str) -> None:
        with self._lock:
            self._tenants.pop(clerk_org_id, None)
            self._memberships = {
                key: membership
                for key, membership in self._memberships.items()
                if membership.clerk_org_id != clerk_org_id
            }

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
            return membership

    def revoke_membership(self, *, clerk_org_id: str, clerk_user_id: str) -> None:
        with self._lock:
            self._memberships.pop((clerk_org_id, clerk_user_id), None)

    def get_active_membership(
        self, *, clerk_org_id: str, clerk_user_id: str
    ) -> DirectoryMembership | None:
        with self._lock:
            membership = self._memberships.get((clerk_org_id, clerk_user_id))
            if membership is None or membership.status != "active":
                return None
            return membership

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
                _directory = AuthDirectory()
    return _directory


def reset_auth_directory() -> None:
    """Reset the shared directory; intended for tests."""
    global _directory
    with _directory_lock:
        _directory = None
