#!/usr/bin/env python3
"""OpenAPI breaking-change gate for REST contracts.

Compares the current working tree OpenAPI artifacts with a baseline git ref and
reports backwards-incompatible contract drift. This intentionally replaces
protobuf-oriented `buf breaking` checks for this OpenAPI/REST repository.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_ROOT = REPO_ROOT / "contracts" / "openapi"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts" / "contract-breaking"
DEFAULT_EXCEPTIONS = REPO_ROOT / "docs" / "governance" / "openapi-breaking-change-exceptions.json"
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
ERROR_STATUS_PREFIXES = ("4", "5")


@dataclass(frozen=True)
class Finding:
    spec: str
    category: str
    message: str
    json_pointer: str
    path: str | None = None
    method: str | None = None
    severity: str = "breaking"

    @property
    def fingerprint(self) -> str:
        payload = "|".join(
            [self.spec, self.category, self.path or "", self.method or "", self.json_pointer]
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def to_json(self, *, approved: bool = False, approval: dict[str, Any] | None = None) -> dict[str, Any]:
        return {
            "fingerprint": self.fingerprint,
            "severity": self.severity,
            "category": self.category,
            "spec": self.spec,
            "path": self.path,
            "method": self.method,
            "jsonPointer": self.json_pointer,
            "message": self.message,
            "approved": approved,
            "approval": approval,
        }


def _run_git(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def _git_ref_exists(ref: str) -> bool:
    result = _run_git(["rev-parse", "--verify", f"{ref}^{{commit}}"])
    return result.returncode == 0


def _git_show_json(ref: str, path: Path) -> dict[str, Any] | None:
    rel = path.relative_to(REPO_ROOT).as_posix()
    result = _run_git(["show", f"{ref}:{rel}"])
    if result.returncode != 0:
        return None
    return json.loads(result.stdout)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _deep_resolve_ref(spec: dict[str, Any], value: Any, seen: set[str] | None = None) -> Any:
    if not isinstance(value, dict) or "$ref" not in value:
        return value
    ref = value["$ref"]
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return value
    seen = seen or set()
    if ref in seen:
        return value
    seen.add(ref)
    target: Any = spec
    for token in ref[2:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(target, dict) or token not in target:
            return value
        target = target[token]
    resolved = copy.deepcopy(target)
    if isinstance(resolved, dict):
        # Sibling keys next to $ref are legal in OpenAPI 3.1; preserve them.
        for key, sibling in value.items():
            if key != "$ref":
                resolved[key] = sibling
    return _deep_resolve_ref(spec, resolved, seen)


def _json_pointer(*parts: str) -> str:
    def escape(part: str) -> str:
        return part.replace("~", "~0").replace("/", "~1")

    return "#" + "".join(f"/{escape(str(part))}" for part in parts)


def _methods(path_item: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(path_item, dict):
        return {}
    return {
        key.lower(): value
        for key, value in path_item.items()
        if key.lower() in HTTP_METHODS and isinstance(value, dict)
    }


def _normalize_type(schema: dict[str, Any]) -> set[str]:
    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        types = {schema_type}
    elif isinstance(schema_type, list):
        types = {item for item in schema_type if isinstance(item, str)}
    else:
        types = set()
    if schema.get("nullable") is True:
        types.add("null")
    return types


def _schema_properties(spec: dict[str, Any], schema: Any) -> dict[str, Any]:
    schema = _deep_resolve_ref(spec, schema)
    if not isinstance(schema, dict):
        return {}
    props = schema.get("properties")
    return props if isinstance(props, dict) else {}


def _schema_required(spec: dict[str, Any], schema: Any) -> set[str]:
    schema = _deep_resolve_ref(spec, schema)
    if not isinstance(schema, dict):
        return set()
    required = schema.get("required")
    return {item for item in required if isinstance(item, str)} if isinstance(required, list) else set()


def _content_schemas(spec: dict[str, Any], container: Any) -> dict[str, Any]:
    container = _deep_resolve_ref(spec, container)
    if not isinstance(container, dict):
        return {}
    content = container.get("content")
    if not isinstance(content, dict):
        return {}
    schemas: dict[str, Any] = {}
    for media_type, media in content.items():
        if isinstance(media_type, str) and isinstance(media, dict) and "schema" in media:
            schemas[media_type] = media["schema"]
    return schemas


def _compare_security(
    findings: list[Finding], spec_name: str, old_op: dict[str, Any], new_op: dict[str, Any], path: str, method: str
) -> None:
    old_security = old_op.get("security")
    new_security = new_op.get("security")
    if old_security != new_security:
        findings.append(
            Finding(
                spec=spec_name,
                category="auth_security_contract_changed",
                path=path,
                method=method,
                json_pointer=_json_pointer("paths", path, method, "security"),
                message=f"Security requirements changed for {method.upper()} {path}.",
            )
        )


def _compare_schema(
    findings: list[Finding],
    *,
    spec_name: str,
    old_spec: dict[str, Any],
    new_spec: dict[str, Any],
    old_schema: Any,
    new_schema: Any,
    pointer: str,
    path: str,
    method: str,
    direction: str,
) -> None:
    old_schema = _deep_resolve_ref(old_spec, old_schema)
    new_schema = _deep_resolve_ref(new_spec, new_schema)
    if not isinstance(old_schema, dict) or not isinstance(new_schema, dict):
        return

    old_types = _normalize_type(old_schema)
    new_types = _normalize_type(new_schema)
    if old_types and new_types and new_types < old_types:
        findings.append(
            Finding(
                spec=spec_name,
                category="type_narrowing",
                path=path,
                method=method,
                json_pointer=pointer + "/type",
                message=(
                    f"Type narrowed at {method.upper()} {path}: "
                    f"{sorted(old_types)} -> {sorted(new_types)}."
                ),
            )
        )
    elif old_types and new_types and old_types.isdisjoint(new_types):
        findings.append(
            Finding(
                spec=spec_name,
                category="type_changed",
                path=path,
                method=method,
                json_pointer=pointer + "/type",
                message=(
                    f"Type changed at {method.upper()} {path}: "
                    f"{sorted(old_types)} -> {sorted(new_types)}."
                ),
            )
        )

    old_enum = old_schema.get("enum")
    new_enum = new_schema.get("enum")
    if isinstance(old_enum, list) and isinstance(new_enum, list):
        removed = [item for item in old_enum if item not in new_enum]
        if removed:
            findings.append(
                Finding(
                    spec=spec_name,
                    category="enum_values_removed",
                    path=path,
                    method=method,
                    json_pointer=pointer + "/enum",
                    message=f"Enum values removed at {method.upper()} {path}: {removed!r}.",
                )
            )

    old_required = _schema_required(old_spec, old_schema)
    new_required = _schema_required(new_spec, new_schema)
    added_required = sorted(new_required - old_required)
    if added_required:
        findings.append(
            Finding(
                spec=spec_name,
                category="required_fields_added",
                path=path,
                method=method,
                json_pointer=pointer + "/required",
                message=f"Required fields added at {method.upper()} {path}: {added_required}.",
            )
        )

    old_props = _schema_properties(old_spec, old_schema)
    new_props = _schema_properties(new_spec, new_schema)
    for prop_name in sorted(set(old_props) - set(new_props)):
        findings.append(
            Finding(
                spec=spec_name,
                category=("request_fields_removed" if direction == "request" else "response_fields_removed"),
                path=path,
                method=method,
                json_pointer=f"{pointer}/properties/{prop_name}",
                message=f"{direction.title()} field removed at {method.upper()} {path}: {prop_name}.",
            )
        )
    for prop_name in sorted(set(old_props) & set(new_props)):
        _compare_schema(
            findings,
            spec_name=spec_name,
            old_spec=old_spec,
            new_spec=new_spec,
            old_schema=old_props[prop_name],
            new_schema=new_props[prop_name],
            pointer=f"{pointer}/properties/{prop_name}",
            path=path,
            method=method,
            direction=direction,
        )

    # Compare homogeneous arrays.
    if "array" in (old_types | new_types):
        _compare_schema(
            findings,
            spec_name=spec_name,
            old_spec=old_spec,
            new_spec=new_spec,
            old_schema=old_schema.get("items"),
            new_schema=new_schema.get("items"),
            pointer=pointer + "/items",
            path=path,
            method=method,
            direction=direction,
        )


def _compare_request_body(
    findings: list[Finding], spec_name: str, old_spec: dict[str, Any], new_spec: dict[str, Any], old_op: dict[str, Any], new_op: dict[str, Any], path: str, method: str
) -> None:
    old_body = old_op.get("requestBody")
    if old_body is None:
        return
    new_body = new_op.get("requestBody")
    if new_body is None:
        findings.append(
            Finding(
                spec=spec_name,
                category="request_body_removed",
                path=path,
                method=method,
                json_pointer=_json_pointer("paths", path, method, "requestBody"),
                message=f"Request body removed for {method.upper()} {path}.",
            )
        )
        return
    old_schemas = _content_schemas(old_spec, old_body)
    new_schemas = _content_schemas(new_spec, new_body)
    for media_type, old_schema in old_schemas.items():
        if media_type not in new_schemas:
            findings.append(
                Finding(
                    spec=spec_name,
                    category="request_media_type_removed",
                    path=path,
                    method=method,
                    json_pointer=_json_pointer("paths", path, method, "requestBody", "content", media_type),
                    message=f"Request media type removed for {method.upper()} {path}: {media_type}.",
                )
            )
            continue
        _compare_schema(
            findings,
            spec_name=spec_name,
            old_spec=old_spec,
            new_spec=new_spec,
            old_schema=old_schema,
            new_schema=new_schemas[media_type],
            pointer=_json_pointer("paths", path, method, "requestBody", "content", media_type, "schema"),
            path=path,
            method=method,
            direction="request",
        )


def _compare_responses(
    findings: list[Finding], spec_name: str, old_spec: dict[str, Any], new_spec: dict[str, Any], old_op: dict[str, Any], new_op: dict[str, Any], path: str, method: str
) -> None:
    old_responses = old_op.get("responses") if isinstance(old_op.get("responses"), dict) else {}
    new_responses = new_op.get("responses") if isinstance(new_op.get("responses"), dict) else {}
    for status, old_response in old_responses.items():
        if not isinstance(status, str):
            continue
        if status not in new_responses:
            category = "error_response_contract_drift" if status.startswith(ERROR_STATUS_PREFIXES) else "response_removed"
            findings.append(
                Finding(
                    spec=spec_name,
                    category=category,
                    path=path,
                    method=method,
                    json_pointer=_json_pointer("paths", path, method, "responses", status),
                    message=f"Response status removed for {method.upper()} {path}: {status}.",
                )
            )
            continue
        old_schemas = _content_schemas(old_spec, old_response)
        new_schemas = _content_schemas(new_spec, new_responses[status])
        for media_type, old_schema in old_schemas.items():
            if media_type not in new_schemas:
                category = "error_response_contract_drift" if status.startswith(ERROR_STATUS_PREFIXES) else "response_media_type_removed"
                findings.append(
                    Finding(
                        spec=spec_name,
                        category=category,
                        path=path,
                        method=method,
                        json_pointer=_json_pointer("paths", path, method, "responses", status, "content", media_type),
                        message=f"Response media type removed for {method.upper()} {path} {status}: {media_type}.",
                    )
                )
                continue
            before_count = len(findings)
            _compare_schema(
                findings,
                spec_name=spec_name,
                old_spec=old_spec,
                new_spec=new_spec,
                old_schema=old_schema,
                new_schema=new_schemas[media_type],
                pointer=_json_pointer("paths", path, method, "responses", status, "content", media_type, "schema"),
                path=path,
                method=method,
                direction="response",
            )
            if status.startswith(ERROR_STATUS_PREFIXES):
                for index in range(before_count, len(findings)):
                    original = findings[index]
                    findings[index] = Finding(
                        spec=original.spec,
                        category="error_response_contract_drift",
                        path=original.path,
                        method=original.method,
                        json_pointer=original.json_pointer,
                        message=f"Error response drift: {original.message}",
                        severity=original.severity,
                    )


def compare_specs(spec_name: str, old_spec: dict[str, Any], new_spec: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    if old_spec.get("security") != new_spec.get("security"):
        findings.append(
            Finding(
                spec=spec_name,
                category="auth_security_contract_changed",
                path=None,
                method=None,
                json_pointer="#/security",
                message="Root OpenAPI security requirements changed.",
            )
        )

    old_paths = old_spec.get("paths") if isinstance(old_spec.get("paths"), dict) else {}
    new_paths = new_spec.get("paths") if isinstance(new_spec.get("paths"), dict) else {}
    for path in sorted(set(old_paths) - set(new_paths)):
        findings.append(
            Finding(
                spec=spec_name,
                category="paths_removed",
                path=path,
                method=None,
                json_pointer=_json_pointer("paths", path),
                message=f"Path removed: {path}.",
            )
        )
    for path in sorted(set(old_paths) & set(new_paths)):
        old_methods = _methods(old_paths[path])
        new_methods = _methods(new_paths[path])
        for method in sorted(set(old_methods) - set(new_methods)):
            findings.append(
                Finding(
                    spec=spec_name,
                    category="methods_removed",
                    path=path,
                    method=method,
                    json_pointer=_json_pointer("paths", path, method),
                    message=f"Method removed: {method.upper()} {path}.",
                )
            )
        for method in sorted(set(old_methods) & set(new_methods)):
            old_op = old_methods[method]
            new_op = new_methods[method]
            _compare_security(findings, spec_name, old_op, new_op, path, method)
            _compare_request_body(findings, spec_name, old_spec, new_spec, old_op, new_op, path, method)
            _compare_responses(findings, spec_name, old_spec, new_spec, old_op, new_op, path, method)
    return findings


def _load_exceptions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = _load_json(path)
    records = data.get("exceptions", [])
    return records if isinstance(records, list) else []


def _approval_for(finding: Finding, records: list[dict[str, Any]], now: datetime) -> dict[str, Any] | None:
    for record in records:
        if not isinstance(record, dict) or record.get("status") != "approved":
            continue
        if not record.get("approvedBy"):
            continue
        if not (record.get("rfc") or record.get("deprecationRecord")):
            continue
        expires_on = record.get("expiresOn")
        if isinstance(expires_on, str):
            try:
                expires = datetime.fromisoformat(expires_on.replace("Z", "+00:00"))
            except ValueError:
                continue
            if expires < now:
                continue
        fingerprints = record.get("fingerprints", [])
        if isinstance(fingerprints, list) and finding.fingerprint in fingerprints:
            return record
        matches = record.get("matches", [])
        if not isinstance(matches, list):
            continue
        for match in matches:
            if not isinstance(match, dict):
                continue
            if match.get("spec") not in (None, finding.spec):
                continue
            if match.get("category") not in (None, finding.category):
                continue
            if match.get("path") not in (None, finding.path):
                continue
            if match.get("method") not in (None, finding.method):
                continue
            pointer = match.get("jsonPointer")
            if pointer is not None and pointer != finding.json_pointer:
                continue
            return record
    return None


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# OpenAPI Breaking-Change Gate Report",
        "",
        f"- Baseline ref: `{report['baselineRef']}`",
        f"- Generated at: `{report['generatedAt']}`",
        f"- Current SHA: `{report['currentSha']}`",
        f"- Result: **{report['result']}**",
        f"- Findings: {report['findingCount']} ({report['approvedCount']} approved, {report['unapprovedCount']} unapproved)",
        "",
    ]
    if report.get("baselineWarning"):
        lines.extend([f"> Warning: {report['baselineWarning']}", ""])
    if not report["findings"]:
        lines.append("No breaking OpenAPI changes were detected.")
        return "\n".join(lines) + "\n"
    lines.extend(["| Status | Category | Spec | Operation | Pointer | Fingerprint |", "|---|---|---|---|---|---|"])
    for finding in report["findings"]:
        status = "approved" if finding["approved"] else "unapproved"
        operation = ""
        if finding.get("method") and finding.get("path"):
            operation = f"{finding['method'].upper()} {finding['path']}"
        elif finding.get("path"):
            operation = finding["path"]
        lines.append(
            f"| {status} | {finding['category']} | {finding['spec']} | {operation} | `{finding['jsonPointer']}` | `{finding['fingerprint']}` |"
        )
    lines.extend(["", "## Details", ""])
    for finding in report["findings"]:
        lines.extend(
            [
                f"### {finding['fingerprint']} — {finding['category']}",
                "",
                finding["message"],
                "",
                f"- Spec: `{finding['spec']}`",
                f"- Pointer: `{finding['jsonPointer']}`",
                f"- Approval: {'approved' if finding['approved'] else 'missing'}",
                "",
            ]
        )
    return "\n".join(lines)


def _write_reports(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "openapi-breaking-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "openapi-breaking-report.md").write_text(_markdown_report(report), encoding="utf-8")


def _current_sha() -> str:
    result = _run_git(["rev-parse", "HEAD"])
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect breaking OpenAPI contract changes.")
    parser.add_argument("--base-ref", default=os.getenv("OPENAPI_BREAKING_BASE_REF", "origin/main"))
    parser.add_argument("--spec-dir", type=Path, default=OPENAPI_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--exceptions", type=Path, default=DEFAULT_EXCEPTIONS)
    parser.add_argument(
        "--fail-on-missing-baseline",
        action="store_true",
        default=os.getenv("GITHUB_ACTIONS") == "true",
        help="Fail when the baseline ref is unavailable. Enabled by default in GitHub Actions.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    spec_dir = args.spec_dir.resolve()
    spec_paths = sorted(spec_dir.glob("*.json"))
    if not spec_paths:
        raise SystemExit(f"No OpenAPI specs found in {spec_dir}")

    baseline_warning: str | None = None
    compare_to_self = False
    if not _git_ref_exists(args.base_ref):
        message = f"Baseline ref '{args.base_ref}' is not available. Fetch the baseline branch before enforcing this gate."
        if args.fail_on_missing_baseline:
            raise SystemExit(message)
        baseline_warning = message + " Local run compared the working tree to itself."
        compare_to_self = True
        print(f"WARNING: {baseline_warning}", file=sys.stderr)

    all_findings: list[Finding] = []
    for current_path in spec_paths:
        rel_name = current_path.name
        current_spec = _load_json(current_path)
        if compare_to_self:
            baseline_spec = current_spec
        else:
            baseline_spec = _git_show_json(args.base_ref, current_path)
        if baseline_spec is None:
            # A new spec cannot break existing clients.
            continue
        all_findings.extend(compare_specs(rel_name, baseline_spec, current_spec))

    now = datetime.now(timezone.utc)
    approvals = _load_exceptions(args.exceptions)
    finding_records: list[dict[str, Any]] = []
    unapproved = 0
    approved = 0
    for finding in all_findings:
        approval = _approval_for(finding, approvals, now)
        is_approved = approval is not None
        approved += int(is_approved)
        unapproved += int(not is_approved)
        finding_records.append(finding.to_json(approved=is_approved, approval=approval))

    result = "pass" if unapproved == 0 else "fail"
    report = {
        "schemaVersion": "1.0",
        "command": "pnpm contract:breaking",
        "baselineRef": args.base_ref,
        "baselineWarning": baseline_warning,
        "generatedAt": now.isoformat(),
        "currentSha": _current_sha(),
        "result": result,
        "findingCount": len(finding_records),
        "approvedCount": approved,
        "unapprovedCount": unapproved,
        "findings": finding_records,
        "approvalSource": args.exceptions.relative_to(REPO_ROOT).as_posix()
        if args.exceptions.resolve().is_relative_to(REPO_ROOT)
        else str(args.exceptions),
    }
    _write_reports(report, args.output_dir)
    print(f"OpenAPI breaking-change report: {args.output_dir / 'openapi-breaking-report.json'}")
    print(f"OpenAPI breaking-change summary: {args.output_dir / 'openapi-breaking-report.md'}")
    if unapproved:
        print(
            f"Detected {unapproved} unapproved OpenAPI breaking change(s). "
            f"Add an approved RFC/deprecation record in {args.exceptions.relative_to(REPO_ROOT)} to allow them.",
            file=sys.stderr,
        )
        return 1
    print("OpenAPI breaking-change gate passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
