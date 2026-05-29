from __future__ import annotations

"""Layer 1 crawler package.

Canonical implementation lives in services/layer1-ingestion/src/crawler/.
"""


from .decision_store import (
    CrawlDecisionRecord,
    CrawlDecisionRepository,
    FallbackStats,
    RouterQualityReport,
)
from .httpx_crawler import FastPathResult, HttpxCrawler, HttpxCrawlerConfig, SSRFProtectionError
from .playwright_crawler import CrawlResult, PlaywrightCrawler
from .quality_gate import AdaptiveQualityGate, QualityGate, QualityThresholds
from .smart_router import QualityDecision, RouteType, RoutingDecision, SmartRouter

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
