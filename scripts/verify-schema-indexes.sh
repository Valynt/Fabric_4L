#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Validate the canonical contract/schema index and local $ref graph.
# Keep this wrapper dependency-light so `pnpm test:schema` can run in CI without
# requiring a project-specific Python virtualenv.

PYTHON_BIN="${PYTHON:-}"
if [[ -z "${PYTHON_BIN}" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "error: python3 or python is required to verify schema indexes" >&2
    exit 127
  fi
fi

"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, unquote

ROOT = Path.cwd()
INDEX_PATH = Path("contracts/schema-index.json")
SCOPED_DIRS = [
    Path("contracts/jsonschema"),
    Path("contracts/openapi"),
    Path("contracts/tool-manifests"),
    Path("contracts/frontend"),
    Path("contracts/auth"),
    Path("contracts/config-policy"),
    Path("contracts/observability"),
    Path("contracts/event-catalog"),
    Path("contracts/agent-registry"),
]
INDEXABLE_EXTENSIONS = {".json", ".yaml", ".yml", ".md"}

errors: list[str] = []
warnings: list[str] = []
summary: dict[str, dict[str, int]] = {}


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: Path) -> Any | None:
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:  # noqa: BLE001 - report all parse failures as governance errors.
        errors.append(f"{rel(path)} is not valid JSON: {exc}")
        return None


def json_pointer_get(document: Any, pointer: str) -> bool:
    if pointer in ("", "#"):
        return True
    if pointer.startswith("#"):
        pointer = pointer[1:]
    if pointer == "":
        return True
    if not pointer.startswith("/"):
        return False

    current = document
    for raw_part in pointer.split("/")[1:]:
        part = unquote(raw_part).replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            if part not in current:
                return False
            current = current[part]
        elif isinstance(current, list):
            if not part.isdigit():
                return False
            idx = int(part)
            if idx >= len(current):
                return False
            current = current[idx]
        else:
            return False
    return True


def iter_refs(node: Any, location: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child_location = f"{location}/{key}"
            if key == "$ref" and isinstance(value, str):
                found.append((value, child_location))
            else:
                found.extend(iter_refs(value, child_location))
    elif isinstance(node, list):
        for idx, value in enumerate(node):
            found.extend(iter_refs(value, f"{location}/{idx}"))
    return found


def category_for(path: Path) -> str:
    path_s = path.as_posix()
    for directory in SCOPED_DIRS:
        directory_s = directory.as_posix() + "/"
        if path_s.startswith(directory_s):
            return directory.as_posix()
    return "other"


def collect_files() -> list[Path]:
    files: list[Path] = []
    for directory in SCOPED_DIRS:
        if not directory.exists():
            errors.append(f"Required contract directory is missing: {directory.as_posix()}")
            continue
        for path in directory.rglob("*"):
            if path.is_file() and path.suffix.lower() in INDEXABLE_EXTENSIONS:
                files.append(path)
    return sorted(files, key=lambda p: p.as_posix())


def normalize_ignored(index: dict[str, Any]) -> set[str]:
    ignored: set[str] = set()
    for item in index.get("ignored_orphans", []):
        if isinstance(item, str):
            ignored.add(item)
        elif isinstance(item, dict) and isinstance(item.get("path"), str):
            ignored.add(item["path"])
        else:
            errors.append(f"contracts/schema-index.json has invalid ignored_orphans entry: {item!r}")
    return ignored


def resolve_ref(ref_value: str, source_path: Path, documents: dict[str, Any], id_to_path: dict[str, Path]) -> None:
    target, fragment = urldefrag(ref_value)
    target_path: Path

    if target == "":
        target_path = source_path
    elif target in id_to_path:
        target_path = id_to_path[target]
    elif "://" in target or target.startswith("urn:") or target.startswith("contract:") or target.startswith("openapi:"):
        errors.append(f"{rel(source_path)} has unresolved external $ref at {ref_value!r}: target id is not indexed")
        return
    else:
        target_path = (source_path.parent / target).resolve()
        try:
            target_path.relative_to(ROOT)
        except ValueError:
            errors.append(f"{rel(source_path)} has $ref escaping repository root at {ref_value!r}")
            return

    target_rel = rel(target_path)
    if target_rel not in documents:
        errors.append(f"{rel(source_path)} has unresolved $ref {ref_value!r}: {target_rel} is not a loaded JSON contract")
        return
    if fragment and not json_pointer_get(documents[target_rel], fragment):
        errors.append(f"{rel(source_path)} has unresolved $ref {ref_value!r}: fragment #{fragment} does not exist in {target_rel}")


if not INDEX_PATH.exists():
    print("ERROR: contracts/schema-index.json is missing", file=sys.stderr)
    sys.exit(1)

index_data = load_json(INDEX_PATH)
if not isinstance(index_data, dict):
    print("ERROR: contracts/schema-index.json must be a JSON object", file=sys.stderr)
    sys.exit(1)

entries = index_data.get("entries")
if not isinstance(entries, list):
    errors.append("contracts/schema-index.json must contain an entries array")
    entries = []

ignored_orphans = normalize_ignored(index_data)
indexed_paths: list[str] = []
index_ids: list[str] = []
entry_by_path: dict[str, dict[str, Any]] = {}

for idx, entry in enumerate(entries):
    if not isinstance(entry, dict):
        errors.append(f"contracts/schema-index.json entries[{idx}] must be an object")
        continue
    path_value = entry.get("path")
    id_value = entry.get("id")
    if not isinstance(path_value, str) or not path_value:
        errors.append(f"contracts/schema-index.json entries[{idx}] is missing a non-empty path")
        continue
    if not isinstance(id_value, str) or not id_value:
        errors.append(f"contracts/schema-index.json entry for {path_value} is missing a non-empty id")
    if Path(path_value).is_absolute() or ".." in Path(path_value).parts:
        errors.append(f"contracts/schema-index.json entry uses non-canonical path: {path_value}")
    indexed_paths.append(path_value)
    if isinstance(id_value, str) and id_value:
        index_ids.append(id_value)
    if path_value in entry_by_path:
        errors.append(f"Duplicate index entry path: {path_value}")
    entry_by_path[path_value] = entry

for duplicate_path, count in Counter(indexed_paths).items():
    if count > 1:
        errors.append(f"Duplicate index path {duplicate_path!r} appears {count} times")
for duplicate_id, count in Counter(index_ids).items():
    if count > 1:
        errors.append(f"Duplicate schema index id {duplicate_id!r} appears {count} times")

actual_files = collect_files()
actual_set = {rel(path) for path in actual_files}
indexed_set = set(indexed_paths)

for indexed_path in sorted(indexed_set):
    if indexed_path not in actual_set:
        errors.append(f"Indexed contract is missing on disk: {indexed_path}")

orphans = sorted((actual_set - indexed_set) - ignored_orphans)
for orphan in orphans:
    errors.append(f"Orphaned contract is not listed in contracts/schema-index.json: {orphan}")

for ignored in sorted(ignored_orphans):
    if ignored not in actual_set:
        warnings.append(f"ignored_orphans entry does not exist on disk: {ignored}")

# Load JSON documents for duplicate $id and $ref checks. Non-JSON indexed files are
# still required to exist and be indexed, but they do not participate in JSON ref resolution.
documents: dict[str, Any] = {}
document_ids: list[tuple[str, str]] = []
id_to_path: dict[str, Path] = {}

for path in actual_files:
    path_rel = rel(path)
    if path.suffix.lower() != ".json":
        continue
    document = load_json(path)
    if document is None:
        continue
    documents[path_rel] = document
    if isinstance(document, dict):
        doc_id = document.get("$id") or document.get("id") if category_for(path) == "contracts/tool-manifests" else document.get("$id")
        if isinstance(doc_id, str) and doc_id:
            document_ids.append((doc_id, path_rel))

# Index ids and document $id values are both resolvable targets. Prefer document ids
# when present; index ids cover OpenAPI/Markdown/YAML contracts that do not carry $id.
for index_id, path_rel in ((entry.get("id"), path_value) for path_value, entry in entry_by_path.items()):
    if isinstance(index_id, str) and index_id and path_rel in actual_set:
        id_to_path.setdefault(index_id, ROOT / path_rel)
for doc_id, path_rel in document_ids:
    if doc_id in id_to_path and rel(id_to_path[doc_id]) != path_rel:
        errors.append(f"Schema id {doc_id!r} maps to both {rel(id_to_path[doc_id])} and {path_rel}")
    id_to_path[doc_id] = ROOT / path_rel

ids_to_paths = defaultdict(list)
for doc_id, path_rel in document_ids:
    ids_to_paths[doc_id].append(path_rel)
for doc_id, paths in sorted(ids_to_paths.items()):
    if len(paths) > 1:
        errors.append(f"Duplicate JSON schema $id {doc_id!r} appears in: {', '.join(paths)}")

for path_rel, document in sorted(documents.items()):
    source_path = ROOT / path_rel
    for ref_value, location in iter_refs(document, ""):
        before = len(errors)
        resolve_ref(ref_value, source_path, documents, id_to_path)
        if len(errors) > before:
            errors[-1] += f" (at {location})"

# Build category summary.
for directory in SCOPED_DIRS:
    key = directory.as_posix()
    actual_in_category = {p for p in actual_set if p.startswith(key + "/")}
    indexed_in_category = {p for p in indexed_set if p.startswith(key + "/")}
    missing_in_category = indexed_in_category - actual_set
    orphan_in_category = (actual_in_category - indexed_set) - ignored_orphans
    duplicate_id_count = 0
    for schema_id, count in Counter(
        entry.get("id")
        for path_value, entry in entry_by_path.items()
        if path_value.startswith(key + "/") and isinstance(entry.get("id"), str)
    ).items():
        if schema_id and count > 1:
            duplicate_id_count += count
    summary[key] = {
        "files": len(actual_in_category),
        "indexed": len(indexed_in_category),
        "missing": len(missing_in_category),
        "orphans": len(orphan_in_category),
        "duplicate_ids": duplicate_id_count,
    }

print("Schema index verification summary")
print("| Contract area | Files | Indexed | Missing | Orphans | Duplicate IDs |")
print("| --- | ---: | ---: | ---: | ---: | ---: |")
for key, row in summary.items():
    print(
        f"| {key} | {row['files']} | {row['indexed']} | {row['missing']} | "
        f"{row['orphans']} | {row['duplicate_ids']} |"
    )
print(f"| TOTAL | {len(actual_set)} | {len(indexed_set & set().union(*[set(p for p in indexed_set if p.startswith(d.as_posix() + '/')) for d in SCOPED_DIRS]))} | "
      f"{len(indexed_set - actual_set)} | {len(orphans)} | "
      f"{sum(1 for _id, count in Counter(index_ids).items() if count > 1)} |")
print(f"\nResolved JSON documents: {len(documents)}")
print(f"Indexed resolver ids: {len(id_to_path)}")

if warnings:
    print("\nWarnings:")
    for warning in warnings:
        print(f"  - {warning}")

if errors:
    print("\nSchema index verification failed:", file=sys.stderr)
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    sys.exit(1)

print("\nSchema index verification passed.")
PY
