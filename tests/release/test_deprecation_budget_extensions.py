import json
from pathlib import Path
import pytest

DEPRECATIONS = json.loads(Path("docs/governance/deprecations.json").read_text())

@pytest.mark.parametrize(
    "dep_id",
    [
        "DEP-HEADER-ACCESS-002",
        "DEP-EXPLICIT-DB-004",
        "DEP-THROW-IN-TOOLS-007",
        "DEP-URL-CONCAT-010",
    ],
)
def test_active_deprecations_have_post_june_2026_target(dep_id):
    item = next(i for i in DEPRECATIONS["items"] if i["id"] == dep_id)
    assert item["status"] in ("active", "in-progress")
    assert item["targetRemoval"] > "2026-06-30"
    assert "extension" in item, f"{dep_id} must document the extension rationale"
