"""Unit tests for Layer 6 API Pydantic schemas."""

import pytest
from pydantic import ValidationError

from layer6_benchmarks.api.schemas import (
    ComparisonRequestPayload,
    ComparisonResponse,
    DatasetUpsertPayload,
    ValidationRequestPayload,
    ValidationResponse,
)


class TestComparisonRequestPayload:
    def test_valid_payload(self) -> None:
        payload = ComparisonRequestPayload(
            dataset_id="ds1",
            metric="m1",
            company_value="123.45",
            industry="manufacturing",
        )
        assert payload.dataset_id == "ds1"
        assert payload.segment is None

    def test_rejects_missing_required_fields(self) -> None:
        with pytest.raises(ValidationError):
            ComparisonRequestPayload(
                metric="m1", company_value="123.45", industry="manufacturing"
            )


class TestValidationRequestPayload:
    def test_default_tolerance(self) -> None:
        payload = ValidationRequestPayload(
            dataset_id="ds1",
            metric="m1",
            value="50.0",
        )
        assert payload.tolerance_percent == 10


class TestDatasetUpsertPayload:
    def test_default_version(self) -> None:
        payload = DatasetUpsertPayload(
            dataset_id="ds1",
            name="Name",
            description="Desc",
            industry="manufacturing",
            metrics={},
        )
        assert payload.version == "1.0.0"


class TestComparisonResponse:
    def test_serialization(self) -> None:
        resp = ComparisonResponse(
            percentile=75,
            peer_median="100.0",
            peer_range=("80.0", "120.0"),
            sample_size=500,
            confidence="high",
            assessment="above_average",
        )
        d = resp.model_dump()
        assert d["percentile"] == 75
        assert d["peer_median"] == "100.0"


class TestValidationResponse:
    def test_deviation_percent_optional(self) -> None:
        resp = ValidationResponse(
            is_valid=True,
            expected_range=("90.0", "110.0"),
            actual_value="100.0",
            deviation_percent=None,
            severity="info",
            message="within range",
        )
        assert resp.deviation_percent is None
