# Goal: Implement the Contract-First Agent Tool Registry

## User Request

> **Tool Registry** | Every agent tool: schema, scope, restrictions, audit hook | Agents team | consumed by L4 `contexts/tools` | contracts/tool-manifests
>
> Build an authoritative governance envelope for every callable tool exposed to agents/MCP clients, with side-effect classification, audit obligations, tenant-isolation controls, approval requirements, and policy-driven exposure filtering. YAML human-authored manifests → validated → compiled JSON index → consumed by Layer 4 runtime. Contract-first: schemas are the source of truth; tests are the executable contract.

## Refined Goal

Deliver a contract-first **Agent Tool Registry** for Value Fabric's Layer 4 (agents) service. The registry is the single source of truth for tool exposure decisions: human-authored YAML tool manifests carry a governance envelope (side-effect class, audit obligations, data-access controls, principal restrictions, approval/confirmation requirements, tenant binding), are validated against a canonical JSON Schema on CI, get compiled into a pinned JSON index, and are consumed read-only by the L4 runtime for policy-driven exposure filtering. Every production-critical behavior must have a passing test; invalid manifests and denied exposures must fail closed.

## Acceptance Criteria

- [ ] AC1 — **Canonical schemas exist and are authoritative**: `contracts/tool-manifests/tool-manifest.schema.json` defines the single-manifest governance envelope; `contracts/tool-manifests/registry.schema.json` defines the compiled registry index. Both are registered in `contracts/schema-index.json`.
- [ ] AC2 — **Example billing manifests validate**: the six `contracts/tool-manifests/billing/*.tool.yaml` manifests (invoice-explain, charge-forecast, subscription-change-draft, credit-request-draft, refund-request-draft, reconciliation-analysis) validate cleanly against `tool-manifest.schema.json`.
- [ ] AC3 — **Policy definitions exist**: `contracts/tool-manifests/policies/billing-agent-policy.yaml` and `general-agent-policy.yaml` declare allowed/denied side-effect sets per agent class.
- [ ] AC4 — **Pydantic loader/validator matches the on-disk schema**: the `tools_manifest` package (models + loader) uses the SAME field names and structure as `tool-manifest.schema.json` (`version`/`status`/`owner`, `principal_types`, `tenant_binding.client_supplied_tenant_authoritative`, `resource_resolver` object, `approval_requirement`, `data_controls.allowed/prohibited`, `runtime.timeout_ms`). No field-name drift between Pydantic models and JSON schema.
- [ ] AC5 — **Validator enforces governance rules**: `scripts/ci/validate_tool_registry.py` (wrapping the loader) fails closed on: invalid manifest vs schema; mutating tools missing `idempotency`/`approval_requirement`/`audit`; `IRREVERSIBLE` tools exposed to `billing-copilot`; and resource resolvers permitting caller-selected tenant authority. Emits a structured pass/fail report with violations and a CI exit code.
- [ ] AC6 — **Generator produces a pinned L4 index**: `scripts/ci/generate_tool_index.py` produces `contracts/tool-manifests/generated/layer4-tool-index.json` (and action-coverage) that includes only validated manifests, pins a registry version + SHA, and is deterministic.
- [ ] AC7 — **Makefile/CI gates wired**: `make check-tool-registry` runs validator + generator and fails on violations or generated-index drift; the target is wired into `.github/workflows/pr-checks.yml`.
- [ ] AC8 — **L4 runtime consumes the registry**: `layer4-agents` loads the generated index (via the `tools_manifest` loader) and filters tool exposure by agent principal class and policy; no ad-hoc governance paths bypass the registry.
- [ ] AC9 — **Tests pass**: behavior-first tests cover validator acceptance + denial, policy filtering (billing-copilot cannot see IRREVERSIBLE), action_id cross-reference, tenant-authority rejection, audit-obligation enforcement, and generated-index inclusion/exclusion. Relevant `pytest` suites and `ruff`/`mypy` checks for changed layer-4 code pass.

## Scope Boundaries

**In scope:**
- JSON Schemas for manifests and registry index (and schema-index registration).
- Billing example manifests + policy definitions.
- The `tools_manifest` Pydantic package (alignment with schema), validator, and generator.
- `make check-tool-registry` + `pr-checks.yml` wiring.
- L4 integration via generated index consumption and policy filtering.
- Behavior-first tests for all of the above.

**Out of scope:**
- Migrating the 32 legacy `contracts/tool-manifests/*.json` files to YAML (grandfather or leave; do not block on it).
- Changing Layer 7 authorization semantics — the registry governs exposure, not authorization; `May this principal perform refund.request` remains Layer 7's job.
- Rewriting `harness/ToolContractRegistry` unless it directly conflicts with the new registry; prefer a compatibility seam.
- Introducing a new UI library or frontend changes.

## Applicable Project Conventions

**Quality gate commands (narrowest first):**
- `pytest services/layer4-agents/tests/ -m "unit or contract_static"` — layer-4 unit/contract tests
- `make lint-layer4` / `make typecheck-layer4` — ruff + mypy for layer 4
- `python scripts/ci/validate_tool_registry.py` and `python scripts/ci/generate_tool_index.py` — registry gates
- `make check-tool-registry` — validated registry + generated index up-to-date
- `make verify` — full gate (may be too heavy; run targeted checks first)

**Commit convention:**
- Conventional commits: `type(scope): description` (≤72 chars title).
- Marker in title: Builder `[B]`, Inspector `[I]`.
- Trailer: `Assisted-by: OpenAI:GPT-5.6 Luna` (Builder) / `Assisted-by: OpenAI:GPT-5.6 Sol` (Inspector).

**Guidelines:**
- `.agent/AGENTS.md`, `.agent/protocols/permissions.md`
- `docs/governance/behavior-first-testing.md` (behavior-first: intended passes, denied fails, failure modes explicit)

**Rules:**
- Fail closed for security, tenant isolation, and governance paths.
- Preserve tenant context: never accept caller-selected tenant authority; tenant_id comes from authenticated context.
- Do not weaken audit obligations or approval requirements to make tests pass.
- YAML for human-authored manifests; compiled JSON for L4.
- No runtime mutation of the registry; changes go through manifest → validate → generate → deploy.

## Notes for the Inspector

- **Known pre-existing drift to verify is resolved**: the `tools_manifest/models.py` authored earlier uses field names (`revision`, `agent_types`, `resource_resolver` as string, `approval`, `data_controls.tenant_scoped`, `timeout_budget_ms`) that do NOT match the on-disk `tool-manifest.schema.json` (`version`/`status`/`owner`, `principal_types`, `tenant_binding.client_supplied_tenant_authoritative`, `resource_resolver` object, `approval_requirement`, `data_controls.allowed/prohibited`, `runtime.timeout_ms`). AC4 requires them to align.
- Inspector must verify AC9 by actually running the targeted gates, not by static inspection alone.
- The current worktree is on branch `valyntxyz-feat/agent-tool-registry`; uncommitted work already exists under `contracts/tool-manifests/`, `scripts/ci/`, and `services/layer4-agents/src/layer4_agents/tools_manifest/` plus modifications to `Makefile`, `.github/workflows/pr-checks.yml`, and `contracts/schema-index.json`.