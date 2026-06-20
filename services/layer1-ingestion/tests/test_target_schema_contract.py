"""Contract tests for Layer 1 target response schemas.

These tests assert that the response models keep OpenAPI-generation-level
compatibility and that the schemas exposed to clients do not drift from the
persistence model.
"""
from __future__ import annotations

import pytest
from pydantic import BaseModel

from layer1_ingestion.api.main import ScrapingTargetDetail, ScrapingTargetSummary
from layer1_ingestion.api._batch_and_stats import TargetStatsResponse


def test_scraping_target_summary_has_source_category() -> None:
    fields = ScrapingTargetSummary.model_fields
    assert "source_category" in fields
    assert fields["source_category"].annotation == str | None


def test_scraping_target_detail_inherits_source_category() -> None:
    fields = ScrapingTargetDetail.model_fields
    assert "source_category" in fields
    assert fields["source_category"].annotation == str | None


def test_target_stats_response_is_exported_schema() -> None:
    assert issubclass(TargetStatsResponse, BaseModel)
    expected_fields = {
        "total",
        "connected",
        "disconnected",
        "error",
        "total_records",
        "average_health_score",
    }
    assert set(TargetStatsResponse.model_fields.keys()) == expected_fields


def test_scraping_target_summary_instantiates_with_source_category() -> None:
    from uuid import uuid4
    from datetime import datetime, timezone

    summary = ScrapingTargetSummary(
        id=uuid4(),
        name="Test",
        url="http://example.com",
        target_type="API_ENDPOINT",
        source_category="crm",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        success_count=0,
        error_count=0,
        average_execution_time_ms=0,
        tags=[],
    )
    assert summary.source_category == "crm"
