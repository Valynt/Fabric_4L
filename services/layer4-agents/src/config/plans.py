"""Plan and feature configuration for billing bootstrap defaults.

This module is intended for defaults/bootstrapping only.
Production billing should use persisted, versioned plan configuration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum as PyEnum
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel


class get_entitlements_responseResult(TypedDictModel):
    features: dict[str, Any]
    plan_id: Any
    plan_name: Any | None = None


class FeatureId(str, PyEnum):
    """Feature identifiers for entitlement checks."""

    # Core features
    BASIC_EXTRACTION = "basic_extraction"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    FORMULA_BUILDER = "formula_builder"

    # Pro features
    ADVANCED_MODELS = "advanced_models"
    PRIORITY_SUPPORT = "priority_support"
    TEAM_COLLABORATION = "team_collaboration"

    # Enterprise features
    CUSTOM_INTEGRATIONS = "custom_integrations"
    DEDICATED_SUPPORT = "dedicated_support"
    SLA_GUARANTEE = "sla_guarantee"


@dataclass(frozen=True)
class Feature:
    """Feature definition with metadata."""

    id: str
    name: str
    description: str
    requires_pro: bool = False
    requires_enterprise: bool = False


@dataclass(frozen=True)
class UsageLimit:
    """Usage limit definition for a metric.

    Attributes:
        metric_name: The metric this limit applies to (e.g., 'api_calls', 'tokens')
        included_amount: Amount included in plan per period
        period: Billing period ('monthly', 'yearly')
        overage_rate: Cost per unit over limit (e.g., 0.01 per API call)
        hard_limit: If True, requests are blocked when limit reached
        warning_threshold: Percentage of limit to trigger warning (e.g., 80)
    """
    metric_name: str
    included_amount: float
    period: str = "monthly"  # 'monthly' or 'yearly'
    overage_rate: float = 0.0  # Cost per unit over limit
    hard_limit: bool = False  # If True, reject when exceeded
    warning_threshold: float = 80.0  # Warn at % of limit


@dataclass(frozen=True)
class Plan:
    """Plan definition with included features and usage limits."""

    id: str
    name: str
    description: str
    features: frozenset[str] = field(default_factory=frozenset)
    stripe_price_id: str | None = None  # Set via env var
    usage_limits: dict[str, UsageLimit] = field(default_factory=dict)  # metric_name -> limit

    def has_feature(self, feature_id: str) -> bool:
        """Check if this plan includes a feature."""
        return feature_id in self.features or "*" in self.features

    def get_usage_limit(self, metric_name: str) -> UsageLimit | None:
        """Get usage limit for a metric."""
        return self.usage_limits.get(metric_name)


# Feature registry
FEATURES: dict[str, Feature] = {
    FeatureId.BASIC_EXTRACTION: Feature(
        id=FeatureId.BASIC_EXTRACTION,
        name="Basic Extraction",
        description="Extract entities and relationships from documents",
    ),
    FeatureId.KNOWLEDGE_GRAPH: Feature(
        id=FeatureId.KNOWLEDGE_GRAPH,
        name="Knowledge Graph",
        description="Visualize and explore knowledge graphs",
    ),
    FeatureId.FORMULA_BUILDER: Feature(
        id=FeatureId.FORMULA_BUILDER,
        name="Formula Builder",
        description="Build and evaluate business formulas",
    ),
    FeatureId.ADVANCED_MODELS: Feature(
        id=FeatureId.ADVANCED_MODELS,
        name="Advanced AI Models",
        description="Access to GPT-4, Claude, and other advanced models",
        requires_pro=True,
    ),
    FeatureId.PRIORITY_SUPPORT: Feature(
        id=FeatureId.PRIORITY_SUPPORT,
        name="Priority Support",
        description="Faster response times for support requests",
        requires_pro=True,
    ),
    FeatureId.TEAM_COLLABORATION: Feature(
        id=FeatureId.TEAM_COLLABORATION,
        name="Team Collaboration",
        description="Share workspaces with team members",
        requires_pro=True,
    ),
    FeatureId.CUSTOM_INTEGRATIONS: Feature(
        id=FeatureId.CUSTOM_INTEGRATIONS,
        name="Custom Integrations",
        description="Build custom data connectors",
        requires_enterprise=True,
    ),
    FeatureId.DEDICATED_SUPPORT: Feature(
        id=FeatureId.DEDICATED_SUPPORT,
        name="Dedicated Support",
        description="Dedicated account manager and support",
        requires_enterprise=True,
    ),
    FeatureId.SLA_GUARANTEE: Feature(
        id=FeatureId.SLA_GUARANTEE,
        name="SLA Guarantee",
        description="99.9% uptime SLA with compensation",
        requires_enterprise=True,
    ),
}

# Usage limit definitions
USAGE_LIMITS = {
    "free": {
        "api_calls": UsageLimit(
            metric_name="api_calls",
            included_amount=1000,
            period="monthly",
            overage_rate=0.0,
            hard_limit=True,
            warning_threshold=80.0,
        ),
        "tokens": UsageLimit(
            metric_name="tokens",
            included_amount=100_000,
            period="monthly",
            overage_rate=0.0,
            hard_limit=True,
            warning_threshold=80.0,
        ),
        "storage_gb": UsageLimit(
            metric_name="storage_gb",
            included_amount=1.0,
            period="monthly",
            overage_rate=0.0,
            hard_limit=True,
            warning_threshold=80.0,
        ),
    },
    "pro": {
        "api_calls": UsageLimit(
            metric_name="api_calls",
            included_amount=50_000,
            period="monthly",
            overage_rate=0.001,  # $0.001 per call = $10 per 10k
            hard_limit=False,
            warning_threshold=80.0,
        ),
        "tokens": UsageLimit(
            metric_name="tokens",
            included_amount=5_000_000,
            period="monthly",
            overage_rate=0.00002,  # $0.02 per 1k tokens
            hard_limit=False,
            warning_threshold=80.0,
        ),
        "storage_gb": UsageLimit(
            metric_name="storage_gb",
            included_amount=50.0,
            period="monthly",
            overage_rate=0.1,  # $0.10 per GB
            hard_limit=False,
            warning_threshold=80.0,
        ),
    },
    "enterprise": {
        "api_calls": UsageLimit(
            metric_name="api_calls",
            included_amount=float("inf"),  # Unlimited
            period="monthly",
            overage_rate=0.0,
            hard_limit=False,
            warning_threshold=90.0,
        ),
        "tokens": UsageLimit(
            metric_name="tokens",
            included_amount=float("inf"),
            period="monthly",
            overage_rate=0.0,
            hard_limit=False,
            warning_threshold=90.0,
        ),
        "storage_gb": UsageLimit(
            metric_name="storage_gb",
            included_amount=float("inf"),
            period="monthly",
            overage_rate=0.0,
            hard_limit=False,
            warning_threshold=90.0,
        ),
    },
}


# Plan definitions
PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Free",
        description="Get started with basic extraction and knowledge exploration",
        features=frozenset({
            FeatureId.BASIC_EXTRACTION,
            FeatureId.KNOWLEDGE_GRAPH,
            FeatureId.FORMULA_BUILDER,
        }),
        usage_limits=USAGE_LIMITS["free"],
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        description="Advanced features for power users and small teams",
        features=frozenset({
            FeatureId.BASIC_EXTRACTION,
            FeatureId.KNOWLEDGE_GRAPH,
            FeatureId.FORMULA_BUILDER,
            FeatureId.ADVANCED_MODELS,
            FeatureId.PRIORITY_SUPPORT,
            FeatureId.TEAM_COLLABORATION,
        }),
        usage_limits=USAGE_LIMITS["pro"],
    ),
    "enterprise": Plan(
        id="enterprise",
        name="Enterprise",
        description="Full platform access with custom integrations and dedicated support",
        features=frozenset({"*"}),  # All features
        usage_limits=USAGE_LIMITS["enterprise"],
    ),
}


def get_plan(plan_id: str) -> Plan | None:
    """Get plan by ID."""
    return PLANS.get(plan_id)


def get_feature(feature_id: str) -> Feature | None:
    """Get feature by ID."""
    return FEATURES.get(feature_id)


def check_entitlement(plan_id: str, feature_id: str) -> bool:
    """Check if a plan has a specific feature."""
    plan = get_plan(plan_id)
    if not plan:
        return False
    return plan.has_feature(feature_id)


def get_plan_features(plan_id: str) -> list[Feature]:
    """Get all features available to a plan."""
    plan = get_plan(plan_id)
    if not plan:
        return []

    if "*" in plan.features:
        return list(FEATURES.values())

    return [f for fid, f in FEATURES.items() if fid in plan.features]


def get_entitlements_response(plan_id: str) -> dict[str, Any]:
    """Get entitlements response for API."""
    plan = get_plan(plan_id)
    if not plan:
        return get_entitlements_responseResult.model_validate({"plan_id": plan_id, "features": {}})

    features = {}
    for fid, feature in FEATURES.items():
        features[fid] = {
            "enabled": plan.has_feature(fid),
            "name": feature.name,
            "description": feature.description,
        }

    return get_entitlements_responseResult.model_validate({
        "plan_id": plan_id,
        "plan_name": plan.name,
        "features": features,
    })


def build_plan_version_payload(plan_id: str) -> dict[str, Any]:
    """Serialize in-code defaults into a persisted plan-version payload."""
    plan = get_plan(plan_id)
    if not plan:
        raise ValueError(f"Unknown plan_id: {plan_id}")

    usage_limits = {
        metric_name: {
            "metric_name": limit.metric_name,
            "included_amount": limit.included_amount,
            "period": limit.period,
            "overage_rate": limit.overage_rate,
            "hard_limit": limit.hard_limit,
            "warning_threshold": limit.warning_threshold,
        }
        for metric_name, limit in plan.usage_limits.items()
    }
    return {
        "plan_id": plan.id,
        "plan_name": plan.name,
        "description": plan.description,
        "features": sorted(plan.features),
        "usage_limits": usage_limits,
    }

