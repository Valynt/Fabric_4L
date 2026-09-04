# Summary — Contract-First Agent Tool Registry

## Outcome

The Layer 4 service now has an authoritative, contract-first **Agent Tool Registry**: human-authored YAML tool manifests carry a full governance envelope (side-effect class, audit obligations, data-access controls, principal restrictions, approval/confirmation requirements, tenant binding), are validated against canonical JSON Schemas on CI, compiled into a pinned, deterministic JSON index, and consumed read-only by the L4 runtime for policy-driven exposure filtering.

**Verdict: PASS** on iteration 1. All acceptance criteria (AC1–AC9) verified by the Inspector.

## What was achieved (mapped to acceptance criteria)

| AC | Deliverable | Status |
| --- | --- | --- |
| AC1 | Canonical `tool-manifest.schema.json` + `registry.schema.json`, registered in `contracts/schema-index.json` | ✅ |
| AC2 | Six billing example manifests validate cleanly (6/6) | ✅ |
| AC3 | `billing-agent-policy.yaml` + `general-agent-policy.yaml` | ✅ |
| AC4 | Pydantic `tools_manifest` package matches schema field-for-field (26 top-level + nested) | ✅ |
| AC5 | `validate_tool_registry.py` fails closed with structured report + CI exit code | ✅ |
| AC6 | `generate_tool_index.py` produces pinned deterministic index (snapshot `c6e7d65a67b42af5`) | ✅ |
| AC7 | `make check-tool-registry` + `.github/workflows/pr-checks.yml` wiring | ✅ |
| AC8 | L4 runtime consumes registry; `filter_tools_for_agent` policy filtering | ✅ |
| AC9 | Behavior-first tests: `tests/contract/test_tool_registry.py` 20/20; existing L4 tool-registry tests 17/17; ruff + mypy clean | ✅ |

## Iteration history

- **Iteration 1**: Builder delivered the full registry (schemas, manifests, policies, loader/validator, generator, Makefile/CI wiring, L4 facade, tests). Inspector verified all ACs -> **PASS**. No rework required.

## Key items raised and how they were resolved

- **AC9 test-data bug** (during Builder): `status: "active"` lowercase vs schema `ACTIVE`; case-sensitive substring assert. Fixed to `"ACTIVE"` + case-insensitive match.
- **mypy `no-any-return`**: `json.load`/`yaml.safe_load` typed via `cast("dict[str, Any]", ...)`.
- **loader shadowing**: imported Pydantic `RegistryValidationReport` under alias to keep the local working-report class.
- **Inspector note (non-blocking)**: `scripts/ci/validate_tool_registry.py` warns that `contracts/auth/action-catalog.json` is missing, so action_id cross-checks are skipped. Recommend confirming the canonical action-catalog location as a follow-up.

## Recommendations

- **Confirm the action-catalog location** so AC5's action_id cross-reference runs unconditionally (currently skipped when the file isn't found).
- **Migrate or grandfather** the 32 legacy `contracts/tool-manifests/*.json` files to the new YAML format (explicitly out of scope this round).
- **Reconcile `harness/ToolContractRegistry`**: consider a compatibility seam or deprecation path now that the registry is authoritative (out of scope this round).
- **Prod behavior-readiness**: the AC9 suite lives under `tests/contract/`; wire registry behaviors into the behavior-readiness/commit-ladder gates for ongoing drift protection.

## User impact

The platform now has a single source of truth for tool exposure decisions: governance metadata can no longer drift from enforcement. Agents/MCP clients are exposed only to validated, policy-filtered tools with enforced audit, tenant, approval, and data-access envelopes — failing closed on violations — while L4 startup stays fast and deterministic via the pinned generated index.