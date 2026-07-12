from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_contains_all, assert_pytest_coverage

pytestmark = [pytest.mark.abuse, pytest.mark.production_readiness]


def test_expensive_query_limit_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/layer3/test_api_rate_limit_contract.py",
            "services/layer3-knowledge/tests/test_rate_limiter_ip_spoofing.py",
            "tests/security/test_layer3_similarity_roi_tenant_isolation.py",
        ),
        label="expensive query limit coverage",
    )
    assert_contains_all(
        "docs/troubleshooting/runbooks/application/slow-queries.md",
        ("slow", "query"),
        label="slow query runbook",
    )

