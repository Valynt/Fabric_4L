"""
Unit tests for Value Realization Ledger models.

Tests for ValueRealizationEntry and ValueRealizationUpdate models.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.value_realization_ledger import (
    UpdateReason,
    ValueRealizationEntry,
    ValueRealizationUpdate,
    ValueType,
)


class TestValueRealizationEntry:
    def test_create_value_realization_entry(self):
        """Should create a value realization entry with required fields."""
        entry = ValueRealizationEntry(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_type=ValueType.ROI.value,
            entry_name="Q1 ROI Calculation",
            description="ROI calculation for Q1 2025",
            current_value=150000.0,
            value_unit="USD",
            value_currency="USD",
            is_active=True,
        )
        assert entry.entry_type == ValueType.ROI.value
        assert entry.current_value == 150000.0
        assert entry.value_currency == "USD"

    def test_value_type_enum_values(self):
        """ValueType enum should have expected values."""
        assert {s.value for s in ValueType} == {
            "roi",
            "cost_savings",
            "revenue_impact",
            "efficiency_gain",
            "time_savings",
            "risk_reduction",
            "custom",
        }

    def test_value_realization_calculation_provenance(self):
        """Should track calculation provenance."""
        entry = ValueRealizationEntry(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_type=ValueType.COST_SAVINGS.value,
            entry_name="Cost Savings",
            current_value=50000.0,
            value_unit="USD",
            formula_id=uuid.uuid4(),
            formula_version="1.0.0",
            benchmark_id=uuid.uuid4(),
            benchmark_version="2.0.0",
            assumption_ids=[uuid.uuid4(), uuid.uuid4()],
        )
        assert entry.formula_id is not None
        assert entry.formula_version == "1.0.0"
        assert entry.benchmark_id is not None
        assert entry.assumption_ids is not None
        assert len(entry.assumption_ids) == 2

    def test_value_realization_context_links(self):
        """Should link to opportunity, account, and business case."""
        entry = ValueRealizationEntry(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_type=ValueType.REVENUE_IMPACT.value,
            entry_name="Revenue Impact",
            current_value=200000.0,
            opportunity_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            business_case_id=uuid.uuid4(),
        )
        assert entry.opportunity_id is not None
        assert entry.account_id is not None
        assert entry.business_case_id is not None

    def test_value_realization_archival(self):
        """Should support archival."""
        entry = ValueRealizationEntry(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_type=ValueType.ROI.value,
            entry_name="Old ROI",
            current_value=100000.0,
            is_active=False,
            archived_at=datetime.now(UTC),
        )
        assert entry.is_active is False
        assert entry.archived_at is not None


class TestValueRealizationUpdate:
    def test_create_value_realization_update(self):
        """Should create a value realization update with required fields."""
        update = ValueRealizationUpdate(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_id=uuid.uuid4(),
            previous_value=100000.0,
            new_value=150000.0,
            value_change=50000.0,
            value_change_percent=50.0,
            update_reason=UpdateReason.NEW_CALCULATION.value,
            updated_by="analyst@example.com",
            updated_by_type="human",
        )
        assert update.previous_value == 100000.0
        assert update.new_value == 150000.0
        assert update.value_change == 50000.0
        assert update.update_reason == UpdateReason.NEW_CALCULATION.value

    def test_update_reason_enum_values(self):
        """UpdateReason enum should have expected values."""
        assert {s.value for s in UpdateReason} == {
            "new_calculation",
            "data_refresh",
            "formula_change",
            "benchmark_update",
            "assumption_change",
            "correction",
            "revalidation",
            "manual_override",
            "other",
        }

    def test_value_realization_update_provenance(self):
        """Should track provenance at time of update."""
        update = ValueRealizationUpdate(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_id=uuid.uuid4(),
            previous_value=100000.0,
            new_value=120000.0,
            update_reason=UpdateReason.FORMULA_CHANGE.value,
            updated_by="system",
            updated_by_type="system",
            formula_id_at_update=uuid.uuid4(),
            formula_version_at_update="2.0.0",
            benchmark_id_at_update=uuid.uuid4(),
            benchmark_version_at_update="1.5.0",
            assumption_ids_at_update=[uuid.uuid4()],
            calculation_metadata={"execution_time_ms": 150},
        )
        assert update.formula_id_at_update is not None
        assert update.formula_version_at_update == "2.0.0"
        assert update.calculation_metadata is not None

    def test_value_realization_update_calculated_fields(self):
        """Should calculate value change and percentage."""
        update = ValueRealizationUpdate(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_id=uuid.uuid4(),
            previous_value=100000.0,
            new_value=150000.0,
            value_change=50000.0,
            value_change_percent=50.0,
            update_reason=UpdateReason.DATA_REFRESH.value,
            updated_by="system",
        )
        assert update.value_change == 50000.0
        assert update.value_change_percent == 50.0

    def test_value_realization_update_negative_change(self):
        """Should handle negative value changes."""
        update = ValueRealizationUpdate(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_id=uuid.uuid4(),
            previous_value=150000.0,
            new_value=120000.0,
            value_change=-30000.0,
            value_change_percent=-20.0,
            update_reason=UpdateReason.CORRECTION.value,
            updated_by="analyst@example.com",
        )
        assert update.value_change == -30000.0
        assert update.value_change_percent == -20.0

    def test_value_realization_update_updater_types(self):
        """Should support different updater types."""
        for updater_type in ["human", "system", "agent"]:
            update = ValueRealizationUpdate(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                entry_id=uuid.uuid4(),
                previous_value=100000.0,
                new_value=110000.0,
                update_reason=UpdateReason.REVALIDATION.value,
                updated_by="updater@example.com",
                updated_by_type=updater_type,
            )
            assert update.updated_by_type == updater_type


class TestValueRealizationRelationships:
    def test_value_realization_entry_has_updates(self):
        """ValueRealizationEntry should have updates relationship."""
        entry = ValueRealizationEntry(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_type=ValueType.ROI.value,
            entry_name="Test Entry",
            current_value=100000.0,
        )
        assert hasattr(entry, "updates")

    def test_value_realization_update_has_entry(self):
        """ValueRealizationUpdate should have entry relationship."""
        update = ValueRealizationUpdate(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            entry_id=uuid.uuid4(),
            previous_value=100000.0,
            new_value=110000.0,
            update_reason=UpdateReason.NEW_CALCULATION.value,
            updated_by="system",
        )
        assert hasattr(update, "entry")
