"""Impact analysis for schema changes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .loader import RegistryLoader
from .models import RegistryCatalog, SchemaRecord


class ImpactAnalyzer:
    """Analyze downstream impact of a schema change by $ref graph and domain/kind index."""

    def __init__(self, loader: RegistryLoader | None = None) -> None:
        self.loader = loader or RegistryLoader()

    def analyze(
        self,
        changed_schema_id: str,
        changed_version: str,
        catalog: RegistryCatalog | None = None,
    ) -> dict[str, Any]:
        """Return impact report for a schema change.

        Impact includes:
        - direct dependents (schemas that $ref the changed schema)
        - same-domain, same-kind consumers
        - subscription notifications
        """
        if catalog is None:
            catalog = self.loader.load_catalog()

        changed_record = catalog.get_schema(changed_schema_id, changed_version)
        if changed_record is None:
            raise ValueError(f"Schema not found: {changed_schema_id}@{changed_version}")

        # Build $ref index
        ref_index = self._build_ref_index(catalog)
        direct_dependents = ref_index.get(changed_schema_id, [])

        # Build domain/kind consumer list
        same_domain_consumers = [
            s.key()
            for s in catalog.schemas
            if s.domain == changed_record.domain and s.schema_id != changed_schema_id
        ]
        same_kind_consumers = [
            s.key()
            for s in catalog.schemas
            if s.kind == changed_record.kind and s.schema_id != changed_schema_id
        ]

        # Subscription notifications
        notifications: list[dict[str, Any]] = []
        for dep_key in direct_dependents:
            record = self._find_record_by_key(dep_key, catalog)
            if record:
                for sub in record.subscriptions:
                    notifications.append(
                        {
                            "schema": dep_key,
                            "team": sub.team,
                            "channel": sub.channel,
                            "events": sub.events,
                        }
                    )

        return {
            "changed_schema": changed_record.key(),
            "direct_dependents": sorted(set(direct_dependents)),
            "same_domain_consumers": sorted(set(same_domain_consumers)),
            "same_kind_consumers": sorted(set(same_kind_consumers)),
            "notifications": notifications,
            "recommendation": self._recommendation(changed_record, direct_dependents),
        }

    def _build_ref_index(self, catalog: RegistryCatalog) -> dict[str, list[str]]:
        """Map schema_id -> list of schema keys that reference it."""
        index: dict[str, list[str]] = {}
        for record in catalog.schemas:
            try:
                artifact = self.loader.load_artifact(record)
            except FileNotFoundError:
                continue
            refs = _collect_schema_id_refs(artifact)
            for ref_id in refs:
                index.setdefault(ref_id, []).append(record.key())
        return index

    def _find_record_by_key(self, key: str, catalog: RegistryCatalog) -> SchemaRecord | None:
        for s in catalog.schemas:
            if s.key() == key:
                return s
        return None

    def _recommendation(self, record: SchemaRecord, dependents: list[str]) -> str:
        if record.status.value in ("PUBLISHED", "DEPRECATED") and dependents:
            return (
                "Breaking changes are prohibited. Consider a new major version or additive evolution. "
                f"Notify {len(dependents)} dependent schema(s)."
            )
        if record.status.value == "DRAFT":
            return "Schema is DRAFT. Breaking changes are allowed but coordinate with stakeholders."
        return "Review compatibility policy before committing changes."


def _collect_schema_id_refs(node: Any, refs: set[str] | None = None) -> set[str]:
    if refs is None:
        refs = set()
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            ref = node["$ref"]
            # Extract schema_id from canonical URL pattern: .../domain/vN/schema_id.schema.json
            # We'll just collect the full URL; the index maps by schema_id prefix if needed.
            # Simplification: if it contains our host, extract the last path segment before .schema.json
            if "valuefabric.ai/contracts/jsonschema/" in ref:
                parts = ref.split("/")
                if parts:
                    last = parts[-1]
                    if ".schema.json" in last:
                        schema_id = last.replace(".schema.json", "")
                        refs.add(schema_id)
            else:
                # External ref: keep as-is
                refs.add(ref)
        for v in node.values():
            _collect_schema_id_refs(v, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_schema_id_refs(item, refs)
    return refs
