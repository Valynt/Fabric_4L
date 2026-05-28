from __future__ import annotations

"""Layer 3 v2 bounded router: Entities domain.

This module is the canonical home for entity endpoints going forward.
It delegates to the existing ``routes.entities`` implementation while
making the security contract explicit at the router boundary.

Migration status (ARCH-L3-007 Part 1):
- Endpoints active: GET /v1/entities, GET /v1/entities/{id},
                    POST /v1/entities/query, POST /v1/entity/traverse
- Monolith equivalents: frozen (no new routes may be added to app_monolith.py)
- Full cutover: ARCH-L3-011 (Sprint 3)

Security contract:
- All routes require authentication via ``require_authenticated``.
- All Cypher queries must use ``TenantScopedCypher`` from
  ``value_fabric.shared.identity.isolation`` — never raw string interpolation.
- Tenant context is sourced exclusively from the authenticated request context,
  never from request body or query parameters.
"""


# Re-export the canonical router.  The v2 prefix signals that this module
# is the bounded, freeze-safe home for entity routes.  The underlying
# implementation in routes.entities already satisfies the security contract.
from ..routes.entities import router  # noqa: F401

__all__ = ["router"]
