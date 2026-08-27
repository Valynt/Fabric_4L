from __future__ import annotations

"""
Compatibility Re-export for Account Intelligence Domain Contracts.

The canonical source of truth lives in ``value_fabric.shared.contracts.account_intelligence``.
This module re-exports the canonical models to ensure backwards compatibility across L4.
"""

from value_fabric.shared.contracts.account_intelligence import (
    AccountIntelligenceProvider,
    AccountSignal,
    CompanyCompetitor,
    CompanyEnrichmentData,
    CompanyResolutionResult,
    EnrichedAccountContext,
    ProvenanceClassification,
    SignalProvenance,
    StakeholderProfile,
)

__all__ = [
    "AccountIntelligenceProvider",
    "AccountSignal",
    "CompanyCompetitor",
    "CompanyEnrichmentData",
    "CompanyResolutionResult",
    "EnrichedAccountContext",
    "ProvenanceClassification",
    "SignalProvenance",
    "StakeholderProfile",
]
