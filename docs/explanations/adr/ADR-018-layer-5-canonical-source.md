# ADR-018: Layer 5 Canonical Source

## Status

Accepted

## Context

Layer 5 historically existed in both `value_fabric/layer5` and
`services/layer5-ground-truth/src/layer5_ground_truth`. Duplicated runtime code
creates contract drift, especially for truth-object validation, model registry
tables, and tenant-scoped database access.

## Decision

`services/layer5-ground-truth/src/layer5_ground_truth` is the canonical Layer 5
runtime source. `value_fabric/layer5` remains a temporary compatibility shim
only. Compatibility modules must re-export canonical modules and must not
contain independent implementation bodies or `sys.path` mutation.

## Consequences

- Docker, Compose, tests, and imports should target the canonical service package.
- CI must keep the compatibility tree shim-only.
- Shim removal requires a separate deprecation window and import telemetry.
- New Layer 5 implementation code must not be added under `value_fabric/layer5`.
