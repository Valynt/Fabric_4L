#!/usr/bin/env python3
"""Convert ZAP scan results to SARIF or validate ZAP scan artifacts.

This helper is invoked after the ZAP Docker full scan to produce a SARIF file
for upload to GitHub Security.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone


def build_sarif(target: str, zap_report_path: Path, output_path: Path) -> int:
    if zap_report_path.exists():
        try:
            zap_data = json.loads(zap_report_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"Invalid ZAP JSON report at {zap_report_path}: {exc}", file=sys.stderr)
            return 1
    else:
        zap_data = {}

    alerts = zap_data.get("site", [{}])[0].get("alerts", []) if isinstance(zap_data, dict) else []

    results = []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        for instance in alert.get("instances", []):
            results.append(
                {
                    "ruleId": f"zap-{alert.get('pluginid', 'unknown')}",
                    "level": "warning",
                    "message": {"text": alert.get("name", "ZAP alert")},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": instance.get("uri", target)},
                                "region": {
                                    "startLine": 1,
                                    "startColumn": 1,
                                },
                            }
                        }
                    ],
                }
            )

    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OWASP ZAP Full Scan",
                        "informationUri": "https://www.zaproxy.org/docs/docker/full-scan/",
                    }
                },
                "results": results,
                "invocations": [
                    {
                        "executionSuccessful": True,
                        "endTimeUtc": datetime.now(timezone.utc).isoformat(),
                    }
                ],
            }
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sarif, indent=2), encoding="utf-8")
    print(f"Wrote SARIF report to {output_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ZAP full scan result converter")
    parser.add_argument("--target", required=True, help="target URL scanned by ZAP")
    parser.add_argument("--output", required=True, help="output SARIF file path")
    parser.add_argument("--use-docker", action="store_true", help="indicates Docker-based ZAP scan")
    args = parser.parse_args(argv)

    zap_report = Path("zap-results/zap-report.json")
    return build_sarif(args.target, zap_report, Path(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
