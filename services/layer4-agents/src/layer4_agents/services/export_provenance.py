from __future__ import annotations

"""Provenance manifest generation for exported case packages."""


import json
from datetime import UTC, datetime
from typing import Any

from value_fabric.shared.crypto.canonical import canonical_hash
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config.settings import get_settings


class _normalize_source_pointerResult(TypedDictModel):
    locator: Any
    pointer: Any
    type: Any

class _validate_claim_and_metric_provenanceResult(TypedDictModel):
    is_valid: bool
    violation_count: Any
    violations: Any

class build_export_provenance_manifestResult(TypedDictModel):
    deterministic_snapshot: Any
    envelope: dict[str, Any]
    provenance_schema_version: Any
    source_references: Any
    truth_object_ids: Any
    workflow_id: Any

class _extract_case_versionResult(TypedDictModel):
    version: Any

PROVENANCE_SCHEMA_VERSION = "1.0.0"


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _sort_primitive_list(values: list[Any]) -> list[Any]:
    deduped = {json.dumps(v, sort_keys=True, default=str): v for v in values}
    return [deduped[k] for k in sorted(deduped.keys())]


def _normalize_source_pointer(pointer: Any) -> dict[str, Any]:
    if isinstance(pointer, str):
        return _normalize_source_pointerResult.model_validate({"pointer": pointer}).model_dump()
    if isinstance(pointer, dict):
        return _normalize_source_pointerResult.model_validate({
            "pointer": pointer.get("pointer")
            or pointer.get("id")
            or pointer.get("uri")
            or pointer.get("url")
            or "unknown",
            "type": pointer.get("type") or pointer.get("source_type"),
            "locator": pointer.get("locator") or pointer.get("path") or pointer.get("offset"),
        }).model_dump()


    return _normalize_source_pointerResult.model_validate({"pointer": str(pointer)}).model_dump()


def _collect_truth_ids(output: dict[str, Any], metadata: dict[str, Any], case_snapshot: dict[str, Any]) -> list[str]:
    explicit_truth_ids = _first_non_empty(
        output.get("assemble_document", {}).get("case_metadata", {}).get("truth_object_ids"),
        output.get("truth_object_ids"),
        metadata.get("truth_object_ids"),
        case_snapshot.get("truth_ids"),
    )
    truth_ids = [str(v) for v in _as_list(explicit_truth_ids)]

    if not truth_ids:
        truth_refs = _first_non_empty(
            output.get("assemble_document", {}).get("case_metadata", {}).get("truth_references"),
            output.get("verify_truth_requirements", {}).get("truth_references"),
            case_snapshot.get("truth_references"),
        )
        truth_ids = [
            str(ref.get("truth_object_id"))
            for ref in _as_list(truth_refs)
            if isinstance(ref, dict) and ref.get("truth_object_id")
        ]

    return sorted(set(truth_ids))


def _collect_source_pointers(output: dict[str, Any], metadata: dict[str, Any], case_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    source_refs = _first_non_empty(
        output.get("assemble_document", {}).get("case_metadata", {}).get("source_references"),
        output.get("source_references"),
        metadata.get("source_references"),
        case_snapshot.get("source_pointers"),
        case_snapshot.get("source_references"),
    )
    normalized = [_normalize_source_pointer(pointer) for pointer in _as_list(source_refs)]
    return _sort_primitive_list(normalized)


def _extract_case_snapshot(workflow_result: dict[str, Any], metadata: dict[str, Any], case_metadata: dict[str, Any]) -> dict[str, Any]:
    raw_snapshot = _first_non_empty(
        metadata.get("case_snapshot"),
        metadata.get("snapshot"),
        case_metadata.get("snapshot"),
        workflow_result.get("case_snapshot"),
    )
    return raw_snapshot if isinstance(raw_snapshot, dict) else {}


def _extract_case_version(workflow_result: dict[str, Any], metadata: dict[str, Any], case_metadata: dict[str, Any]) -> dict[str, Any]:
    raw_version = _first_non_empty(
        metadata.get("case_version"),
        case_metadata.get("case_version"),
        workflow_result.get("case_version"),
    )
    if isinstance(raw_version, str):
        return _extract_case_versionResult.model_validate({"version": raw_version})
    return raw_version if isinstance(raw_version, dict) else {}


def _hash_canonical(payload: Any) -> str:
    """Deprecated: delegates to shared.crypto.canonical.canonical_hash()."""
    return canonical_hash(payload)


def _validate_claim_and_metric_provenance(
    claims: list[dict[str, Any]],
    metric_formulas: list[dict[str, Any]],
) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []

    for claim in claims:
        claim_id = claim.get("claim_id") or claim.get("id") or "unknown-claim"
        evidence = _as_list(claim.get("evidence_pointers"))
        if not evidence:
            violations.append(
                {
                    "type": "narrative_claim_missing_evidence",
                    "claim_id": claim_id,
                    "message": "Narrative claim must include at least one evidence pointer.",
                }
            )

    for metric in metric_formulas:
        metric_name = metric.get("metric") or metric.get("name") or "unknown-metric"
        has_formula = bool(metric.get("formula"))
        has_inputs = bool(_as_list(metric.get("inputs")))
        has_input_provenance = bool(_as_list(metric.get("input_provenance")))
        if has_formula and (not has_inputs or not has_input_provenance):
            violations.append(
                {
                    "type": "metric_missing_input_provenance",
                    "metric": metric_name,
                    "message": "Quantified metrics must include formula inputs and input provenance.",
                }
            )

    return _validate_claim_and_metric_provenanceResult.model_validate({
        "is_valid": not violations,
        "violation_count": len(violations),
        "violations": violations,
    })


def build_export_provenance_manifest(
    *,
    case_id: str,
    workflow_result: dict[str, Any],
    actor_context: RequestContext | None,
    export_id: str,
) -> dict[str, Any]:
    """Build provenance manifest JSON for case exports.

    Resolved merge preserving both:
    - richer case snapshot / version extraction
    - operational model/tool version metadata
    - legacy compatibility fields
    """
    output = workflow_result.get("output", {})
    metadata = workflow_result.get("metadata", {})
    assemble_output = output.get("assemble_document", {})

    sdes_bundle = output.get("generate_sdes", {}) or metadata.get("sdes", {})

    case_metadata = _first_non_empty(
        assemble_output.get("case_metadata"),
        output.get("case_metadata"),
        metadata.get("case_metadata"),
    ) or {}

    case_snapshot = _extract_case_snapshot(workflow_result, metadata, case_metadata)
    case_version = _extract_case_version(workflow_result, metadata, case_metadata)

    workflow_id = (
        workflow_result.get("workflow_id")
        or metadata.get("workflow_id")
        or case_snapshot.get("workflow_id")
        or case_id
    )

    truth_ids = _collect_truth_ids(output, metadata, case_snapshot)
    source_pointers = _collect_source_pointers(output, metadata, case_snapshot)

    threshold_decisions = _sort_primitive_list(
        _as_list(
            _first_non_empty(
                case_snapshot.get("threshold_decisions"),
                case_metadata.get("threshold_decisions"),
            )
        )
    )

    assumptions = _sort_primitive_list(
        _as_list(
            _first_non_empty(
                case_snapshot.get("assumptions"),
                case_metadata.get("assumptions"),
                case_metadata.get("key_assumptions"),
            )
        )
    )

    approvals = _sort_primitive_list(
        _as_list(
            _first_non_empty(
                case_snapshot.get("approvals"),
                case_metadata.get("approvals"),
            )
        )
    )

    metric_formulas = _sort_primitive_list(
        _as_list(
            _first_non_empty(
                case_snapshot.get("metric_formulas"),
                case_snapshot.get("metrics"),
                case_metadata.get("metric_formulas"),
            )
        )
    )

    narrative_claims = _sort_primitive_list(
        _as_list(
            _first_non_empty(
                case_snapshot.get("narrative_claims"),
                case_metadata.get("narrative_claims"),
            )
        )
    )

    snapshot_version = (
        case_version.get("version")
        or case_version.get("id")
        or case_snapshot.get("version")
        or case_snapshot.get("snapshot_version")
    )
    snapshot_hash = (
        case_version.get("hash")
        or case_version.get("version_hash")
        or case_snapshot.get("hash")
        or case_snapshot.get("version_hash")
    )

    deterministic_snapshot = {
        "schema_version": PROVENANCE_SCHEMA_VERSION,
        "case_id": case_id,
        "workflow_id": workflow_id,
        "truth_ids": truth_ids,
        "source_pointers": source_pointers,
        # Legacy compatibility aliases for downstream readers expecting these names.
        "truth_object_ids": truth_ids,
        "source_references": source_pointers,
        "threshold_decisions": threshold_decisions,
        "sdes_references": {
            "canonical_case_id": sdes_bundle.get("canonical_case_id"),
            "account_id": sdes_bundle.get("account_id"),
            "signals": [item.get("id") for item in sdes_bundle.get("signals", [])],
            "drivers": [item.get("id") for item in sdes_bundle.get("drivers", [])],
            "evidence": [item.get("id") for item in sdes_bundle.get("evidence", [])],
            "stakeholders": [item.get("id") for item in sdes_bundle.get("stakeholders", [])],
        },
        "model_versions": {
            "openai_model": get_settings().openai_model,
            "anthropic_model": get_settings().anthropic_model,
            "layer4_app_version": get_settings().app_version,
        },
        "tool_versions": {
            "export_document": "1.1.0",
        },
        "assumptions": assumptions,
        "approvals": approvals,
        "metric_formulas": metric_formulas,
        "narrative_claims": narrative_claims,
        "case_snapshot": {
            "version": snapshot_version,
            "version_hash": snapshot_hash,
            "persisted_snapshot_id": case_snapshot.get("id")
            or case_snapshot.get("snapshot_id"),
        },
    }

    if not deterministic_snapshot["case_snapshot"]["version_hash"]:
        deterministic_snapshot["case_snapshot"]["version_hash"] = _hash_canonical(case_snapshot)

    deterministic_snapshot["provenance_validation"] = _validate_claim_and_metric_provenance(
        claims=narrative_claims,
        metric_formulas=metric_formulas,
    ).model_dump()
    deterministic_snapshot["deterministic_fingerprint"] = _hash_canonical(
        deterministic_snapshot
    )

    return build_export_provenance_manifestResult.model_validate({
        "provenance_schema_version": PROVENANCE_SCHEMA_VERSION,
        "deterministic_snapshot": deterministic_snapshot,
        # Legacy compatibility for existing audit/event readers.
        "workflow_id": workflow_id,
        "truth_object_ids": truth_ids,
        "source_references": source_pointers,
        # Operational envelope (non-deterministic by design).
        "envelope": {
            "export_id": export_id,
            "generated_at": datetime.now(UTC).isoformat(),
            "model_versions": {
                "openai_model": get_settings().openai_model,
                "anthropic_model": get_settings().anthropic_model,
                "layer4_app_version": get_settings().app_version,
            },
            "tool_versions": {
                "export_document": "1.1.0",
            },
            "actor": {
                "user_id": actor_context.user_id if actor_context else None,
                "api_key_id": actor_context.api_key_id if actor_context else None,
                "roles": actor_context.roles if actor_context else [],
                "identity_source": actor_context.source if actor_context else "unknown",
            },
            "tenant": {
                "tenant_id": str(actor_context.tenant_id) if actor_context else None,
            },
            "timestamps": {
                "workflow_created_at": workflow_result.get("created_at"),
                "workflow_completed_at": workflow_result.get("completed_at"),
            },
        },
    }).model_dump()

