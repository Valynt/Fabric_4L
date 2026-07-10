"""VMRT runner — executes golden cases against the in-process benchmark engine.

The runner is intentionally self-contained: it calls the *same pure functions*
that the production API handlers call (percentile bucketing, assessment
labelling, tolerance range validation) rather than hitting the HTTP layer.
This keeps VMRT fast and hermetic while still exercising the real computation.

Structured log events follow the standard defined in
``docs/reference/structured-logging-standard.md`` §Benchmarks (L6):

* ``benchmark.run_started`` — INFO
* ``benchmark.iteration_completed`` — DEBUG
* ``benchmark.run_completed`` — INFO
* ``benchmark.regression_detected`` — WARNING (when any case fails)
"""

from __future__ import annotations

import decimal
import time
from decimal import Decimal
from typing import Any

import structlog

from ..models.benchmark_dataset import (
    FINANCIAL_SERVICES_BENCHMARK_SEED,
    HEALTHCARE_BENCHMARK_SEED,
    MANUFACTURING_BENCHMARK_SEED,
    SAAS_B2B_BENCHMARK_SEED,
    BenchmarkDataset,
    BenchmarkMetric,
    StatisticalProfile,
)
from .golden_cases import GOLDEN_CASES
from .models import VMRTCase, VMRTCaseKind, VMRTResult, VMRTRunSummary

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Seed index
# ---------------------------------------------------------------------------

def _build_seed_index() -> dict[str, BenchmarkDataset]:
    """Build an in-memory index of all built-in seed datasets."""
    index: dict[str, BenchmarkDataset] = {}
    for seed in (
        MANUFACTURING_BENCHMARK_SEED,
        SAAS_B2B_BENCHMARK_SEED,
        HEALTHCARE_BENCHMARK_SEED,
        FINANCIAL_SERVICES_BENCHMARK_SEED,
    ):
        dataset = _dataset_from_seed(seed)
        index[dataset.dataset_id] = dataset
    return index


def _dataset_from_seed(seed: dict[str, Any]) -> BenchmarkDataset:
    dataset = BenchmarkDataset(
        dataset_id=seed["dataset_id"],
        name=seed["name"],
        description=seed["description"],
        industry=seed["industry"],
        segment=seed.get("segment"),
        geography=seed.get("geography"),
        version=seed.get("version", "1.0.0"),
        data_source=seed.get("data_source"),
        is_public=seed.get("is_public", False),
        tenant_id="system",
        ownership_mode="global_system",
    )
    for metric_data in seed.get("metrics", {}).values():
        profile_data = metric_data["profile"]
        profile = StatisticalProfile(
            p10=Decimal(profile_data["p10"]),
            p25=Decimal(profile_data["p25"]),
            p50=Decimal(profile_data["p50"]),
            p75=Decimal(profile_data["p75"]),
            p90=Decimal(profile_data["p90"]),
            mean=Decimal(profile_data["mean"]),
            std_dev=Decimal(profile_data["std_dev"]),
            sample_size=profile_data["sample_size"],
        )
        metric = BenchmarkMetric(
            name=metric_data["name"],
            unit=metric_data["unit"],
            description=metric_data["description"],
            profile=profile,
            lower_bound=(
                Decimal(metric_data["lower_bound"])
                if metric_data.get("lower_bound") is not None
                else None
            ),
            upper_bound=(
                Decimal(metric_data["upper_bound"])
                if metric_data.get("upper_bound") is not None
                else None
            ),
            is_higher_better=metric_data.get("is_higher_better", True),
        )
        dataset.add_metric(metric)
    return dataset


# ---------------------------------------------------------------------------
# Pure computation helpers (mirror the production API handlers exactly)
# ---------------------------------------------------------------------------

def _compute_compare(
    company_value: Decimal,
    metric: BenchmarkMetric,
) -> tuple[int, str, str]:
    """Return ``(percentile, assessment, confidence)`` for a compare case."""
    profile = metric.profile

    if company_value <= profile.p10:
        distribution_percentile = 5
    elif company_value <= profile.p25:
        distribution_percentile = 17
    elif company_value <= profile.p50:
        distribution_percentile = 37
    elif company_value <= profile.p75:
        distribution_percentile = 62
    elif company_value <= profile.p90:
        distribution_percentile = 82
    else:
        distribution_percentile = 95

    if metric.is_higher_better:
        percentile = distribution_percentile
    else:
        percentile = 100 - distribution_percentile

    if percentile >= 80:
        assessment = "top_performer"
    elif percentile >= 60:
        assessment = "above_average"
    elif percentile >= 40:
        assessment = "average"
    elif percentile >= 20:
        assessment = "below_average"
    else:
        assessment = "needs_improvement"

    if profile.sample_size >= 1000:
        confidence = "high"
    elif profile.sample_size >= 500:
        confidence = "medium"
    else:
        confidence = "low"

    return percentile, assessment, confidence


def _compute_validate(
    value: Decimal,
    metric: BenchmarkMetric,
    tolerance_percent: int,
) -> tuple[bool, str]:
    """Return ``(is_valid, severity)`` for a validate case."""
    profile = metric.profile
    tolerance_factor = Decimal(tolerance_percent) / Decimal(100)
    range_min = profile.p10 * (Decimal(1) - tolerance_factor)
    range_max = profile.p90 * (Decimal(1) + tolerance_factor)
    is_valid = range_min <= value <= range_max

    median = profile.p50
    deviation_percent = (
        0.0 if value == median else float((value - median) / median * 100)
    )

    if is_valid:
        severity = "info"
    else:
        abs_deviation = abs(deviation_percent)
        if abs_deviation > 50:
            severity = "error"
        elif abs_deviation > 25:
            severity = "warning"
        else:
            severity = "info"

    return is_valid, severity


# ---------------------------------------------------------------------------
# Case executor
# ---------------------------------------------------------------------------

def _run_case(case: VMRTCase, seed_index: dict[str, BenchmarkDataset]) -> VMRTResult:
    dataset = seed_index.get(case.dataset_id)
    if dataset is None:
        return VMRTResult(
            case=case,
            passed=False,
            failure_reason=f"Dataset '{case.dataset_id}' not found in seed index",
        )

    metric = dataset.get_metric(case.metric)
    if metric is None:
        return VMRTResult(
            case=case,
            passed=False,
            failure_reason=f"Metric '{case.metric}' not found in dataset '{case.dataset_id}'",
        )

    if case.kind == VMRTCaseKind.COMPARE:
        return _run_compare_case(case, metric)
    else:
        return _run_validate_case(case, metric)


def _run_compare_case(case: VMRTCase, metric: BenchmarkMetric) -> VMRTResult:
    try:
        percentile, assessment, confidence = _compute_compare(case.company_value, metric)
    except (ValueError, decimal.InvalidOperation) as exc:
        return VMRTResult(
            case=case,
            passed=False,
            failure_reason=f"Computation error: {exc}",
        )

    failures: list[str] = []
    if case.expected_percentile is not None and percentile != case.expected_percentile:
        failures.append(
            f"percentile: expected {case.expected_percentile}, got {percentile}"
        )
    if case.expected_assessment is not None and assessment != case.expected_assessment:
        failures.append(
            f"assessment: expected '{case.expected_assessment}', got '{assessment}'"
        )
    if case.expected_confidence is not None and confidence != case.expected_confidence:
        failures.append(
            f"confidence: expected '{case.expected_confidence}', got '{confidence}'"
        )

    return VMRTResult(
        case=case,
        passed=not failures,
        actual_percentile=percentile,
        actual_assessment=assessment,
        actual_confidence=confidence,
        failure_reason="; ".join(failures),
    )


def _run_validate_case(case: VMRTCase, metric: BenchmarkMetric) -> VMRTResult:
    try:
        is_valid, severity = _compute_validate(
            case.company_value, metric, case.tolerance_percent
        )
    except (ValueError, decimal.InvalidOperation) as exc:
        return VMRTResult(
            case=case,
            passed=False,
            failure_reason=f"Computation error: {exc}",
        )

    failures: list[str] = []
    if case.expected_is_valid is not None and is_valid != case.expected_is_valid:
        failures.append(
            f"is_valid: expected {case.expected_is_valid}, got {is_valid}"
        )
    if case.expected_severity is not None and severity != case.expected_severity:
        failures.append(
            f"severity: expected '{case.expected_severity}', got '{severity}'"
        )

    return VMRTResult(
        case=case,
        passed=not failures,
        actual_is_valid=is_valid,
        actual_severity=severity,
        failure_reason="; ".join(failures),
    )


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class VMRTRunner:
    """Executes VMRT golden cases and emits structured log events.

    Parameters
    ----------
    cases:
        Override the default :data:`.golden_cases.GOLDEN_CASES` list.  Useful
        for targeted testing of a subset of cases.
    name:
        Human-readable name for this run, used in log events.
    """

    def __init__(
        self,
        cases: list[VMRTCase] | None = None,
        name: str = "valueos-benchmark-vmrt",
    ) -> None:
        self._cases = cases if cases is not None else GOLDEN_CASES
        self._name = name
        self._seed_index: dict[str, BenchmarkDataset] = _build_seed_index()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_all(self) -> VMRTRunSummary:
        """Run every registered golden case and return a summary."""
        run_start = time.monotonic()

        logger.info(
            "benchmark.run_started",
            benchmark_name=self._name,
            dataset_size=len(self._cases),
        )

        results: list[VMRTResult] = []
        for iteration, case in enumerate(self._cases, start=1):
            iter_start = time.monotonic()
            result = _run_case(case, self._seed_index)
            results.append(result)

            duration_ms = int((time.monotonic() - iter_start) * 1000)
            score = 1.0 if result.passed else 0.0
            logger.debug(
                "benchmark.iteration_completed",
                benchmark_name=self._name,
                iteration=iteration,
                case_id=case.id,
                score=score,
                duration_ms=duration_ms,
            )

        summary = VMRTRunSummary(results=results)
        total_duration_ms = int((time.monotonic() - run_start) * 1000)

        logger.info(
            "benchmark.run_completed",
            benchmark_name=self._name,
            avg_score=round(summary.pass_rate, 4),
            duration_ms=total_duration_ms,
            total=summary.total,
            passed=summary.passed,
            failed=summary.failed,
        )

        if summary.regression_detected:
            previous_score = 1.0  # assume prior run was clean
            logger.warning(
                "benchmark.regression_detected",
                benchmark_name=self._name,
                score=round(summary.pass_rate, 4),
                threshold=1.0,
                previous_score=previous_score,
                failed_cases=[r.case.id for r in summary.failed_results()],
            )

        return summary

    def log_summary(self, summary: VMRTRunSummary) -> None:
        """Log a human-readable summary of a completed run."""
        bound = logger.bind(benchmark_name=self._name)
        if summary.regression_detected:
            bound.warning(
                "VMRT regression summary",
                total=summary.total,
                passed=summary.passed,
                failed=summary.failed,
                pass_rate=f"{summary.pass_rate:.1%}",
            )
            for result in summary.failed_results():
                bound.warning(
                    "VMRT case FAILED",
                    case_id=result.case.id,
                    reason=result.failure_reason,
                )
        else:
            bound.info(
                "VMRT all cases passed",
                total=summary.total,
                pass_rate=f"{summary.pass_rate:.1%}",
            )
