"""Value Model Regression Testing (VMRT) for Layer 6 Benchmark Service.

VMRT provides deterministic regression tests for benchmark comparison and
validation logic. It runs known-good ``golden cases`` through the statistical
engine and detects any drift in computed percentiles, assessments, or
validation outcomes.

Usage::

    from layer6_benchmarks.vmrt import VMRTRunner

    runner = VMRTRunner()
    results = runner.run_all()
    runner.log_summary(results)
"""

from .models import VMRTCase, VMRTResult, VMRTRunSummary
from .runner import VMRTRunner

__all__ = ["VMRTCase", "VMRTResult", "VMRTRunSummary", "VMRTRunner"]
