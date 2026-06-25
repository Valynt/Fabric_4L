#!/usr/bin/env python3
"""Validate repo-owned ValueOS benchmark and VMRT readiness evidence."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SERVICE_SRC = ROOT / "services" / "layer6-benchmarks" / "src"
sys.path.insert(0, str(SERVICE_SRC))

from layer6_benchmarks.models.valueos_contracts import validate_vmrt_trace  # noqa: E402
from layer6_benchmarks.seed.load_benchmark_packs import validate_valueos_pack  # noqa: E402
from layer6_benchmarks.seed.valueos_default_pack import (  # noqa: E402
    VALUEOS_BASELINE_METRIC_TARGET,
    VALUEOS_REQUIRED_INDUSTRIES,
    build_valueos_default_metrics,
)

BENCHMARK_SCHEMA = ROOT / "contracts/jsonschema/valueos-benchmark-metric.schema.json"
VMRT_SCHEMA = ROOT / "contracts/jsonschema/valueos-vmrt.schema.json"
SCHEMA_INDEX = ROOT / "contracts/schema-index.json"
ARTIFACT = ROOT / "artifacts/readiness/valueos-benchmark-vmrt-readiness.json"


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _schema_validator(path: Path) -> Draft202012Validator:
    schema = _load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _json_schema_payload(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {
            key: _json_schema_payload(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_json_schema_payload(item) for item in value]
    return value


def _gold_vmrt_trace() -> dict[str, Any]:
    return {
        "trace_id": "valueos-readiness-trace-001",
        "schema_version": "1.0.0",
        "industry": "technology",
        "persona": "CFO",
        "value_type": "cost_savings",
        "lifecycle_stage": "justify_commit",
        "product_category": "AI workflow automation",
        "scope": "global_system",
        "pains": [
            {
                "id": "manual-analysis-delay",
                "description": "Manual analysis delays value-case decisions.",
                "persona_owner": "CFO",
                "severity": "high",
            },
            {
                "id": "inconsistent-assumptions",
                "description": "Assumptions vary across teams and deal stages.",
                "persona_owner": "RevOps",
                "severity": "medium",
            },
        ],
        "capabilities": [
            {
                "id": "benchmark-grounding",
                "description": "Ground assumptions in governed benchmark distributions.",
                "pain_ids": ["manual-analysis-delay", "inconsistent-assumptions"],
            },
            {
                "id": "traceable-value-model",
                "description": "Maintain explicit value-model reasoning traceability.",
                "pain_ids": ["inconsistent-assumptions"],
            },
        ],
        "outcomes": [
            {
                "id": "faster-business-case",
                "description": "Business cases move from draft to review faster.",
                "capability_ids": ["benchmark-grounding"],
            },
            {
                "id": "higher-approval-confidence",
                "description": "Approvers can inspect assumptions and evidence.",
                "capability_ids": ["traceable-value-model"],
            },
        ],
        "kpis": [
            {
                "id": "case-cycle-time",
                "name": "Business case cycle time",
                "outcome_ids": ["faster-business-case"],
                "baseline": {"value": 30, "unit": "days"},
                "target": {"value": 18, "unit": "days"},
                "timeframe": "12 months",
                "benchmark_metric_id": "technology_value_driver_001",
            },
            {
                "id": "approval-rework-rate",
                "name": "Approval rework rate",
                "outcome_ids": ["higher-approval-confidence"],
                "baseline": {"value": 22, "unit": "percent"},
                "target": {"value": 12, "unit": "percent"},
                "timeframe": "12 months",
                "benchmark_metric_id": "technology_value_driver_002",
            },
        ],
        "financial_impacts": [
            {
                "id": "analyst-time-savings",
                "description": "Reduced analyst time for value-model iteration.",
                "kpi_ids": ["case-cycle-time"],
                "formula": "cases_per_year * hours_saved_per_case * loaded_hourly_cost",
                "inputs": {"cases_per_year": 80, "hours_saved_per_case": 12, "loaded_hourly_cost": 120},
                "currency": "USD",
                "time_horizon": "annual",
                "sensitivity_bounds": {"low": 72000, "high": 144000},
            },
            {
                "id": "rework-avoidance",
                "description": "Avoided rework from traceable assumptions.",
                "kpi_ids": ["approval-rework-rate"],
                "formula": "cases_per_year * rework_delta * rework_cost",
                "inputs": {"cases_per_year": 80, "rework_delta": 0.1, "rework_cost": 5000},
                "currency": "USD",
                "time_horizon": "annual",
                "sensitivity_bounds": {"low": 30000, "high": 60000},
            },
        ],
        "reasoning": {
            "natural_language_chain": [
                "The CFO pain is delayed approval from manual business-case analysis.",
                "Benchmark grounding reduces assumption search and review time.",
                "Traceable value models connect each assumption to an approvable KPI.",
                "Cycle-time reduction is measured against a governed benchmark metric.",
                "Rework reduction follows from clearer assumption ownership.",
                "Both impacts retain KPI linkage back to capabilities and pains.",
            ]
        },
        "assumptions": [
            {
                "id": "annual-case-volume",
                "description": "The customer evaluates 80 value cases per year.",
                "assumption_type": "customer_input",
                "confidence": 0.8,
                "approval_state": "pending",
                "source": "discovery intake",
            }
        ],
        "quality_scores": {
            "logical_coherence": 4.4,
            "benchmark_alignment": 4.1,
            "financial_rigor": 4.0,
            "story_clarity": 4.3,
            "overall": 4.2,
            "reviewer": "valueos-readiness",
            "reviewed_at": "2026-06-25T00:00:00Z",
        },
    }


def check_schema_index() -> CheckResult:
    index = _load_json(SCHEMA_INDEX)
    paths = {entry.get("path") for entry in index.get("entries", [])}
    required = {
        "contracts/jsonschema/valueos-benchmark-metric.schema.json",
        "contracts/jsonschema/valueos-vmrt.schema.json",
    }
    missing = sorted(required - paths)
    return CheckResult(
        name="schema_index",
        passed=not missing,
        detail="indexed" if not missing else f"missing: {', '.join(missing)}",
    )


def check_benchmark_pack() -> CheckResult:
    metrics = build_valueos_default_metrics()
    validate_valueos_pack(metrics)
    industries = {metric.segmentation.industry for metric in metrics}
    invalid = [
        metric.metric_id
        for metric in metrics
        if not metric.provenance
        or metric.provenance[0].confidence_score <= 0
        or metric.distribution.sample_size <= 0
    ]
    passed = (
        len(metrics) >= VALUEOS_BASELINE_METRIC_TARGET
        and set(VALUEOS_REQUIRED_INDUSTRIES).issubset(industries)
        and not invalid
    )
    return CheckResult(
        name="benchmark_pack",
        passed=passed,
        detail=(
            f"{len(metrics)} metrics across {len(industries)} industries"
            if passed
            else f"invalid metrics: {', '.join(invalid[:10])}"
        ),
    )


def check_schemas_accept_gold_payloads() -> CheckResult:
    metrics = build_valueos_default_metrics()
    benchmark_payload = _json_schema_payload(metrics[0].model_dump(mode="python"))
    _schema_validator(BENCHMARK_SCHEMA).validate(benchmark_payload)
    vmrt_payload = _gold_vmrt_trace()
    _schema_validator(VMRT_SCHEMA).validate(vmrt_payload)
    validate_vmrt_trace(vmrt_payload)
    return CheckResult(
        name="schema_gold_payloads",
        passed=True,
        detail="benchmark metric and VMRT gold payloads validate",
    )


def main() -> int:
    checks = [check_schema_index(), check_benchmark_pack(), check_schemas_accept_gold_payloads()]
    passed = all(check.passed for check in checks)
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(
            {
                "status": "passed" if passed else "failed",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "checks": [asdict(check) for check in checks],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status} {check.name}: {check.detail}")
    print(f"wrote {ARTIFACT.relative_to(ROOT).as_posix()}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
