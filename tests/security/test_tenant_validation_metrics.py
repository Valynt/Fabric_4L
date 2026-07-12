"""Tenant validation metrics regression tests for Layer 4 database validation."""

from __future__ import annotations

import importlib

import pytest

db = importlib.import_module("database")
import database_facade as database


class TestTenantValidationMetricsTracking:
    def setup_method(self):
        db.reset_tenant_validation_metrics()

    def test_tracks_successful_validation(self):
        tenant = "550e8400-e29b-41d4-a716-446655440000"
        assert db.validate_tenant_id(tenant) == tenant

        metrics = db.get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 0


class TestMetricsAccuracy:
    def setup_method(self):
        db.reset_tenant_validation_metrics()

    @pytest.mark.parametrize(
        "tenant_id,error_key",
        [
            (None, "missing_context_errors"),
            ("", "empty_tenant_errors"),
            ("not-a-uuid", "uuid_format_errors"),
        ],
    )
    def test_failure_metrics_counted(self, tenant_id, error_key):
        with pytest.raises(db.TenantContextError):
            db.validate_tenant_id(tenant_id)

        metrics = db.get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 1
        assert metrics[error_key] == 1


class TestMetricsResetFunctionality:
    def test_reset_sets_all_counters_to_zero(self):
        with pytest.raises(db.TenantContextError):
            db.validate_tenant_id("bad")
        db.reset_tenant_validation_metrics()

        metrics = db.get_tenant_validation_metrics()
        assert all(v == 0 for v in metrics.values())


class TestReservedKeywordHandling:
    def setup_method(self):
        db.reset_tenant_validation_metrics()

    def test_reserved_keyword_is_accepted(self):
        assert db.validate_tenant_id("system") == "system"
        metrics = db.get_tenant_validation_metrics()
        assert metrics["validations_total"] == 1
        assert metrics["validation_failures"] == 0


class TestStableModulePathGuard:
    def test_canonical_layer4_database_path_is_resolvable(self):
        module = importlib.import_module("database")

        assert hasattr(module, "validate_tenant_id")
        assert hasattr(module, "get_tenant_validation_metrics")
        assert module.validate_tenant_id("system") == "system"


def test_tenant_validation_metrics_round_trip_and_reset():
    """Metrics counters should increment during validation and reset deterministically."""
    database.reset_tenant_validation_metrics()

    ok_tenant = "550e8400-e29b-41d4-a716-446655440000"
    assert database.validate_tenant_id(ok_tenant) == ok_tenant

    metrics = database.get_tenant_validation_metrics()
    assert metrics["validations_total"] >= 1

    database.reset_tenant_validation_metrics()
    reset = database.get_tenant_validation_metrics()
    assert reset == {
        "validations_total": 0,
        "validation_failures": 0,
        "uuid_format_errors": 0,
        "missing_context_errors": 0,
        "empty_tenant_errors": 0,
    }


def test_layer4_database_import_path_is_stable_facade():
    """Guard: tests rely on database_facade module staying stable."""
    assert database.__name__ == "database_facade"
    assert hasattr(database, "validate_tenant_id")
    assert hasattr(database, "get_tenant_validation_metrics")


def test_layer4_database_module_is_stable_compatibility_alias():
    """Guard: canonical database module must be importable and functional."""
    import database as database_module

    assert database_module.__name__ == "database"
    assert callable(database_module.validate_tenant_id)
