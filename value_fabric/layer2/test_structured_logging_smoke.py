import json

import structlog

from value_fabric.layer2 import configure_structured_logging


def test_layer2_structured_logging_json(capsys):
    configure_structured_logging()
    structlog.get_logger("layer2.test").info("layer2_log_smoke", event="layer2_log_smoke", tenant_id="tenant-1", request_id="req-1", document_id="doc-1")
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["event"] == "layer2_log_smoke"
    assert payload["tenant_id"] == "tenant-1"
    assert payload["request_id"] == "req-1"
