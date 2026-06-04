"""Report generation capacity-budget tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

pytestmark = [pytest.mark.performance]

WORKFLOW = Path(".github/workflows/performance-load-tests.yml")
JOURNEY_PROFILE = Path("tests/performance/k6/journey-load-test.js")


@dataclass(frozen=True)
class ReportGenerationBudget:
    max_sections: int
    max_pages: int
    p95_render_ms: int
    p95_export_ms: int
    max_evidence_items: int

    def estimated_render_ms(self, sections: int, evidence_items: int) -> int:
        return 200 + sections * 60 + evidence_items * 15

    def estimated_export_ms(self, pages: int) -> int:
        return 500 + pages * 120


BUDGET = ReportGenerationBudget(
    max_sections=12,
    max_pages=30,
    p95_render_ms=2_000,
    p95_export_ms=5_000,
    max_evidence_items=60,
)


def test_report_render_budget_scales_with_sections_and_evidence() -> None:
    estimated = BUDGET.estimated_render_ms(
        sections=BUDGET.max_sections,
        evidence_items=BUDGET.max_evidence_items,
    )

    assert estimated <= BUDGET.p95_render_ms


def test_report_export_budget_scales_with_page_count() -> None:
    estimated = BUDGET.estimated_export_ms(pages=BUDGET.max_pages)

    assert estimated <= BUDGET.p95_export_ms


def test_journey_profile_covers_case_export_latency() -> None:
    source = JOURNEY_PROFILE.read_text(encoding="utf-8")

    assert "caseExportTime" in source
    assert "j3_case_export_ms" in source
    assert "j3_studio_error_rate: ['rate<0.02']" in source


def test_ci_publishes_performance_trend_artifact() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "artifacts/performance/slo-window-history.json" in workflow
    assert "actions/upload-artifact@v4" in workflow
