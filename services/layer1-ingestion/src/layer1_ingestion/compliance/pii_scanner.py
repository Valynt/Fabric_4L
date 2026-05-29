"""PII detection and scanning using Microsoft Presidio.

Detects personally identifiable information in crawled content
and provides quarantine functionality for compliance.
"""

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import structlog

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

from value_fabric.shared.models.typed_dict import TypedDictModel

from ..shared.config import settings
from ..shared.models import PIIStatus


class PIIEntity_to_dictResult(TypedDictModel):
    end: Any
    entity_type: Any
    score: Any
    start: Any
    text: Any

class PIIScanResult_to_dictResult(TypedDictModel):
    engine_version: Any
    entities: Any
    entity_count: Any
    has_pii: Any
    highest_score: Any
    scan_timestamp: Any
    text_hash: Any

class PIIScanner_get_summary_statsResult(TypedDictModel):
    clean: Any
    detection_rate: Any
    entity_type_counts: Any
    flagged: Any
    pii_detected: Any
    quarantined: Any
    total_scanned: Any

logger = structlog.get_logger()


class PIIEntityType(str, Enum):
    """Types of PII entities that can be detected."""

    CREDIT_CARD = "CREDIT_CARD"
    CRYPTO = "CRYPTO"
    DATE_TIME = "DATE_TIME"
    EMAIL_ADDRESS = "EMAIL_ADDRESS"
    IBAN_CODE = "IBAN_CODE"
    IP_ADDRESS = "IP_ADDRESS"
    NRP = "NRP"  # Nationality, religious, political
    LOCATION = "LOCATION"
    PERSON = "PERSON"
    PHONE_NUMBER = "PHONE_NUMBER"
    MEDICAL_LICENSE = "MEDICAL_LICENSE"
    US_BANK_NUMBER = "US_BANK_NUMBER"
    US_DRIVER_LICENSE = "US_DRIVER_LICENSE"
    US_ITIN = "US_ITIN"
    US_PASSPORT = "US_PASSPORT"
    US_SSN = "US_SSN"
    SSN = "SSN"  # Generic SSN


@dataclass
class PIIEntity:
    """A detected PII entity."""

    entity_type: str
    text: str
    start: int
    end: int
    score: float  # Confidence score 0.0-1.0

    def to_dict(self) -> dict[str, Any]:
        return PIIEntity_to_dictResult.model_validate({
            "entity_type": self.entity_type,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "score": round(self.score, 4),
        })


@dataclass
class PIIScanResult:
    """Result of a PII scan."""

    text_hash: str
    entities: list[PIIEntity] = field(default_factory=list)
    has_pii: bool = False
    highest_score: float = 0.0
    scan_timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    engine_version: str = "presidio"

    def to_dict(self) -> dict[str, Any]:
        return PIIScanResult_to_dictResult.model_validate({
            "text_hash": self.text_hash,
            "has_pii": self.has_pii,
            "entities": [e.to_dict() for e in self.entities],
            "highest_score": round(self.highest_score, 4),
            "entity_count": len(self.entities),
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "engine_version": self.engine_version,
        })


class PIIScanner:
    """PII detection scanner using Microsoft Presidio.

    Scans text content for personally identifiable information
    and provides classification (clean/flagged/quarantined).
    """

    # PII types to check by default
    DEFAULT_ENTITIES = [
        PIIEntityType.CREDIT_CARD,
        PIIEntityType.SSN,
        PIIEntityType.US_SSN,
        PIIEntityType.EMAIL_ADDRESS,
        PIIEntityType.PHONE_NUMBER,
        PIIEntityType.US_DRIVER_LICENSE,
        PIIEntityType.US_PASSPORT,
        PIIEntityType.US_BANK_NUMBER,
        PIIEntityType.IP_ADDRESS,
        PIIEntityType.US_ITIN,
    ]

    def __init__(
        self,
        threshold_flag: float | None = None,
        threshold_quarantine: float | None = None,
        enabled_entities: list[PIIEntityType] | None = None,
    ):
        self.threshold_flag = threshold_flag or settings.pii_threshold_flag
        self.threshold_quarantine = threshold_quarantine or settings.pii_threshold_quarantine
        self.enabled_entities = enabled_entities or self.DEFAULT_ENTITIES
        self.logger = logger

        # Initialize Presidio engines
        self._analyzer: Any | None = None
        self._anonymizer: Any | None = None
        self._nlp_engine: Any | None = None

        self._init_engines()

    def _init_engines(self):
        """Initialize Presidio analyzer and anonymizer engines."""
        if not PRESIDIO_AVAILABLE:
            self.logger.warning("Presidio not available - PII scanning disabled")
            return

        try:
            # Initialize NLP engine
            # For production, you'd want to configure this properly
            # with a loaded spaCy model
            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()

            self.logger.info("PII scanner initialized with Presidio")

        except Exception as e:
            self.logger.error("Failed to initialize Presidio engines", error_code="PRESIDIO_INIT_ERROR")
            self._analyzer = None
            self._anonymizer = None

    def is_available(self) -> bool:
        """Check if PII scanning is available."""
        return PRESIDIO_AVAILABLE and self._analyzer is not None

    def scan(self, text: str, language: str = "en") -> PIIScanResult:
        """Scan text for PII.

        Args:
            text: Text to scan
            language: Language code (default: en)

        Returns:
            PIIScanResult with detected entities
        """
        if not text or not self.is_available():
            return PIIScanResult(text_hash=self._hash_text(text or ""), has_pii=False)

        try:
            # Run analysis
            entity_types = [e.value for e in self.enabled_entities]

            results = self._analyzer.analyze(text=text, entities=entity_types, language=language)

            # Convert to PIIEntity objects
            entities = []
            highest_score = 0.0

            for result in results:
                entity = PIIEntity(
                    entity_type=result.entity_type,
                    text=text[result.start : result.end],
                    start=result.start,
                    end=result.end,
                    score=result.score,
                )
                entities.append(entity)
                highest_score = max(highest_score, result.score)

            scan_result = PIIScanResult(
                text_hash=self._hash_text(text),
                entities=entities,
                has_pii=len(entities) > 0,
                highest_score=highest_score,
            )

            self.logger.debug(
                "PII scan completed", entity_count=len(entities), highest_score=highest_score
            )

            return scan_result

        except Exception as e:
            self.logger.error("PII scan failed", error_code="PII_SCAN_ERROR")
            return PIIScanResult(
                text_hash=self._hash_text(text), has_pii=False, scan_timestamp=datetime.now(UTC)
            )

    def classify_content(self, scan_result: PIIScanResult) -> str:
        """Classify content based on PII scan results.

        Args:
            scan_result: Result from scan()

        Returns:
            Classification: 'clean', 'flagged', or 'quarantined'
        """
        if not scan_result.has_pii:
            return PIIStatus.CLEAN.value

        if scan_result.highest_score >= self.threshold_quarantine:
            return PIIStatus.QUARANTINED.value

        if scan_result.highest_score >= self.threshold_flag:
            return PIIStatus.FLAGGED.value

        return PIIStatus.CLEAN.value

    def anonymize(self, text: str, scan_result: PIIScanResult | None = None) -> str:
        """Anonymize PII in text.

        Replaces PII with placeholders like <CREDIT_CARD>, <EMAIL_ADDRESS>.

        Args:
            text: Text to anonymize
            scan_result: Optional pre-computed scan result

        Returns:
            Anonymized text
        """
        if not self.is_available() or not text:
            return text

        if scan_result is None:
            scan_result = self.scan(text)

        if not scan_result.has_pii:
            return text

        try:
            # Build anonymizer operators
            operators = {}
            for entity in scan_result.entities:
                # Use entity type as the anonymized value
                operators[entity.entity_type] = self._anonymizer.operators.REPLACE

            # Anonymize
            anonymized = self._anonymizer.anonymize(
                text=text,
                analyzer_results=[
                    type(
                        "Result",
                        (),
                        {
                            "entity_type": e.entity_type,
                            "start": e.start,
                            "end": e.end,
                            "score": e.score,
                        },
                    )()
                    for e in scan_result.entities
                ],
                operators=operators,
            )

            return anonymized.text

        except Exception as e:
            self.logger.error("Anonymization failed", error_code="ANONYMIZATION_ERROR")
            return text

    def _hash_text(self, text: str) -> str:
        """Create a simple hash of text for identification."""
        return hashlib.md5(text.encode()).hexdigest()[:16]

    def get_summary_stats(self, scan_results: list[PIIScanResult]) -> dict[str, Any]:
        """Get summary statistics from multiple scan results.

        Args:
            scan_results: List of scan results

        Returns:
            Summary statistics dict
        """
        total_scanned = len(scan_results)
        pii_detected = sum(1 for r in scan_results if r.has_pii)
        quarantined = sum(1 for r in scan_results if self.classify_content(r) == "quarantined")
        flagged = sum(1 for r in scan_results if self.classify_content(r) == "flagged")

        # Count by entity type
        entity_counts: dict[str, int] = {}
        for result in scan_results:
            for entity in result.entities:
                entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1

        return PIIScanner_get_summary_statsResult.model_validate({
            "total_scanned": total_scanned,
            "pii_detected": pii_detected,
            "quarantined": quarantined,
            "flagged": flagged,
            "clean": total_scanned - pii_detected,
            "entity_type_counts": entity_counts,
            "detection_rate": round(pii_detected / total_scanned, 4) if total_scanned > 0 else 0,
        })


# Global scanner instance
_scanner = None


def get_scanner() -> PIIScanner:
    """Get the global PII scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = PIIScanner()
    return _scanner
