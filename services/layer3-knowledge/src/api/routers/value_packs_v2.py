from __future__ import annotations

"""Layer 3 v2 bounded router: Value Packs domain.

This module is the canonical home for value-pack endpoints going forward.
It delegates to the existing ``routes.value_packs`` implementation while
making the security contract explicit at the router boundary.

Migration status (ARCH-L3-007 Part 1):
- Endpoints active: all /v1/value-packs/* routes
- Monolith equivalents: frozen (no new routes may be added to app_monolith.py)
- Full cutover: ARCH-L3-011 (Sprint 3)

Security contract:
- All mutating routes require authentication via ``require_authenticated``
  or a validated API key with tenant context.
- All Cypher queries must use ``TenantScopedCypher`` from
  ``value_fabric.shared.identity.isolation`` — never raw string interpolation.
- Tenant context is sourced exclusively from the authenticated request context
  or the validated API key; never from request body or query parameters.
"""


# Re-export the canonical router.  The v2 prefix signals that this module
# is the bounded, freeze-safe home for value-pack routes.  The underlying
# implementation in routes.value_packs already satisfies the security contract.
from ..routes.value_packs import router  # noqa: F401

__all__ = ["router"]
