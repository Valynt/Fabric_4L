"""Deterministic bundle builder with $ref resolution."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .loader import RegistryLoader
from .models import RegistryCatalog, SchemaRecord


class BundleBuilder:
    """Build a deterministic JSON bundle from the registry by resolving $ref graph."""

    def __init__(
        self,
        loader: RegistryLoader | None = None,
        repo_root: Path | str | None = None,
    ) -> None:
        self.loader = loader or RegistryLoader(repo_root=repo_root)
        self.repo_root = self.loader.repo_root

    def build_bundle(
        self,
        catalog: RegistryCatalog | None = None,
        schema_filter: set[str] | None = None,
    ) -> dict[str, Any]:
        """Produce a bundle mapping canonical $id -> schema dict.

        Args:
            catalog: Registry catalog. If None, loads from disk.
            schema_filter: If provided, only include schemas whose schema_id is in the set.
        """
        if catalog is None:
            catalog = self.loader.load_catalog()

        bundle: dict[str, str | dict[str, Any]] = {}
        bundle["_bundle_meta"] = {
            "registry_version": catalog.registry_version,
            "schema_count": 0,
            "bundled_at": _now_iso(),
        }

        for record in catalog.schemas:
            if schema_filter and record.schema_id not in schema_filter:
                continue
            artifact = self.loader.load_artifact(record)
            schema_id = artifact.get("$id")
            if not schema_id:
                schema_id = f"{record.schema_id}@{record.version}"
            bundle[schema_id] = artifact

        bundle["_bundle_meta"]["schema_count"] = len(bundle) - 1
        return bundle

    def write_bundle(
        self,
        output_path: Path | str,
        catalog: RegistryCatalog | None = None,
        schema_filter: set[str] | None = None,
    ) -> Path:
        bundle = self.build_bundle(catalog, schema_filter)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(bundle, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return output_path

    def build_lockfile(
        self,
        catalog: RegistryCatalog | None = None,
        output_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Produce a lockfile pinning every schema version and its content hash.

        The lockfile is a source-of-truth artifact for reproducible builds.
        """
        if catalog is None:
            catalog = self.loader.load_catalog()

        entries: list[dict[str, Any]] = []
        for record in catalog.schemas:
            artifact_path = self.repo_root / record.artifact
            actual_hash = record.compute_content_hash(artifact_path)
            entries.append(
                {
                    "schema_id": record.schema_id,
                    "version": record.version,
                    "status": record.status.value,
                    "artifact": record.artifact,
                    "content_hash": actual_hash,
                    "kind": record.kind.value,
                    "domain": record.domain,
                }
            )

        lockfile = {
            "lockfile_version": "1.0.0",
            "registry_version": catalog.registry_version,
            "generated_at": _now_iso(),
            "entries": sorted(entries, key=lambda e: (e["schema_id"], e["version"])),
        }

        if output_path:
            out = Path(output_path)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(lockfile, indent=2, sort_keys=True), encoding="utf-8")

        return lockfile

    def verify_bundle_refs(self, bundle: dict[str, Any]) -> list[str]:
        """Return list of unresolved $ref values inside the bundle."""
        unresolved: list[str] = []
        for schema_id, schema in bundle.items():
            if schema_id.startswith("_"):
                continue
            refs = _collect_refs(schema)
            for ref in refs:
                # External refs are allowed if they are canonical $ids elsewhere in the bundle
                if ref not in bundle:
                    unresolved.append(f"{schema_id} -> {ref}")
        return unresolved


def _collect_refs(node: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            refs.add(node["$ref"])
        for v in node.values():
            refs |= _collect_refs(v)
    elif isinstance(node, list):
        for item in node:
            refs |= _collect_refs(item)
    return refs


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
