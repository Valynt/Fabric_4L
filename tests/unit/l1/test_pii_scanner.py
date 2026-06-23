"""Unit tests for Layer 1 PII scanner (P0-004)."""

from __future__ import annotations

import pytest

from layer1_ingestion.compliance.pii_scanner import (
    PIIEntity,
    PIIScanResult,
    PIIScanner,
)
from layer1_ingestion.shared.models import PIIStatus

pytestmark = [pytest.mark.unit]


class TestPIIEntity:
    """PIIEntity dataclass behavior."""

    def test_to_dict_structure(self) -> None:
        entity = PIIEntity(
            entity_type="EMAIL_ADDRESS",
            text="user@example.com",
            start=0,
            end=16,
            score=0.95,
        )
        d = entity.to_dict()
        assert d["entity_type"] == "EMAIL_ADDRESS"
        assert d["text"] == "user@example.com"
        assert d["score"] == 0.95
        assert d["start"] == 0
        assert d["end"] == 16


class TestPIIScanResult:
    """PIIScanResult dataclass behavior."""

    def test_empty_scan(self) -> None:
        result = PIIScanResult(text_hash="abc123")
        assert result.has_pii is False
        assert result.entities == []
        assert result.highest_score == 0.0

    def test_scan_with_entities(self) -> None:
        entity = PIIEntity(
            entity_type="SSN",
            text="123-45-6789",
            start=0,
            end=11,
            score=0.99,
        )
        result = PIIScanResult(
            text_hash="abc123",
            entities=[entity],
            has_pii=True,
            highest_score=0.99,
        )
        d = result.to_dict()
        assert d["has_pii"] is True
        assert d["entity_count"] == 1
        assert d["highest_score"] == 0.99
        assert len(d["entities"]) == 1

    def test_multiple_entities_highest_score(self) -> None:
        result = PIIScanResult(
            text_hash="abc",
            entities=[
                PIIEntity("A", "a", 0, 1, 0.5),
                PIIEntity("B", "b", 1, 2, 0.9),
            ],
            has_pii=True,
            highest_score=0.9,
        )
        assert result.to_dict()["highest_score"] == 0.9

    def test_to_dict_timestamp_isoformat(self) -> None:
        from datetime import UTC, datetime

        ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        result = PIIScanResult(text_hash="abc", scan_timestamp=ts)
        assert result.to_dict()["scan_timestamp"] == ts.isoformat()


class TestPIIScannerClassifyContent:
    """PIIScanner content classification without Presidio."""

    def test_clean_when_no_pii(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(text_hash="abc", has_pii=False)
        assert scanner.classify_content(result) == PIIStatus.CLEAN.value

    def test_clean_when_below_flag_threshold(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(text_hash="abc", has_pii=True, highest_score=0.3)
        assert scanner.classify_content(result) == PIIStatus.CLEAN.value

    def test_flagged_above_flag_below_quarantine(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(text_hash="abc", has_pii=True, highest_score=0.7)
        assert scanner.classify_content(result) == PIIStatus.FLAGGED.value

    def test_quarantined_above_quarantine_threshold(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(text_hash="abc", has_pii=True, highest_score=0.95)
        assert scanner.classify_content(result) == PIIStatus.QUARANTINED.value

    def test_exactly_at_flag_threshold(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(text_hash="abc", has_pii=True, highest_score=0.5)
        assert scanner.classify_content(result) == PIIStatus.FLAGGED.value

    def test_exactly_at_quarantine_threshold(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(text_hash="abc", has_pii=True, highest_score=0.9)
        assert scanner.classify_content(result) == PIIStatus.QUARANTINED.value


class TestPIIScannerSummaryStats:
    """PIIScanner aggregate statistics."""

    def test_empty_results(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        stats = scanner.get_summary_stats([])
        assert stats["total_scanned"] == 0
        assert stats["pii_detected"] == 0
        assert stats["detection_rate"] == 0

    def test_all_clean(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        results = [
            PIIScanResult(text_hash="a", has_pii=False),
            PIIScanResult(text_hash="b", has_pii=False),
        ]
        stats = scanner.get_summary_stats(results)
        assert stats["total_scanned"] == 2
        assert stats["clean"] == 2
        assert stats["pii_detected"] == 0
        assert stats["detection_rate"] == 0.0

    def test_mixed_classifications(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        results = [
            PIIScanResult(text_hash="a", has_pii=False),
            PIIScanResult(text_hash="b", has_pii=True, highest_score=0.6),
            PIIScanResult(text_hash="c", has_pii=True, highest_score=0.95),
        ]
        stats = scanner.get_summary_stats(results)
        assert stats["total_scanned"] == 3
        assert stats["clean"] == 1
        assert stats["flagged"] == 1
        assert stats["quarantined"] == 1
        assert stats["pii_detected"] == 2
        assert stats["detection_rate"] == round(2 / 3, 4)

    def test_entity_type_counts(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        result = PIIScanResult(
            text_hash="a",
            has_pii=True,
            highest_score=0.8,
            entities=[
                PIIEntity("EMAIL_ADDRESS", "a", 0, 1, 0.8),
                PIIEntity("EMAIL_ADDRESS", "b", 2, 3, 0.8),
                PIIEntity("SSN", "c", 4, 5, 0.8),
            ],
        )
        stats = scanner.get_summary_stats([result])
        assert stats["entity_type_counts"]["EMAIL_ADDRESS"] == 2
        assert stats["entity_type_counts"]["SSN"] == 1


class TestPIIScannerHashText:
    """Text hashing determinism."""

    def test_hash_is_deterministic(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        h1 = scanner._hash_text("hello world")
        h2 = scanner._hash_text("hello world")
        assert h1 == h2
        assert len(h1) == 16

    def test_hash_differs_for_different_text(self) -> None:
        scanner = PIIScanner(threshold_flag=0.5, threshold_quarantine=0.9)
        h1 = scanner._hash_text("hello")
        h2 = scanner._hash_text("world")
        assert h1 != h2
