"""Fixtures for the production-path certification suite."""

from __future__ import annotations

import os
import uuid

import pytest

from tests.certification.harness import (
    CertificationHarness,
    CertificationRecorder,
    current_git_sha,
)
from tests.shared.live_harness import SeedIds, build_seed_ids

CERT_RUN_ID = os.getenv(
    "CERTIFICATION_RUN_ID", f"certification-{uuid.uuid4().hex[:8]}"
)


@pytest.fixture(scope="session")
def cert_seed_ids() -> SeedIds:
    """Deterministic per-run seed identifiers for the certification tenants."""
    return build_seed_ids(CERT_RUN_ID)


@pytest.fixture(scope="session")
def cert_recorder() -> CertificationRecorder:
    return CertificationRecorder(
        run_id=CERT_RUN_ID,
        trace_id=f"trace-{CERT_RUN_ID}",
        git_sha=current_git_sha(),
    )


@pytest.fixture(scope="session")
def cert_harness(
    cert_seed_ids: SeedIds, cert_recorder: CertificationRecorder
) -> CertificationHarness:
    return CertificationHarness(cert_seed_ids, cert_recorder)
