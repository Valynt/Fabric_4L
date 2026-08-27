#!/usr/bin/env python3
"""Self-contained contract test for zap_json_to_sarif.py."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from zap_json_to_sarif import convert


def main() -> int:
    sample = {
        "site": [
            {
                "@name": "http://127.0.0.1:8001",
                "alerts": [
                    {
                        "pluginid": "10020",
                        "alert": "Missing Anti-clickjacking Header",
                        "riskcode": "2",
                        "confidence": "2",
                        "desc": "Header missing",
                        "solution": "Set an anti-clickjacking header",
                        "instances": [
                            {
                                "uri": "http://127.0.0.1:8001/health",
                                "method": "GET",
                                "param": "",
                                "evidence": "must-not-leak",
                            }
                        ],
                    }
                ],
            }
        ]
    }

    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "zap.json"
        report.write_text(json.dumps(sample), encoding="utf-8")
        sarif = convert([report])

    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "OWASP ZAP Full Scan"
    assert run["results"][0]["ruleId"] == "ZAP-10020"
    assert run["results"][0]["level"] == "warning"
    assert "must-not-leak" not in json.dumps(sarif)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
