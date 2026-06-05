# Test Inventory

**Generated:** April 29, 2026  
**Purpose:** Repository-wide test inventory for Autonomous Test Assurance Agent  
**Baseline Pass Rate:** 46.56% (447 passed, 197 failed, 246 skipped, 70 errors)

---

## Current Executable Suite Entrypoints

Use this table as the maintained path from a test-related issue to the canonical suite and public validation command. The generated inventory below is historical coverage context; these entrypoints are the current interfaces guarded by `pnpm docs:check`.

| Domain | Source paths | Public validation command |
| --- | --- | --- |
| Layer 1 ingestion | `services/layer1-ingestion/tests` | `make test-layer1` |
| Layer 2 extraction | `services/layer2-extraction/tests` | `make test-layer2` |
| Layer 3 knowledge | `services/layer3-knowledge/tests` | `make test-layer3` |
| Layer 4 agents | `services/layer4-agents/tests`, `tests/agents` | `make test-layer4` |
| Layer 5 ground truth | `services/layer5-ground-truth/tests` | `make test-layer5` |
| Layer 6 benchmarks | `services/layer6-benchmarks/tests` | `make test-layer6` |
| Cross-layer contracts | `tests/contract` | `make contract-tests` |
| Security and tenant isolation | `tests/security`, `tests/tenancy` | `pnpm test:security` |
| Production readiness | `tests/security`, `tests/reliability`, `tests/observability`, `tests/recovery`, `tests/release`, `tests/tenancy`, `tests/billing`, `tests/abuse`, `tests/config`, `tests/audit` | `pnpm test:production-readiness` |
| Frontend verification | `apps/web/src`, `apps/web/e2e` | `pnpm run verify:frontend` |
| Documentation and discovery | `tests/docs`, `docs/development`, `docs/testing` | `pnpm docs:check` |

---

## Summary by Layer

| Layer | Test Files | Est. Tests | Status |
|-------|-----------|------------|--------|
| Layer 1 (Ingestion) | 15 | ~120 | Needs negative tests |
| Layer 2 (Extraction) | 9 | ~70 | Needs negative tests |
| Layer 3 (Knowledge) | 28 | ~160 | Has tenant isolation tests |
| Layer 4 (Agents) | 46 | ~330 | Extensive coverage |
| Layer 5 (Ground Truth) | 6 | ~25 | Needs expansion |
| Layer 6 (Benchmarks) | 2 | ~15 | Needs expansion |
| Frontend | 47 | ~150 | Good coverage |
| E2E Tests | 18 | ~92 | Playwright-based |
| Root/Security | 37 | ~340 | Strong coverage |
| Root/Contract | 20 | ~70 | API contracts |
| Root/Integration | 10+ | ~50 | Cross-layer |
| **Total** | **238+** | **~1,371** | **Critical gap: Pass rate** |

---

## Backend Tests by Layer

### Layer 1 - Ingestion (15 files)

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/unit/test_adapters.py` | Content adapter interfaces | 10 | unit |
| `tests/unit/test_celery_tasks.py` | Background task execution | 15 | unit |
| `tests/unit/test_crawler_config.py` | Crawler configuration | 8 | unit |
| `tests/unit/test_crawler_telemetry.py` | Metrics and monitoring | 6 | unit |
| `tests/unit/test_models.py` | Data model validation | 12 | unit |
| `tests/unit/test_pdf_adapter.py` | PDF processing | 10 | unit |
| `tests/unit/test_playwright_crawler.py` | Browser automation | 15 | unit |
| `tests/unit/test_scheduler.py` | Job scheduling | 8 | unit |
| `tests/unit/test_todo_placeholder_regressions.py` | Regression prevention | 4 | unit |
| `tests/integration/test_fast_path_pipeline.py` | Pipeline integration | 6 | integration |
| `tests/integration/test_router_edge_cases.py` | Router behavior | 5 | integration |
| `tests/crawler/test_httpx_crawler.py` | HTTP crawling | 12 | unit |
| `tests/crawler/test_quality_gate.py` | Content quality | 8 | unit |
| `tests/crawler/test_smart_router.py` | Request routing | 10 | unit |
| `tests/benchmarks/test_router_performance.py` | Performance SLOs | 3 | performance |

**Total Layer 1:** 15 files, ~142 tests

### Layer 2 - Extraction (9 files)

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_chunker.py` | Text chunking logic | 12 | unit |
| `tests/test_extract_and_ingest_pipeline.py` | Pipeline orchestration | 10 | integration |
| `tests/test_extraction.py` | Entity extraction | 15 | unit |
| `tests/test_llm_cost_metrics.py` | LLM cost tracking | 8 | unit |
| `tests/test_llm_extractor.py` | LLM integration | 12 | unit |
| `tests/test_ontology_alignment.py` | Ontology mapping | 8 | unit |
| `tests/test_sse_streaming.py` | SSE protocol | 8 | unit |
| `tests/test_sse_streaming_behavior.py` | Streaming edge cases | 6 | unit |
| `tests/test_tier_policy.py` | Tier enforcement | 5 | unit |

**Total Layer 2:** 9 files, ~84 tests

### Layer 3 - Knowledge (28 files)

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_api.py` | API endpoint tests | 25 | integration |
| `tests/test_config.py` | Configuration | 8 | unit |
| `tests/test_config_import_surface.py` | Config loading | 6 | unit |
| `tests/test_dil_phase1.py` | DIL Phase 1 | 8 | integration |
| `tests/test_dil_phase2.py` | DIL Phase 2 | 8 | integration |
| `tests/test_e2e_pipeline.py` | End-to-end pipeline | 10 | integration |
| `tests/test_error_handling_integration.py` | Error handling | 8 | integration |
| `tests/test_exception_handlers.py` | Exception management | 6 | unit |
| `tests/test_exceptions.py` | Custom exceptions | 5 | unit |
| `tests/test_graphrag_endpoints.py` | GraphRAG API | 8 | integration |
| `tests/test_health_endpoints.py` | Health checks | 4 | unit |
| `tests/test_hybrid_search_api_compat.py` | Search compatibility | 6 | integration |
| `tests/test_ingestion.py` | Data ingestion | 10 | integration |
| `tests/test_ingestion_endpoints.py` | Ingestion API | 8 | integration |
| `tests/test_neo4j_integration.py` | Neo4j integration | 12 | requires_neo4j |
| `tests/test_neo4j_schema_integration.py` | Schema validation | 8 | requires_neo4j |
| `tests/test_pack_loader.py` | Pack loading | 6 | unit |
| `tests/test_query_validator.py` | Query validation | 8 | unit |
| `tests/test_required_field_validator.py` | Field validation | 6 | unit |
| `tests/test_retrieval.py` | Data retrieval | 8 | unit |
| `tests/test_scenario_engine.py` | Scenario simulation | 6 | unit |
| `tests/test_search_endpoints.py` | Search API | 10 | integration |
| `tests/test_tenant_context_extraction.py` | Tenant context | 6 | security |
| `tests/test_tenant_isolation.py` | Tenant isolation | 8 | security |
| `tests/test_tenant_read_isolation.py` | Read isolation | 6 | security |
| `tests/test_value_packs.py` | Value pack operations | 8 | integration |
| `tests/test_vector_e2e.py` | Vector search | 6 | integration |
| `tests/test_versioning_registration.py` | Version management | 5 | unit |

**Total Layer 3:** 28 files, ~190 tests (including security-focused)

### Layer 4 - Agents (46 files)

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_accounts_api.py` | Account operations | 20 | integration |
| `tests/test_analysis_routes.py` | Analysis API | 15 | integration |
| `tests/test_billing_service.py` | Billing logic | 18 | unit |
| `tests/test_business_case_claim_promotion.py` | Claim promotion | 10 | integration |
| `tests/test_c1_proxy.py` | Proxy functionality | 10 | integration |
| `tests/test_case_permissions_and_audit.py` | Permissions + audit | 15 | security |
| `tests/test_checkpoint_boundary.py` | Checkpoint edge cases | 12 | integration |
| `tests/test_checkpoint_resume.py` | Resume functionality | 15 | integration |
| `tests/test_checkpoint_resume_failure_paths.py` | Failure recovery | 15 | integration |
| `tests/test_code_quality.py` | Code standards | 5 | unit |
| `tests/test_crm_sync_service.py` | CRM integration | 20 | integration |
| `tests/test_dil_phase3.py` | DIL Phase 3 | 8 | integration |
| `tests/test_enrichment.py` | Enrichment logic | 12 | integration |
| `tests/test_export_provenance.py` | Provenance export | 10 | integration |
| `tests/test_feature_flags.py` | Feature flag logic | 12 | unit |
| `tests/test_health_tracker.py` | Health monitoring | 15 | unit |
| `tests/test_integration_service.py` | Integration logic | 10 | integration |
| `tests/test_interfaces_exports.py` | Interface validation | 6 | unit |
| `tests/test_knowledge_tool_persistence.py` | Tool persistence | 10 | integration |
| `tests/test_langgraph_execution.py` | LangGraph workflows | 25 | integration |
| `tests/test_llm_budget_guardrails.py` | LLM cost controls | 5 | unit |
| `tests/test_llm_cost_metrics.py` | Cost tracking | 8 | unit |
| `tests/test_llm_cost_tracking.py` | Usage tracking | 10 | unit |
| `tests/test_messaging.py` | Message queuing | 18 | integration |
| `tests/test_model_registry.py` | Model management | 12 | unit |
| `tests/test_notification.py` | Notification system | 15 | unit |
| `tests/test_oidc.py` | OIDC authentication | 12 | security |
| `tests/test_oidc_cleanup.py` | OIDC cleanup | 8 | security |
| `tests/test_pack_variable_loader.py` | Variable loading | 10 | unit |
| `tests/test_phase3_control_plane.py` | Control plane | 12 | integration |
| `tests/test_provenance.py` | Provenance tracking | 15 | integration |
| `tests/test_security_fixes.py` | Security fixes | 15 | security |
| `tests/test_tenant_api.py` | Tenant API | 15 | security |
| `tests/test_tenant_isolation.py` | Tenant isolation | 15 | security |
| `tests/test_tenant_lifecycle.py` | Tenant lifecycle | 10 | security |
| `tests/test_tenant_provisioning.py` | Provisioning | 12 | security |
| `tests/test_tenant_rate_limits.py` | Rate limiting | 8 | security |
| `tests/test_tiers.py` | Tier management | 10 | unit |
| `tests/test_usage_idempotency.py` | Idempotency | 10 | security |
| `tests/test_usage_service.py` | Usage tracking | 12 | unit |
| `tests/test_value_hypothesis.py` | Value hypotheses | 10 | integration |
| `tests/test_webhook_security.py` | Webhook security | 15 | security |
| `tests/test_websocket_manager.py` | WebSocket handling | 20 | integration |
| `tests/test_workflow_controls.py` | Workflow management | 15 | integration |
| `tests/test_workflows_real_execution.py` | Real execution | 8 | integration |
| `tests/unit/test_workflow_state_machine.py` | State transitions | 30 | unit |

**Total Layer 4:** 46 files, ~460 tests (extensive security coverage)

### Layer 5 - Ground Truth (6 files)

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_api.py` | API endpoint tests | 12 | integration |
| `tests/test_freshness_monitor.py` | Freshness monitoring | 8 | unit |
| `tests/test_model_registry.py` | Model registry | 10 | integration |
| `tests/test_security_fixes.py` | Security fixes | 8 | security |
| `tests/test_state_machine.py` | State machine | 10 | unit |
| `tests/unit/test_ground_truth_service.py` | Ground truth service | 20 | unit |

**Total Layer 5:** 6 files, ~68 tests

### Layer 6 - Benchmarks (2 files)

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_benchmark_api.py` | Benchmark API | 10 | integration |
| `tests/test_benchmark_edge_cases.py` | Edge cases | 8 | unit |

**Total Layer 6:** 2 files, ~18 tests

---

## Root-Level Tests

### Security Tests (37 files, ~340 tests)

**Core Security Files:**
| File | Purpose | Tests |
|------|---------|-------|
| `test_owasp_top10_complete.py` | Full OWASP Top 10 | 80 |
| `test_owasp_top10.py` | Core OWASP tests | 50 |
| `test_tenant_isolation.py` | Tenant isolation | 15 |
| `test_cross_tenant_api.py` | Cross-tenant API | 20 |
| `test_rbac.py` | Role-based access | 12 |
| `test_input_validation.py` | Input validation | 15 |
| `test_rls_enforcement.py` | RLS enforcement | 15 |
| `test_adversarial_auth.py` | Adversarial auth | 20 |
| `test_secrets_protection.py` | Secrets protection | 12 |
| `test_oidc.py` | OIDC security | 15 |
| `test_websocket_auth.py` | WebSocket auth | 15 |
| `test_tenant_boundary_fails_closed.py` | Fail-closed tests | 12 |
| `test_tenant_context_contract.py` | Context contract | 18 |
| `test_injection.py` | Injection attacks | 15 |
| `test_security_headers.py` | Security headers | 8 |
| `test_security_misconfiguration.py` | Misconfiguration | 15 |
| `test_shared_security_middleware.py` | Middleware tests | 15 |
| `test_supply_chain.py` | Supply chain | 12 |
| `test_privileged_audit.py` | Privileged access | 15 |
| `test_tenant_audit.py` | Tenant audit | 12 |

**Additional Files (17 more):** test_jwt_rotation, test_p0_5_api_key_rejection, test_p1_12_prompt_delimiters, test_p1_13_websocket_auth, test_p1_14_security_middleware, test_p1_20_xxe_prevention, test_export_tenant_access, test_knowledge_tools_tenant_isolation, test_neo4j_tenant_query_enforcement, test_security_fixes, test_security_smoke, test_tenant_lifecycle, test_tenant_mismatch, test_collection_verification, test_cross_layer_tenant

### Contract Tests (20 files, ~70 tests)

| File | Purpose |
|------|---------|
| `test_l2_l3_contract.py` | L2-L3 interface |
| `test_l3_formulas_contract.py` | Formula API |
| `test_l3_graph_contract.py` | Graph API |
| `test_l3_value_trees_contract.py` | Value tree API |
| `test_l4_frontend_contract.py` | Frontend API |
| `test_l4_workflows_contract.py` | Workflow API |
| `test_tool_manifests.py` | Tool definitions |
| `test_api_main_architecture.py` | API architecture |
| `test_entity_contract.py` | Entity contracts |
| `test_layer3_contract.py` | Layer 3 API |
| `test_layer5_contract.py` | Layer 5 API |

### Integration Tests (10+ files, ~50 tests)

| File | Purpose |
|------|---------|
| `test_entity_api.py` | Entity API integration |
| `test_pack_integration.py` | Pack integration |
| `billing_entitlements/test_billing_entitlements_regression.py` | Billing regression |
| `test_tenant_rate_limiting.py` | Rate limiting |

### Other Root Tests

| File | Purpose | Tests |
|------|---------|-------|
| `test_model_registry_integration.py` | Model registry | 12 |
| `agents/test_conversation_service.py` | Conversation | 10 |
| `agents/test_taxonomy_refactor.py` | Taxonomy | 8 |
| `arch/test_tenant_architecture.py` | Architecture | 8 |
| `arch/test_testability_architecture.py` | Testability | 14 |
| `k8s/*` (11 files) | K8s tests | ~150 |
| `performance/*` (10 files) | Performance | ~30 |
| `evals/skills/*` (17 files) | Skill evals | ~80 |

---

## Frontend Tests

### Unit/Component Tests (47 files, ~150 tests)

**Hook Tests (25 files):**
- useAccounts, useAuth, useBenchmarks, useBilling, useDocuments
- useFormulaDependents, useFormulaVersions, useFormulas
- useGraphQuery (+comprehensive, +integration, +performance, +property)
- useHealthMonitor, useIngestion, useJobStream, useL5Governance
- useModels, useOpportunities, usePlatformSettings, useProvenance
- useValuePacks, useVariables, useWorkflows

**Page Tests (10 files):**
- AgentWorkflows, BusinessCase, DecisionTrace, EntityBrowser
- ExtractionEngine, GovernancePages, GraphExplorer, IngestionJobs
- MyModels, ValuePacks, AdminPages

**Other Tests (12 files):**
- App/Router, api/client, components/WfPrimitives, contexts/AuthContext
- navigation/accountRouting, navigation/navSchema
- formulaBuilderLogic, routes/criticalFlows.smoke
- services/authClient, stores/userTierStore, utils

### E2E Tests (18 files, ~92 tests)

| File | Purpose |
|------|---------|
| `admin-system.spec.ts` | Admin system |
| `admin.spec.ts` | Admin operations |
| `auth-lifecycle.spec.ts` | Auth lifecycle |
| `business-case-list.spec.ts` | Business case list |
| `business-case.spec.ts` | Business case workflow |
| `command-center.spec.ts` | Command center |
| `decision-trace.spec.ts` | Decision tracing |
| `extraction-engine.spec.ts` | Extraction |
| `formula-builder.spec.ts` | Formula builder |
| `graph-explorer.spec.ts` | Graph explorer |
| `my-models.spec.ts` | My models |
| `navigation.spec.ts` | Navigation |
| `opportunity-finder.spec.ts` | Opportunity finder |
| `source-configuration.spec.ts` | Source config |
| `value-tree-explorer.spec.ts` | Value tree |
| `whitespace-analysis.spec.ts` | Whitespace |
| `accessibility/axe-audit.spec.ts` | WCAG audit (15 tests) |

---

## CI Gates

### Required (PR Merge Blocking)

| Gate | Workflow | Status |
|------|----------|--------|
| PR Checks | `pr-checks.yml` | Active |
| Contract Checks | `contract-checks.yml` | Active |
| Security Gates | `security-gates.yml` | Active |
| K8s Dry Run | `k8s-dry-run.yml` | Active |

### Nightly/Scheduled

| Gate | Workflow | Trigger |
|------|----------|---------|
| Integration Tests | `integration-tests.yml` | Schedule/Manual |
| Smoke Tests | `smoke-gate.yml` | PR (optional) |
| Performance Tests | `performance-load-tests.yml` | Schedule/Manual |
| Contract Drift | `contract-drift-check.yml` | Schedule |
| AI Evals | `ai-evals-pipeline.yml` | PR/Schedule |
| Chaos Testing | `chaos-testing.yml` | Schedule |

### Test Commands

```bash
# Backend tests
pytest -m unit -n auto --timeout=60
pytest -m integration --timeout=120
pytest -m contract --timeout=60
pytest -m security --timeout=60

# Frontend tests
pnpm test -- --coverage
pnpm run lint
pnpm tsc --noEmit

# E2E tests
pnpm exec playwright test
pnpm exec playwright test e2e/accessibility/
```

---

## Production Invariant Coverage Assessment

| Boundary | Test Files | Coverage | Gaps |
|----------|-----------|----------|------|
| Tenant Isolation | 15+ files | Good | Needs more negative tests |
| Authentication | 10+ files | Good | OIDC/WebSocket gaps |
| Authorization | 5+ files | Moderate | Role escalation tests needed |
| Input Validation | 5+ files | Moderate | Oversized payload tests |
| RLS Enforcement | 3+ files | Good | Cross-layer verification |
| Secrets Protection | 2 files | Moderate | Log redaction tests |
| Idempotency | 2 files | Basic | Webhook duplicate tests |
| Rate Limiting | 3+ files | Good | Burst handling tests |

---

## Critical Findings

### 1. Pass Rate Crisis
- **Current:** 46.56% pass rate
- **Failed:** 197 tests
- **Skipped:** 246 tests
- **Errors:** 70 tests

### 2. High-Value Targets for Phase 4

**P0 (Block Release):**
- Tenant isolation negative tests
- Auth bypass tests
- RLS cross-tenant verification

**P1 (Core Coverage):**
- Input validation boundary tests
- Webhook idempotency tests
- Frontend route guard tests
- Secrets in logs tests

### 3. Test File Health
- **Strong:** L4 Agents (46 files), Security (37 files)
- **Weak:** L6 Benchmarks (2 files), L5 Ground Truth (6 files)
- **At Risk:** High skip count suggests flaky/pending tests

---

## Next Steps (Phase 2)

1. Extract production invariants from code
2. Map invariant enforcement points
3. Identify specific test gaps per boundary
4. Build prioritized gap matrix
