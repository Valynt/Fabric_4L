#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

python - <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urlparse

REPO_ROOT = Path.cwd()
INDEX_PATH = REPO_ROOT / "contracts" / "schema-index.json"
CONTRACT_ROOTS = [
    REPO_ROOT / "contracts" / "jsonschema",
    REPO_ROOT / "contracts" / "openapi",
    REPO_ROOT / "contracts" / "tool-manifests",
    REPO_ROOT / "contracts" / "frontend",
    REPO_ROOT / "contracts" / "auth",
    REPO_ROOT / "contracts" / "config-policy",
    REPO_ROOT / "contracts" / "observability",
]
INDEXABLE_SUFFIXES = {".json", ".yaml", ".yml", ".md"}

Finding = tuple[str, str, str]
findings: list[Finding] = []
summary: list[tuple[str, int, int, str]] = []
json_documents: dict[Path, Any] = {}
yaml_ref_documents: dict[Path, str] = {}
schema_id_to_paths: dict[str, list[Path]] = {}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def add_finding(code: str, path: Path | str, detail: str) -> None:
    findings.append((code, str(path) if isinstance(path, str) else rel(path), detail))


def load_json(path: Path) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        add_finding("invalid-json", path, f"{exc.msg} at line {exc.lineno}, column {exc.colno}")
    except OSError as exc:
        add_finding("unreadable", path, str(exc))
    return None


def walk_json(value: Any, visitor, location: str = "#") -> None:
    visitor(value, location)
    if isinstance(value, dict):
        for key, child in value.items():
            escaped = str(key).replace("~", "~0").replace("/", "~1")
            walk_json(child, visitor, f"{location}/{escaped}")
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            walk_json(child, visitor, f"{location}/{idx}")


def resolve_pointer(document: Any, pointer: str) -> bool:
    if pointer in ("", "#"):
        return True
    if pointer.startswith("#"):
        pointer = pointer[1:]
    if not pointer.startswith("/"):
        return False
    current = document
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return False
            if index < 0 or index >= len(current):
                return False
            current = current[index]
        else:
            return False
    return True


def normalize_repo_path(path_value: str) -> Path:
    candidate = Path(path_value)
    if candidate.is_absolute():
        return candidate.resolve()
    return (REPO_ROOT / candidate).resolve()


def discover_files() -> set[Path]:
    discovered: set[Path] = set()
    for root in CONTRACT_ROOTS:
        if not root.exists():
            add_finding("missing-root", root, "Contract root directory is required by schema-index governance")
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in INDEXABLE_SUFFIXES:
                discovered.add(path.resolve())
    return discovered


def load_index() -> tuple[dict[str, Any], list[dict[str, Any]], set[str]]:
    if not INDEX_PATH.exists():
        add_finding("missing-index", INDEX_PATH, "Canonical schema index is required")
        return {}, [], set()
    index = load_json(INDEX_PATH)
    if not isinstance(index, dict):
        add_finding("invalid-index", INDEX_PATH, "Canonical schema index must be a JSON object")
        return {}, [], set()
    entries = index.get("entries")
    if not isinstance(entries, list):
        add_finding("invalid-index", INDEX_PATH, "Canonical schema index must contain an entries array")
        entries = []
    ignored = index.get("ignored_orphans", [])
    if not isinstance(ignored, list) or not all(isinstance(item, str) for item in ignored):
        add_finding("invalid-index", INDEX_PATH, "ignored_orphans must be an array of repository-relative paths")
        ignored = []
    return index, [entry for entry in entries if isinstance(entry, dict)], set(ignored)


def collect_contract_documents(files: set[Path]) -> None:
    for path in sorted(files):
        if path.suffix.lower() == ".json":
            document = load_json(path)
            if document is None:
                continue
            json_documents[path] = document
            schema_id = document.get("$id") if isinstance(document, dict) else None
            if isinstance(schema_id, str) and schema_id:
                schema_id_to_paths.setdefault(schema_id, []).append(path)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            try:
                yaml_ref_documents[path] = path.read_text(encoding="utf-8")
            except OSError as exc:
                add_finding("unreadable", path, str(exc))


def validate_index_entries(entries: list[dict[str, Any]], discovered: set[Path]) -> set[Path]:
    indexed_paths: set[Path] = set()
    paths_seen: dict[Path, int] = {}
    indexed_ids: dict[str, list[str]] = {}

    for ordinal, entry in enumerate(entries, start=1):
        entry_path_value = entry.get("path")
        if not isinstance(entry_path_value, str) or not entry_path_value:
            add_finding("index-entry-path-missing", INDEX_PATH, f"Entry #{ordinal} must declare a non-empty path")
            continue
        entry_path = normalize_repo_path(entry_path_value)
        indexed_paths.add(entry_path)
        paths_seen[entry_path] = paths_seen.get(entry_path, 0) + 1

        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            add_finding("index-entry-id-missing", INDEX_PATH, f"Entry {entry_path_value} must declare a non-empty id")
        else:
            indexed_ids.setdefault(entry_id, []).append(entry_path_value)

        if not entry_path.exists():
            add_finding("missing-index-entry-target", INDEX_PATH, f"Indexed path does not exist: {entry_path_value}")
            continue
        if entry_path not in discovered:
            add_finding("index-entry-out-of-scope", entry_path, "Indexed path is outside the governed contract roots")

    for path, count in sorted(paths_seen.items(), key=lambda item: rel(item[0])):
        if count > 1:
            add_finding("duplicate-index-path", path, f"Path appears {count} times in canonical index")
    for schema_id, paths in sorted(indexed_ids.items()):
        if len(paths) > 1:
            add_finding("duplicate-index-id", INDEX_PATH, f"Index id {schema_id!r} is used by: {', '.join(paths)}")

    return indexed_paths


def validate_orphans(discovered: set[Path], indexed_paths: set[Path], ignored: set[str]) -> None:
    ignored_paths = {normalize_repo_path(path) for path in ignored}
    for path in sorted(discovered - indexed_paths - ignored_paths):
        add_finding("orphaned-contract", path, "File is not listed in contracts/schema-index.json")
    for path in sorted(ignored_paths):
        if not path.exists():
            add_finding("stale-orphan-ignore", path, "ignored_orphans entry does not exist")
        elif path in indexed_paths:
            add_finding("redundant-orphan-ignore", path, "ignored_orphans entry is also indexed")


def validate_duplicate_schema_ids() -> None:
    for schema_id, paths in sorted(schema_id_to_paths.items()):
        if len(paths) > 1:
            add_finding("duplicate-schema-id", INDEX_PATH, f"$id {schema_id!r} appears in: {', '.join(rel(path) for path in paths)}")


def target_for_ref(source_path: Path, ref_value: str) -> tuple[Path, str] | None:
    ref_without_fragment, fragment = urldefrag(ref_value)
    if not ref_without_fragment:
        return source_path, f"#{fragment}" if fragment else "#"

    parsed = urlparse(ref_without_fragment)
    if parsed.scheme and parsed.scheme not in {"file"}:
        matches = schema_id_to_paths.get(ref_without_fragment, [])
        if len(matches) == 1:
            return matches[0], f"#{fragment}" if fragment else "#"
        if len(matches) > 1:
            add_finding("ambiguous-ref", source_path, f"$ref {ref_value!r} matches multiple schema IDs")
            return None
        add_finding("unresolved-ref-target", source_path, f"$ref {ref_value!r} does not match an indexed local schema $id")
        return None

    if parsed.scheme == "file":
        target_path = Path(parsed.path).resolve()
    else:
        target_path = (source_path.parent / ref_without_fragment).resolve()
    return target_path, f"#{fragment}" if fragment else "#"


def validate_ref_target(source_path: Path, ref_value: str, location: str) -> None:
    target = target_for_ref(source_path, ref_value)
    if target is None:
        return
    target_path, pointer = target
    target_document = json_documents.get(target_path)
    if target_document is None:
        if target_path.exists():
            target_document = load_json(target_path)
            if target_document is not None:
                json_documents[target_path] = target_document
        if target_document is None:
            add_finding("unresolved-ref-target", source_path, f"$ref {ref_value!r} at {location} targets missing or invalid file {rel(target_path)}")
            return
    if not resolve_pointer(target_document, pointer):
        add_finding("unresolved-ref-pointer", source_path, f"$ref {ref_value!r} at {location} targets missing pointer {pointer} in {rel(target_path)}")


def validate_refs() -> int:
    ref_count = 0
    for source_path, document in sorted(json_documents.items(), key=lambda item: rel(item[0])):
        def visitor(value: Any, location: str) -> None:
            nonlocal ref_count
            if not isinstance(value, dict) or "$ref" not in value:
                return
            ref_value = value["$ref"]
            if not isinstance(ref_value, str) or not ref_value:
                add_finding("invalid-ref", source_path, f"Non-empty string $ref required at {location}")
                return
            ref_count += 1
            validate_ref_target(source_path, ref_value, location)

        walk_json(document, visitor)

    for source_path, text in sorted(yaml_ref_documents.items(), key=lambda item: rel(item[0])):
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped.startswith("$ref:"):
                continue
            ref_value = stripped.split(":", 1)[1].strip().strip('"\'')
            if not ref_value:
                add_finding("invalid-ref", source_path, f"Non-empty string $ref required at line {line_number}")
                continue
            ref_count += 1
            validate_ref_target(source_path, ref_value, f"line {line_number}")

    return ref_count


def append_summary(label: str, total: int, failures_before: int, detail: str = "") -> None:
    summary.append((label, total, len(findings) - failures_before, detail))


def print_summary(discovered: set[Path], indexed_paths: set[Path], ref_count: int) -> None:
    rows = [
        ("Check", "Count", "Findings", "Status"),
        ("Governed files", str(len(discovered)), "-", "indexed"),
        ("Index entries", str(len(indexed_paths)), "-", "loaded"),
        ("JSON documents", str(len(json_documents)), "-", "parsed"),
        ("$ref references", str(ref_count), "-", "checked"),
    ]
    for label, total, failure_count, detail in summary:
        rows.append((label, str(total), str(failure_count), "PASS" if failure_count == 0 else f"FAIL {detail}".strip()))

    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    print("\nSchema Index Verification Summary")
    print(" | ".join(rows[0][column].ljust(widths[column]) for column in range(4)))
    print("-+-".join("-" * width for width in widths))
    for row in rows[1:]:
        print(" | ".join(row[column].ljust(widths[column]) for column in range(4)))


def main() -> int:
    discovered = discover_files()
    failures_before = len(findings)
    _index, entries, ignored = load_index()
    indexed_paths = validate_index_entries(entries, discovered)
    append_summary("Index integrity", len(entries), failures_before)

    failures_before = len(findings)
    validate_orphans(discovered, indexed_paths, ignored)
    append_summary("Orphan detection", len(discovered), failures_before)

    collect_contract_documents(discovered | indexed_paths)
    failures_before = len(findings)
    validate_duplicate_schema_ids()
    append_summary("Duplicate schema IDs", len(schema_id_to_paths), failures_before)

    failures_before = len(findings)
    ref_count = validate_refs()
    append_summary("$ref resolution", ref_count, failures_before)

    print_summary(discovered, indexed_paths, ref_count)

    if findings:
        print("\nFindings:")
        for code, path, detail in findings:
            print(f"- [{code}] {path}: {detail}")
        return 1

    print("\nResult: passed; schema contract indexes are complete and resolvable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
PY
