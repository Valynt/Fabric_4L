# L2 Component — contracts

## Purpose

Versioned cross-surface contracts (`contracts/`). The machine-readable agreement between
frontend, gateway, layers, agents, and tools. Runtime source, published specifications,
generated clients, and consumers must agree; breaking changes require an approved version
transition. No undocumented route or event enters production.

## Owned journey stages / behaviors

Cross-cutting — constrains every behavior's boundary surfaces:

- BEH-03 — `contracts/tool-manifests/graph_traverse.json`
- BEH-04 — `contracts/tool-manifests/calculate_roi.json`, `evaluate_formula.json`,
  `sensitivity_analysis.json`
- BEH-06 — `contracts/tool-manifests/generate_business_case.json`
- BEH-07 — `contracts/tool-manifests/assemble_document.json`, `generate_section.json`,
  `document_export.json`
- Frontend boundary — `contracts/frontend/01-api-boundary-contract.md`,
  `02-type-synchronization-contract.md`, `03-hook-architecture-contract.md`

## Key verified paths

- Root: `contracts/README.md`, `GOVERNANCE.md`, `behavior-contract.yaml`,
  `drift-allowlist.yaml`, `route-auth-allowlist.yaml`, `route-contracts.json`,
  `layer4-route-contract-matrix.json`, `schema-index.json`, `value-signal.json`
- `contracts/openapi/` — `fabric-4l-api.json` plus per-layer specs (`layer1-ingestion`,
  `layer2-extraction`, `layer2-5-signal-refinery`, `layer3-knowledge`, `layer4-agents`,
  `layer5-ground-truth`, `layer6-benchmarks`, `privacy-dsar`, `signals`)
- `contracts/jsonschema/` — `signal.json`, `entity.json`, `claim-types.v1.json`,
  `agent-response-envelope.json`, `billing-domain.schema.json`, `dsar-request.schema.json`,
  `layer3-entity-resolution-contract.json`,
  `layer4-workflow-replay-event-envelope-v1.schema.json`, `system-route-health.json`, `workflows/`
- `contracts/tool-manifests/` — 32 tool JSONs
- `contracts/agent-registry/` — `compatibility-matrix.json`, `agents/`, `prompts/`,
  `reasoning-policies/`, `schemas/`, `tools/`, `workflows/`
- `contracts/auth/`, `config-policy/`, `deprecations/`, `observability/`, `rfcs/`

## Dependencies

- Produced and consumed by every service and `apps/web`. Owned change process in
  `contracts/GOVERNANCE.md`.
- `packages/platform-contract/` (`schemas/`, `scripts/`, `CONTRACT.md`) enforces the platform
  contract; `packages/eslint-plugin-fabric-contracts/` lints contract usage.

## Primary gates

- **AG-03** contract-compliance — this component IS the contract surface: OpenAPI drift,
  schema validation, deprecation enforcement.
- **AG-01** repository-integrity — generated-file drift detection, canonical configuration.
