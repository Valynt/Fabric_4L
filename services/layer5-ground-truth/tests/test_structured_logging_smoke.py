import json

from layer5_ground_truth.observability.structured_logging import configure_structured_logging, get_logger


def test_layer5_structured_logging_json(capsys):
    configure_structured_logging()
    get_logger("layer5.test").info("layer5_log_smoke", event="layer5_log_smoke", tenant_id="tenant-5", request_id="req-5", truth_object_id="t-1")
    out = capsys.readouterr().out.strip()
    payload = json.loads(out)
    assert payload["event"] == "layer5_log_smoke"
    assert payload["tenant_id"] == "tenant-5"
    assert payload["request_id"] == "req-5"
