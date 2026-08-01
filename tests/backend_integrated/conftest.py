"""Shared backend-integrated validation harness for the Fabric_4L milestone.

These tests intentionally exercise live Fabric_4L service contracts instead of
frontend route mocks. They are additive to the Playwright validation program and
must fail closed when services, persistence, tenant boundaries, or audit trails
are unavailable.

The harness implementation lives in ``tests/shared/live_harness.py`` so the
production-path certification suite (``tests/certification/``) can reuse the
same request, seeding, and tenant-denial primitives.
"""

from __future__ import annotations

import pytest
from tests.shared.live_harness import (
    RUN_SLUG_SUFFIX,
    SERVICE_URLS,
    BackendValidationHarness,
    SeedIds,
    build_seed_ids,
)

__all__ = [
    "BackendValidationHarness",
    "RUN_SLUG_SUFFIX",
    "SERVICE_URLS",
    "SeedIds",
]


@pytest.fixture(scope="session")
def seed_ids() -> SeedIds:
    return build_seed_ids()


@pytest.fixture
def backend(seed_ids: SeedIds) -> BackendValidationHarness:
    return BackendValidationHarness(seed_ids)


@pytest.fixture(scope="session")
def validation_seed_plan(seed_ids: SeedIds) -> dict:
    return {
        "tenants": [seed_ids.tenant_a, seed_ids.tenant_b],
        "users": [seed_ids.user_admin, seed_ids.user_reviewer],
        "roles": ["admin", "reviewer", "sales_rep", "value_engineer", "executive_buyer"],
        "accounts": [seed_ids.account_id],
        "documents": [seed_ids.document_id],
        "value_packs": [seed_ids.value_pack_id],
        "benchmarks": [seed_ids.benchmark_id],
        "evidence_records": [seed_ids.evidence_id],
        "formula_inputs": [seed_ids.formula_id],
        "crm_mock_records": [seed_ids.crm_connection_id],
        "approval_states": ["draft", "submitted", "changes_requested", "approved", "exported"],
    }
