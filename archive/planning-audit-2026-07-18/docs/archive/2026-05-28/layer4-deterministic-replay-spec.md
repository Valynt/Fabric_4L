# Layer 4 Deterministic Replay Specification

## Purpose

This specification defines how Layer 4 workflow checkpoint snapshots are compared for deterministic replay validation across restart and retry scenarios.

## Canonicalized Fields (Must Match Across Replays)

The following semantic fields MUST be identical after replay normalization:

- `workflow.state_transitions`: ordered transition sequence and status edges.
- `workflow.tool_decisions`: ordered tool-selection and decision records.
- `workflow.structured_outputs`: structured result payload consumed downstream.
- `workflow.status`: terminal workflow status used for completion gating.
- `serialization.format` and `serialization.version`: snapshot wire contract.

Any mismatch in these fields is a deterministic replay failure.

## Allowed Non-Deterministic Fields and Normalization

The following fields are allowed to vary and are normalized before comparison:

- Timestamps: `created_at`, `updated_at`, `started_at`, `completed_at`, `resumed_at`, `*_timestamp`
- Correlation and tracing identifiers: `trace_id`, `span_id`, `request_id`, `run_id`, `checkpoint_id`, `event_id`, `idempotency_key`
- UUIDv4 string values appearing in scalar fields

Normalization rules:

1. Known non-deterministic keys are replaced with `"<normalized:<field_name>>"`.
2. ISO-8601 timestamp scalar values are replaced with `"<normalized:timestamp>"`.
3. UUIDv4 scalar values are replaced with `"<normalized:uuid-v4>"`.
4. Mapping keys are sorted recursively before comparison.

## Checkpoint Snapshot Serialization Contract

Snapshot comparison assumes:

- `serialization.format = "json"`
- `serialization.version = "1.0"`

Future serialization versions MUST retain compatibility adapters in replay tests, or explicitly version-gate determinism assertions.

## WS3 Gate Requirement

WS3 completion is gated on stable replay outcomes:

- Baseline run and replayed run after restart/retry must pass semantic-equivalence comparison.
- Replay gate fails closed when canonicalized fields diverge after normalization.
