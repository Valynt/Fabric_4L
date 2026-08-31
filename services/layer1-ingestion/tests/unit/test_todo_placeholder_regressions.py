"""Regression tests for TODO-backed placeholder outputs in Layer 1 APIs/tasks."""

from pathlib import Path

API_MAIN_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "layer1_ingestion"
    / "api"
    / "main.py"
)
TARGET_HANDLERS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "layer1_ingestion"
    / "api"
    / "target_handlers.py"
)
SKILL_HANDLERS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "layer1_ingestion"
    / "api"
    / "skill_handlers.py"
)
ADMIN_HANDLERS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "layer1_ingestion"
    / "api"
    / "admin_handlers.py"
)
COMPLIANCE_HANDLERS_PATH = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "layer1_ingestion"
    / "api"
    / "compliance_handlers.py"
)
TASKS_PATH = Path(__file__).resolve().parents[2] / "src" / "layer1_ingestion" / "shared" / "tasks"


def test_api_runtime_placeholders_not_hardcoded() -> None:
    """API must not return TODO-era hardcoded constants."""
    source = (
        API_MAIN_PATH.read_text(encoding="utf-8")
        + TARGET_HANDLERS_PATH.read_text(encoding="utf-8")
        + SKILL_HANDLERS_PATH.read_text(encoding="utf-8")
        + ADMIN_HANDLERS_PATH.read_text(encoding="utf-8")
        + COMPLIANCE_HANDLERS_PATH.read_text(encoding="utf-8")
    )

    disallowed_literals = [
        "queue_position=1",
        '"crawl_delays_respected": 0',
        '"average_delay_ms": 0',
        '"allowlisted": 0',
        '"available_browsers": 5',
        '"average_wait_time_ms": 0',
    ]
    for literal in disallowed_literals:
        assert literal not in source, f"Placeholder literal reintroduced: {literal}"


def test_api_unknown_values_include_explanatory_metadata() -> None:
    """Any unknown API metric should include explicit explanatory metadata."""
    source = (
        API_MAIN_PATH.read_text(encoding="utf-8")
        + TARGET_HANDLERS_PATH.read_text(encoding="utf-8")
        + SKILL_HANDLERS_PATH.read_text(encoding="utf-8")
        + ADMIN_HANDLERS_PATH.read_text(encoding="utf-8")
        + COMPLIANCE_HANDLERS_PATH.read_text(encoding="utf-8")
    )

    required_metadata_fields = [
        "queue_position_metadata",
        "average_delay_ms_metadata",
        "available_browsers_metadata",
        "average_wait_time_ms_metadata",
    ]
    for field in required_metadata_fields:
        assert field in source, f"Missing explanatory metadata field: {field}"


def test_task_extraction_time_not_hardcoded_zero() -> None:
    """Extraction timing in storage stage must not use a fixed 0 value."""
    source = "".join(
        p.read_text(encoding="utf-8")
        for p in sorted(TASKS_PATH.glob("*.py"))
    )
    assert "extraction_time_ms=0" not in source
