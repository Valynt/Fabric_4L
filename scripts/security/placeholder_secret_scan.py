#!/usr/bin/env python3
"""Scan manifests or a live cluster for placeholder secret values."""

from __future__ import annotations

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


PLACEHOLDER_RE = re.compile(
    r"(REPLACE_WITH_[A-Z0-9_]+|<INFISICAL_[A-Z0-9_]+>|CHANGE_ME|YOUR_CLIENT_ID|"
    r"replace-me|sk-placeholder|sk-ant-placeholder|dev-secret-key-change-in-production)",
    re.IGNORECASE,
)
PRODUCTION_FORBIDDEN_PLACEHOLDER_RE = re.compile(
    r"(REPLACE_WITH_[A-Z0-9_]+|devpassword|minioadmin)",
    re.IGNORECASE,
)

NON_PROD_VALUES = {"dev", "development", "local", "test"}
PROD_NAMESPACE_RE = re.compile(r"(prod|production|staging|stage)", re.IGNORECASE)
PROD_TARGET_SOURCE_RE = re.compile(r"(prod|production|staging|stage|helm|kustomize|rendered)", re.IGNORECASE)

# Keep this list intentionally explicit and narrow.
LOCAL_COMPOSE_ALLOWLIST = {
    "docker-compose.dev.yml",
    "infra/compose/docker-compose.full.dev-vault.yml",
    "infra/compose/docker-compose.e2e.yml",
    "infra/compose/docker-compose.test.yml",
}


def decode_b64(value: str) -> str:
    try:
        return base64.b64decode(value, validate=True).decode("utf-8", errors="replace")
    except Exception:
        return value


def scalar_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values: list[str] = []
        for child in value.values():
            values.extend(scalar_values(child))
        return values
    if isinstance(value, list):
        values = []
        for child in value:
            values.extend(scalar_values(child))
        return values
    return []


def is_guarded_dev_secret(doc: dict[str, Any]) -> bool:
    if doc.get("kind") != "Secret":
        return False
    metadata = doc.get("metadata") or {}
    labels = metadata.get("labels") or {}
    annotations = metadata.get("annotations") or {}
    namespace = metadata.get("namespace", "")
    env = labels.get("value-fabric.io/environment") or labels.get("environment")
    return (
        env in NON_PROD_VALUES
        and labels.get("value-fabric.io/non-prod-only") == "true"
        and labels.get("value-fabric.io/secret-scope") == "dev-placeholder"
        and namespace not in {"value-fabric-prod", "value-fabric-production", "value-fabric-staging"}
        and bool(annotations.get("value-fabric.io/allowed-namespaces"))
    )


def scan_doc(doc: dict[str, Any], source: str, allow_guarded_dev: bool) -> list[str]:
    if not isinstance(doc, dict):
        return []

    metadata = doc.get("metadata") or {}
    labels = metadata.get("labels") or {}
    if labels.get("value-fabric.io/control") in {
        "placeholder-secret-scan",
        "secret-placeholder-admission",
    }:
        return []

    identity = f"{doc.get('kind', '<unknown>')}/{metadata.get('name', '<unnamed>')}"
    namespace = metadata.get("namespace")
    if namespace:
        identity = f"{namespace}/{identity}"

    guarded_dev = allow_guarded_dev and is_guarded_dev_secret(doc)
    findings: list[str] = []

    source_name = Path(source).name
    is_local_compose_source = source_name in LOCAL_COMPOSE_ALLOWLIST
    is_production_target_source = bool(PROD_TARGET_SOURCE_RE.search(source))

    if doc.get("kind") == "Secret":
        for field in ("stringData", "data"):
            values = (doc.get(field) or {}).items()
            for key, value in values:
                rendered = decode_b64(str(value)) if field == "data" else str(value)
                if PLACEHOLDER_RE.search(rendered):
                    if guarded_dev:
                        continue
                    findings.append(f"{source}: {identity} {field}.{key} contains placeholder value")
                if (
                    not is_local_compose_source
                    and (
                        is_production_target_source
                        or (namespace and PROD_NAMESPACE_RE.search(namespace))
                    )
                    and PRODUCTION_FORBIDDEN_PLACEHOLDER_RE.search(rendered)
                ):
                    findings.append(
                        f"{source}: {identity} {field}.{key} contains production-forbidden placeholder value"
                    )
    else:
        for value in scalar_values(doc):
            if PLACEHOLDER_RE.search(value):
                findings.append(f"{source}: {identity} contains placeholder value")
            if (
                not is_local_compose_source
                and (
                    is_production_target_source
                    or (namespace and PROD_NAMESPACE_RE.search(namespace))
                )
                and PRODUCTION_FORBIDDEN_PLACEHOLDER_RE.search(value)
            ):
                findings.append(f"{source}: {identity} contains production-forbidden placeholder value")

    return findings


def iter_manifest_docs(paths: list[Path]) -> list[tuple[str, dict[str, Any]]]:
    docs: list[tuple[str, dict[str, Any]]] = []
    for path in paths:
        if path.is_dir():
            files = [
                child
                for child in path.rglob("*")
                if child.suffix.lower() in {".yaml", ".yml", ".json"}
            ]
        else:
            files = [path]

        for file_path in files:
            try:
                with file_path.open("r", encoding="utf-8") as handle:
                    loaded = list(yaml.safe_load_all(handle))
            except Exception as exc:
                print(f"warning: skipped {file_path}: {exc}", file=sys.stderr)
                continue
            for doc in loaded:
                if isinstance(doc, dict):
                    docs.append((str(file_path), doc))
    return docs


def scan_manifests(paths: list[Path], allow_guarded_dev: bool) -> list[str]:
    findings: list[str] = []
    for source, doc in iter_manifest_docs(paths):
        findings.extend(scan_doc(doc, source, allow_guarded_dev))
    return findings


def kubectl_json(args: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        ["kubectl", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "kubectl command failed")
    return json.loads(proc.stdout)


def scan_runtime(namespaces: list[str] | None, allow_guarded_dev: bool) -> list[str]:
    base = ["get", "secrets,configmaps", "-o", "json"]
    if namespaces:
        items: list[dict[str, Any]] = []
        for namespace in namespaces:
            payload = kubectl_json(["-n", namespace, *base])
            items.extend(payload.get("items", []))
    else:
        payload = kubectl_json(["-A", *base])
        items = payload.get("items", [])

    findings: list[str] = []
    for doc in items:
        findings.extend(scan_doc(doc, "cluster", allow_guarded_dev))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Manifest files or directories")
    parser.add_argument("--runtime", action="store_true", help="Scan the current kubectl cluster")
    parser.add_argument("--namespace", action="append", help="Runtime namespace to scan; repeatable")
    parser.add_argument(
        "--allow-guarded-dev",
        action="store_true",
        help="Allow Secret placeholders only when explicit non-prod guard labels are present",
    )
    args = parser.parse_args()

    findings: list[str] = []
    if args.paths:
        findings.extend(scan_manifests(args.paths, args.allow_guarded_dev))
    if args.runtime:
        findings.extend(scan_runtime(args.namespace, args.allow_guarded_dev))

    if not args.paths and not args.runtime:
        parser.error("provide manifest paths and/or --runtime")

    if findings:
        print("Placeholder scan failed:")
        for finding in findings:
            print(f"  - {finding}")
        return 1

    print("Placeholder scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
