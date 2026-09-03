# Billing De-Duplication (R3: Knowledge Duplication — L4/L7)

**Branch:** `fix/billing-dedup-single-owner`
**Description:** Pick one owner for the billing money-domain, wire the other as a client or delete the dead duplicate, and make the L4 route shims honest so the divergence can never silently re-occur.

## Goal

Resolve the Critical Brooks-Lint finding R3: billing domain logic is implemented twice — L4 (`layer4-agents`) has the complete production Stripe/subscription/usage implementation; L7 (`layer7-billing`) carries a parallel, Phase-1-stub implementation with a separate database. The misleading "Phase 1 forwarding stub" docstrings in L4 make the duplication dangerous: an engineer who trusts them patches only Layer 7 while L4 keeps diverging. This plan de-duplicates to **a single owner**, wires or removes the other, and ratchets the removal so the parallel package cannot be silently reintroduced.

## Evidence (research, verified in-repo)

- **L4 `:8004` is the only real Stripe billing implementation**: `services/layer4-agents/src/layer4_agents/api/routes/billing.py` (~1300 lines) implements subscription, checkout (`checkout.Session.create mode="subscription"`), portal, cancel/update/reactivate, entitlements, webhook (IP check + `STRIPE_WEBHOOK_SECRET`), usage events, invoices, charges, revenue, balance. Persisted in `billing_*` tables (10 migrations), RLS, 20+ test files.
- **L4 is what production consumes**: frontend `useBilling` → `apiGet('l4','/billing/subscription?...')` → baseURL `/api/v1/agents` → gateway → Layer4Client → L4 :8004. No `l7` caller exists in `apps/web/src`. Gateway `BillingEventPublisher` publishes usage events to `{layer4_api_base_url}/v1/billing/events` (L4). `tests/billing/test_checkout_flow.py` certifies `services/layer4-agents/.../billing_service.py` is the checkout implementation.
- **L7 `:8008` is a Phase-1 stub with zero production consumers**: `get_subscription` returns a hardcoded free-tier default; `create_checkout`/`create_portal` raise `ServiceUnavailableError("not yet configured in L7")`. It uses separate `l7_billing_*` tables in a separate `layer7_billing` database, has **no migrations directory**, and is only wired in `docker-compose.full.yml` (+ k8s "internal", Makefile build, CI gates). No code imports `layer7_billing` as a library. Repo's own arch test (`test_legacy_billing_removal.py`) already ratchets that the previous legacy billing package (`services/billing/`, zero consumers) was deleted; the same zero-consumer argument now applies to L7.
- **Governance documents claim L4 forwards to L7 (false)** and vice-versa: ADR-023 (superseded, canonical = L7), `docs/architecture/layer7-billing.md`, COMPAT-L4-003 (L4 = "thin forwarding shims", removal target 2026-10-31), and L4's `billing_usage.py`/`billing_overages.py`/`billing_webhooks.py` docstrings ("Phase 1 forwarding stub — canonical implementation now in layer7-billing"). These assertions are prose-only; there is **no L4→L7 HTTP client anywhere** in `src/layer4_agents`.
- **The canonical OpenAPI contract** is `contracts/openapi/layer7-billing.json` (checked by `check_contract_freshness.sh`, `router_contract_gate.py`); it defines the full billing API surface (plans, usage-events, aggregates, invoices, payment-state, webhook, subscription, checkout, portal, limits, events, usage summary). L4 already implements the union of these paths.

## Recommended Direction: **L4 is canonical — delete Layer 7**

The evidence is unambiguous: L4 is the live, complete, production-consumed implementation; L7 is a zero-consumer Phase-1 stub. Completing the L7 extraction (porting ~1300 lines of real Stripe logic + a money-domain data migration + repointing frontend/gateway/contracts + moving 20 test files) is a multi-week, high-risk migration that does not fit in one PR and would put money-domain behavior at risk. Removing L7 is the DRY-compliant, behavior-preserving, single-PR move — and the same precedent already ratified for `services/billing/` (COMPAT-BILL-001).

The canonical **contract** (`contracts/openapi/layer7-billing.json`) is retained as the single spec of the billing API shape; the **runtime** becomes L4 only.

## Implementation Steps

### Step 1: Make L4 billing route docstrings honest (no behavior change) — ✅ COMPLETE
**Files:**
- [x] `services/layer4-agents/src/layer4_agents/api/routes/billing_usage.py`
- [x] `services/layer4-agents/src/layer4_agents/api/routes/billing_overages.py`
- [x] `services/layer4-agents/src/layer4_agents/api/routes/billing_webhooks.py`
- [x] `services/layer4-agents/src/layer4_agents/api/routes/billing.py` (module docstring) — verified already honest ("Production billing routes backed by Layer 4 services"), no edit required

**What:** Rewrite the module docstrings that claim "Phase 1 forwarding stub — canonical implementation now in layer7-billing" to state the truth: L4 **is** the canonical billing runtime; these routers re-register L4's own handlers (`from . import billing`). Remove any prose that instructs engineers to patch L7. This is the immediate de-fusing of the "actively dangerous" misleading claim.

**Testing:** `grep -rn "Phase 1 forwarding stub\|now in layer7-billing\|forwards to.*Layer 7" services/layer4-agents/src/layer4_agents/api/routes/` returns 0; `pytest tests/arch -k billing` passes; no route/behavior change (docstrings only), so `pytest services/layer4-agents/tests/test_billing_route_coverage.py services/layer4-agents/tests/unit/test_billing_route_characterization.py` still green.
- [x] grep returns 0 (verified)
- [x] `pytest tests/arch -k billing` → 4 passed
- [x] `test_billing_route_coverage.py` + `unit/test_billing_route_characterization.py` → 49 passed

### Step 2: Delete the duplicate `services/layer7-billing/` service and its wiring
**Files:**
- Delete: `services/layer7-billing/` (entire tree: `src/layer7_billing/`, `tests/`, `Dockerfile`, `pyproject.toml`, `pytest.ini`, `uv.lock`, `README.md`)
- Update references:
  - `infra/compose/docker-compose.full.yml` — remove `layer7-billing` service; remove `layer7_billing` from `POSTGRES_MULTIPLE_DATABASES`
  - `Makefile` — remove layer7 docker build target (L733), the `layer7-billing` entry in release image-digests loop (L738), and the context list (L743)
  - `scripts/ci/build-reproducibility-check.sh` — remove `layer7-billing` from `LAYERS`
  - `scripts/ci/check_package_manager_policy.mjs`, `scripts/ci/check_hardcoded_credentials.py`, `scripts/ci/k8s_preflight.py`, `scripts/ci/router_contract_gate.py`, `scripts/ci/run_tenant_isolation_gate.py`, `scripts/ci/supply_chain_gate.py`, `scripts/security/setup_infisical_folders.py`, `scripts/export_openapi.py`
  - `pytest.ini` — remove `services/layer7-billing/src` from `pythonpath`; keep `billing` marker
  - `.github/CODEOWNERS` — remove `# Layer 7: Billing` block (root `@value-fabric/maintainers` remains)
  - `.env.example` — remove `VITE_L7_PREFIX`, `LAYER7_DATABASE_URL`, `LAYER7_PORT` and Infisical path comments
  - `docs/` sweep (see Step 5)
- **Do NOT delete** `contracts/openapi/layer7-billing.json` — it remains the canonical billing API contract (implemented by L4).

**What:** Remove the parallel L7 implementation and strip all its deploy/test/config surface so frozen-lockfile, docker build, k8s preflight, contract gate, and tenant-isolation gate checks no longer reference it.

**Testing:** `grep -rn "layer7" --include="*.py" --include="*.yml" --include="*.yaml" --include="*.json" --include="*.sh" --include="*.mjs" --include="*.toml" --include="*.ini" .` returns only the retained contract + docs; `scripts/ci/build-reproducibility-check.sh` & `make verify-structure` pass; `make contract-tests` passes.
- [x] grep (git grep, code/config scope): remaining refs = retained contract machinery (`contracts/openapi/layer7-billing.json`, `scripts/export_openapi.py`, `scripts/ci/check_contract_freshness.sh`, `contracts/route-contracts.json`, `contracts/schema-index.json`), docs (Step 5), Step-3 test files, `apps/web/contracts/endpoint-hook-registry.json` (Step 4). No production code outside the retained contract still references `layer7_billing`.
- [x] `scripts/ci/structural_preflight.py --strict` → 0 findings (ran directly; `make` shell fork fails on this Windows host)
- [x] `scripts/ci/python_contract_lint.py --strict --baseline config/ci/python_contract_lint_baseline.json` → exit 0 (2 pre-existing MEDIUM in unrelated security tests)
- [x] `scripts/ci/check_layer1_api_main_shim_drift.py` → OK; `scripts/ci/check_shared_imports.py --strict --scope executable` → 0 findings
- [ ] `scripts/ci/build-reproducibility-check.sh` — NOT RUN (Docker daemon unavailable + Windows bash fork failure); covered by `check_deployable_service_images` Step-3 remap instead
- [ ] `make contract-tests` — runs in Step 3/6 after test remap

### Step 3: Ratchet removal + recertify the single owner
**Files:**
- `tests/arch/test_legacy_billing_removal.py` — extend to ratchet `services/layer7-billing/` must not be reintroduced and no deploy/test surface can import `layer7_billing` (mirrors existing `services/billing` ratchet)
- `tests/billing/test_checkout_flow.py` — confirm it still asserts L4 `billing_service.py` + `contracts/openapi/layer7-billing.json` (both retained); remove any L7-runtime assertions
- `tests/unit/l7/*` — delete or remap to L4 equivalents (L4 already has webhook/security/idempotency coverage)
- Other L7-referencing tests: `tests/security/test_billing_tenant_boundary.py`, `tests/security/test_hostile_tenant_endpoint_family_contracts.py`, `tests/security/test_webhook_security_p0.py`, `tests/recovery/test_restore_billing_state.py`, `tests/observability/test_telemetry_config_validation.py`, `tests/backend_integrated/test_otel_trace_receipt.py`, `tests/e2e/test_distributed_tracing.py`, `tests/ci/test_deployable_service_images.py`, `tests/ci/test_tenant_isolation_gate.py`, `tests/ci/test_bunnyshell_environment_contract.py`, `tests/contract/test_otel_instrumentation.py` — repoint to L4 where they tested L7's runtime

**What:** Add an arch ratchet (behavior-first: intended-only behavior = single billing owner) and migrate remaining tests so the suite proves the new single-owner invariant.

**Testing:** `pytest tests/arch tests/billing tests/security -k billing` passes; `tests/contract/test_billing_contracts.py` passes against L4's OpenAPI contract; `make check-behavior-contract` reflects the new intended/denied behavior.

### Step 4: Repoint the billing OpenAPI contract metadata to L4 runtime — ✅ COMPLETE
**Files:**
- [x] `contracts/openapi/layer7-billing.json` — **regenerated as a deterministic subset export of L4's app** (`scripts/export_openapi.py` L4 Billing spec → `layer7-billing.json`). 26 paths, all `/v1/billing/*`, `info.title` = "Layer 4: Billing API", `x-backend-service: layer4-agents`.
- [x] `scripts/export_openapi.py` — L4 Billing spec added to `EXPORT_SPECS`; `_filter_openapi_to_billing_subset()` implemented (path filter + info override + ownership marker); shim condition widened to include `layer7-billing.json`.
- [x] `tests/contract/test_billing_contracts.py` — **rewritten** for L4 surface: static contract==L4 runtime subset equality, only-billing-paths, L4-ownership metadata, fail-closed auth (unauthenticated → 401/403), authenticated passes gate (UUID tenant; non-UUID legacy tenants rejected when `TESTING` not set), webhook w/o `Stripe-Signature` → 422. No DB/Stripe dependency. **6 passed.**
- [x] `apps/web/contracts/endpoint-hook-registry.json` — 26 `source: "layer7-billing"` entries synchronized to match the regenerated 26 `/v1/billing/*` routes. `scripts/ci/check_endpoint_coverage.py` passes (0 missing, 0 stale, 0 orphan).

**DEVIATION from plan:** plan L71 claimed "contract path shape unchanged"; the regenerated subset export **changes the path set** (old L7 contract declared 26 different paths incl. `/v1/billing/plans`, `/usage-events`, `/usage-aggregates`, `/payment-state`, `/ready`, `/entitlements/.../decision`; L4's surface instead declares charges/invoices/reports/revenue etc). Plan L16 "L4 already implements the union of these paths" was **refuted** — L4 implements its own billing surface which is the source of truth. The freshness gate (`check_contract_freshness.sh`) requires the committed file to equal the export, so the regenerated subset is the intended replacement.

**What:** Keep the contract as the billing API source of truth but make its implementation pointer honest (L4, not L7).

**Testing:** `scripts/ci/check_contract_freshness.sh` / `scripts/export_openapi.py --check` passes; `tests/contract/test_billing_contracts.py` passes; `scripts/ci/check_endpoint_coverage.py` passes.
- [x] `python scripts/export_openapi.py --check` → 10 specs checked, all up to date
- [x] `pytest tests/contract/test_billing_contracts.py -o addopts=""` → 6 passed
- [x] `python scripts/ci/check_endpoint_coverage.py` → 0 missing, 0 stale, 0 orphan, exit 0

### Step 5: Governance + docs consistency (ADR, registry, architecture doc)
**Files:**
- [x] `docs/explanations/adr/ADR-023-billing-service-extraction.md` — add a supersession note (2026 date): L7 extraction retired 2026; canonical runtime is L4; document evidence (zero consumers, stub impl, separate empty DB)
- [x] `docs/governance/compatibility-debt-registry.md` — archive/remove COMPAT-L4-003 (L4 routes are no longer "forwarding shims"; they are canonical) and billing L7 table rows; record the removal decision
- [x] `docs/architecture/layer7-billing.md` — rewrite to reflect that billing runtime is L4 and the `layer7-billing.json` contract remains the API spec (or fold into a single "billing" architecture page)
- [x] `docs/reference/layer-runtime-path-governance.md`, `docs/core-concepts/architecture.md`, `docs/reference/service-routing-and-api-version-matrix.md`, `docs/reference/deployable-service-images.md`, `control-plane/architecture/README.md`, `.env.dev.example`, `DESIGN.md`/agent reference (`.agent` docs) — any L7-canonical claims corrected
- [x] `apps/web/src/api/client.ts` + `apps/web/src/vite-env.d.ts` — remove unused `l7` layer prefix entry (and `VITE_LAYER7_ROUTE_PREFIX`/`VITE_L7_PREFIX` env keys); drop `l7` from `LayerKey`/`VALID_LAYER_KEYS` after confirming no caller (research confirmed zero `l7` callers in `apps/web/src` — already clean, no edits needed)

**What:** Make written governance match the single-owner code reality so docs can never again misdirect an engineer to L7.

**Testing:** `make check-docs` (if present) / `pre-commit run --all-files`; `grep -rn "layer7-billing" docs/ | grep -v "docs/archive"` returns only the corrected pages.

### Step 6: Full validation gate
**Files:** none (governance)
**What:** Run the complete verification surface for a billing change: `make verify` (or the PR-checks equivalents), `make contract-tests`, targeted `pytest services/layer4-agents/tests`, frontend `pnpm --dir apps/web run typecheck && pnpm --dir apps/web run test:contracts`.
**Testing:** All gates green; diff shows no behavior change to L4 billing routes; `git grep layer7` clean except retained contract/docs.

## Decisions (resolved — user unavailable, reviewed later)

The single-PR de-duplication plan is finalized under **Option A: L4 is canonical, delete `services/layer7-billing/`**, with the `contracts/openapi/layer7-billing.json` contract retained as the billing API spec and the frontend `l7` surface removed. The harder Option B (complete the L7 extraction: port Stripe logic, migrate money-domain data, repoint consumers) is a multi-phase effort and intentionally out of scope for one PR; if the team later wants it, it should start from the code here after L4 was ratified as the single owner.

1. **Direction: Option A** — L4 canonical, delete `services/layer7-billing` (zero consumers, complete implementation, single-PR, same precedent as COMPAT-BILL-001). Option B deferred.
2. **Contract:** keep `contracts/openapi/layer7-billing.json` as the canonical billing API contract, metadata repointed to L4 runtime (Step 4). Not deleted.
3. **Frontend `l7` layer:** remove the unused prefix/config surface (zero callers verified).