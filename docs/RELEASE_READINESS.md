# Release Readiness — Enterprise B2B SaaS Candidate

Repository: `bmsull560/Fabric_4L` (Value Fabric)  
Branch: `agent/enterprise-release-20260618-075002`  
Generated: 2026-06-18  
Owner: Autonomous release engineer

> This document tracks the transformation of the existing product into a defensible, production-packaged enterprise B2B SaaS release candidate. It is updated continuously as work progresses.

## 1. Baseline

Initial validation run before major changes:

| Gate | Command | Result | Notes |
|------|---------|--------|-------|
| Lint (backend) | `make lint` | **PASS** | No ruff errors |
| Typecheck (backend) | `make typecheck` | **PASS** | Fixed 42 mypy errors in `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py` |
| Typecheck (frontend) | `pnpm --dir apps/web run typecheck` | **PASS** | `tsc --noEmit` clean |
| Lint (frontend) | `pnpm --dir apps/web run lint` | **PASS** | ESLint clean |
| Contract tests | `make contract-tests` | **PASS** (66 passed, 9 skipped) | 262 warnings, mostly FastAPI `regex` deprecation and SQLAlchemy legacy `Query.get()` |
| Frontend unit tests | `pnpm --dir apps/web run test --run` | **FAIL** (9 failed, 6 files) | See `frontend-test-failures` below |
| Audit tests | `pnpm run test:audit` | **PASS** (6 passed) | |
| L1 typecheck | `make typecheck-layer1` | **PASS** | |

### Frontend test failures (baseline)

1. `src/pages/admin/AdminPages.test.tsx` — multiple API-Keys tabs found; clipboard mock failure (`Cannot set property clipboard of #<Navigator>`).
2. `src/api/__tests__/contract/accounts-create.contract.test.ts` — inline snapshot not initialized (`SnapshotClient.setup()` missing).
3. `src/api/__tests__/contract/openapi-drift.contract.test.ts` — `layer2-extraction.json` path `/v1/extract` not in allowed route list.
4. `src/components/ui/virtual-list.visual.test.tsx` — 3 obsolete snapshots.

### Security / dependency audit

The `reports/audit-2026-06-18/` bundle was produced during a prior automated run. Re-running `pnpm run test:audit` passes. The stale report showed `pnpm_audit` with 3 high / 11 moderate / 6 low JS vulnerabilities, `pip_audit` failure, and `bandit` exit code 1. These need refreshed, actionable triage before release.

## 2. Product & Architecture Findings

### What the product is

Value Fabric is an enterprise agentic SaaS platform that transforms unstructured enterprise data into structured knowledge via a 6-layer pipeline:

- **L1 Ingestion**: canonical source intake (notes, web, audio, CRM, PDF, meeting) with idempotency, outbox, and tenant isolation.
- **L2 Extraction**: ontology-guided extraction of signals and value drivers.
- **L3 Knowledge**: Neo4j knowledge graph + semantic layer.
- **L4 Agents**: LangGraph workflows, ROI analysis, business cases, approvals.
- **L5 Ground Truth**: TruthObject validation and evidence decisions.
- **L6 Benchmarks**: peer comparison and statistical validation.

Frontend is React/Vite/TanStack Query/Zustand/Tailwind/shadcn/ui.

### Critical user journeys (to be verified end-to-end)

1. Tenant onboarding / workspace creation
2. User sign-in / sign-out / session lifecycle
3. L1 source ingestion → L2 extraction → L3 graph → L4 hypothesis/ROI/case → L5 approval → L6 benchmark
4. Admin: billing, API keys, user/role management, health monitoring
5. Security: tenant isolation, RBAC, audit logging

### Current gap register (P0/P1/P2)

| Priority | Gap | Evidence | Status |
|----------|-----|----------|--------|
| **P0** | Frontend unit tests failing | 9 failures across 6 files | Open |
| **P0** | Dependency/security audit needs triage | `pnpm_audit` high findings, `pip_audit`, `bandit` | Open |
| **P1** | OpenAPI drift: `/v1/extract` path not allowed | `openapi-drift.contract.test.ts` | Open |
| **P1** | Virtual list obsolete snapshots | `virtual-list.visual.test.tsx` | Open |
| **P1** | L1 source routes mypy SQLAlchemy typing | Fixed via `_orm_to_response` helper | **Resolved** |
| **P2** | End-to-end L1-L6 golden path not smoke-tested | `scripts/validation/l1-l6-golden-path-curl.sh` exists | Open |

## 3. Implemented Changes

### Type-check / code quality

- `services/layer1-ingestion/src/layer1_ingestion/api/source_routes.py`
  - Added generic `_orm_to_response(model_class, instance)` helper to map SQLAlchemy ORM instances to Pydantic response models without mypy `Column[...]` errors.
  - Replaced manual `SourceDetailResponse`, `SourceVersionResponse`, and `IngestionRunResponse` constructors with the helper.
  - Added `cast` for `version_number` and `revision` fields.
  - Added type ignores for SQLAlchemy ORM attribute assignments (`run.status`, `run.completed_at`).

### Tooling fixes (from previous session)

- `tests/tools/test_tool_result_contract.py` and `tests/tools/test_tool_tenant_boundaries.py`: canonical imports, mock fixes, pyright assertions.
- `apps/web/src/hooks/useExtractionResults.ts`: restored `withApiError` wrapper.
- `docker-compose.full.yml`: restored Redis password validation.
- `apps/web/src/features/intelligence-workspace/components/EvidenceTabContent.tsx`: removed dead state.
- `apps/web/src/hooks/useValueSignals.ts`: removed dead `useReviewSignal`.
- `services/layer4-agents/src/layer4_agents/tools/calculation_tools.py`: Python 3.14 `ast.Num` compatibility.

## 4. Validation Commands

```bash
# Static gates
make lint
make typecheck
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run lint

# Contract / audit
make contract-tests
pnpm run test:audit

# Frontend unit
pnpm --dir apps/web run test --run

# Integration / smoke (requires live stack)
make test-backend-integrated-validation
make test-backend-integrated-release-smoke
```

## 5. Remaining Work

1. Fix the 9 frontend unit-test failures.
2. Refresh and triage the security/dependency audit (`pnpm audit`, `pip-audit`, `bandit`).
3. Resolve the OpenAPI drift contract failure.
4. Update/remove obsolete virtual-list snapshots.
5. Run the L1-L6 golden-path curl smoke test against a live stack.
6. Complete the remaining sections of this document as work proceeds.

## 6. Assumptions

See `docs/ASSUMPTIONS.md`.

## 7. Residual Risks

- The product is not yet fully smoke-tested end-to-end in a clean environment.
- Dependency vulnerabilities have not been triaged for exploitability.
- Some contract tests are skipped; their release impact must be reviewed.

---

Status: **NO-GO** until P0 frontend test failures and security audit findings are resolved.
