"""Pipeline stage tasks and routing helpers (facade).

This module re-exports the Layer 1 pipeline stage tasks, their async
counterparts, and the crawl-routing helpers from
``layer1_ingestion.shared.tasks``, which remains the single source of truth.
It provides a cohesive import surface without moving any implementation.

Important: these bindings are snapshots of the canonical module. Celery task
names, beat schedules, and persistent patches keep addressing
``layer1_ingestion.shared.tasks.<name>`` exactly as before.
"""

from .tasks import (
    _acrawl_url_with_routing,
    _ai_extraction_stage_async,
    _apply_crawl_delay,
    _browser_crawl_stage_async,
    _capture_raw_content,
    _check_robots_txt,
    _compliance_check_stage_async,
    _crawl_browser,
    _execute_browser_path,
    _execute_browser_routing,
    _execute_fast_path,
    _execute_fast_path_routing,
    _execute_fast_with_fallback_routing,
    _execute_routing,
    _handle_compliance_error,
    _persist_routing_decision,
    _record_queue_latency,
    _record_stage_completion,
    _record_stage_metrics,
    _should_fail_closed,
    _validate_url_safety,
    _verify_l3_graph_population,
    ai_extraction_stage,
    browser_crawl_stage,
    compliance_check_stage,
    crawl_url_with_routing,
    notification_stage,
    post_processing_stage,
    process_scraping_job,
    storage_stage,
    validation_stage,
)

__all__ = [
    "_acrawl_url_with_routing",
    "_ai_extraction_stage_async",
    "_apply_crawl_delay",
    "_browser_crawl_stage_async",
    "_capture_raw_content",
    "_check_robots_txt",
    "_compliance_check_stage_async",
    "_crawl_browser",
    "_execute_browser_path",
    "_execute_browser_routing",
    "_execute_fast_path",
    "_execute_fast_path_routing",
    "_execute_fast_with_fallback_routing",
    "_execute_routing",
    "_handle_compliance_error",
    "_persist_routing_decision",
    "_record_queue_latency",
    "_record_stage_completion",
    "_record_stage_metrics",
    "_should_fail_closed",
    "_validate_url_safety",
    "_verify_l3_graph_population",
    "ai_extraction_stage",
    "browser_crawl_stage",
    "compliance_check_stage",
    "crawl_url_with_routing",
    "notification_stage",
    "post_processing_stage",
    "process_scraping_job",
    "storage_stage",
    "validation_stage",
]
