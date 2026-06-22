"""Read-only Layer 3 vector store health and architecture drift check.

Layer 3 uses Neo4j 5 native vector indexes. PostgreSQL pgvector is not an
active backend for current retrieval paths, so this gate verifies that repo
configuration and canonical docs stay aligned with the Neo4j-native design.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

ACTIVE_VECTOR_STORE = "neo4j_native"
REQUIRED_VECTOR_INDEXES: dict[str, tuple[str, str]] = {
    "capability_embedding_idx": ("Capability", "embedding"),
    "usecase_embedding_idx": ("UseCase", "embedding"),
    "persona_embedding_idx": ("Persona", "embedding"),
    "valuedriver_embedding_idx": ("ValueDriver", "embedding"),
}

COMPOSE_FILES = (
    Path("docker-compose.dev.yml"),
    Path("infra/compose/docker-compose.backend-integrated.yml"),
    Path("docker-compose.full.yml"),
    Path("services/layer3-knowledge/docker-compose.yml"),
)

CANONICAL_DOC_PATTERNS: dict[Path, tuple[re.Pattern[str], ...]] = {
    Path("docs/architecture.md"): (
        re.compile(r"\bpgvector\b", re.IGNORECASE),
        re.compile(r"\bPinecone\b", re.IGNORECASE),
        re.compile(r"\bQdrant\b", re.IGNORECASE),
    ),
    Path("docs/reference/layer3-knowledge-api.md"): (
        re.compile(r"\bpgvector\b", re.IGNORECASE),
        re.compile(r"\bPinecone\b", re.IGNORECASE),
        re.compile(r"\bQdrant\b", re.IGNORECASE),
    ),
    Path("services/layer3-knowledge/src/docs/api_documentation.py"): (
        re.compile(r"\bPinecone\b", re.IGNORECASE),
        re.compile(r"\bpgvector\b", re.IGNORECASE),
        re.compile(r"\bQdrant\b", re.IGNORECASE),
    ),
    Path("docs/Providers.md"): (
        re.compile(r"\|\s*Pinecone\s*\|\s*L3\s*\|", re.IGNORECASE),
        re.compile(r"requires\s+Pinecone", re.IGNORECASE),
        re.compile(r"vector search fallback", re.IGNORECASE),
    ),
}


@dataclass(frozen=True)
class Finding:
    key: str
    message: str


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _repo_rel(path: Path, repo_root: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return path.as_posix()


def _find_neo4j_images(repo_root: Path) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    pattern = re.compile(r"image:\s*[\"']?neo4j:(?P<tag>[^\s\"']+)", re.IGNORECASE)
    for rel_path in COMPOSE_FILES:
        path = repo_root / rel_path
        if not path.exists():
            continue
        for match in pattern.finditer(_read(path)):
            tag = match.group("tag").rstrip(",")
            images.append({"file": rel_path.as_posix(), "tag": tag})
    return images


def _check_neo4j_images(repo_root: Path) -> tuple[list[dict[str, str]], list[Finding]]:
    images = _find_neo4j_images(repo_root)
    errors: list[Finding] = []
    if not images:
        errors.append(Finding("neo4j_image_missing", "No Neo4j image declarations found in canonical compose files."))
        return images, errors

    for image in images:
        tag = image["tag"]
        if not re.match(r"^5(?:[.\-]|$)", tag):
            errors.append(
                Finding(
                    "neo4j_image_not_v5",
                    f"{image['file']} uses neo4j:{tag}; Layer 3 vector indexes require Neo4j 5.x.",
                )
            )
    return images, errors


def _check_index_declarations(repo_root: Path) -> tuple[dict[str, dict[str, str]], list[Finding]]:
    constraints_path = repo_root / "services/layer3-knowledge/src/schema/constraints.py"
    initializer_path = repo_root / "services/layer3-knowledge/src/schema/initializer.py"
    settings_path = repo_root / "services/layer3-knowledge/src/config/settings.py"
    errors: list[Finding] = []
    declared: dict[str, dict[str, str]] = {}

    for path in (constraints_path, initializer_path, settings_path):
        if not path.exists():
            errors.append(Finding("required_file_missing", f"Required vector health source is missing: {_repo_rel(path, repo_root)}"))
            return declared, errors

    constraints = _read(constraints_path)
    initializer = _read(initializer_path)
    settings = _read(settings_path)

    for index_name, (label, property_name) in REQUIRED_VECTOR_INDEXES.items():
        declaration = re.compile(
            rf"Index\(\s*[\"']{re.escape(index_name)}[\"']\s*,\s*[\"']{label}[\"']\s*,\s*\[[\"']{property_name}[\"']\]\s*,\s*[\"']vector[\"']\s*\)",
            re.MULTILINE,
        )
        if not declaration.search(constraints):
            errors.append(
                Finding(
                    "vector_index_declaration_missing",
                    f"Missing required Neo4j vector index declaration for {index_name} on {label}.{property_name}.",
                )
            )
            continue
        declared[index_name] = {"label": label, "property": property_name}

    dimension_sources = {
        "constraints_get_settings": "embedding_dimension = get_settings().embedding_dimension" in constraints,
        "constraints_index_config": "`vector.dimensions`: {embedding_dimension}" in constraints,
        "initializer_expected": "expected = self.settings.embedding_dimension" in initializer,
        "initializer_index_config": "`vector.dimensions`: {embedding_dimension}" in initializer,
        "settings_env_alias": 'alias="EMBEDDING_DIMENSION"' in settings,
    }
    for key, ok in dimension_sources.items():
        if not ok:
            errors.append(
                Finding(
                    "embedding_dimension_source_drift",
                    f"Embedding dimension source check failed: {key}. Vector index dimensions must come from EMBEDDING_DIMENSION.",
                )
            )

    return declared, errors


def _check_canonical_docs(repo_root: Path) -> list[Finding]:
    errors: list[Finding] = []
    for rel_path, patterns in CANONICAL_DOC_PATTERNS.items():
        path = repo_root / rel_path
        if not path.exists():
            errors.append(Finding("canonical_doc_missing", f"Canonical vector architecture doc is missing: {rel_path.as_posix()}"))
            continue
        text = _read(path)
        for pattern in patterns:
            if pattern.search(text):
                errors.append(
                    Finding(
                        "stale_vector_store_reference",
                        f"{rel_path.as_posix()} still matches stale active vector-store wording: {pattern.pattern}",
                    )
                )
    return errors


def _check_backend_selection(vector_store_backend: str) -> list[Finding]:
    if vector_store_backend == ACTIVE_VECTOR_STORE:
        return []
    return [
        Finding(
            "unsupported_vector_store_backend",
            f"Vector store backend {vector_store_backend!r} is not supported. Current active backend is {ACTIVE_VECTOR_STORE!r}; pgvector_required=false.",
        )
    ]


def run_static_checks(repo_root: Path, vector_store_backend: str = ACTIVE_VECTOR_STORE) -> dict[str, Any]:
    images, image_errors = _check_neo4j_images(repo_root)
    declared_indexes, index_errors = _check_index_declarations(repo_root)
    errors = [
        *_check_backend_selection(vector_store_backend),
        *image_errors,
        *index_errors,
        *_check_canonical_docs(repo_root),
    ]
    return {
        "active_vector_store": ACTIVE_VECTOR_STORE,
        "pgvector_required": False,
        "mode": "static",
        "neo4j_images": images,
        "required_vector_indexes": declared_indexes,
        "errors": [finding.__dict__ for finding in errors],
    }


def _live_neo4j_check(embedding_dimension: int) -> dict[str, Any]:
    try:
        from neo4j import GraphDatabase
    except ImportError as exc:
        return {"status": "unhealthy", "error": f"neo4j package is unavailable: {exc}"}

    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "devpassword")
    database = os.environ.get("NEO4J_DATABASE") or None

    query = (
        "SHOW INDEXES YIELD name, type, labelsOrTypes, properties, state, options "
        "WHERE type = 'VECTOR' RETURN name, labelsOrTypes, properties, state, options"
    )
    details: dict[str, Any] = {}
    errors: list[Finding] = []

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session(database=database) as session:
            records = list(session.run(query))
        driver.close()
    except Exception as exc:  # pragma: no cover - live dependency failure shape
        return {"status": "unhealthy", "error": f"Neo4j vector index query failed: {exc}"}

    by_name = {record["name"]: record for record in records}
    for index_name, (label, property_name) in REQUIRED_VECTOR_INDEXES.items():
        record = by_name.get(index_name)
        if record is None:
            errors.append(Finding("live_vector_index_missing", f"Missing live Neo4j vector index: {index_name}."))
            continue

        options = record.get("options") or {}
        index_config = options.get("indexConfig") or {}
        actual_dimension = index_config.get("vector.dimensions")
        similarity = index_config.get("vector.similarity_function")
        state = record.get("state")
        labels = record.get("labelsOrTypes") or []
        properties = record.get("properties") or []
        details[index_name] = {
            "state": state,
            "dimension": actual_dimension,
            "similarity_function": similarity,
            "labels": labels,
            "properties": properties,
        }
        if state != "ONLINE":
            errors.append(Finding("live_vector_index_not_online", f"{index_name} is {state}; expected ONLINE."))
        if actual_dimension != embedding_dimension:
            errors.append(
                Finding(
                    "live_vector_index_dimension_mismatch",
                    f"{index_name} dimension is {actual_dimension}; expected {embedding_dimension}.",
                )
            )
        if similarity != "cosine":
            errors.append(Finding("live_vector_index_similarity_mismatch", f"{index_name} similarity is {similarity}; expected cosine."))
        if label not in labels or property_name not in properties:
            errors.append(
                Finding(
                    "live_vector_index_target_mismatch",
                    f"{index_name} targets labels={labels} properties={properties}; expected {label}.{property_name}.",
                )
            )

    return {
        "status": "healthy" if not errors else "unhealthy",
        "indexes": details,
        "errors": [finding.__dict__ for finding in errors],
    }


def run_checks(
    repo_root: Path,
    *,
    vector_store_backend: str = ACTIVE_VECTOR_STORE,
    live: bool = False,
    embedding_dimension: int = 384,
) -> dict[str, Any]:
    report = run_static_checks(repo_root, vector_store_backend)
    if live:
        report["mode"] = "live"
        report["live"] = _live_neo4j_check(embedding_dimension)
        live_errors = report["live"].get("errors") or []
        if report["live"].get("status") != "healthy" and not live_errors:
            report["errors"].append({"key": "live_vector_store_unhealthy", "message": report["live"].get("error", "Live vector check failed.")})
        else:
            report["errors"].extend(live_errors)
    return report


def _emit_text(report: dict[str, Any]) -> None:
    print(f"active_vector_store={report['active_vector_store']}")
    print(f"pgvector_required={str(report['pgvector_required']).lower()}")
    print(f"mode={report['mode']}")
    print("neo4j_images=" + ",".join(f"{item['file']}:neo4j:{item['tag']}" for item in report["neo4j_images"]))
    print("required_vector_indexes=" + ",".join(sorted(report["required_vector_indexes"])))
    if "live" in report:
        print(f"live_status={report['live'].get('status')}")
    if report["errors"]:
        print("errors:")
        for error in report["errors"]:
            print(f"- {error['key']}: {error['message']}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    parser.add_argument("--live", action="store_true", help="Connect to Neo4j and validate live vector indexes.")
    parser.add_argument(
        "--vector-store-backend",
        default=os.environ.get("VECTOR_STORE_BACKEND", ACTIVE_VECTOR_STORE),
        help="Expected vector backend. Only neo4j_native is supported currently.",
    )
    parser.add_argument(
        "--embedding-dimension",
        type=int,
        default=int(os.environ.get("EMBEDDING_DIMENSION", "384")),
        help="Configured embedding dimension for live Neo4j index validation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = run_checks(
        args.repo_root,
        vector_store_backend=args.vector_store_backend,
        live=args.live,
        embedding_dimension=args.embedding_dimension,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _emit_text(report)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
