from __future__ import annotations

"""Layer 1 crawler package.

Canonical implementation lives in services/layer1-ingestion/src/crawler/.
"""


from .httpx_crawler import FastPathResult, HttpxCrawler, HttpxCrawlerConfig, SSRFProtectionError
from .playwright_crawler import CrawlResult, PlaywrightCrawler
from .quality_gate import AdaptiveQualityGate, QualityGate, QualityThresholds
from .smart_router import QualityDecision, RouteType, RoutingDecision, SmartRouter

_DECISION_STORE_EXPORTS = {
    "CrawlDecisionRecord",
    "CrawlDecisionRepository",
    "FallbackStats",
    "RouterQualityReport",
}


def __getattr__(name: str):
    if name in _DECISION_STORE_EXPORTS:
        from . import decision_store

        return getattr(decision_store, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AdaptiveQualityGate",
    "CrawlDecisionRecord",
    "CrawlDecisionRepository",
    "CrawlResult",
    "FallbackStats",
    "FastPathResult",
    "HttpxCrawler",
    "HttpxCrawlerConfig",
    "PlaywrightCrawler",
    "QualityDecision",
    "QualityGate",
    "QualityThresholds",
    "RouteType",
    "RouterQualityReport",
    "RoutingDecision",
    "SSRFProtectionError",
    "SmartRouter",
]
