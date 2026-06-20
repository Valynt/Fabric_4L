"""Logical execution stages for the Layer 1 ingestion pipeline.

Maps the spec-defined stage names onto the canonical ``IngestionRunStatus``
values used by the pipeline state machine.
"""

from __future__ import annotations

from enum import Enum

from layer1_ingestion.shared.models import IngestionRunStatus


class IngestionStage(str, Enum):
    """Logical execution stages for Layer 1 Ingestion."""

    VALIDATING_ACCESS = IngestionRunStatus.VALIDATING_ACCESS.value
    RESOLVING_CONNECTOR = IngestionRunStatus.RESOLVING_CONNECTOR.value
    FETCHING_SOURCE = IngestionRunStatus.FETCHING_SOURCE.value
    APPLYING_POLICY = IngestionRunStatus.APPLYING_POLICY.value
    NORMALIZING_DOCUMENT = IngestionRunStatus.NORMALIZING.value
    SEGMENTING_CHUNKS = IngestionRunStatus.CHUNKING.value
    EXTRACTING_SIGNALS = IngestionRunStatus.EXTRACTING.value
    SYNTHESIZING_CLAIMS = IngestionRunStatus.BUILDING_CLAIMS.value
    VALIDATING_PARAMETERS = IngestionRunStatus.VALIDATING_CLAIMS.value
    PROJECTING_SUMMARY = IngestionRunStatus.PROJECTING_SUMMARY.value
    READY = IngestionRunStatus.READY.value
