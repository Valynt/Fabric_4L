"""
Unit tests for Formula Governance models.

Tests for Formula, FormulaVersion, and FormulaParameter models.
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.formula_governance import (
    Formula,
    FormulaParameter,
    FormulaStatus,
    FormulaType,
    FormulaVersion,
    ParameterType,
)


class TestFormula:
    def test_create_formula(self):
        """Should create a formula with required fields."""
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="ROI Calculation",
            slug="roi-calculation",
            formula_type=FormulaType.ROI_CALCULATION.value,
            description="Calculates return on investment",
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={"type": "object"},
            output_schema={"type": "number"},
            is_active=True,
        )
        assert formula.slug == "roi-calculation"
        assert formula.formula_type == FormulaType.ROI_CALCULATION.value
        assert formula.is_active is True

    def test_formula_type_enum_values(self):
        """FormulaType enum should have expected values."""
        assert {s.value for s in FormulaType} == {
            "roi_calculation",
            "cost_savings",
            "revenue_impact",
            "efficiency_gain",
            "risk_reduction",
            "custom",
        }

    def test_formula_deprecation(self):
        """Should support deprecation with reason."""
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Old Formula",
            slug="old-formula",
            formula_type=FormulaType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
            is_active=False,
            deprecated_at=datetime.now(UTC),
            deprecation_reason="Replaced by new formula",
        )
        assert formula.is_active is False
        assert formula.deprecated_at is not None
        assert formula.deprecation_reason == "Replaced by new formula"


class TestFormulaVersion:
    def test_create_formula_version(self):
        """Should create a formula version with required fields."""
        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            version="1.0.0",
            expression="return investment / cost",
            expression_language="python",
            status=FormulaStatus.DRAFT.value,
        )
        assert version.version == "1.0.0"
        assert version.expression_language == "python"
        assert version.status == FormulaStatus.DRAFT.value

    def test_formula_status_enum_values(self):
        """FormulaStatus enum should have expected values."""
        assert {s.value for s in FormulaStatus} == {
            "draft",
            "pending_approval",
            "approved",
            "deprecated",
            "archived",
        }

    def test_formula_version_approval(self):
        """Should track approval information."""
        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            version="1.0.0",
            expression="return value",
            expression_language="python",
            status=FormulaStatus.APPROVED.value,
            approved_by="approver@example.com",
            approved_at=datetime.now(UTC),
        )
        assert version.status == FormulaStatus.APPROVED.value
        assert version.approved_by == "approver@example.com"
        assert version.approved_at is not None


class TestFormulaParameter:
    def test_create_formula_parameter(self):
        """Should create a formula parameter with required fields."""
        param = FormulaParameter(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            name="investment",
            display_name="Investment Amount",
            parameter_type=ParameterType.CURRENCY.value,
            description="The initial investment amount",
            required=True,
        )
        assert param.name == "investment"
        assert param.parameter_type == ParameterType.CURRENCY.value
        assert param.required is True

    def test_parameter_type_enum_values(self):
        """ParameterType enum should have expected values."""
        assert {s.value for s in ParameterType} == {
            "number",
            "string",
            "boolean",
            "currency",
            "percentage",
            "date",
            "duration",
        }

    def test_formula_parameter_constraints(self):
        """Should support parameter constraints."""
        param = FormulaParameter(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            name="discount_rate",
            parameter_type=ParameterType.PERCENTAGE.value,
            required=False,
            default_value=0.1,
            min_value=0.0,
            max_value=1.0,
        )
        assert param.required is False
        assert param.default_value == 0.1
        assert param.min_value == 0.0
        assert param.max_value == 1.0

    def test_formula_parameter_allowed_values(self):
        """Should support allowed values for enum-like parameters."""
        param = FormulaParameter(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            name="region",
            parameter_type=ParameterType.STRING.value,
            allowed_values=["north_america", "europe", "asia"],
        )
        assert param.allowed_values == ["north_america", "europe", "asia"]


class TestFormulaRelationships:
    def test_formula_has_versions(self):
        """Formula should have versions relationship."""
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Formula",
            slug="test-formula",
            formula_type=FormulaType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
        )
        assert hasattr(formula, "versions")

    def test_formula_has_parameters(self):
        """Formula should have parameters relationship."""
        formula = Formula(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            name="Test Formula",
            slug="test-formula",
            formula_type=FormulaType.CUSTOM.value,
            current_version="1.0.0",
            latest_version="1.0.0",
            input_schema={},
            output_schema={},
        )
        assert hasattr(formula, "parameters")

    def test_formula_version_has_formula(self):
        """FormulaVersion should have formula relationship."""
        version = FormulaVersion(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            version="1.0.0",
            expression="return value",
            expression_language="python",
        )
        assert hasattr(version, "formula")

    def test_formula_parameter_has_formula(self):
        """FormulaParameter should have formula relationship."""
        param = FormulaParameter(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            formula_id=uuid.uuid4(),
            name="test",
            parameter_type=ParameterType.NUMBER.value,
        )
        assert hasattr(param, "formula")
