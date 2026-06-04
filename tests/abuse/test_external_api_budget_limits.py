from __future__ import annotations

import pytest

from tests.production_readiness.manifest import assert_paths_exist, assert_pytest_coverage, assert_readme_documents_gap


pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_external_api_budget_limit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/unit/test_llm_cost_log_schema.py",
            "tests/chaos/test_llm_failure.py",
        ),
        label="external API budget coverage",
    )
    assert_paths_exist(
        (
            "docs/troubleshooting/runbooks/application/budget-exceeded.md",
            "docs/troubleshooting/runbooks/application/llm-cost-anomaly.md",
        ),
        label="external API budget runbooks",
    )
    assert_readme_documents_gap("tests/abuse/README.md", "EXTERNAL_PROVIDER_BUDGET_LIVE_ENFORCEMENT")

