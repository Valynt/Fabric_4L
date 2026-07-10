"""Tests for the VMRT runner — golden case regression detection.

These tests exercise the VMRT runner in isolation (no Neo4j, no HTTP) by
using the in-process seed dataset index.  Each test asserts:

- Happy path: all built-in golden cases pass when the engine is unmodified.
- Regression path: a deliberately wrong expected value is detected.
- Edge cases: unknown dataset / metric are reported as failures without
  raising.
- Structured log events: the runner emits the correct structured events.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from layer6_benchmarks.vmrt.golden_cases import GOLDEN_CASES
from layer6_benchmarks.vmrt.models import VMRTCase, VMRTCaseKind, VMRTRunSummary
from layer6_benchmarks.vmrt.runner import (
    VMRTRunner,
    _build_seed_index,
    _compute_compare,
    _compute_validate,
    _run_case,
)


# ---------------------------------------------------------------------------
# Seed index helpers
# ---------------------------------------------------------------------------

class TestSeedIndex:
    def test_index_contains_all_seed_datasets(self) -> None:
        index = _build_seed_index()
        expected_ids = {
            "manufacturing-efficiency-2024",
            "saas-b2b-efficiency-2024",
            "healthcare-operational-2024",
            "financial-services-performance-2024",
        }
        assert expected_ids == set(index.keys())

    def test_manufacturing_has_oee_metric(self) -> None:
        index = _build_seed_index()
        ds = index["manufacturing-efficiency-2024"]
        metric = ds.get_metric("oee_overall_equipment_effectiveness")
        assert metric is not None
        assert metric.is_higher_better is True
        assert metric.profile.sample_size == 1250

    def test_saas_churn_is_lower_is_better(self) -> None:
        index = _build_seed_index()
        metric = index["saas-b2b-efficiency-2024"].get_metric("annual_churn_rate_percent")
        assert metric is not None
        assert metric.is_higher_better is False


# ---------------------------------------------------------------------------
# Pure computation helpers
# ---------------------------------------------------------------------------

class TestComputeCompare:
    """Mirror tests for the private compare helper."""

    def _oee_metric(self):
        index = _build_seed_index()
        return index["manufacturing-efficiency-2024"].get_metric(
            "oee_overall_equipment_effectiveness"
        )

    def test_below_p10_gives_5th_percentile(self) -> None:
        metric = self._oee_metric()
        p, a, c = _compute_compare(Decimal("40"), metric)
        assert p == 5
        assert a == "needs_improvement"
        assert c == "high"

    def test_above_p90_gives_95th_percentile(self) -> None:
        metric = self._oee_metric()
        p, a, c = _compute_compare(Decimal("90"), metric)
        assert p == 95
        assert a == "top_performer"

    def test_lower_is_better_inverts_percentile(self) -> None:
        index = _build_seed_index()
        # defect_rate_percent: is_higher_better=False
        metric = index["manufacturing-efficiency-2024"].get_metric("defect_rate_percent")
        assert metric is not None
        # value below p10 is excellent for lower-is-better → percentile = 100 - 5 = 95
        p, a, c = _compute_compare(Decimal("0.05"), metric)
        assert p == 95
        assert a == "top_performer"

    def test_medium_confidence_for_sample_size_between_500_and_1000(self) -> None:
        index = _build_seed_index()
        # net_revenue_retention_percent has sample_size=980
        metric = index["saas-b2b-efficiency-2024"].get_metric(
            "net_revenue_retention_percent"
        )
        assert metric is not None
        _, _, confidence = _compute_compare(Decimal("112"), metric)
        assert confidence == "medium"

    def test_low_confidence_for_small_sample(self) -> None:
        """Build a synthetic metric with sample_size < 500."""
        from layer6_benchmarks.models.benchmark_dataset import (
            BenchmarkMetric,
            StatisticalProfile,
        )

        metric = BenchmarkMetric(
            name="tiny",
            unit="pct",
            description="",
            profile=StatisticalProfile(
                p10=Decimal("10"),
                p25=Decimal("20"),
                p50=Decimal("30"),
                p75=Decimal("40"),
                p90=Decimal("50"),
                mean=Decimal("30"),
                std_dev=Decimal("10"),
                sample_size=200,
            ),
        )
        _, _, confidence = _compute_compare(Decimal("35"), metric)
        assert confidence == "low"


class TestComputeValidate:
    def _oee_metric(self):
        return _build_seed_index()["manufacturing-efficiency-2024"].get_metric(
            "oee_overall_equipment_effectiveness"
        )

    def test_value_at_median_is_valid_info(self) -> None:
        metric = self._oee_metric()
        is_valid, severity = _compute_validate(Decimal("65"), metric, tolerance_percent=10)
        assert is_valid is True
        assert severity == "info"

    def test_upper_boundary_exact_is_valid(self) -> None:
        # p90 = 85, tolerance = 10 % → max = 85 * 1.10 = 93.5
        metric = self._oee_metric()
        is_valid, severity = _compute_validate(Decimal("93.5"), metric, tolerance_percent=10)
        assert is_valid is True

    def test_just_above_upper_boundary_is_invalid(self) -> None:
        metric = self._oee_metric()
        # 93.51 > 93.5 → out of range
        is_valid, _ = _compute_validate(Decimal("93.51"), metric, tolerance_percent=10)
        assert is_valid is False

    def test_large_deviation_yields_error_severity(self) -> None:
        metric = self._oee_metric()
        # OEE = 10 is far below range; deviation from p50=65 is ~-84.6 %
        _, severity = _compute_validate(Decimal("10"), metric, tolerance_percent=10)
        assert severity == "error"

    def test_moderate_deviation_yields_warning_severity(self) -> None:
        """Build a synthetic out-of-range but moderate deviation case."""
        from layer6_benchmarks.models.benchmark_dataset import (
            BenchmarkMetric,
            StatisticalProfile,
        )

        # p10=10, p50=100, p90=200 — choose value=140 which is valid (≤200*1.1),
        # so test an invalid value with ~35% deviation: value=135 with tighter tolerance.
        metric = BenchmarkMetric(
            name="m",
            unit="u",
            description="",
            profile=StatisticalProfile(
                p10=Decimal("10"),
                p25=Decimal("50"),
                p50=Decimal("100"),
                p75=Decimal("150"),
                p90=Decimal("200"),
                mean=Decimal("100"),
                std_dev=Decimal("40"),
                sample_size=500,
            ),
        )
        # tolerance 0% makes upper bound = 200, lower bound = 10
        # value = 135 is within range → info
        # use tolerance 0: range 10 to 200 — need a value outside
        # value=201 → deviation from p50=100 is 101%, severity=error
        # For warning we need deviation 25-50 %: e.g. value = 130 out of range
        # with tolerance_percent=0: range = [10, 200]. value=130 is inside.
        # Use tight tolerance=1: range = [10*0.99=9.9, 200*1.01=202].
        # Still inside. Let's use a metric where p90 is very low.
        metric2 = BenchmarkMetric(
            name="m2",
            unit="u",
            description="",
            profile=StatisticalProfile(
                p10=Decimal("10"),
                p25=Decimal("15"),
                p50=Decimal("20"),
                p75=Decimal("25"),
                p90=Decimal("30"),
                mean=Decimal("20"),
                std_dev=Decimal("5"),
                sample_size=500,
            ),
        )
        # p10*(1-0) = 10, p90*(1+0) = 30 with tolerance=0
        # value=26 (30%  deviation from p50=20): is_valid → 10<=26<=30 → True, info
        # value=32 (60% deviation): out of range, severity error
        # For warning: deviation 25-50 %, e.g. value=35 → dev=75% → error
        # value=27: dev=35% but is 10<=27<=30 → valid
        # Adjusted: use tolerance=0, value=32 → out of range, dev=60% → error
        # To get warning: need ~35% deviation from p50 but value outside range
        # E.g. p50=100, p90=110, tolerance=0: range=[p10*(1-0), 110], 
        # value=135 → dev=35% → warning
        metric3 = BenchmarkMetric(
            name="m3",
            unit="u",
            description="",
            profile=StatisticalProfile(
                p10=Decimal("80"),
                p25=Decimal("90"),
                p50=Decimal("100"),
                p75=Decimal("105"),
                p90=Decimal("110"),
                mean=Decimal("100"),
                std_dev=Decimal("8"),
                sample_size=500,
            ),
        )
        # range with tol=0: [80, 110]. value=135: dev=(135-100)/100*100=35% → warning
        is_valid, severity = _compute_validate(Decimal("135"), metric3, tolerance_percent=0)
        assert is_valid is False
        assert severity == "warning"


# ---------------------------------------------------------------------------
# _run_case
# ---------------------------------------------------------------------------

class TestRunCase:
    def test_unknown_dataset_returns_failure(self) -> None:
        case = VMRTCase(
            id="bad-ds",
            kind=VMRTCaseKind.COMPARE,
            dataset_id="nonexistent-dataset",
            metric="oee",
            company_value=Decimal("70"),
        )
        index = _build_seed_index()
        result = _run_case(case, index)
        assert result.passed is False
        assert "not found" in result.failure_reason

    def test_unknown_metric_returns_failure(self) -> None:
        case = VMRTCase(
            id="bad-metric",
            kind=VMRTCaseKind.COMPARE,
            dataset_id="manufacturing-efficiency-2024",
            metric="nonexistent_metric",
            company_value=Decimal("70"),
        )
        index = _build_seed_index()
        result = _run_case(case, index)
        assert result.passed is False
        assert "not found" in result.failure_reason

    def test_correct_compare_case_passes(self) -> None:
        case = VMRTCase(
            id="ok",
            kind=VMRTCaseKind.COMPARE,
            dataset_id="manufacturing-efficiency-2024",
            metric="oee_overall_equipment_effectiveness",
            company_value=Decimal("40"),
            expected_percentile=5,
            expected_assessment="needs_improvement",
            expected_confidence="high",
        )
        index = _build_seed_index()
        result = _run_case(case, index)
        assert result.passed is True
        assert result.failure_reason == ""

    def test_wrong_expected_percentile_detected(self) -> None:
        case = VMRTCase(
            id="wrong-p",
            kind=VMRTCaseKind.COMPARE,
            dataset_id="manufacturing-efficiency-2024",
            metric="oee_overall_equipment_effectiveness",
            company_value=Decimal("40"),
            expected_percentile=99,  # wrong
            expected_assessment="needs_improvement",
            expected_confidence="high",
        )
        index = _build_seed_index()
        result = _run_case(case, index)
        assert result.passed is False
        assert "percentile" in result.failure_reason

    def test_correct_validate_case_passes(self) -> None:
        case = VMRTCase(
            id="ok-val",
            kind=VMRTCaseKind.VALIDATE,
            dataset_id="manufacturing-efficiency-2024",
            metric="oee_overall_equipment_effectiveness",
            company_value=Decimal("65"),
            expected_is_valid=True,
            expected_severity="info",
            tolerance_percent=10,
        )
        index = _build_seed_index()
        result = _run_case(case, index)
        assert result.passed is True

    def test_wrong_expected_validity_detected(self) -> None:
        case = VMRTCase(
            id="wrong-valid",
            kind=VMRTCaseKind.VALIDATE,
            dataset_id="manufacturing-efficiency-2024",
            metric="oee_overall_equipment_effectiveness",
            company_value=Decimal("65"),
            expected_is_valid=False,  # wrong — 65 is within range
            expected_severity="error",
            tolerance_percent=10,
        )
        index = _build_seed_index()
        result = _run_case(case, index)
        assert result.passed is False
        assert "is_valid" in result.failure_reason


# ---------------------------------------------------------------------------
# VMRTRunner
# ---------------------------------------------------------------------------

class TestVMRTRunner:
    def test_all_golden_cases_pass(self) -> None:
        """Smoke test: the full golden case suite must pass against the engine."""
        runner = VMRTRunner()
        summary = runner.run_all()
        failed = summary.failed_results()
        failure_msgs = [f"{r.case.id}: {r.failure_reason}" for r in failed]
        assert summary.regression_detected is False, (
            f"VMRT regression detected in {summary.failed} / {summary.total} cases:\n"
            + "\n".join(failure_msgs)
        )

    def test_custom_case_subset(self) -> None:
        """Runner accepts a custom case list and only runs those."""
        cases = [
            VMRTCase(
                id="subset-1",
                kind=VMRTCaseKind.COMPARE,
                dataset_id="manufacturing-efficiency-2024",
                metric="oee_overall_equipment_effectiveness",
                company_value=Decimal("90"),
                expected_percentile=95,
                expected_assessment="top_performer",
                expected_confidence="high",
            )
        ]
        runner = VMRTRunner(cases=cases, name="subset-run")
        summary = runner.run_all()
        assert summary.total == 1
        assert summary.passed == 1

    def test_regression_detected_when_case_fails(self) -> None:
        """When a case fails the summary reports regression_detected=True."""
        cases = [
            VMRTCase(
                id="deliberate-fail",
                kind=VMRTCaseKind.COMPARE,
                dataset_id="manufacturing-efficiency-2024",
                metric="oee_overall_equipment_effectiveness",
                company_value=Decimal("40"),
                expected_percentile=99,  # intentionally wrong — actual is 5
            )
        ]
        runner = VMRTRunner(cases=cases)
        summary = runner.run_all()
        assert summary.regression_detected is True
        assert summary.failed == 1
        failed = summary.failed_results()
        assert failed[0].case.id == "deliberate-fail"
        assert "percentile" in failed[0].failure_reason

    def test_regression_warning_log_emitted(self) -> None:
        """When regression is detected the runner calls logger.warning."""
        cases = [
            VMRTCase(
                id="deliberate-fail",
                kind=VMRTCaseKind.COMPARE,
                dataset_id="manufacturing-efficiency-2024",
                metric="oee_overall_equipment_effectiveness",
                company_value=Decimal("40"),
                expected_percentile=99,  # wrong
            )
        ]
        runner = VMRTRunner(cases=cases)

        with patch("layer6_benchmarks.vmrt.runner.logger") as mock_log:
            mock_log.info = MagicMock()
            mock_log.debug = MagicMock()
            mock_log.warning = MagicMock()
            runner.run_all()
            warning_events = [
                call.args[0]
                for call in mock_log.warning.call_args_list
                if call.args
            ]
        assert "benchmark.regression_detected" in warning_events

    def test_log_summary_called_on_summary(self) -> None:
        """log_summary does not raise."""
        runner = VMRTRunner()
        summary = runner.run_all()
        runner.log_summary(summary)  # should not raise

    def test_golden_cases_cover_both_compare_and_validate(self) -> None:
        compare_cases = [c for c in GOLDEN_CASES if c.kind == VMRTCaseKind.COMPARE]
        validate_cases = [c for c in GOLDEN_CASES if c.kind == VMRTCaseKind.VALIDATE]
        assert len(compare_cases) >= 5, "Need at least 5 compare golden cases"
        assert len(validate_cases) >= 3, "Need at least 3 validate golden cases"

    def test_golden_cases_cover_higher_and_lower_better(self) -> None:
        higher_cases = [c for c in GOLDEN_CASES if c.is_higher_better]
        lower_cases = [c for c in GOLDEN_CASES if not c.is_higher_better]
        assert higher_cases, "Need at least one is_higher_better=True case"
        assert lower_cases, "Need at least one is_higher_better=False case"

    def test_golden_cases_cover_multiple_datasets(self) -> None:
        dataset_ids = {c.dataset_id for c in GOLDEN_CASES}
        assert len(dataset_ids) >= 2, "Golden cases should cover at least 2 datasets"
