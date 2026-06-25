"""ValueOS benchmark and VMRT contract tests."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from pydantic import ValidationError as PydanticValidationError

from layer6_benchmarks.models.valueos_contracts import (
    validate_valueos_benchmark_metric,
    validate_vmrt_trace,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_SCHEMA = REPO_ROOT / "contracts" / "jsonschema" / "valueos-benchmark-metric.schema.json"
VMRT_SCHEMA = REPO_ROOT / "contracts" / "jsonschema" / "valueos-vmrt.schema.json"


def _schema_validator(path: Path) -> Draft202012Validator:
    schema = json.loads(path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def valid_metric_payload() -> dict:
    return {
        "metric_id": "finance_ap_cost_per_invoice",
        "slug": "finance-ap-cost-per-invoice",
        "display_name": "AP cost per invoice",
        "description": "All-in cost to process one accounts-payable invoice.",
        "unit": "USD",
        "taxonomy": {
            "value_pillar": "operational_efficiency",
            "functional_domain": "finance",
            "category": "accounts_payable",
            "lifecycle_stage": "justify_commit",
            "value_type": "cost_savings",
        },
        "segmentation": {
            "industry": "technology",
            "company_size_band": "mid_market",
            "geography": "US",
            "maturity_band": "manual",
            "revenue_band": "10m_100m",
        },
        "distribution": {
            "p10": 4.2,
            "p25": 6.33,
            "p50": 8.4,
            "p75": 10.89,
            "p90": 14.9,
            "mean": 8.8,
            "std_dev": 2.1,
            "sample_size": 6744,
            "shape": "skewed_right",
        },
        "provenance": [
            {
                "source_name": "APQC Open Standards Benchmarking",
                "source_type": "licensed_research",
                "publication_year": 2023,
                "license_class": "licensed_restricted",
                "ingested_at": "2026-06-25T12:00:00Z",
                "confidence_score": 0.92,
                "extraction_method": "curated_manual_entry",
                "caveats": ["Licensed details cannot be exposed in customer output."],
            }
        ],
        "governance": {
            "version": "1.0.0",
            "vintage": "2026Q2",
            "status": "active",
            "owner": "benchmark-governance",
            "reviewer": "value-engineering",
            "reviewed_at": "2026-06-25T12:00:00Z",
            "stale_after": "2027-06-25",
        },
    }


def valid_vmrt_payload() -> dict:
    return {
        "trace_id": "vos-pt1-trace-001",
        "schema_version": "1.0.0",
        "industry": "technology",
        "persona": "CFO",
        "value_type": "cost_savings",
        "lifecycle_stage": "justify_commit",
        "product_category": "accounts_payable_automation",
        "scope": "global_system",
        "pains": [
            {
                "id": "pain_manual_ap",
                "description": "Manual invoice processing increases finance labor cost.",
                "persona_owner": "CFO",
                "severity": "high",
            },
            {
                "id": "pain_error_rework",
                "description": "Exception handling creates avoidable rework.",
                "persona_owner": "Controller",
                "severity": "medium",
            },
        ],
        "capabilities": [
            {
                "id": "cap_invoice_capture",
                "description": "Automated invoice capture and coding.",
                "pain_ids": ["pain_manual_ap"],
            },
            {
                "id": "cap_exception_routing",
                "description": "Rules-based exception routing.",
                "pain_ids": ["pain_error_rework"],
            },
        ],
        "outcomes": [
            {
                "id": "outcome_lower_unit_cost",
                "description": "Lower processing cost per invoice.",
                "capability_ids": ["cap_invoice_capture"],
            },
            {
                "id": "outcome_less_rework",
                "description": "Fewer exception touches.",
                "capability_ids": ["cap_exception_routing"],
            },
        ],
        "kpis": [
            {
                "id": "kpi_cost_per_invoice",
                "name": "Cost per invoice",
                "outcome_ids": ["outcome_lower_unit_cost"],
                "baseline": {"value": 12.4, "unit": "USD"},
                "target": {"value": 6.1, "unit": "USD"},
                "timeframe": "12 months",
                "benchmark_metric_id": "finance_ap_cost_per_invoice",
            },
            {
                "id": "kpi_exception_rate",
                "name": "Invoice exception rate",
                "outcome_ids": ["outcome_less_rework"],
                "baseline": {"value": 3.2, "unit": "percent"},
                "target": {"value": 1.1, "unit": "percent"},
                "timeframe": "12 months",
                "benchmark_metric_id": "finance_invoice_exception_rate",
            },
        ],
        "financial_impacts": [
            {
                "id": "impact_invoice_savings",
                "description": "Gross processing savings from lower unit cost.",
                "kpi_ids": ["kpi_cost_per_invoice"],
                "formula": "(baseline_cost - target_cost) * annual_invoice_count",
                "inputs": {
                    "baseline_cost": 12.4,
                    "target_cost": 6.1,
                    "annual_invoice_count": 30000,
                },
                "currency": "USD",
                "time_horizon": "annual",
                "sensitivity_bounds": {"low": 138000, "high": 186000},
            },
            {
                "id": "impact_rework_savings",
                "description": "Savings from reduced exception rework.",
                "kpi_ids": ["kpi_exception_rate"],
                "formula": "(baseline_rate - target_rate) * invoices * rework_cost",
                "inputs": {
                    "baseline_rate": 0.032,
                    "target_rate": 0.011,
                    "invoices": 30000,
                    "rework_cost": 18,
                },
                "currency": "USD",
                "time_horizon": "annual",
                "sensitivity_bounds": {"low": 9000, "high": 15000},
            },
        ],
        "reasoning": {
            "natural_language_chain": [
                "Benchmark the current AP unit cost against the peer distribution.",
                "Quantify annual invoice volume from vendor count and billing cadence.",
                "Set the target unit cost from the automation benchmark range.",
                "Calculate unit savings between baseline and target cost.",
                "Multiply unit savings by annual invoice count.",
                "Apply implementation costs and sensitivity bounds before promotion.",
            ]
        },
        "assumptions": [
            {
                "id": "assumption_invoice_volume",
                "description": "Annual invoice count is based on 2,500 vendors.",
                "assumption_type": "customer_input",
                "confidence": 0.82,
                "approval_state": "pending",
                "source": "discovery_workshop",
            }
        ],
        "quality_scores": {
            "logical_coherence": 4.4,
            "benchmark_alignment": 4.1,
            "financial_rigor": 4.3,
            "story_clarity": 4.2,
            "overall": 4.25,
            "reviewer": "value-engineering",
            "reviewed_at": "2026-06-25T12:00:00Z",
        },
    }


def test_valueos_benchmark_metric_schema_accepts_distribution_first_metric() -> None:
    _schema_validator(BENCHMARK_SCHEMA).validate(valid_metric_payload())


def test_valueos_benchmark_metric_schema_rejects_missing_provenance() -> None:
    payload = valid_metric_payload()
    payload["provenance"] = []

    with pytest.raises(ValidationError):
        _schema_validator(BENCHMARK_SCHEMA).validate(payload)


def test_valueos_benchmark_metric_runtime_rejects_unordered_percentiles() -> None:
    payload = valid_metric_payload()
    payload["distribution"]["p25"] = 20

    with pytest.raises(PydanticValidationError, match="VALUEOS_METRIC_DISTRIBUTION_ORDER_INVALID"):
        validate_valueos_benchmark_metric(payload)


def test_valueos_benchmark_metric_runtime_requires_source_confidence() -> None:
    payload = valid_metric_payload()
    del payload["provenance"][0]["confidence_score"]

    with pytest.raises(PydanticValidationError):
        validate_valueos_benchmark_metric(payload)


def test_vmrt_schema_accepts_gold_trace_shape() -> None:
    _schema_validator(VMRT_SCHEMA).validate(valid_vmrt_payload())


def test_vmrt_runtime_accepts_traceable_pain_to_impact_graph() -> None:
    trace = validate_vmrt_trace(valid_vmrt_payload())

    assert trace.financial_impacts[0].kpi_ids == ["kpi_cost_per_invoice"]
    assert trace.kpis[0].benchmark_metric_id == "finance_ap_cost_per_invoice"


def test_vmrt_runtime_rejects_financial_impact_with_unknown_kpi() -> None:
    payload = valid_vmrt_payload()
    payload["financial_impacts"][0]["kpi_ids"] = ["kpi_missing"]

    with pytest.raises(PydanticValidationError, match="VMRT_UNKNOWN_KPI_REF"):
        validate_vmrt_trace(payload)


def test_vmrt_runtime_rejects_orphaned_outcome_chain() -> None:
    payload = valid_vmrt_payload()
    payload["outcomes"][0]["capability_ids"] = ["cap_missing"]

    with pytest.raises(PydanticValidationError, match="VMRT_UNKNOWN_CAPABILITY_REF"):
        validate_vmrt_trace(payload)


def test_vmrt_schema_rejects_too_short_reasoning_chain() -> None:
    payload = deepcopy(valid_vmrt_payload())
    payload["reasoning"]["natural_language_chain"] = ["too short"]

    with pytest.raises(ValidationError):
        _schema_validator(VMRT_SCHEMA).validate(payload)

