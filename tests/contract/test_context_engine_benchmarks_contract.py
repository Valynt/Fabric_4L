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

    try:
        ContextEngineItem.model_validate(payload_with_unknown_key)
        accepted_unknown = True
    except Exception:
        accepted_unknown = False

    assert not accepted_unknown, "ContextEngineItem must reject unknown/untyped keys"


def test_context_engine_benchmarks_openapi_uses_typed_item_schema() -> None:
    schema = app.openapi()
    benchmark_get = schema["paths"]["/v1/context-engine/benchmarks"]["get"]
    content_schema = benchmark_get["responses"]["200"]["content"]["application/json"]["schema"]

    assert content_schema["$ref"].endswith("PaginatedResponse_ContextEngineItem_")

    item_schema = schema["components"]["schemas"]["ContextEngineItem"]
    assert item_schema.get("additionalProperties") is False
