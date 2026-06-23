from __future__ import annotations

"""Layer 1 crawler package.

Canonical implementation lives in services/layer1-ingestion/src/crawler/.
"""


_DECISION_STORE_EXPORTS = {
    "CrawlDecisionRecord",
    "CrawlDecisionRepository",
    "FallbackStats",
    "RouterQualityReport",
}

_LAZY_EXPORTS = {
    "AdaptiveQualityGate": (".quality_gate", "AdaptiveQualityGate"),
    "CrawlResult": (".playwright_crawler", "CrawlResult"),
    "FastPathResult": (".httpx_crawler", "FastPathResult"),
    "HttpxCrawler": (".httpx_crawler", "HttpxCrawler"),
    "HttpxCrawlerConfig": (".httpx_crawler", "HttpxCrawlerConfig"),
    "PlaywrightCrawler": (".playwright_crawler", "PlaywrightCrawler"),
    "QualityDecision": (".smart_router", "QualityDecision"),
    "QualityGate": (".quality_gate", "QualityGate"),
    "QualityThresholds": (".quality_gate", "QualityThresholds"),
    "RouteType": (".smart_router", "RouteType"),
    "RoutingDecision": (".smart_router", "RoutingDecision"),
    "SSRFProtectionError": (".httpx_crawler", "SSRFProtectionError"),
    "SmartRouter": (".smart_router", "SmartRouter"),
}


def __getattr__(name: str):
    if name in _DECISION_STORE_EXPORTS:
        from . import decision_store

        return getattr(decision_store, name)
    if name in _LAZY_EXPORTS:
        from importlib import import_module

        module_name, attr_name = _LAZY_EXPORTS[name]
        return getattr(import_module(module_name, __name__), attr_name)
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
