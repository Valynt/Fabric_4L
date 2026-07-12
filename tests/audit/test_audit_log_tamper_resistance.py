from __future__ import annotations

import pytest
from tests.production_readiness.manifest import assert_pytest_coverage

pytestmark = [pytest.mark.audit, pytest.mark.production_readiness]


def test_audit_log_tamper_resistance_coverage_exists() -> None:
    assert_pytest_coverage(
        (
            "tests/shared/audit/test_ledger_chain.py",
            "tests/security/test_layer5_audit_mutation_protection.py",
            "services/layer5-ground-truth/tests/test_audit_append_only_guards.py",
            "tests/recovery/test_restore_audit_logs.py",
        ),
        label="audit log tamper resistance coverage",
    )

