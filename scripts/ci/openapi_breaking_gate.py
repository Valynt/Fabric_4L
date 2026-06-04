#!/usr/bin/env python3
"""OpenAPI breaking-change gate for REST contracts.

Compares the OpenAPI specs in contracts/openapi on the current branch against a
Git baseline ref and reports compatibility-impacting changes. This is the
architecture-correct replacement for buf breaking in this REST/OpenAPI repo.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_ROOT = REPO_ROOT / "contracts" / "openapi"
DEPRECATIONS_PATH = (
    REPO_ROOT / "contracts" / "deprecations" / "generated-contract-deprecations.json"
)
RFCS_ROOT = REPO_ROOT / "contracts" / "rfcs"
DEFAULT_REPORT_JSON = (
    REPO_ROOT / "reports" / "contracts" / "openapi-breaking-report.json"
)
DEFAULT_REPORT_MD = REPO_ROOT / "reports" / "contracts" / "openapi-breaking-report.md"
HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}
ERROR_STATUS_PREFIXES = ("4", "5")


@dataclass(frozen=True)
class Finding:
    severity: str
    category: str
    spec: str
    location: str
    message: str
    approval_key: str
    before: Any = None
    after: Any = None
    approved: bool = False
    approval_source: str | None = None

    def to_json(self) -> dict[str, Any]:
        payload = {
            "severity": self.severity,
            "category": self.category,
            "spec": self.spec,
            "location": self.location,
            "message": self.message,
            "approval_key": self.approval_key,
            "approved": self.approved,
            "approval_source": self.approval_source,
        }
        if self.before is not None:
            payload["before"] = self.before
        if self.after is not None:
            payload["after"] = self.after
        return payload


def _run_git(
    args: list[str], *, check: bool = False
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=check,
    )


def _git_ref_exists(ref: str) -> bool:
    return _run_git(["rev-parse", "--verify", "--quiet", ref]).returncode == 0


def _default_base_ref() -> str:
    explicit = os.getenv("OPENAPI_BREAKING_BASE_REF")
    if explicit:
        return explicit
    github_base = os.getenv("GITHUB_BASE_REF")
    if github_base:
        remote_ref = f"origin/{github_base}"
        if _git_ref_exists(remote_ref):
            return remote_ref
        return github_base
    for candidate in ("origin/main", "main", "origin/develop", "develop", "HEAD~1"):
        if _git_ref_exists(candidate):
            return candidate
    return "HEAD"


def _json_loads(text: str, *, source: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"OpenAPI document must be a JSON object: {source}")
    return value


def _load_current_specs() -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for path in sorted(OPENAPI_ROOT.glob("*.json")):
        specs[path.name] = _json_loads(
            path.read_text(encoding="utf-8"), source=str(path)
        )
    return specs


def _baseline_spec_names(base_ref: str) -> list[str]:
    result = _run_git(["ls-tree", "--name-only", f"{base_ref}:contracts/openapi"])
    if result.returncode != 0:
        return []
    return sorted(
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().endswith(".json")
    )


def _load_baseline_specs(
    base_ref: str, spec_names: Iterable[str]
) -> dict[str, dict[str, Any]]:
    specs: dict[str, dict[str, Any]] = {}
    for name in sorted(set(spec_names) | set(_baseline_spec_names(base_ref))):
        git_path = f"contracts/openapi/{name}"
        result = _run_git(["show", f"{base_ref}:{git_path}"])
        if result.returncode != 0:
            # New specs are additive from the current branch perspective.
            continue
        specs[name] = _json_loads(result.stdout, source=f"{base_ref}:{git_path}")
    return specs


def _load_approvals() -> dict[str, str]:
    approvals: dict[str, str] = {}
    if DEPRECATIONS_PATH.exists():
        data = json.loads(DEPRECATIONS_PATH.read_text(encoding="utf-8"))
        for entry in data.get("entries", []):
            if not isinstance(entry, dict):
                continue
            keys = {str(entry.get("key", "")).strip()}
            method = str(entry.get("method", "")).upper()
            path = str(entry.get("path", ""))
            if method and path:
                keys.add(f"{method} {path}")
            for key in keys:
                if key:
                    approvals[key] = str(DEPRECATIONS_PATH.relative_to(REPO_ROOT))

    if RFCS_ROOT.exists():
        for path in sorted(RFCS_ROOT.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            if (
                "status:** approved" not in text.lower()
                and "**status:** approved" not in text.lower()
            ):
                continue
            approval_source = str(path.relative_to(REPO_ROOT))
            for line in text.splitlines():
                stripped = line.strip().lstrip("-*").strip()
                upper = stripped.upper()
                for method in HTTP_METHODS:
                    token = f"{method.upper()} "
                    if token in upper:
                        idx = upper.index(token)
                        endpoint = stripped[idx:].strip().strip("`.;")
                        approvals[endpoint] = approval_source
    return approvals


def _approval_for(key: str, approvals: dict[str, str]) -> tuple[bool, str | None]:
    if key in approvals:
        return True, approvals[key]
    # Field findings use endpoint-or-schema prefixes before '#'.
    prefix = key.split("#", 1)[0]
    if prefix in approvals:
        return True, approvals[prefix]
    return False, None


def _resolve_ref(
    spec: dict[str, Any], ref: str, seen: set[str] | None = None
) -> dict[str, Any]:
    if not ref.startswith("#/"):
        return {}
    seen = seen or set()
    if ref in seen:
        return {}
    seen.add(ref)
    node: Any = spec
    for part in ref[2:].split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict):
            return {}
        node = node.get(part)
    if isinstance(node, dict) and "$ref" in node:
        return _resolve_ref(spec, str(node["$ref"]), seen)
    return node if isinstance(node, dict) else {}


def _merge_schema(
    spec: dict[str, Any], schema: dict[str, Any], seen: set[str] | None = None
) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    seen = seen or set()
    if "$ref" in schema:
        resolved = _resolve_ref(spec, str(schema["$ref"]), seen)
        merged = dict(resolved)
        merged.update({k: v for k, v in schema.items() if k != "$ref"})
        schema = merged
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged: dict[str, Any] = {k: v for k, v in schema.items() if k != "allOf"}
        properties: dict[str, Any] = {}
        required: list[str] = []
        for item in schema["allOf"]:
            item_schema = _merge_schema(spec, item, seen)
            properties.update(item_schema.get("properties", {}))
            required.extend(item_schema.get("required", []))
            for key, value in item_schema.items():
                if key not in {"properties", "required"}:
                    merged.setdefault(key, value)
        if properties:
            merged["properties"] = {**merged.get("properties", {}), **properties}
        if required:
            merged["required"] = sorted(set(merged.get("required", []) + required))
        schema = merged
    return schema


def _schema_types(schema: dict[str, Any]) -> set[str]:
    if "type" in schema:
        value = schema["type"]
        if isinstance(value, list):
            return {str(item) for item in value}
        return {str(value)}
    for keyword in ("oneOf", "anyOf"):
        if isinstance(schema.get(keyword), list):
            found: set[str] = set()
            for item in schema[keyword]:
                if isinstance(item, dict):
                    found.update(_schema_types(item))
            if found:
                return found
    if "enum" in schema:
        return {type(item).__name__ for item in schema.get("enum", [])}
    if "properties" in schema:
        return {"object"}
    if "items" in schema:
        return {"array"}
    return set()


def _flatten_fields(
    spec: dict[str, Any], schema: dict[str, Any], prefix: str = ""
) -> dict[str, dict[str, Any]]:
    schema = _merge_schema(spec, schema)
    fields: dict[str, dict[str, Any]] = {}
    if not schema:
        return fields
    properties = (
        schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    )
    required = (
        set(schema.get("required", []))
        if isinstance(schema.get("required"), list)
        else set()
    )
    for name, raw_child in properties.items():
        if not isinstance(raw_child, dict):
            continue
        child = _merge_schema(spec, raw_child)
        field_path = f"{prefix}.{name}" if prefix else str(name)
        fields[field_path] = {
            "types": sorted(_schema_types(child)),
            "enum": (
                list(child.get("enum", []))
                if isinstance(child.get("enum"), list)
                else None
            ),
            "required": name in required,
            "minimum": child.get("minimum"),
            "maximum": child.get("maximum"),
            "minLength": child.get("minLength"),
            "maxLength": child.get("maxLength"),
            "minItems": child.get("minItems"),
            "maxItems": child.get("maxItems"),
        }
        fields.update(_flatten_fields(spec, child, field_path))
        items = child.get("items")
        if isinstance(items, dict):
            fields.update(_flatten_fields(spec, items, f"{field_path}[]"))
    return fields


def _json_schema_for_media(
    operation: dict[str, Any], section: str, status: str | None = None
) -> dict[str, Any] | None:
    container: Any
    if section == "request":
        container = operation.get("requestBody", {})
    else:
        container = operation.get("responses", {}).get(status or "", {})
    if not isinstance(container, dict):
        return None
    content = container.get("content")
    if not isinstance(content, dict):
        return None
    media = content.get("application/json") or content.get("application/problem+json")
    if not isinstance(media, dict):
        return None
    schema = media.get("schema")
    return schema if isinstance(schema, dict) else None


def _operation_security(spec: dict[str, Any], operation: dict[str, Any]) -> Any:
    if "security" in operation:
        return operation.get("security")
    return spec.get("security")


def _append(
    findings: list[Finding],
    approvals: dict[str, str],
    *,
    category: str,
    spec: str,
    location: str,
    message: str,
    approval_key: str,
    before: Any = None,
    after: Any = None,
    severity: str = "breaking",
) -> None:
    approved, source = _approval_for(approval_key, approvals)
    findings.append(
        Finding(
            severity=severity,
            category=category,
            spec=spec,
            location=location,
            message=message,
            approval_key=approval_key,
            before=before,
            after=after,
            approved=approved,
            approval_source=source,
        )
    )


def _is_narrowed(
    before: dict[str, Any], after: dict[str, Any]
) -> tuple[bool, str, Any, Any]:
    before_types = set(before.get("types") or [])
    after_types = set(after.get("types") or [])
    if before_types and after_types:
        if after_types < before_types:
            return True, "type narrowed", sorted(before_types), sorted(after_types)
        if after_types != before_types:
            return True, "type changed", sorted(before_types), sorted(after_types)

    before_enum = before.get("enum")
    after_enum = after.get("enum")
    if isinstance(before_enum, list) and isinstance(after_enum, list):
        removed = [item for item in before_enum if item not in after_enum]
        if removed:
            return True, "enum values removed", before_enum, after_enum

    numeric_checks = (
        ("minimum", lambda old, new: new > old),
        ("minLength", lambda old, new: new > old),
        ("minItems", lambda old, new: new > old),
        ("maximum", lambda old, new: new < old),
        ("maxLength", lambda old, new: new < old),
        ("maxItems", lambda old, new: new < old),
    )
    for key, predicate in numeric_checks:
        old = before.get(key)
        new = after.get(key)
        if (
            isinstance(old, (int, float))
            and isinstance(new, (int, float))
            and predicate(old, new)
        ):
            return True, f"constraint {key} narrowed", old, new
    return False, "", None, None


def _compare_field_maps(
    findings: list[Finding],
    approvals: dict[str, str],
    *,
    spec_name: str,
    endpoint_key: str,
    location: str,
    category_prefix: str,
    before_fields: dict[str, dict[str, Any]],
    after_fields: dict[str, dict[str, Any]],
) -> None:
    for field, before in sorted(before_fields.items()):
        if field not in after_fields:
            category = f"removed_{category_prefix}_field"
            if category_prefix == "error_response":
                category = "error_response_contract_drift"
            _append(
                findings,
                approvals,
                category=category,
                spec=spec_name,
                location=f"{location}.{field}",
                message=f"Removed {category_prefix.replace('_', ' ')} field '{field}'.",
                approval_key=f"{endpoint_key}#{field}",
                before=before,
                after=None,
            )
            continue
        narrowed, message, before_value, after_value = _is_narrowed(
            before, after_fields[field]
        )
        if narrowed:
            category = (
                "type_narrowing" if "enum" not in message else "enum_value_removal"
            )
            if category_prefix == "error_response":
                category = "error_response_contract_drift"
            _append(
                findings,
                approvals,
                category=category,
                spec=spec_name,
                location=f"{location}.{field}",
                message=f"{message.capitalize()} for field '{field}'.",
                approval_key=f"{endpoint_key}#{field}",
                before=before_value,
                after=after_value,
            )

    for field, after in sorted(after_fields.items()):
        before = before_fields.get(field)
        if after.get("required") and (before is None or not before.get("required")):
            category = "required_field_addition"
            if category_prefix == "error_response":
                category = "error_response_contract_drift"
            _append(
                findings,
                approvals,
                category=category,
                spec=spec_name,
                location=f"{location}.{field}",
                message=f"Field '{field}' became required.",
                approval_key=f"{endpoint_key}#{field}",
                before=before,
                after=after,
            )


def _compare_operation(
    findings: list[Finding],
    approvals: dict[str, str],
    *,
    spec_name: str,
    before_spec: dict[str, Any],
    after_spec: dict[str, Any],
    path: str,
    method: str,
    before_operation: dict[str, Any],
    after_operation: dict[str, Any],
) -> None:
    endpoint_key = f"{method.upper()} {path}"
    if _operation_security(before_spec, before_operation) != _operation_security(
        after_spec, after_operation
    ):
        _append(
            findings,
            approvals,
            category="auth_security_contract_change",
            spec=spec_name,
            location=endpoint_key,
            message="Operation security requirements changed.",
            approval_key=endpoint_key,
            before=_operation_security(before_spec, before_operation),
            after=_operation_security(after_spec, after_operation),
        )

    before_request = _json_schema_for_media(before_operation, "request")
    after_request = _json_schema_for_media(after_operation, "request")
    if before_request and not after_request:
        _append(
            findings,
            approvals,
            category="removed_request_body",
            spec=spec_name,
            location=f"{endpoint_key} requestBody",
            message="Removed JSON request body schema.",
            approval_key=endpoint_key,
            before=before_request,
            after=None,
        )
    elif before_request and after_request:
        _compare_field_maps(
            findings,
            approvals,
            spec_name=spec_name,
            endpoint_key=endpoint_key,
            location=f"{endpoint_key} requestBody",
            category_prefix="request",
            before_fields=_flatten_fields(before_spec, before_request),
            after_fields=_flatten_fields(after_spec, after_request),
        )

    before_responses = (
        before_operation.get("responses", {})
        if isinstance(before_operation.get("responses"), dict)
        else {}
    )
    after_responses = (
        after_operation.get("responses", {})
        if isinstance(after_operation.get("responses"), dict)
        else {}
    )
    for status, before_response in sorted(before_responses.items()):
        if status not in after_responses:
            _append(
                findings,
                approvals,
                category=(
                    "error_response_contract_drift"
                    if str(status).startswith(ERROR_STATUS_PREFIXES)
                    else "removed_response"
                ),
                spec=spec_name,
                location=f"{endpoint_key} response {status}",
                message=f"Removed response status '{status}'.",
                approval_key=endpoint_key,
                before=before_response,
                after=None,
            )
            continue
        before_schema = _json_schema_for_media(
            before_operation, "response", str(status)
        )
        after_schema = _json_schema_for_media(after_operation, "response", str(status))
        if before_schema and not after_schema:
            _append(
                findings,
                approvals,
                category=(
                    "error_response_contract_drift"
                    if str(status).startswith(ERROR_STATUS_PREFIXES)
                    else "removed_response_schema"
                ),
                spec=spec_name,
                location=f"{endpoint_key} response {status}",
                message=f"Removed JSON response schema for status '{status}'.",
                approval_key=endpoint_key,
                before=before_schema,
                after=None,
            )
        elif before_schema and after_schema:
            prefix = (
                "error_response"
                if str(status).startswith(ERROR_STATUS_PREFIXES)
                else "response"
            )
            _compare_field_maps(
                findings,
                approvals,
                spec_name=spec_name,
                endpoint_key=endpoint_key,
                location=f"{endpoint_key} response {status}",
                category_prefix=prefix,
                before_fields=_flatten_fields(before_spec, before_schema),
                after_fields=_flatten_fields(after_spec, after_schema),
            )


def _compare_specs(
    current_specs: dict[str, dict[str, Any]],
    baseline_specs: dict[str, dict[str, Any]],
    approvals: dict[str, str],
) -> list[Finding]:
    findings: list[Finding] = []
    for spec_name, before_spec in sorted(baseline_specs.items()):
        after_spec = current_specs.get(spec_name)
        if not after_spec:
            _append(
                findings,
                approvals,
                category="removed_spec",
                spec=spec_name,
                location=spec_name,
                message="Removed entire OpenAPI spec.",
                approval_key=spec_name,
            )
            continue
        before_paths = (
            before_spec.get("paths", {})
            if isinstance(before_spec.get("paths"), dict)
            else {}
        )
        after_paths = (
            after_spec.get("paths", {})
            if isinstance(after_spec.get("paths"), dict)
            else {}
        )
        for path, before_path_item in sorted(before_paths.items()):
            if path not in after_paths:
                _append(
                    findings,
                    approvals,
                    category="removed_path",
                    spec=spec_name,
                    location=path,
                    message=f"Removed path '{path}'.",
                    approval_key=path,
                    before=before_path_item,
                    after=None,
                )
                continue
            if not isinstance(before_path_item, dict) or not isinstance(
                after_paths[path], dict
            ):
                continue
            for method, before_operation in sorted(before_path_item.items()):
                if method.lower() not in HTTP_METHODS or not isinstance(
                    before_operation, dict
                ):
                    continue
                after_operation = after_paths[path].get(method)
                if not isinstance(after_operation, dict):
                    _append(
                        findings,
                        approvals,
                        category="removed_method",
                        spec=spec_name,
                        location=f"{method.upper()} {path}",
                        message=f"Removed method '{method.upper()} {path}'.",
                        approval_key=f"{method.upper()} {path}",
                        before=before_operation,
                        after=None,
                    )
                    continue
                _compare_operation(
                    findings,
                    approvals,
                    spec_name=spec_name,
                    before_spec=before_spec,
                    after_spec=after_spec,
                    path=path,
                    method=method,
                    before_operation=before_operation,
                    after_operation=after_operation,
                )
    return findings


def _write_reports(
    *,
    json_path: Path,
    markdown_path: Path,
    base_ref: str,
    findings: list[Finding],
    baseline_spec_count: int,
    current_spec_count: int,
) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    unapproved = [finding for finding in findings if not finding.approved]
    payload = {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "base_ref": base_ref,
        "current_ref": "HEAD",
        "baseline_spec_count": baseline_spec_count,
        "current_spec_count": current_spec_count,
        "status": "failed" if unapproved else "passed",
        "summary": {
            "total_findings": len(findings),
            "approved_findings": len(findings) - len(unapproved),
            "unapproved_findings": len(unapproved),
        },
        "findings": [finding.to_json() for finding in findings],
    }
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# OpenAPI Breaking-Change Report",
        "",
        f"- Base ref: `{base_ref}`",
        "- Current ref: `HEAD`",
        f"- Status: **{payload['status']}**",
        f"- Total findings: {len(findings)}",
        f"- Unapproved findings: {len(unapproved)}",
        "",
    ]
    if not findings:
        lines.append("No breaking OpenAPI changes detected.")
    else:
        lines.extend(
            [
                "| Severity | Approved | Spec | Category | Location | Message | Approval |",
                "| --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for finding in findings:
            lines.append(
                "| "
                + " | ".join(
                    [
                        finding.severity,
                        "yes" if finding.approved else "no",
                        finding.spec,
                        finding.category,
                        f"`{finding.location}`",
                        finding.message.replace("|", "\\|"),
                        finding.approval_source or "",
                    ]
                )
                + " |"
            )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect breaking OpenAPI contract changes against a baseline ref."
    )
    parser.add_argument(
        "--base-ref",
        default=_default_base_ref(),
        help="Git ref used as the compatibility baseline.",
    )
    parser.add_argument("--report-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--report-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    current_specs = _load_current_specs()
    baseline_specs = _load_baseline_specs(args.base_ref, current_specs.keys())
    if not baseline_specs:
        raise SystemExit(f"No baseline OpenAPI specs found at ref '{args.base_ref}'.")
    approvals = _load_approvals()
    findings = _compare_specs(current_specs, baseline_specs, approvals)
    _write_reports(
        json_path=args.report_json,
        markdown_path=args.report_md,
        base_ref=args.base_ref,
        findings=findings,
        baseline_spec_count=len(baseline_specs),
        current_spec_count=len(current_specs),
    )
    unapproved = [finding for finding in findings if not finding.approved]
    print(f"OpenAPI breaking-change report: {args.report_json.relative_to(REPO_ROOT)}")
    print(f"OpenAPI breaking-change report: {args.report_md.relative_to(REPO_ROOT)}")
    if unapproved:
        print(
            f"Detected {len(unapproved)} unapproved breaking OpenAPI change(s).",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if findings:
        print(
            f"Detected {len(findings)} approved breaking OpenAPI change(s); gate passed."
        )
    else:
        print("No breaking OpenAPI changes detected.")


if __name__ == "__main__":
    main()
