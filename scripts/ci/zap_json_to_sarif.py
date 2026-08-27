#!/usr/bin/env python3
"""Convert one or more OWASP ZAP JSON reports into GitHub-compatible SARIF.

The converter intentionally omits ZAP's raw evidence/attack payloads so scanner
results can be published without copying potentially sensitive response data
into GitHub code scanning.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


RISK_TO_LEVEL = {
    "0": "note",
    "1": "note",
    "2": "warning",
    "3": "error",
}

RISK_TO_SECURITY_SEVERITY = {
    "0": "0.1",
    "1": "2.0",
    "2": "5.0",
    "3": "8.0",
}


def _text(value: object) -> str:
    return str(value or "").strip()


def _rule_id(alert: dict[str, object]) -> str:
    plugin_id = _text(alert.get("pluginid")) or "unknown"
    return f"ZAP-{plugin_id}"


def _safe_target(value: object, fallback: str = "") -> str:
    target = _text(value) or fallback
    parsed = urlsplit(target)
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return target.split("?", 1)[0].split("#", 1)[0]


def _help_uri(value: object) -> str | None:
    reference = html.unescape(_text(value))
    for candidate in re.findall(r"https?://[^\s<>\"]+", reference):
        parsed = urlsplit(candidate.rstrip(".,);"))
        if parsed.scheme in {"http", "https"} and parsed.netloc:
            return candidate.rstrip(".,);")
    return None


def convert(paths: list[Path]) -> dict[str, object]:
    rules: dict[str, dict[str, object]] = {}
    results: list[dict[str, object]] = []

    for path in paths:
        data = json.loads(path.read_text(encoding="utf-8"))
        for site in data.get("site", []) or []:
            site_name = _text(site.get("@name"))
            for alert in site.get("alerts", []) or []:
                rule_id = _rule_id(alert)
                risk_code = _text(alert.get("riskcode"))
                alert_name = _text(alert.get("alert")) or rule_id
                description = _text(alert.get("desc"))
                solution = _text(alert.get("solution"))
                reference = _help_uri(alert.get("reference"))

                rule = rules.setdefault(
                    rule_id,
                    {
                        "id": rule_id,
                        "name": alert_name,
                        "shortDescription": {"text": alert_name},
                        "fullDescription": {"text": description or alert_name},
                        "help": {"text": solution or description or alert_name},
                        "properties": {
                            "tags": ["security", "dynamic-analysis", "owasp-zap"],
                            "security-severity": RISK_TO_SECURITY_SEVERITY.get(risk_code, "5.0"),
                        },
                    },
                )
                if reference:
                    rule["helpUri"] = reference

                instances = alert.get("instances") or [{}]
                for instance in instances:
                    uri = _safe_target(instance.get("uri"), site_name)
                    method = _text(instance.get("method")) or "HTTP"
                    parameter = _text(instance.get("param"))
                    message = f"{alert_name}: {method} {uri}".strip()
                    if parameter:
                        message += f" (parameter: {parameter})"

                    result: dict[str, object] = {
                        "ruleId": rule_id,
                        "level": RISK_TO_LEVEL.get(risk_code, "warning"),
                        "message": {"text": message},
                        "properties": {
                            "target": uri,
                            "method": method,
                            "riskCode": risk_code,
                            "confidence": _text(alert.get("confidence")),
                            "report": path.name,
                        },
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": uri},
                                    "region": {"startLine": 1, "startColumn": 1},
                                }
                            }
                        ],
                    }
                    results.append(result)

    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OWASP ZAP Full Scan",
                        "informationUri": "https://www.zaproxy.org/",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    sarif = convert(args.reports)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(sarif, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
