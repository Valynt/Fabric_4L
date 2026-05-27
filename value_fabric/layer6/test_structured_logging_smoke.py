import json

import structlog

from value_fabric.layer6 import configure_structured_logging


def test_layer6_structured_logging_json(capsys):
    configure_structured_logging()
    structlog.get_logger("layer6.test").info("layer6_log_smoke", event="layer6_log_smoke", tenant_id="tenant-6", request_id="req-6", benchmark_id="b-1")
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["event"] == "layer6_log_smoke"
    assert payload["tenant_id"] == "tenant-6"
    assert payload["request_id"] == "req-6"
