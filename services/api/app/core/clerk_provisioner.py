"""Clerk -> Fabric provisioning policy: immutable identity mapping.

The ONLY source for a Fabric tenant scope is the signed Clerk organization
identity (the ``org_id`` claim / ``organization.*`` webhook events). A Fabric
tenant is NEVER inferred from an email domain or from client-supplied metadata.

Identity mapping rules (deterministic / immutable once assigned):

- Clerk user ID -> Fabric user identity  : ``fabric_user_id_for()``.
  The Clerk user id is itself the stable Fabric identity, so re-provisioning
  the same Clerk user always yields the same Fabric user.
- Clerk organization ID -> immutable Fabric tenant ID : ``fabric_tenant_id_for()``.
  Deterministically derived from the Clerk org id so the mapping is stable
  across directory resets, replay, and re-provisioning; it never changes for a
  given org, and a recreated org maps back to the same tenant.

Organization membership is mapped to a *tenant-scoped role assignment* at
authorization time (see ``auth_context_builder.normalize_clerk_role``), not by
this module.
"""
from __future__ import annotations

# Prefix keeps Fabric tenant ids distinguishable from raw Clerk org ids and
# from any uuid-based tenant ids emitted by other provisioning paths.
TENANT_ID_PREFIX = "t_"


def fabric_tenant_id_for(clerk_org_id: str) -> str:
    """Return the immutable Fabric tenant id for a Clerk organization id."""
    return f"{TENANT_ID_PREFIX}{clerk_org_id}"


def fabric_user_id_for(clerk_user_id: str) -> str:
    """Return the stable Fabric user identity for a Clerk user id.

    The Clerk user id *is* the Fabric identity (it is already immutable and
    globally unique), so provisioning passes it through unchanged.
    """
    return clerk_user_id
