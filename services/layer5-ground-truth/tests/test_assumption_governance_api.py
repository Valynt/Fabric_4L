import json


def test_openapi_exposes_assumption_governance_paths() -> None:
    with open("contracts/openapi/layer5-ground-truth.json", encoding="utf-8") as f:
        spec = json.load(f)

    assert "/api/v1/assumptions" in spec["paths"]
    assert "/api/v1/policy-rules" in spec["paths"]
    assert "/api/v1/assumptions/{assumption_id}/apply" in spec["paths"]
