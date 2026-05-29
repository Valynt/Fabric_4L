"""Smoke tests for the Layer 1 import surface."""

from __future__ import annotations

import importlib


def test_layer1_entrypoint_modules_import() -> None:
    for module_name in (
        "layer1_ingestion.api.main",
        "layer1_ingestion.api.app_monolith",
    ):
        module = importlib.import_module(module_name)
        assert module is not None
        assert getattr(module, "__file__", None)
        assert hasattr(module, "app")


def test_crawler_modules_resolve_via_canonical_and_compatibility_paths() -> None:
    canonical_httpx = importlib.import_module("layer1_ingestion.crawler.httpx_crawler")
    canonical_router = importlib.import_module("layer1_ingestion.crawler.smart_router")
    canonical_store = importlib.import_module("layer1_ingestion.crawler.decision_store")
    compatibility_pkg = importlib.import_module("src.crawler")

    assert canonical_httpx.HttpxCrawler is not None
    assert canonical_router.SmartRouter is not None
    assert canonical_store.CrawlDecisionRepository is not None
    assert compatibility_pkg.HttpxCrawler is canonical_httpx.HttpxCrawler
    assert compatibility_pkg.SmartRouter is canonical_router.SmartRouter
    assert compatibility_pkg.CrawlDecisionRepository is canonical_store.CrawlDecisionRepository


def test_canonical_crawler_package_exports_not_empty() -> None:
    crawler_pkg = importlib.import_module("layer1_ingestion.crawler")

    assert crawler_pkg.__all__
    for name in ("HttpxCrawler", "SmartRouter", "CrawlDecisionRepository"):
        assert name in crawler_pkg.__all__
        assert getattr(crawler_pkg, name, None) is not None
