#!/usr/bin/env python3
"""Canonical tenant-scope classification for Layer 4 routes.

Single source of truth used by:

- ``scripts/export_openapi.py`` — stamps ``x-tenant-scope`` into
  ``contracts/openapi/layer4-agents.json`` for every operation.
- ``scripts/ci/enrich_layer4_matrix_tenant_scope.py`` — seeds
  ``tenant_scope`` on route-contract-matrix entries.
- ``scripts/ci/check_openapi_tenant_scope.py`` — cross-checks matrix and
  OpenAPI scope metadata against this classifier.

Scope values mirror ``contracts/event-catalog/event-entry.schema.json``:
``TENANT``, ``TENANT_AND_BILLING_ACCOUNT``, ``GLOBAL``, ``SYSTEM``.
"""

from __future__ import annotations

SCOPE_TENANT = "TENANT"
SCOPE_TENANT_AND_BILLING_ACCOUNT = "TENANT_AND_BILLING_ACCOUNT"
SCOPE_GLOBAL = "GLOBAL"
SCOPE_SYSTEM = "SYSTEM"

TENANT_SCOPE_ENUM = frozenset(
    {
        SCOPE_TENANT,
        SCOPE_TENANT_AND_BILLING_ACCOUNT,
        SCOPE_GLOBAL,
        SCOPE_SYSTEM,
    }
)

# Platform/health routes that carry no tenant context.
GLOBAL_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/metrics"),
        ("GET", "/ready"),
    }
)

# Cross-tenant admin, inbound external webhooks and unauthenticated
# service-to-service callbacks that have no authenticated tenant context.
SYSTEM_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        # Stripe webhook (signature-verified, no tenant token).
        ("POST", "/v1/billing/webhook"),
        # Cross-tenant admin overview.
        ("GET", "/v1/admin/tenant-overview"),
        # CRM inbound webhooks (no authenticated tenant context).
        ("GET", "/v1/webhooks/crm/health"),
        ("POST", "/v1/webhooks/crm/hubspot"),
        ("POST", "/v1/webhooks/crm/salesforce"),
        # Repo-audit inbound webhook (tenant passed via query param).
        ("POST", "/v1/repo-audit/webhook/github"),
    }
)


def classify_tenant_scope(method: str, path: str) -> str:
    """Return the canonical tenant scope for a Layer 4 ``(method, path)``.

    Resolution order:

    1. Explicit ``GLOBAL`` routes (platform health probes).
    2. Explicit ``SYSTEM`` routes (cross-tenant admin / inbound webhooks).
    3. All billing routes except the Stripe webhook are
       ``TENANT_AND_BILLING_ACCOUNT``.
    4. Everything else defaults to ``TENANT``.
    """
    key = (method.upper(), path)
    if key in GLOBAL_ROUTES:
        return SCOPE_GLOBAL
    if key in SYSTEM_ROUTES:
        return SCOPE_SYSTEM
    if path == "/v1/billing" or path.startswith("/v1/billing/"):
        return SCOPE_TENANT_AND_BILLING_ACCOUNT
    return SCOPE_TENANT


def is_valid_tenant_scope(value: str) -> bool:
    """Return True when ``value`` is one of the canonical scope constants."""
    return value in TENANT_SCOPE_ENUM