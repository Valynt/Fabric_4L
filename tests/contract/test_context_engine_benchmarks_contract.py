from app.models.schemas import ContextEngineItem
from app.main import app


def test_context_engine_item_forbids_untyped_payload_keys() -> None:
    """Regression: untyped dict keys must not be accepted in benchmark payload items."""
    payload_with_unknown_key = {
        "id": "benchmark-1",
        "name": "Cycle Time Benchmark",
        "industry": "manufacturing",
        "category": "efficiency",
        "median_value": 12.5,
        "unit": "days",
        "unexpected_key": "should-fail",
    }

    import pytest
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ContextEngineItem.model_validate(payload_with_unknown_key)


def test_context_engine_benchmarks_openapi_uses_typed_item_schema() -> None:
    schema = app.openapi()
    benchmark_get = schema["paths"]["/v1/context-engine/benchmarks"]["get"]
    content_schema = benchmark_get["responses"]["200"]["content"]["application/json"]["schema"]

    ref = content_schema.get("$ref") or (
        content_schema.get("allOf", [{}])[0].get("$ref", "")
    )
    assert ref.endswith("PaginatedResponse_ContextEngineItem_")

    item_schema = schema["components"]["schemas"]["ContextEngineItem"]
    assert item_schema.get("additionalProperties") is False
