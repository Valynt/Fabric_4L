# Value Fabric Test Catalog
## Complete Inventory of Test Suite

**Generated:** April 19, 2026
**Total Test Files:** 100+
**Total Estimated Tests:** 500+

---

## Summary by Category

| Category | Files | Est. Tests | Coverage Target | Status |
|----------|-------|------------|-------------------|--------|
| Unit Tests | 50+ | 350+ | 80% | ✅ Implemented |
| Integration Tests | 20+ | 100+ | 70% | ✅ Implemented |
| Contract Tests | 15+ | 75+ | 100% API | ✅ Implemented |
| E2E Tests | 20+ | 80+ | 5 Journeys | ✅ Implemented |
| Security Tests | 10+ | 100+ | OWASP Top 10 | ✅ Implemented |
| Accessibility Tests | 5+ | 40+ | WCAG 2.1 AA | ✅ Implemented |
| Performance Tests | 8+ | 30+ | SLOs | ✅ Implemented |

---

## Backend Unit Tests

### Layer 1 - Ingestion

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
| `tests/benchmarks/test_router_performance.py` | Performance SLOs | 3 | performance |
| `tests/crawler/test_httpx_crawler.py` | HTTP crawling | 12 | unit |
| `tests/crawler/test_quality_gate.py` | Content quality | 8 | unit |
| `tests/crawler/test_smart_router.py` | Request routing | 10 | unit |

**Total Layer 1:** 16 files, ~142 tests

### Layer 2 - Extraction

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_chunker.py` | Text chunking logic | 12 | unit |
| `tests/test_extract_and_ingest_pipeline.py` | Pipeline orchestration | 10 | integration |
| `tests/test_extraction.py` | Entity extraction | 15 | unit |
| `tests/test_job_sse.py` | Server-sent events | 8 | unit |
| `tests/test_llm_extractor.py` | LLM integration | 12 | unit |
| `tests/test_ontology_alignment.py` | Ontology mapping | 8 | unit |
| `tests/test_sse_streaming_behavior.py` | Streaming edge cases | 6 | unit |
| `tests/test_sse_streaming.py` | SSE protocol | 8 | unit |
| `tests/test_tier_policy.py` | Tier enforcement | 5 | unit |

**Total Layer 2:** 9 files, ~84 tests

### Layer 3 - Knowledge

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_api.py` | API endpoint tests | 25 | integration |
| `tests/test_config_import_surface.py` | Config loading | 6 | unit |
| `tests/test_config.py` | Configuration | 8 | unit |
| `tests/test_e2e_pipeline.py` | End-to-end pipeline | 10 | integration |
| `tests/test_error_handling_integration.py` | Error handling | 8 | integration |
| `tests/test_exception_handlers.py` | Exception management | 6 | unit |
| `tests/test_exceptions.py` | Custom exceptions | 5 | unit |
| `tests/test_graphrag_endpoints.py` | GraphRAG API | 8 | integration |
| `tests/test_health_endpoints.py` | Health checks | 4 | unit |
| `tests/test_hybrid_search_api_compat.py` | Search compatibility | 6 | integration |
| `tests/test_ingestion_endpoints.py` | Ingestion API | 8 | integration |
| `tests/test_ingestion.py` | Data ingestion | 10 | integration |
| `tests/test_neo4j_integration.py` | Neo4j integration | 12 | requires_neo4j |
| `tests/test_neo4j_schema_integration.py` | Schema validation | 8 | requires_neo4j |
| `tests/test_required_field_validator.py` | Field validation | 6 | unit |
| `tests/test_retrieval.py` | Data retrieval | 8 | unit |
| `tests/test_scenario_engine.py` | Scenario simulation | 6 | unit |
| `tests/test_search_endpoints.py` | Search API | 10 | integration |
| `tests/test_value_packs.py` | Value pack operations | 8 | integration |
| `tests/test_vector_e2e.py` | Vector search | 6 | integration |
| `tests/test_versioning_registration.py` | Version management | 5 | unit |

**Total Layer 3:** 25+ files, ~161 tests

### Layer 4 - Agents

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/unit/test_workflow_state_machine.py` | State transitions | 30 | unit |
| `tests/test_accounts_api.py` | Account operations | 20 | integration |
| `tests/test_billing_service.py` | Billing logic | 18 | unit |
| `tests/test_c1_proxy.py` | Proxy functionality | 10 | integration |
| `tests/test_checkpoint_boundary.py` | Checkpoint edge cases | 12 | integration |
| `tests/test_checkpoint_resume.py` | Resume functionality | 15 | integration |
| `tests/test_checkpoint_resume_failure_paths.py` | Failure recovery | 15 | integration |
| `tests/test_code_quality.py` | Code standards | 5 | unit |
| `tests/test_crm_sync_service.py` | CRM integration | 20 | integration |
| `tests/test_feature_flags.py` | Feature flag logic | 12 | unit |
| `tests/test_health_tracker.py` | Health monitoring | 15 | unit |
| `tests/test_integration_service.py` | Integration logic | 10 | integration |
| `tests/test_interfaces_exports.py` | Interface validation | 6 | unit |
| `tests/test_langgraph_execution.py` | LangGraph workflows | 25 | integration |
| `tests/test_llm_budget_guardrails.py` | LLM cost controls | 5 | unit |
| `tests/test_llm_cost_metrics.py` | Cost tracking | 8 | unit |
| `tests/test_llm_cost_tracking.py` | Usage tracking | 10 | unit |
| `tests/test_messaging.py` | Message queuing | 18 | integration |
| `tests/test_model_registry.py` | Model management | 12 | unit |
| `tests/test_notification.py` | Notification system | 15 | unit |
| `tests/test_oidc.py` | OIDC authentication | 12 | integration |
| `tests/test_pack_variable_loader.py` | Variable loading | 10 | unit |
| `tests/test_provenance.py` | Provenance tracking | 15 | integration |
| `tests/test_tenant_rate_limits.py` | Rate limiting | 8 | unit |
| `tests/test_websocket_manager.py` | WebSocket handling | 20 | integration |
| `tests/test_workflow_controls.py` | Workflow management | 15 | integration |
| `tests/test_workflows_real_execution.py` | Real execution | 8 | integration |

**Total Layer 4:** 27 files, ~337 tests

### Layer 5 - Ground Truth

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/unit/test_ground_truth_service.py` | Evidence management | 20 | unit |

**Total Layer 5:** 1 file (additional tests needed), ~20 tests

### Layer 6 - Benchmarks

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/unit/test_benchmark_calculations.py` | Benchmark math | 15 | unit |

**Total Layer 6:** 1 file (additional tests needed), ~15 tests

---

## Root-Level Tests

### Architecture Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/arch/test_tenant_architecture.py` | Tenant isolation | 8 | arch |
| `tests/arch/test_testability_architecture.py` | Testability design | 6 | arch |

### Chaos Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/chaos/chaos-validation-suite.py` | System resilience | 5 | chaos |
| `tests/chaos/tenant-isolation-loadtest.py` | Load testing | 3 | chaos, performance |
| `tests/chaos/tenant-race-condition-test.py` | Race condition detection | 4 | chaos |

### Contract Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/contract/schema_assertions.py` | Schema validation | 6 | contract |
| `tests/contract/test_api_main_architecture.py` | API architecture | 4 | contract |
| `tests/contract/test_l2_l3_contract.py` | L2-L3 interface | 5 | contract |
| `tests/contract/test_l3_formulas_contract.py` | Formula API | 6 | contract |
| `tests/contract/test_l3_graph_contract.py` | Graph API | 5 | contract |
| `tests/contract/test_l3_value_trees_contract.py` | Value tree API | 5 | contract |
| `tests/contract/test_l4_frontend_contract.py` | Frontend API | 4 | contract |
| `tests/contract/test_l4_workflows_contract.py` | Workflow API | 5 | contract |
| `tests/contract/test_tool_manifests.py` | Tool definitions | 8 | contract |
| `tests/contract/test_entity_contract.py` | Entity contracts | 6 | contract |
| `tests/contract/test_layer3_contract.py` | Layer 3 API | 8 | contract |
| `tests/contract/test_layer5_contract.py` | Layer 5 API | 5 | contract |

**Total Contract:** 12 files, ~67 tests

### Security Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/security/test_injection.py` | Injection attacks | 15 | security |
| `tests/security/test_owasp_top10.py` | OWASP compliance | 50 | security |
| `tests/security/test_owasp_top10_complete.py` | Full OWASP suite | 80 | security |
| `tests/security/test_rbac.py` | Role-based access | 12 | security |
| `tests/security/test_security_headers.py` | HTTP security | 8 | security |
| `tests/security/test_security_misconfiguration.py` | Config security | 10 | security |
| `tests/security/test_security_smoke.py` | Security basics | 6 | security |
| `tests/security/test_shared_security_middleware.py` | Middleware tests | 8 | security |
| `tests/security/test_supply_chain.py` | Dependency security | 4 | security |
| `tests/security/test_tenant_isolation.py` | Tenant separation | 10 | security |

**Total Security:** 10 files, ~103 tests

### Performance Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/performance/test_api_latency.py` | API response times | 8 | performance |
| `tests/performance/test_entity_operations.py` | Entity performance | 6 | performance |
| `tests/performance/test_hybrid_search.py` | Search performance | 5 | performance |
| `tests/performance/test_layer3_knowledge.py` | L3 benchmarks | 6 | performance |
| `tests/performance/test_load.py` | Load testing | 4 | performance |
| `tests/performance/test_search_latency.py` | Search latency | 4 | performance |
| `tests/performance/test_throughput.py` | Throughput | 3 | performance |

**Total Performance:** 7+ files, ~30 tests

### Penetration Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/penetration/zap-full-scan.py` | OWASP ZAP scan | 1 | pentest |

### Other Root Tests

| File | Purpose | Test Count | Markers |
|------|---------|------------|---------|
| `tests/test_model_registry_integration.py` | Model registry | 12 | integration |
| `tests/gitops/test_rollouts.py` | GitOps deployment | 5 | gitops |
| `tests/evals/skills/test_evaluate_formula.py` | Formula evaluation | 6 | eval |
| `tests/evals/skills/test_semantic_search.py` | Search evaluation | 5 | eval |
| `tests/integration/test_entity_api.py` | Entity API | 8 | integration |
| `tests/integration/test_pack_integration.py` | Pack integration | 6 | integration |
| `tests/integration/billing_entitlements/test_billing_entitlements_regression.py` | Billing regression | 10 | integration |

---

## Frontend Tests

### Unit/Component Tests

| File | Purpose | Test Count | Type |
|------|---------|------------|------|
| `client/src/utils.test.ts` | Utility functions | 5 | unit |
| `client/src/api/client.test.ts` | API client | 10 | unit |
| `client/src/components/WfPrimitives.test.tsx` | WF components | 8 | component |
| `client/src/contexts/AuthContext.test.tsx` | Auth context | 6 | integration |
| `client/src/hooks/useAccounts.test.tsx` | Accounts hook | 5 | unit |
| `client/src/hooks/useAuth.test.ts` | Auth hook | 6 | unit |
| `client/src/hooks/useBenchmarks.test.ts` | Benchmarks hook | 4 | unit |
| `client/src/hooks/useBilling.test.tsx` | Billing hook | 6 | unit |
| `client/src/hooks/useDocuments.test.tsx` | Documents hook | 5 | unit |
| `client/src/hooks/useFormulaDependents.test.ts` | Dependents hook | 4 | unit |
| `client/src/hooks/useFormulas.test.ts` | Formulas hook | 6 | unit |
| `client/src/hooks/useFormulaVersions.test.ts` | Versions hook | 4 | unit |
| `client/src/hooks/useGraphQuery.test.ts` | Graph hook | 6 | unit |
| `client/src/hooks/useHealthMonitor.test.ts` | Health hook | 4 | unit |
| `client/src/hooks/useIngestion.test.ts` | Ingestion hook | 4 | unit |
| `client/src/hooks/useJobStream.test.ts` | Job stream hook | 4 | unit |
| `client/src/hooks/useModels.test.tsx` | Models hook | 5 | unit |
| `client/src/hooks/usePlatformSettings.test.tsx` | Settings hook | 4 | unit |
| `client/src/hooks/useProvenance.test.tsx` | Provenance hook | 4 | unit |
| `client/src/hooks/useValuePacks.test.tsx` | Value packs hook | 6 | unit |
| `client/src/hooks/useVariables.test.ts` | Variables hook | 4 | unit |
| `client/src/hooks/useWorkflows.test.ts` | Workflows hook | 4 | unit |
| `client/src/pages/AgentWorkflows.test.tsx` | Agent workflows | 6 | component |
| `client/src/pages/BusinessCase.test.tsx` | Business case | 5 | component |
| `client/src/pages/DecisionTrace.test.tsx` | Decision trace | 4 | component |
| `client/src/pages/EntityBrowser.contract.test.tsx` | Entity browser | 5 | contract |
| `client/src/pages/ExtractionEngine.test.tsx` | Extraction engine | 6 | component |
| `client/src/pages/formulaBuilderLogic.test.ts` | Formula logic | 8 | unit |
| `client/src/pages/GraphExplorer.test.tsx` | Graph explorer | 6 | component |
| `client/src/pages/IngestionJobs.test.tsx` | Ingestion jobs | 4 | component |

**Total Frontend Unit:** 29 files, ~147 tests

### E2E Tests

| File | Purpose | Test Count | Browsers |
|------|---------|------------|----------|
| `e2e/admin-system.spec.ts` | Admin system | 5 | All |
| `e2e/admin.spec.ts` | Admin operations | 6 | All |
| `e2e/business-case-list.spec.ts` | Business case list | 4 | All |
| `e2e/business-case.spec.ts` | Business case workflow | 5 | All |
| `e2e/command-center.spec.ts` | Command center | 4 | All |
| `e2e/decision-trace.spec.ts` | Decision tracing | 4 | All |
| `e2e/extraction-engine.spec.ts` | Extraction | 4 | All |
| `e2e/fixtures/tier-helpers.ts` | Tier test helpers | N/A | Helper |
| `e2e/formula-builder.spec.ts` | Formula builder | 5 | All |
| `e2e/graph-explorer.spec.ts` | Graph explorer | 6 | All |
| `e2e/my-models.spec.ts` | My models | 7 | All |
| `e2e/navigation.spec.ts` | Navigation | 10 | All |
| `e2e/opportunity-finder.spec.ts` | Opportunity finder | 4 | All |
| `e2e/source-configuration.spec.ts` | Source config | 3 | All |
| `e2e/value-tree-explorer.spec.ts` | Value tree | 4 | All |
| `e2e/whitespace-analysis.spec.ts` | Whitespace | 3 | All |
| `e2e/accessibility/axe-audit.spec.ts` | WCAG audit | 15 | Chrome |
| `e2e/performance/page-load.spec.ts` | Performance | 3 | Chrome |

**Total E2E:** 18 files, ~92 tests

---

## Domain Pack Tests

### AI Technology Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/ai-technology/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/ai-technology/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/ai-technology/tests/test_pack_integrity.py` | Pack integrity | 3 |

### Energy Utilities Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/energy-utilities/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/energy-utilities/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/energy-utilities/tests/test_pack_integrity.py` | Pack integrity | 3 |

### Financial Services Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/financial-services/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/financial-services/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/financial-services/tests/test_pack_integrity.py` | Pack integrity | 3 |

### Life Sciences Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/life-sciences/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/life-sciences/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/life-sciences/tests/test_pack_integrity.py` | Pack integrity | 3 |

### Manufacturing Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/manufacturing/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/manufacturing/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/manufacturing/tests/test_pack_integrity.py` | Pack integrity | 3 |

### Retail Consumer Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/retail-consumer/tests/conftest.py` | Test fixtures | N/A |
| `packs/retail-consumer/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/retail-consumer/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/retail-consumer/tests/test_pack_integrity.py` | Pack integrity | 3 |
| `packs/retail-consumer/tests/test_workflow_template.py` | Workflow | 4 |

### Software Pack

| File | Purpose | Test Count |
|------|---------|------------|
| `packs/software/tests/test_formula_execution.py` | Formula execution | 5 |
| `packs/software/tests/test_ontology_relationships.py` | Ontology | 4 |
| `packs/software/tests/test_pack_integrity.py` | Pack integrity | 3 |

**Total Domain Packs:** 22 files, ~81 tests

---

## SDK Tests

### Python SDK

| File | Purpose | Test Count |
|------|---------|------------|
| `sdk/python/tests/test_cli_search.py` | CLI search | 4 |
| `sdk/python/tests/test_cli.py` | CLI operations | 6 |
| `sdk/python/tests/test_client.py` | SDK client | 8 |
| `sdk/python/tests/test_generated_client.py` | Generated client | 5 |

**Total SDK:** 4 files, ~23 tests

---

## Test Infrastructure Files

### Python Test Infrastructure

| File | Purpose |
|------|---------|
| `pytest.ini` | Root pytest configuration with markers, coverage |
| `tests/factories.py` | Factory Boy test data factories |
| `tests/conftest.py` | Shared pytest fixtures (root) |
| `services/layer1-ingestion/tests/conftest.py` | L1 fixtures |
| `services/layer4-agents/tests/conftest.py` | L4 fixtures |
| `services/layer5-ground-truth/tests/conftest.py` | L5 fixtures |
| `tests/security/conftest.py` | Security test fixtures |
| `tests/contract/conftest.py` | Contract test fixtures |
| `tests/evals/conftest.py` | Eval test fixtures |

### Frontend Test Infrastructure

| File | Purpose |
|------|---------|
| `frontend/vitest.config.ts` | Vitest configuration |
| `frontend/playwright.config.ts` | Playwright configuration |
| `frontend/client/test/setup.ts` | Test environment setup |
| `frontend/client/src/test-utils.tsx` | React testing utilities |
| `frontend/client/src/test/mocks/handlers.ts` | MSW API mocks |
| `frontend/client/src/test/mocks/server.ts` | MSW server setup |
| `frontend/client/src/test/mocks/browser.ts` | MSW browser setup |

---

## Test Coverage Summary

### By Layer

| Layer | Unit | Integration | Contract | E2E | Security | Total |
|-------|------|-------------|----------|-----|----------|-------|
| L1 Ingestion | 120 | 20 | 5 | - | - | 145 |
| L2 Extraction | 70 | 14 | 5 | - | - | 89 |
| L3 Knowledge | 50 | 100 | 20 | - | - | 170 |
| L4 Agents | 150 | 170 | 10 | - | - | 330 |
| L5 Ground Truth | 20 | - | 5 | - | - | 25 |
| L6 Benchmarks | 15 | - | 5 | - | - | 20 |
| Frontend | 147 | - | - | 92 | - | 239 |
| Root/Shared | 30 | 50 | 67 | - | 103 | 250 |
| Domain Packs | 60 | 20 | - | - | - | 80 |
| SDK | 23 | - | - | - | - | 23 |

**Grand Total:** ~1,371 tests across 155+ files

---

## CI/CD Test Execution

### GitHub Actions Workflow

**Job:** `backend-tests`
- Unit tests: `pytest -m unit -n auto --timeout=60`
- Integration tests: `pytest -m integration --timeout=120`
- Contract tests: `pytest -m contract --timeout=60`
- Security tests: `pytest -m security --timeout=60`

**Job:** `frontend-tests`
- Unit tests: `pnpm --dir apps/web run test -- --coverage`
- Lint: `pnpm --dir apps/web run lint`
- Type check: `pnpm --dir apps/web run typecheck`

**Job:** `e2e-tests`
- E2E tests: `pnpm exec playwright test`
- Accessibility: `pnpm exec playwright test e2e/accessibility/`

**Job:** `performance-tests`
- Benchmarks: `pytest -m performance --timeout=300 -v`

---

## Test Maintenance Notes

### Recently Added

1. `services/layer4-agents/tests/unit/test_workflow_state_machine.py` (30 tests)
2. `services/layer5-ground-truth/tests/unit/test_ground_truth_service.py` (20 tests)
3. `frontend/e2e/accessibility/axe-audit.spec.ts` (15 tests)
4. `tests/security/test_owasp_top10_complete.py` (80 tests)
5. `tests/factories.py` (Factory Boy data factories)
6. `frontend/client/src/test/mocks/handlers.ts` (MSW mocks)

### Gaps Identified

1. **Layer 5** - Additional service tests needed
2. **Layer 6** - Benchmark calculation tests need expansion
3. **Frontend** - Additional component coverage for admin pages
4. **Chaos** - Expand fault injection scenarios

### Flaky Tests

None currently flagged. Monitor CI for new flaky tests.

---

## Document Information

**Maintainer:** Value Fabric Engineering
**Last Updated:** April 19, 2026
**Update Frequency:** Sprint-based
**Next Review:** May 19, 2026
