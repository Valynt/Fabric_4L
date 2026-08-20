"""Clerk Billing Integration — Synchronizes Clerk subscription events with Fabric tenant entitlements.

Provides mapping from Clerk B2B/B2C subscription plans and feature items
to Fabric 4L tenant entitlement grants stored in AuthDirectory / DB.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from app.core.auth_directory import AuthDirectory, get_auth_directory

logger = structlog.get_logger(__name__)

# Canonical Tier → Entitlements Mapping
PLAN_ENTITLEMENT_MAP: dict[str, set[str]] = {
    "starter": {
        "tier:starter",
        "features:l1_ingestion",
        "features:l2_extraction",
    },
    "free": {
        "tier:starter",
        "features:l1_ingestion",
        "features:l2_extraction",
    },
    "pro": {
        "tier:pro",
        "features:l1_ingestion",
        "features:l2_extraction",
        "features:l3_graph_rag",
        "features:l4_agents_basic",
        "features:analytics_standard",
    },
    "growth": {
        "tier:pro",
        "features:l1_ingestion",
        "features:l2_extraction",
        "features:l3_graph_rag",
        "features:l4_agents_basic",
        "features:analytics_standard",
    },
    "enterprise": {
        "tier:enterprise",
        "features:l1_ingestion",
        "features:l2_extraction",
        "features:l3_graph_rag",
        "features:l4_autonomous_agents",
        "features:l5_ground_truth",
        "features:l6_benchmarks_custom",
        "features:analytics_advanced",
        "features:sso_enforced",
        "features:audit_export",
    },
}

DEFAULT_FALLBACK_ENTITLEMENTS: set[str] = {"tier:starter", "features:l1_ingestion"}


def resolve_plan_entitlements(
    plan_slug: str | None,
    features: list[str] | None = None,
    add_ons: list[str] | None = None,
) -> set[str]:
    """Resolve a normalized set of Fabric entitlement tokens for a given plan and optional add-ons."""
    slug = (plan_slug or "").lower().strip()
    entitlements = set(PLAN_ENTITLEMENT_MAP.get(slug, DEFAULT_FALLBACK_ENTITLEMENTS))

    if features:
        for f in features:
            f_norm = f.strip().lower()
            if f_norm:
                entitlements.add(f"features:{f_norm}" if not f_norm.startswith("features:") else f_norm)

    if add_ons:
        for a in add_ons:
            a_norm = a.strip().lower()
            if a_norm:
                entitlements.add(f"addon:{a_norm}" if not a_norm.startswith("addon:") else a_norm)

    return entitlements


def process_clerk_billing_event(
    event_type: str,
    data: dict[str, Any],
    directory: AuthDirectory | None = None,
) -> bool:
    """Process a Clerk Billing webhook event and update tenant entitlements.

    Handled event types:
        - subscription.created
        - subscription.updated
        - subscription.deleted / subscription.canceled
        - subscription.item.created
        - subscription.item.updated
        - payment_attempt.failed
        - payment_attempt.succeeded

    Returns True if an entitlement update was applied, False otherwise.
    """
    if directory is None:
        directory = get_auth_directory()

    # Resolve organization / tenant id
    clerk_org_id = (
        data.get("organization_id")
        or data.get("org_id")
        or (data.get("organization") or {}).get("id")
    )

    if not clerk_org_id:
        # Some billing events might be user-scoped; if no org, we log and skip
        logger.debug(
            "skipping user-scoped or org-less billing event",
            event_type=event_type,
            operation="billing_event_apply",
        )
        return False

    tenant = directory.get_tenant_by_clerk_org(clerk_org_id)
    if not tenant:
        logger.warning(
            "tenant not found for billing event",
            clerk_org_id=clerk_org_id,
            event_type=event_type,
            operation="billing_event_apply",
        )
        raise KeyError("tenant_not_found")

    status = (data.get("status") or "").lower()
    plan_slug = (
        data.get("plan_slug")
        or (data.get("plan") or {}).get("slug")
        or (data.get("plan") or {}).get("name")
        or "starter"
    )

    # Calculate expiration / validity
    current_period_end = (
        data.get("current_period_end")
        or (data.get("subscription") or {}).get("current_period_end")
    )
    valid_until: int | None = None
    if current_period_end:
        try:
            valid_until = int(current_period_end)
        except (ValueError, TypeError):
            valid_until = None

    if event_type in {"subscription.created", "subscription.updated", "subscription.item.created", "subscription.item.updated"}:
        if status in {"active", "trialing", "past_due"}:
            features = data.get("features") or (data.get("plan") or {}).get("features") or []
            if isinstance(features, list):
                feature_names = [f.get("name") or f.get("slug") or str(f) if isinstance(f, dict) else str(f) for f in features]
            else:
                feature_names = []

            entitlements = resolve_plan_entitlements(plan_slug=plan_slug, features=feature_names)
            directory.set_tenant_entitlements(tenant.id, entitlements, valid_until=valid_until)
            logger.info(
                "updated tenant entitlements from clerk subscription",
                tenant_id=tenant.id,
                clerk_org_id=clerk_org_id,
                plan_slug=plan_slug,
                entitlements=list(entitlements),
                valid_until=valid_until,
                operation="billing_event_apply",
            )
            return True
        elif status in {"canceled", "unpaid", "incomplete_expired"}:
            # Downgrade to fallback starter tier
            entitlements = set(DEFAULT_FALLBACK_ENTITLEMENTS)
            directory.set_tenant_entitlements(tenant.id, entitlements, valid_until=int(time.time()))
            logger.info(
                "downgraded tenant entitlements due to subscription cancellation",
                tenant_id=tenant.id,
                clerk_org_id=clerk_org_id,
                status=status,
                operation="billing_event_apply",
            )
            return True

    elif event_type in {"subscription.deleted", "subscription.canceled"}:
        entitlements = set(DEFAULT_FALLBACK_ENTITLEMENTS)
        directory.set_tenant_entitlements(tenant.id, entitlements, valid_until=int(time.time()))
        logger.info(
            "cleared tenant entitlements on subscription deletion",
            tenant_id=tenant.id,
            clerk_org_id=clerk_org_id,
            operation="billing_event_apply",
        )
        return True

    elif event_type == "payment_attempt.failed":
        logger.warning(
            "billing payment attempt failed for tenant",
            tenant_id=tenant.id,
            clerk_org_id=clerk_org_id,
            operation="billing_payment_failed",
        )
        # Note: Grace period policies can be applied here; we preserve current entitlements with warning
        return False

    return False
