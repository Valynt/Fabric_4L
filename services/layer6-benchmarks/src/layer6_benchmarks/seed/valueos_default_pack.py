"""Default ValueOS benchmark pack definitions.

The pack is intentionally service-local seed data: it is global benchmark
reference content loaded through Layer 6, not tenant-owned customer data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from layer6_benchmarks.models.valueos_contracts import ValueOSBenchmarkMetric

VALUEOS_REQUIRED_INDUSTRIES = [
    "technology",
    "financial_services",
    "healthcare",
    "manufacturing",
    "retail",
]

VALUEOS_METRICS_PER_INDUSTRY = 20
VALUEOS_BASELINE_METRIC_TARGET = len(VALUEOS_REQUIRED_INDUSTRIES) * VALUEOS_METRICS_PER_INDUSTRY

_INGESTED_AT = datetime(2026, 6, 25, 12, 0, 0, tzinfo=timezone.utc)

_INDUSTRY_SOURCE_NAMES = {
    "technology": "ValueOS Technology Benchmark Council",
    "financial_services": "ValueOS Financial Services Benchmark Council",
    "healthcare": "ValueOS Healthcare Benchmark Council",
    "manufacturing": "ValueOS Manufacturing Benchmark Council",
    "retail": "ValueOS Retail Benchmark Council",
}

_METRIC_BLUEPRINTS = [
    ("finance", "accounts_payable", "cost_per_invoice", "AP cost per invoice", "USD", "cost_savings", False),
    ("finance", "working_capital", "days_sales_outstanding", "Days sales outstanding", "days", "cost_savings", False),
    ("finance", "planning", "forecast_variance", "Forecast variance", "percent", "risk_mitigation", False),
    ("finance", "procurement", "sourcing_cycle_time", "Sourcing cycle time", "days", "cost_savings", False),
    ("sales", "pipeline", "sales_cycle_days", "Sales cycle length", "days", "revenue_uplift", False),
    ("sales", "pipeline", "win_rate", "Competitive win rate", "percent", "revenue_uplift", True),
    ("sales", "pipeline", "qualified_pipeline_conversion", "Qualified pipeline conversion", "percent", "revenue_uplift", True),
    ("sales", "pricing", "average_contract_value", "Average contract value", "USD", "revenue_uplift", True),
    ("customer_success", "retention", "logo_churn", "Logo churn", "percent", "revenue_uplift", False),
    ("customer_success", "retention", "net_revenue_retention", "Net revenue retention", "percent", "revenue_uplift", True),
    ("customer_success", "support", "cost_per_ticket", "Cost per support ticket", "USD", "cost_savings", False),
    ("customer_success", "support", "first_contact_resolution", "First contact resolution", "percent", "cost_savings", True),
    ("operations", "productivity", "employee_productivity_index", "Employee productivity index", "index", "cost_savings", True),
    ("operations", "automation", "manual_touch_rate", "Manual touch rate", "percent", "cost_savings", False),
    ("operations", "quality", "defect_or_error_rate", "Defect or error rate", "percent", "risk_mitigation", False),
    ("operations", "cycle_time", "order_to_cash_cycle_time", "Order-to-cash cycle time", "days", "cost_savings", False),
    ("risk", "compliance", "audit_preparation_hours", "Audit preparation hours", "hours", "risk_mitigation", False),
    ("risk", "security", "incident_resolution_hours", "Incident resolution time", "hours", "risk_mitigation", False),
    ("technology", "cloud", "cloud_spend_per_employee", "Cloud spend per employee", "USD", "cost_savings", False),
    ("technology", "service", "system_availability", "System availability", "percent", "risk_mitigation", True),
]

_INDUSTRY_BASE_MULTIPLIER = {
    "technology": Decimal("1.00"),
    "financial_services": Decimal("1.18"),
    "healthcare": Decimal("1.10"),
    "manufacturing": Decimal("0.92"),
    "retail": Decimal("0.84"),
}

_UNIT_BASELINES = {
    "USD": Decimal("100"),
    "days": Decimal("30"),
    "percent": Decimal("20"),
    "hours": Decimal("80"),
    "index": Decimal("65"),
}


def build_valueos_default_metric_payloads() -> list[dict[str, Any]]:
    """Build the default 100-metric ValueOS benchmark pack payloads."""
    payloads: list[dict[str, Any]] = []
    for industry in VALUEOS_REQUIRED_INDUSTRIES:
        for idx, blueprint in enumerate(_METRIC_BLUEPRINTS, start=1):
            payloads.append(_metric_payload(industry=industry, blueprint=blueprint, index=idx))
    return payloads


def build_valueos_default_metrics() -> list[ValueOSBenchmarkMetric]:
    """Return validated ValueOS benchmark metrics for the default pack."""
    return [
        ValueOSBenchmarkMetric.model_validate(payload)
        for payload in build_valueos_default_metric_payloads()
    ]


def _metric_payload(
    *,
    industry: str,
    blueprint: tuple[str, str, str, str, str, str, bool],
    index: int,
) -> dict[str, Any]:
    domain, category, specific_metric, display_name, unit, value_type, higher_is_better = blueprint
    metric_id = f"{industry}_{domain}_{specific_metric}"
    p10, p25, p50, p75, p90, mean, std_dev = _distribution_values(
        industry=industry,
        unit=unit,
        index=index,
        higher_is_better=higher_is_better,
    )
    return {
        "metric_id": metric_id,
        "slug": metric_id.replace("_", "-"),
        "display_name": f"{display_name} ({industry.replace('_', ' ').title()})",
        "description": (
            f"Curated ValueOS benchmark for {display_name.lower()} in "
            f"{industry.replace('_', ' ')}."
        ),
        "unit": unit,
        "taxonomy": {
            "value_pillar": _value_pillar(value_type),
            "functional_domain": domain,
            "category": category,
            "lifecycle_stage": "justify_commit" if index % 2 else "realize_expand",
            "value_type": value_type,
        },
        "segmentation": {
            "industry": industry,
            "company_size_band": "enterprise",
            "geography": "global",
            "maturity_band": "standardized",
            "revenue_band": "100m_1b",
        },
        "distribution": {
            "p10": float(p10),
            "p25": float(p25),
            "p50": float(p50),
            "p75": float(p75),
            "p90": float(p90),
            "mean": float(mean),
            "std_dev": float(std_dev),
            "sample_size": 640 + (index * 37),
            "shape": "skewed_right" if not higher_is_better else "normal",
        },
        "provenance": [
            {
                "source_name": _INDUSTRY_SOURCE_NAMES[industry],
                "source_type": "proprietary_survey",
                "publication_year": 2026,
                "license_class": "internal",
                "ingested_at": _INGESTED_AT.isoformat().replace("+00:00", "Z"),
                "extraction_method": "curated_default_pack",
                "confidence_score": 0.82 if index % 3 else 0.74,
                "caveats": ["Default pack baseline; replace with licensed source record when available."],
            }
        ],
        "governance": {
            "version": "1.0.0",
            "vintage": "2026Q2",
            "status": "active",
            "owner": "benchmark-governance",
            "reviewer": "value-engineering",
            "reviewed_at": _INGESTED_AT.isoformat().replace("+00:00", "Z"),
            "stale_after": "2027-06-25",
        },
    }


def _distribution_values(
    *,
    industry: str,
    unit: str,
    index: int,
    higher_is_better: bool,
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    base = _UNIT_BASELINES[unit] * _INDUSTRY_BASE_MULTIPLIER[industry] * (
        Decimal("0.70") + (Decimal(index) / Decimal("40"))
    )
    if unit == "percent":
        base = min(base, Decimal("75"))
    if higher_is_better:
        p10 = base * Decimal("0.70")
        p25 = base * Decimal("0.85")
        p50 = base
        p75 = base * Decimal("1.12")
        p90 = base * Decimal("1.25")
    else:
        p10 = base * Decimal("0.55")
        p25 = base * Decimal("0.75")
        p50 = base
        p75 = base * Decimal("1.35")
        p90 = base * Decimal("1.80")
    mean = (p25 + p50 + p75) / Decimal("3")
    std_dev = (p90 - p10) / Decimal("4")
    return tuple(_quantize(value) for value in (p10, p25, p50, p75, p90, mean, std_dev))


def _value_pillar(value_type: str) -> str:
    if value_type in {"revenue_growth", "revenue_uplift"}:
        return "revenue_growth"
    if value_type == "risk_mitigation":
        return "risk_reduction"
    return "operational_efficiency"


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"))

