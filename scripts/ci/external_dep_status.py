"""External dependency probe + classify engine.

Emit a per-service health report and a readiness verdict. The classifier is
deliberately conservative: only a well-formed, unambiguous probe response with
an explicitly configured 'down' status may be classified as `down`. Every
timeout, probe error, unexpected status, or malformed response is `unknown`,
which for required coverage triggers `EXTERNAL_DEPENDENCY_UNAVAILABLE`.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import yaml

CLASSIFICATIONS = {"hermetic", "controlled", "third_party"}
COVERAGES = {"required", "informational"}
VERDICT_REQUIRED_DOWN = "EXTERNAL_DEPENDENCY_UNAVAILABLE"
REQUIRED_FIELDS = (
    "id", "service", "classification", "consuming_jobs", "coverage",
    "probe", "probe_timeout_seconds", "retry_policy", "failure_owner",
    "hostname_allowlist",
)


@dataclass
class ServiceSpec:
    id: str
    service: str
    classification: str
    consuming_jobs: list[str]
    coverage: str
    probe: dict[str, Any]
    probe_timeout_seconds: float
    retry_policy: dict[str, Any]
    failure_owner: str
    hostname_allowlist: list[str]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def verify_hostname_allowed(url: str, allowlist: list[str]) -> bool:
    """Return True only if the URL's host is in the allowlist."""
    host = urllib.parse.urlparse(url).hostname or ""
    return any(host == a or host.endswith("." + a) for a in allowlist)


def load_and_validate_registry(path: Path) -> list[str]:
    """Load the YAML registry, returning a list of validation error strings."""
    errors: list[str] = []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else None
    services = (raw or {}).get("services", [])
    if not isinstance(services, list) or not services:
        return ["registry must contain a non-empty services list"]
    for index, item in enumerate(services):
        if not isinstance(item, dict):
            errors.append(f"$services[{index}] must be a mapping")
            continue
        missing = sorted(set(REQUIRED_FIELDS) - item.keys())
        if missing:
            errors.append(f"$services[{index}] missing required fields: {', '.join(missing)}")
            continue
        classification = str(item["classification"])
        coverage = str(item["coverage"])
        if classification not in CLASSIFICATIONS:
            errors.append(f"$services[{index}] invalid classification: {classification}")
        if coverage not in COVERAGES:
            errors.append(f"$services[{index}] invalid coverage: {coverage}")
        if coverage == "required" and classification == "third_party":
            errors.append(
                f"$services[{index}] coverage 'required' is forbidden for third_party "
                f"(required verification must use hermetic/controlled)"
            )
        allowlist = item.get("hostname_allowlist", [])
        if classification != "hermetic" and not allowlist:
            errors.append(f"$services[{index}] non-hermetic service requires hostname_allowlist")
        probe = item["probe"]
        if not isinstance(probe, dict) or "url" not in probe:
            errors.append(f"$services[{index}] probe must be a mapping with a url")
        else:
            url = str(probe["url"])
            try:
                parsed = urllib.parse.urlparse(url)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    errors.append(f"$services[{index}] probe url is not an http(s) URL: {url}")
                elif not verify_hostname_allowed(url, allowlist):
                    errors.append(
                        f"$services[{index}] probe url host {parsed.hostname} not in hostname_allowlist"
                    )
            except ValueError as exc:
                errors.append(f"$services[{index}] invalid probe url: {exc}")
    return errors


def classify_probe_result(
    status_code: int | None,
    ok: bool,
    well_formed: bool,
    expected_status: int | None,
    configured_down_statuses: set[int],
) -> str:
    """Conservative classification. Unknown unless a well-formed+unambiguous down."""
    if ok and well_formed and configured_down_statuses and status_code in configured_down_statuses:
        return "down"
    if ok and well_formed and expected_status is not None and status_code == expected_status:
        return "up"
    return "unknown"


def _probe_once(spec: ServiceSpec) -> tuple[int | None, bool, bool]:
    """Return (status_code, ok, well_formed). Never raises to the caller."""
    probe = spec.probe
    url = str(probe["url"])
    method = str(probe.get("method", "GET"))
    req = urllib.request.Request(url, method=method)
    timeout = float(spec.probe_timeout_seconds)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            # 'well_formed' we approximate by a successful HTTP response body read;
            # for JSON endpoints a later verification could parse the body. Here we
            # require the response to have completed without transport error.
            body = resp.read(512)
            ok = True
            well_formed = body is not None
            return resp.status, ok, well_formed
    except urllib.error.HTTPError as exc:
        # An HTTP error status is 'ok' in the network sense but we still validate
        # that the configured down/expected statuses are matched by the classifier.
        return exc.code, True, True
    except (urllib.error.URLError, socket.timeout, TimeoutError, OSError, ValueError):
        return None, False, False


def probe_service(spec: ServiceSpec) -> dict[str, Any]:
    attempts = int(spec.retry_policy.get("max_attempts", 1))
    backoff = float(spec.retry_policy.get("backoff_seconds", 0))
    expected_status = spec.probe.get("expected_status")
    configured_down = set(spec.probe.get("down_statuses", []) or [])
    status_code, ok, well_formed = None, False, False
    for attempt in range(attempts):
        status_code, ok, well_formed = _probe_once(spec)
        classification = classify_probe_result(
            status_code, ok, well_formed, expected_status, configured_down
        )
        if classification in ("up", "down"):
            break
        if attempt < attempts - 1:
            time.sleep(backoff)
    classification = classify_probe_result(
        status_code, ok, well_formed, expected_status, configured_down
    )
    return {
        "id": spec.id,
        "coverage": spec.coverage,
        "classification": spec.classification,
        "status": classification,
        "final_status_code": status_code,
        "well_formed": well_formed,
        "failure_owner": spec.failure_owner,
    }


def build_report(specs: list[ServiceSpec]) -> tuple[dict[str, Any], str | None]:
    """Return (report, verdict). Verdict is the EXTERNAL code or None when safe."""
    results = [probe_service(spec) for spec in specs]
    required_unavailable = [
        r for r in results
        if r["coverage"] == "required" and r["status"] != "up"
    ]
    report = {"results": results, "required_unavailable": [r["id"] for r in required_unavailable]}
    if required_unavailable:
        return report, VERDICT_REQUIRED_DOWN
    return report, None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="External dependency probe/classify gate")
    parser.add_argument("--config", default="config/ci/external_dependencies.yaml")
    parser.add_argument("--output", default="reports/external-dep-status.json")
    parser.add_argument("--root", default=None, help="repo root override (tests)")
    args = parser.parse_args(argv)
    root = Path(args.root) if args.root else _repo_root()
    config_path = root / args.config
    errors = load_and_validate_registry(config_path)
    if errors:
        print("\n".join(errors))
        return 2
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    specs = [ServiceSpec(**item) for item in raw["services"]]
    report, verdict = build_report(specs)
    out = root / args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if verdict:
        print(f"VERDICT: {verdict}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
