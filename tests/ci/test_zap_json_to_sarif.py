from __future__ import annotations

import json
from pathlib import Path

from scripts.ci.zap_json_to_sarif import convert


def test_convert_sanitizes_targets_and_emits_locations(tmp_path: Path) -> None:
    report = tmp_path / "zap.json"
    report.write_text(
        json.dumps(
            {
                "site": [
                    {
                        "@name": "https://example.test",
                        "alerts": [
                            {
                                "pluginid": "10020",
                                "alert": "Header issue",
                                "reference": "<p>https://example.test/advice</p>",
                                "instances": [
                                    {
                                        "uri": "https://example.test/path?token=secret#payload",
                                        "method": "GET",
                                    }
                                ],
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = convert([report])["runs"][0]["results"][0]

    assert result["properties"]["target"] == "https://example.test/path"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == (
        "https://example.test/path"
    )
    assert "token=secret" not in json.dumps(result)
    rules = convert([report])["runs"][0]["tool"]["driver"]["rules"]
    assert rules[0]["helpUri"] == "https://example.test/advice"
    assert (
        result["ruleId"] and result["ruleId"] in json.dumps(rules)
    )
