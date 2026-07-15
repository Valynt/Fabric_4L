from __future__ import annotations

from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel


class _execute_browser_pathResult(TypedDictModel):
    blocked_resources: Any
    config_used: Any
    content_length: Any
    duration_ms: Any
    error: Any
    final_url: Any
    scroll_triggered: Any
    status_code: bool
    text_length: Any
    title: Any


class process_scraping_jobResult(TypedDictModel):
    job_id: Any
    success: bool
    task_id: Any


class crawl_url_with_routingResult(TypedDictModel):
    decision_id: Any
    duration_ms: Any
    final_path: Any
    job_id: Any
    success: bool
    url: Any


class cleanup_old_contentResult(TypedDictModel):
    cutoff_date: Any
    deleted_count: Any


class compliance_check_stageResult(TypedDictModel):
    error: str | None = None
    job_id: Any
    success: bool


class browser_crawl_stageResult(TypedDictModel):
    job_id: Any
    raw_content_id: Any
    success: bool


class ai_extraction_stageResult(TypedDictModel):
    entities_extracted: Any | None = None
    job_id: Any
    skipped: bool
    success: bool
    tokens_consumed: Any | None = None


class post_processing_stageResult(TypedDictModel):
    job_id: Any
    success: bool


class validation_stageResult(TypedDictModel):
    job_id: Any
    success: bool


class storage_stageResult(TypedDictModel):
    job_id: Any
    success: bool


class notification_stageResult(TypedDictModel):
    error: Any
    job_id: Any
    success: bool


