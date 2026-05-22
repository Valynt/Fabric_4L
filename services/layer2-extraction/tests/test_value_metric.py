"""Tests for the ValueMetric ontology model and its graph integration.

Validates:
- ValueMetric Pydantic model validation and field defaults
- MetricDirection enum alignment
- ExtractionResult.get_all_entities() includes ValueMetric
- RDF generator emits ValueMetric nodes and ValueDriver→impacts→ValueMetric triples
- ValueMetricExtractionResponse structured output wrapper
"""

import uuid

import pytest

from layer2_extraction.models import (
    ExtractionResult,
    MetricDirection,
    ValueCategory,
    ValueDriver,
    ValueMetric,
    ValueMetricExtractionResponse,
)
from layer2_extraction.output.rdf_generator import generate_rdf


UUID_STRING_LENGTH = 36


class TestValueMetricModel:
    """Unit tests for the ValueMetric Pydantic model."""

    def test_creates_value_metric_with_required_fields(self):
        """Should create ValueMetric with only required fields and auto-generate UUID."""
        vm = ValueMetric(
            name="Days Sales Outstanding",
            description="Average number of days to collect payment after a sale",
            unit="days",
        )

        assert vm.name == "Days Sales Outstanding"
        assert vm.unit == "days"
        assert len(vm.id) == UUID_STRING_LENGTH
        assert vm.confidence == 0.0
        assert vm.direction == MetricDirection.LOWER_IS_BETTER

    def test_creates_value_metric_with_all_fields(self):
        """Should accept all optional fields."""
        driver_id = str(uuid.uuid4())
        vm = ValueMetric(
            name="Net Revenue Retention",
            description="Percentage of recurring revenue retained from existing customers",
            unit="%",
            direction=MetricDirection.HIGHER_IS_BETTER,
            baseline_value=95.0,
            target_value=110.0,
            benchmark_source="KeyBanc SaaS Survey 2024",
            formula_string="{retained_revenue} / {starting_revenue} * 100",
            value_driver_ids=[driver_id],
            confidence=0.92,
        )

        assert vm.direction == MetricDirection.HIGHER_IS_BETTER
        assert vm.baseline_value == 95.0
        assert vm.target_value == 110.0
        assert vm.benchmark_source == "KeyBanc SaaS Survey 2024"
        assert driver_id in vm.value_driver_ids
        assert vm.confidence == 0.92

    def test_rejects_empty_name(self):
        """Should reject empty or blank name."""
        with pytest.raises(ValueError):
            ValueMetric(
                name="",
                description="A valid description for the metric",
                unit="days",
            )

    def test_rejects_short_description(self):
        """Should reject description shorter than 10 characters."""
        with pytest.raises(ValueError):
            ValueMetric(name="DSO", description="Too short", unit="days")

    def test_rejects_confidence_out_of_range(self):
        """Should reject confidence values outside [0.0, 1.0]."""
        with pytest.raises(ValueError):
            ValueMetric(
                name="DSO",
                description="Days sales outstanding metric",
                unit="days",
                confidence=1.5,
            )

    def test_rejects_invalid_value_driver_ref(self):
        """Should reject non-UUID value_driver_ids."""
        with pytest.raises(ValueError):
            ValueMetric(
                name="DSO",
                description="Days sales outstanding metric",
                unit="days",
                value_driver_ids=["not-a-uuid"],
            )

    def test_normalizes_name_whitespace(self):
        """Should strip leading/trailing whitespace from name."""
        vm = ValueMetric(
            name="  Inventory Turns  ",
            description="Number of times inventory is sold per year",
            unit="turns/year",
        )
        assert vm.name == "Inventory Turns"

    def test_rejects_extra_fields(self):
        """Should reject unknown extra fields (extra='forbid')."""
        with pytest.raises(ValueError):
            ValueMetric(
                name="DSO",
                description="Days sales outstanding metric",
                unit="days",
                unknown_field="value",
            )


class TestMetricDirectionEnum:
    """Validate MetricDirection enum values."""

    def test_all_directions_present(self):
        """MetricDirection has all three expected values."""
        expected = {"higher_is_better", "lower_is_better", "target_value"}
        actual = {d.value for d in MetricDirection}
        assert actual == expected

    def test_direction_from_string(self):
        """MetricDirection can be created from string values."""
        assert MetricDirection("higher_is_better") == MetricDirection.HIGHER_IS_BETTER
        assert MetricDirection("lower_is_better") == MetricDirection.LOWER_IS_BETTER
        assert MetricDirection("target_value") == MetricDirection.TARGET_VALUE


class TestExtractionResultWithValueMetric:
    """Validate ExtractionResult includes ValueMetric in entity collections."""

    def test_extraction_result_has_value_metrics_field(self):
        """ExtractionResult accepts value_metrics list."""
        vm = ValueMetric(
            name="Churn Rate",
            description="Percentage of customers lost in a given period",
            unit="%",
            direction=MetricDirection.LOWER_IS_BETTER,
        )
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        assert len(result.value_metrics) == 1
        assert result.value_metrics[0].name == "Churn Rate"

    def test_get_all_entities_includes_value_metrics(self):
        """get_all_entities() returns ValueMetric instances."""
        vm = ValueMetric(
            name="DSO",
            description="Days sales outstanding for AR collections",
            unit="days",
        )
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        all_entities = result.get_all_entities()
        assert vm in all_entities

    def test_get_entity_by_id_finds_value_metric(self):
        """get_entity_by_id() can locate a ValueMetric by its UUID."""
        vm = ValueMetric(
            name="DSO",
            description="Days sales outstanding for AR collections",
            unit="days",
        )
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        found = result.get_entity_by_id(vm.id)
        assert found is vm

    def test_extraction_result_default_empty_value_metrics(self):
        """ExtractionResult defaults value_metrics to an empty list."""
        result = ExtractionResult(source_url="https://example.com")
        assert result.value_metrics == []


class TestValueMetricRDFGeneration:
    """Validate RDF generator emits correct triples for ValueMetric."""

    def _make_metric(self, **kwargs) -> ValueMetric:
        defaults = {
            "name": "Days Sales Outstanding",
            "description": "Average number of days to collect payment after a sale",
            "unit": "days",
        }
        defaults.update(kwargs)
        return ValueMetric(**defaults)

    def test_rdf_contains_value_metric_type(self):
        """Generated RDF declares the entity as a ValueMetric."""
        vm = self._make_metric()
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        rdf = generate_rdf(result, [])
        assert "ValueMetric" in rdf

    def test_rdf_contains_metric_name(self):
        """Generated RDF includes the metric name literal."""
        vm = self._make_metric(name="Inventory Turns")
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        rdf = generate_rdf(result, [])
        assert "Inventory Turns" in rdf

    def test_rdf_contains_metric_unit(self):
        """Generated RDF includes the unit literal."""
        vm = self._make_metric(unit="turns/year")
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        rdf = generate_rdf(result, [])
        assert "turns/year" in rdf

    def test_rdf_contains_direction(self):
        """Generated RDF includes the direction literal."""
        vm = self._make_metric(direction=MetricDirection.HIGHER_IS_BETTER)
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        rdf = generate_rdf(result, [])
        assert "higher_is_better" in rdf

    def test_rdf_emits_impacts_relationship(self):
        """Generated RDF emits ValueDriver→impacts→ValueMetric triple."""
        vd = ValueDriver(
            category=ValueCategory.COST_REDUCTION,
            name="Reduce AR Cycle",
            description="Reduce accounts receivable collection cycle",
            unit="days",
        )
        vm = self._make_metric(value_driver_ids=[vd.id])
        result = ExtractionResult(
            source_url="https://example.com",
            value_drivers=[vd],
            value_metrics=[vm],
        )
        rdf = generate_rdf(result, [])
        assert "impacts" in rdf
        assert vd.id in rdf
        assert vm.id in rdf

    def test_rdf_emits_baseline_and_target_values(self):
        """Generated RDF includes numeric baseline and target values."""
        vm = self._make_metric(baseline_value=45.0, target_value=37.0)
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        rdf = generate_rdf(result, [])
        assert "45" in rdf
        assert "37" in rdf

    def test_rdf_omits_optional_fields_when_not_set(self):
        """Generated RDF does not emit optional properties when they are None."""
        vm = self._make_metric()
        result = ExtractionResult(source_url="https://example.com", value_metrics=[vm])
        rdf = generate_rdf(result, [])
        # benchmarkSource, baselineValue, targetValue should be absent when not set
        assert "benchmarkSource" not in rdf
        assert "baselineValue" not in rdf
        assert "targetValue" not in rdf


class TestValueMetricExtractionResponse:
    """Validate the structured output wrapper for LLM extraction."""

    def test_empty_response(self):
        """ValueMetricExtractionResponse accepts an empty list."""
        response = ValueMetricExtractionResponse(value_metrics=[])
        assert response.value_metrics == []

    def test_response_with_metrics(self):
        """ValueMetricExtractionResponse wraps a list of ValueMetric instances."""
        vm = ValueMetric(
            name="DSO",
            description="Days sales outstanding for AR collections",
            unit="days",
        )
        response = ValueMetricExtractionResponse(value_metrics=[vm])
        assert len(response.value_metrics) == 1
        assert response.value_metrics[0].name == "DSO"

    def test_rejects_extra_fields(self):
        """ValueMetricExtractionResponse enforces extra='forbid'."""
        with pytest.raises(ValueError):
            ValueMetricExtractionResponse(value_metrics=[], unknown="field")
