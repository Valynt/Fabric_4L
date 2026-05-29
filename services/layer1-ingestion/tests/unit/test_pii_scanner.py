"""Tests for PIIScanner (layer1-ingestion/src/compliance/pii_scanner.py).

Covers:
- PIIEntity.to_dict()
- PIIScanResult.to_dict()
- PIIScanner.is_available() when Presidio is absent
- PIIScanner.scan() when scanner unavailable (returns empty result)
- PIIScanner.scan() with empty/None text
- PIIScanner.classify_content() – clean / flagged / quarantined thresholds
- PIIScanner.anonymize() when scanner unavailable
- PIIScanner._hash_text()
- PIIScanner.get_summary_stats() – totals, entity counts, detection_rate
- get_scanner() singleton
"""

import importlib
import sys
import types
import unittest

import pytest
from datetime import datetime, UTC
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Stub out presidio so the module can be imported without the real package
# ---------------------------------------------------------------------------

_protego_missing = importlib.util.find_spec("protego") is None
if _protego_missing:
    pytestmark = pytest.mark.skip(reason="protego not installed — optional slow dep")
    PIIEntity = None  # type: ignore[misc]
    PIIScanResult = None  # type: ignore[misc]
    PIIScanner = None  # type: ignore[misc]
    get_scanner = None  # type: ignore[misc]
    PIIStatus = None  # type: ignore[misc]
else:
    def _install_presidio_stubs():
        """Insert minimal stubs for presidio so PRESIDIO_AVAILABLE = True path works."""
        if "presidio_analyzer" not in sys.modules:
            pa = types.ModuleType("presidio_analyzer")
            pa.AnalyzerEngine = MagicMock
            pa.RecognizerResult = MagicMock
            sys.modules["presidio_analyzer"] = pa

        if "presidio_anonymizer" not in sys.modules:
            pu = types.ModuleType("presidio_anonymizer")
            pu.AnonymizerEngine = MagicMock
            pu.OperatorConfig = MagicMock
            sys.modules["presidio_anonymizer"] = pu

    _install_presidio_stubs()

    from layer1_ingestion.compliance.pii_scanner import (  # noqa: E402
        PIIEntity,
        PIIScanResult,
        PIIScanner,
        get_scanner,
    )
    from layer1_ingestion.shared.models import PIIStatus  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_scanner_unavailable() -> PIIScanner:
    """Return a PIIScanner that considers itself unavailable (no presidio)."""
    scanner = PIIScanner.__new__(PIIScanner)
    scanner.threshold_flag = 0.6
    scanner.threshold_quarantine = 0.85
    scanner.enabled_entities = []
    scanner.logger = MagicMock()
    scanner._analyzer = None
    scanner._anonymizer = None
    scanner._nlp_engine = None
    return scanner


def _make_entity(entity_type: str = "EMAIL_ADDRESS", score: float = 0.9) -> PIIEntity:
    return PIIEntity(entity_type=entity_type, text="test@example.com", start=0, end=16, score=score)


def _make_scan_result(has_pii: bool = False, highest_score: float = 0.0) -> PIIScanResult:
    return PIIScanResult(
        text_hash="abc123",
        entities=[_make_entity(score=highest_score)] if has_pii else [],
        has_pii=has_pii,
        highest_score=highest_score,
    )


# ---------------------------------------------------------------------------
# PIIEntity
# ---------------------------------------------------------------------------

class TestPIIEntity:
    def test_to_dict_contains_expected_keys(self):
        entity = _make_entity()
        d = entity.to_dict()
        assert set(d.keys()) == {"entity_type", "text", "start", "end", "score"}

    def test_to_dict_score_rounded(self):
        entity = PIIEntity(entity_type="SSN", text="123-45-6789", start=0, end=11, score=0.99999)
        d = entity.to_dict()
        assert d["score"] == round(0.99999, 4)

    def test_to_dict_values_match(self):
        entity = _make_entity()
        d = entity.to_dict()
        assert d["entity_type"] == "EMAIL_ADDRESS"
        assert d["text"] == "test@example.com"
        assert d["start"] == 0
        assert d["end"] == 16


# ---------------------------------------------------------------------------
# PIIScanResult
# ---------------------------------------------------------------------------

class TestPIIScanResult:
    def test_to_dict_has_pii_false_when_no_entities(self):
        result = _make_scan_result(has_pii=False)
        d = result.to_dict()
        assert d["has_pii"] is False
        assert d["entity_count"] == 0

    def test_to_dict_has_pii_true_when_entities_present(self):
        result = _make_scan_result(has_pii=True, highest_score=0.9)
        d = result.to_dict()
        assert d["has_pii"] is True
        assert d["entity_count"] == 1

    def test_to_dict_scan_timestamp_is_iso_string(self):
        result = _make_scan_result()
        d = result.to_dict()
        # Should be parseable as a datetime
        dt = datetime.fromisoformat(d["scan_timestamp"])
        assert dt is not None

    def test_to_dict_highest_score_rounded(self):
        result = PIIScanResult(text_hash="x", has_pii=True, highest_score=0.87654321)
        d = result.to_dict()
        assert d["highest_score"] == round(0.87654321, 4)

    def test_to_dict_engine_version_default(self):
        result = _make_scan_result()
        d = result.to_dict()
        assert d["engine_version"] == "presidio"


# ---------------------------------------------------------------------------
# PIIScanner – unavailable path
# ---------------------------------------------------------------------------

class TestPIIScannerUnavailable:
    def setup_method(self):
        self.scanner = _make_scanner_unavailable()

    def test_is_available_false(self):
        assert self.scanner.is_available() is False

    def test_scan_empty_text_returns_clean_result(self):
        result = self.scanner.scan("")
        assert result.has_pii is False
        assert result.entities == []

    def test_scan_none_equivalent_text_returns_clean_result(self):
        # scan() guards: `if not text or not self.is_available()`
        result = self.scanner.scan("")
        assert isinstance(result, PIIScanResult)

    def test_scan_returns_scan_result_when_unavailable(self):
        result = self.scanner.scan("My name is John")
        assert isinstance(result, PIIScanResult)
        assert result.has_pii is False

    def test_anonymize_returns_text_unchanged_when_unavailable(self):
        text = "test@example.com"
        assert self.scanner.anonymize(text) == text


# ---------------------------------------------------------------------------
# PIIScanner – classify_content
# ---------------------------------------------------------------------------

class TestClassifyContent:
    def setup_method(self):
        self.scanner = PIIScanner.__new__(PIIScanner)
        self.scanner.threshold_flag = 0.6
        self.scanner.threshold_quarantine = 0.85
        self.scanner.logger = MagicMock()
        self.scanner._analyzer = None
        self.scanner._anonymizer = None

    def test_no_pii_returns_clean(self):
        result = _make_scan_result(has_pii=False)
        assert self.scanner.classify_content(result) == PIIStatus.CLEAN.value

    def test_score_below_flag_threshold_returns_clean(self):
        result = PIIScanResult(text_hash="x", has_pii=True, highest_score=0.3)
        assert self.scanner.classify_content(result) == PIIStatus.CLEAN.value

    def test_score_at_flag_threshold_returns_flagged(self):
        result = PIIScanResult(text_hash="x", has_pii=True, highest_score=0.6)
        assert self.scanner.classify_content(result) == PIIStatus.FLAGGED.value

    def test_score_between_flag_and_quarantine_returns_flagged(self):
        result = PIIScanResult(text_hash="x", has_pii=True, highest_score=0.75)
        assert self.scanner.classify_content(result) == PIIStatus.FLAGGED.value

    def test_score_at_quarantine_threshold_returns_quarantined(self):
        result = PIIScanResult(text_hash="x", has_pii=True, highest_score=0.85)
        assert self.scanner.classify_content(result) == PIIStatus.QUARANTINED.value

    def test_score_above_quarantine_threshold_returns_quarantined(self):
        result = PIIScanResult(text_hash="x", has_pii=True, highest_score=1.0)
        assert self.scanner.classify_content(result) == PIIStatus.QUARANTINED.value


# ---------------------------------------------------------------------------
# PIIScanner – _hash_text
# ---------------------------------------------------------------------------

class TestHashText:
    def setup_method(self):
        self.scanner = _make_scanner_unavailable()

    def test_hash_is_16_char_hex(self):
        h = self.scanner._hash_text("hello world")
        assert len(h) == 16
        int(h, 16)  # should not raise

    def test_same_text_same_hash(self):
        text = "consistent input"
        assert self.scanner._hash_text(text) == self.scanner._hash_text(text)

    def test_different_text_different_hash(self):
        assert self.scanner._hash_text("abc") != self.scanner._hash_text("xyz")

    def test_empty_string_has_valid_hash(self):
        h = self.scanner._hash_text("")
        assert len(h) == 16


# ---------------------------------------------------------------------------
# PIIScanner – get_summary_stats
# ---------------------------------------------------------------------------

class TestGetSummaryStats:
    def setup_method(self):
        self.scanner = _make_scanner_unavailable()
        # Override classify_content so we don't need real thresholds
        self.scanner.threshold_flag = 0.6
        self.scanner.threshold_quarantine = 0.85

    def test_empty_results_returns_zero_totals(self):
        stats = self.scanner.get_summary_stats([])
        assert stats["total_scanned"] == 0
        assert stats["pii_detected"] == 0
        assert stats["quarantined"] == 0
        assert stats["flagged"] == 0
        assert stats["clean"] == 0
        assert stats["detection_rate"] == 0

    def test_all_clean_results(self):
        results = [_make_scan_result(has_pii=False) for _ in range(3)]
        stats = self.scanner.get_summary_stats(results)
        assert stats["total_scanned"] == 3
        assert stats["pii_detected"] == 0
        assert stats["clean"] == 3
        assert stats["detection_rate"] == 0.0

    def test_mixed_results_counts(self):
        clean = _make_scan_result(has_pii=False)
        flagged = PIIScanResult(
            text_hash="f1",
            has_pii=True,
            highest_score=0.7,
            entities=[_make_entity(score=0.7)],
        )
        quarantined = PIIScanResult(
            text_hash="q1",
            has_pii=True,
            highest_score=0.95,
            entities=[_make_entity(score=0.95)],
        )
        stats = self.scanner.get_summary_stats([clean, flagged, quarantined])
        assert stats["total_scanned"] == 3
        assert stats["pii_detected"] == 2
        assert stats["flagged"] == 1
        assert stats["quarantined"] == 1

    def test_entity_type_counts_aggregated(self):
        e1 = _make_entity(entity_type="EMAIL_ADDRESS", score=0.9)
        e2 = _make_entity(entity_type="EMAIL_ADDRESS", score=0.9)
        e3 = _make_entity(entity_type="PHONE_NUMBER", score=0.9)

        r1 = PIIScanResult(text_hash="r1", has_pii=True, highest_score=0.9, entities=[e1, e3])
        r2 = PIIScanResult(text_hash="r2", has_pii=True, highest_score=0.9, entities=[e2])

        stats = self.scanner.get_summary_stats([r1, r2])
        assert stats["entity_type_counts"]["EMAIL_ADDRESS"] == 2
        assert stats["entity_type_counts"]["PHONE_NUMBER"] == 1

    def test_detection_rate_calculated(self):
        results = [
            _make_scan_result(has_pii=True, highest_score=0.9),
            _make_scan_result(has_pii=False),
        ]
        stats = self.scanner.get_summary_stats(results)
        assert stats["detection_rate"] == 0.5


# ---------------------------------------------------------------------------
# get_scanner singleton
# ---------------------------------------------------------------------------

class TestGetScanner:
    def test_returns_pii_scanner_instance(self):
        import layer1_ingestion.compliance.pii_scanner as pii_mod
        # Reset singleton
        pii_mod._scanner = None
        scanner = get_scanner()
        assert isinstance(scanner, PIIScanner)

    def test_returns_same_instance_on_repeated_calls(self):
        import layer1_ingestion.compliance.pii_scanner as pii_mod
        pii_mod._scanner = None
        s1 = get_scanner()
        s2 = get_scanner()
        assert s1 is s2
