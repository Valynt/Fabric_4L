"""Unit tests for VMRT data models."""

from __future__ import annotations

from decimal import Decimal

import pytest

from layer6_benchmarks.vmrt.models import (
    VMRTCase,
    VMRTCaseKind,
    VMRTResult,
    VMRTRunSummary,
)


class TestVMRTCase:
    def test_compare_case_defaults(self) -> None:
        case = VMRTCase(
            id="test-case",
            kind=VMRTCaseKind.COMPARE,
            dataset_id="ds-1",
            metric="oee",
            company_value=Decimal("70"),
        )
        assert case.id == "test-case"
        assert case.kind == VMRTCaseKind.COMPARE
        assert case.company_value == Decimal("70")
        assert case.expected_percentile is None
        assert case.expected_is_valid is None
        assert case.tolerance_percent == 10
        assert case.is_higher_better is True

    def test_validate_case_defaults(self) -> None:
        case = VMRTCase(
            id="val-case",
            kind=VMRTCaseKind.VALIDATE,
            dataset_id="ds-1",
            metric="defect",
            company_value=Decimal("1.5"),
            expected_is_valid=True,
            expected_severity="info",
            is_higher_better=False,
        )
        assert case.kind == VMRTCaseKind.VALIDATE
        assert case.expected_is_valid is True
        assert case.expected_severity == "info"
        assert case.is_higher_better is False


class TestVMRTResult:
    def _make_case(self) -> VMRTCase:
        return VMRTCase(
            id="c",
            kind=VMRTCaseKind.COMPARE,
            dataset_id="ds",
            metric="m",
            company_value=Decimal("50"),
        )

    def test_passed_result(self) -> None:
        result = VMRTResult(case=self._make_case(), passed=True)
        assert result.passed is True
        assert result.failure_reason == ""

    def test_failed_result(self) -> None:
        result = VMRTResult(
            case=self._make_case(),
            passed=False,
            failure_reason="percentile: expected 37, got 5",
        )
        assert result.passed is False
        assert "percentile" in result.failure_reason


class TestVMRTRunSummary:
    def _make_case(self, cid: str) -> VMRTCase:
        return VMRTCase(
            id=cid,
            kind=VMRTCaseKind.COMPARE,
            dataset_id="ds",
            metric="m",
            company_value=Decimal("50"),
        )

    def test_empty_summary(self) -> None:
        summary = VMRTRunSummary()
        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.regression_detected is False
        assert summary.pass_rate == 1.0

    def test_all_passing(self) -> None:
        results = [
            VMRTResult(case=self._make_case(f"c{i}"), passed=True) for i in range(5)
        ]
        summary = VMRTRunSummary(results=results)
        assert summary.total == 5
        assert summary.passed == 5
        assert summary.failed == 0
        assert summary.regression_detected is False
        assert summary.pass_rate == 1.0
        assert summary.failed_results() == []

    def test_partial_failure(self) -> None:
        results = [
            VMRTResult(case=self._make_case("c0"), passed=True),
            VMRTResult(
                case=self._make_case("c1"),
                passed=False,
                failure_reason="mismatch",
            ),
            VMRTResult(case=self._make_case("c2"), passed=True),
        ]
        summary = VMRTRunSummary(results=results)
        assert summary.total == 3
        assert summary.passed == 2
        assert summary.failed == 1
        assert summary.regression_detected is True
        assert abs(summary.pass_rate - 2 / 3) < 1e-9
        failed = summary.failed_results()
        assert len(failed) == 1
        assert failed[0].case.id == "c1"

    def test_all_failing(self) -> None:
        results = [
            VMRTResult(
                case=self._make_case(f"c{i}"),
                passed=False,
                failure_reason="bad",
            )
            for i in range(3)
        ]
        summary = VMRTRunSummary(results=results)
        assert summary.total == 3
        assert summary.passed == 0
        assert summary.failed == 3
        assert summary.pass_rate == 0.0
        assert summary.regression_detected is True
