import json
from pathlib import Path


def test_openapi_exposes_assumption_governance_paths() -> None:
    spec_path = Path(__file__).resolve().parents[3] / "contracts/openapi/layer5-ground-truth.json"
    with spec_path.open(encoding="utf-8") as f:
        spec = json.load(f)

    assert "/api/v1/assumptions" in spec["paths"]
    assert "/api/v1/policy-rules" in spec["paths"]
    assert "/api/v1/assumptions/{assumption_id}/apply" in spec["paths"]
