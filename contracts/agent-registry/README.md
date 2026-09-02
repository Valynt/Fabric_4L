# Agent Registry Contracts

This directory is the **semantic source of truth** for Layer 4 agent behavior. Phase 1 established the registry without changing runtime behavior; **Phase 2** adds a compatibility matrix consumed by runtime, AG-UI, lint, and CI validation in warning mode. The registry records the minimum contract metadata needed to detect architectural drift in agents, prompts, reasoning policies, tools, workflows, memory references, and semantic event envelopes.

## Directory Structure

| Path | Purpose |
|---|---|
| `schemas/` | JSON Schema contracts for registry documents (`tool-registry.schema.json`, `skill.schema.json`, …). |
| `agents/manifest.json` | Canonical production Layer 4 agent roster and expected decision envelopes. |
| `compatibility-matrix.json` | Phase 2 semantic-contract compatibility matrix covering agent, prompt, tool, workflow, memory, and AG-UI event envelope versions. |
| `tools/manifest.json` | Centralized tool interface registry mapped to `contracts/tool-manifests/*.json`, including per-tool `tenant_scope`. |
| `prompts/` | Versioned prompt metadata and changelog evidence, one entry per runtime prompt under `services/layer4-agents/prompts/**/v1/*.md`. |
| `skills/` | Skill registry entries keyed by the Layer 4 skill manifests under `services/layer4-agents/skills/*.md`. |
| `reasoning-policies/` | Confidence, evidence, escalation, and allowed-tool policy contracts. |
| `workflows/` | Workflow state-machine entries with states, transitions, and invariants. |

The compatibility matrix intentionally starts with `enforcement_default: "warn"`. Runtime validators and frontend event schemas surface semantic-contract gaps without blocking execution until strict enforcement is explicitly promoted through the governance process.

## Layer 4 Runtime Model Selectors

Layer 4 runtime selectors must remain aligned with contract-governed model inventory. Current selectors approved for runtime defaults and fallback:

- `gpt-4`
- `gpt-4o`
- `claude-3-sonnet-20240229`

## Tool `tenant_scope`

Every tool in `tools/manifest.json` carries a `tenant_scope` drawn from the
canonical four-value enum shared with the event catalog and the Layer 4
OpenAPI `x-tenant-scope` extension:

- `TENANT` — tool reads/writes tenant-owned data and must be called with a
  tenant context (the default for almost all tools).
- `TENANT_AND_BILLING_ACCOUNT` — tool may touch billing-account-scoped data
  in addition to tenant data.
- `GLOBAL` — tool is not tenant-scoped (e.g. platform metadata, model
  inventory lookups).
- `SYSTEM` — tool is platform/system level and only reachable through
  orchestration, never user-invoked.

`tenant_scope` extends the existing `tenant_required: true` provenance
requirement: a `TENANT`-scoped tool must be invoked with `tenant_id` present
in its provenance block. `check_agent_registry.py` emits a blocking error when
a tool entry is missing `tenant_scope` or uses a value outside the enum.

## Skill Registry

`skills/` holds one entry per Layer 4 skill manifest under
`services/layer4-agents/skills/*.md`, keyed by the manifest filename. Each
entry records `skill_path`, the owning `tool_name`, `description`, `inputs`,
`outputs`, and `governance`, and validates against
`schemas/skill.schema.json`. The registry is cross-checked against the
runtime directory so skills cannot drift: any runtime skill without a
registry entry is reported as a drift warning (blocking under `--strict`).

## Strict Mode and Runtime Drift Cross-Check

`check_agent_registry.py` statically validates every registry document and
then cross-checks the registries against runtime artifacts:

- Every runtime prompt under `services/layer4-agents/prompts/**/v1/*.md` must
  have a matching entry in `prompts/`.
- Every runtime skill under `services/layer4-agents/skills/*.md` must have a
  matching entry in `skills/`.

Unregistered runtime files are reported as drift warnings in normal mode and
as hard failures under `--strict`. CI runs the validator in strict mode
(`AGENT_REGISTRY_STRICT=1` or `--strict`), so prompt and skill drift cannot
pass CI.

## Change Discipline

Registry changes are governed by `contracts/GOVERNANCE.md`. Prompt,
reasoning-policy, workflow, and tool-interface changes must carry
changelog or migration notes and remain compatible with the existing
Contract Council RFC process. CI validation initially runs in
warning mode so teams can close coverage gaps before enforcement is
promoted to blocking.

## Validation

Run the registry contract validator from the repository root. The same command validates the Phase 2 `compatibility-matrix.json` and emits warnings when registered agents and compatibility entries drift:

```bash
python scripts/ci/check_agent_registry.py
```

Use strict mode when preparing promotion from warning-only coverage checks to
blocking enforcement:

```bash
python scripts/ci/check_agent_registry.py --strict
```
