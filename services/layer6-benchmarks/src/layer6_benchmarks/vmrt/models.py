"""VMRT data models.

Defines the golden-case and result types used by the Value Model Regression
Testing runner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum


class VMRTCaseKind(str, Enum):
    """Whether the case exercises compare or validate logic."""

    COMPARE = "compare"
    VALIDATE = "validate"


@dataclass
class VMRTCase:
    """A single golden-case assertion for the VMRT runner.

    Each case pairs an input with the exact output that the current benchmark
    engine must produce.  If the engine produces a different result the case is
    flagged as a regression.
    """

    #: Unique human-readable identifier for this golden case.
    id: str
    #: Which statistical operation this case exercises.
    kind: VMRTCaseKind
    #: ID of the benchmark dataset under test.
    dataset_id: str
    #: The metric name within the dataset.
    metric: str
    #: The value being submitted to the engine.
    company_value: Decimal
    #: Expected percentile (compare cases only).
    expected_percentile: int | None = None
    #: Expected assessment string (compare cases only).
    expected_assessment: str | None = None
    #: Expected confidence string (compare cases only).
    expected_confidence: str | None = None
    #: Expected ``is_valid`` flag (validate cases only).
    expected_is_valid: bool | None = None
    #: Expected severity string (validate cases only).
    expected_severity: str | None = None
    #: Tolerance percent used for validate cases (default 10).
    tolerance_percent: int = 10
    #: Human-readable description of what this case tests.
    description: str = ""
    #: Whether ``is_higher_better`` should be True for the metric.
    is_higher_better: bool = True


@dataclass
class VMRTResult:
    """Outcome of running a single :class:`VMRTCase`."""

    case: VMRTCase
    passed: bool
    #: Actual percentile returned by the engine (compare cases).
    actual_percentile: int | None = None
    #: Actual assessment returned by the engine (compare cases).
    actual_assessment: str | None = None
    #: Actual confidence returned by the engine (compare cases).
    actual_confidence: str | None = None
    #: Actual ``is_valid`` flag from the engine (validate cases).
    actual_is_valid: bool | None = None
    #: Actual severity from the engine (validate cases).
    actual_severity: str | None = None
    #: Human-readable failure explanation (empty when passed).
    failure_reason: str = ""


@dataclass
class VMRTRunSummary:
    """Aggregated summary of a full VMRT run."""

    results: list[VMRTResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def regression_detected(self) -> bool:
        return self.failed > 0

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 1.0
        return self.passed / self.total

    def failed_results(self) -> list[VMRTResult]:
        return [r for r in self.results if not r.passed]
