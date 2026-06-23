import json

import structlog
from structlog.processors import JSONRenderer

from layer6_benchmarks.logging_config import configure_structured_logging


def test_layer6_structured_logging_json() -> None:
    configure_structured_logging()

    processors = structlog.get_config()["processors"]
    renderer = processors[-1]

    assert isinstance(renderer, JSONRenderer)

    rendered = renderer(
        None,
        "info",
        {
            "event": "layer6_log_smoke",
            "tenant_id": "tenant-6",
            "request_id": "req-6",
            "benchmark_id": "b-1",
        },
    )
    payload = json.loads(rendered)
    assert payload["event"] == "layer6_log_smoke"
    assert payload["tenant_id"] == "tenant-6"
    assert payload["request_id"] == "req-6"
