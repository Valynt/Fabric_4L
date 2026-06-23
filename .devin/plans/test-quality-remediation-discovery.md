# Test Quality Remediation - Discovery Output

Generated: 2026-04-15

## Repository Testing Landscape

### Frameworks by Layer

| Layer | Framework | Test Count | Coverage Tool |
|-------|-----------|------------|---------------|
| Layer 1 (Ingestion) | pytest | 9 unit tests | pytest-cov |
| Layer 2 (Extraction) | pytest | 8 tests | pytest-cov |
| Layer 3 (Knowledge) | pytest | 16 tests | pytest-cov |
| Layer 4 (Agents) | pytest | 15+ tests | pytest-cov |
| Cross-layer Tests | pytest | 33 tests | pytest-cov |
| Frontend | Vitest | 24 unit tests | v8 |
| Frontend E2E | Playwright | 9 spec files | N/A |

### Python Test File Locations

**Layer 1 - Ingestion (9 files)**:
- `tests/unit/test_adapters.py`
- `tests/unit/test_celery_tasks.py`
- `tests/unit/test_crawler_config.py`
- `tests/unit/test_crawler_telemetry.py`
- `tests/unit/test_models.py`
- `tests/unit/test_pdf_adapter.py`
- `tests/unit/test_playwright_crawler.py`
- `tests/unit/test_scheduler.py`
- `tests/unit/test_todo_placeholder_regressions.py`

**Layer 2 - Extraction (8 files)**:
- `tests/test_chunker.py`
- `tests/test_extract_and_ingest_pipeline.py`
- `tests/test_extraction.py`
- `tests/test_job_sse.py`
- `tests/test_llm_extractor.py`
- `tests/test_ontology_alignment.py`
- `tests/test_sse_streaming.py`
- `tests/test_tier_policy.py`

**Layer 3 - Knowledge (16 files)**:
- `tests/test_api.py`
- `tests/test_config.py`
- `tests/test_config_import_surface.py`
- `tests/test_e2e_pipeline.py`
- `tests/test_error_handling_integration.py`
- `tests/test_exception_handlers.py`
- `tests/test_exceptions.py`
- `tests/test_graphrag_endpoints.py`
- `tests/test_health_endpoints.py`
- `tests/test_hybrid_search_api_compat.py`
- `tests/test_ingestion.py`
- `tests/test_ingestion_endpoints.py`
- `tests/test_neo4j_integration.py`
- `tests/test_neo4j_schema_integration.py`
- `tests/test_required_field_validator.py`
- `tests/test_scenario_engine.py`
- `tests/test_search_endpoints.py`
- `tests/test_vector_e2e.py`
- `tests/test_versioning_registration.py`

**Layer 4 - Agents (15+ files)**:
- `tests/test_accounts_api.py`
- `tests/test_billing_service.py`
- `tests/test_c1_proxy.py`
- `tests/test_checkpoint_resume.py`
- `tests/test_checkpoint_resume_failure_paths.py`
- `tests/test_code_quality.py`
- `tests/test_crm_sync_service.py`
- `tests/test_feature_flags.py`
- `tests/test_health_tracker.py`
- `tests/test_interfaces_exports.py`
- `tests/test_langgraph_execution.py`
- `tests/test_llm_budget_guardrails.py`
- ...more

**Cross-layer Tests (33 files)**:
- Contract tests: `tests/contract/test_*.py` (9 files)
- Security tests: `tests/security/test_*.py` (5 files)
- Chaos tests: `tests/chaos/*.py` (3 files)
- Architecture tests: `tests/arch/*.py` (2 files)
- Evals: `tests/evals/skills/*.py` (2 files)
- GitOps: `tests/gitops/*.py` (1 file)
- Integration: `tests/integration/**/*.py` (1 file)

### Frontend Test File Locations

**Unit Tests (24 files)**:
- `client/src/api/client.test.ts`
- `client/src/components/WfPrimitives.test.tsx`
- `client/src/contexts/AuthContext.test.tsx`
- `client/src/hooks/useAccounts.test.tsx`
- `client/src/hooks/useAuth.test.ts`
- `client/src/hooks/useBenchmarks.test.ts`
- `client/src/hooks/useBilling.test.tsx`
- `client/src/hooks/useDocuments.test.tsx`
- `client/src/hooks/useFormulas.test.ts`
- `client/src/hooks/useGraphQuery.test.ts`
- `client/src/hooks/useJobStream.test.ts`
- `client/src/hooks/useProvenance.test.tsx`
- `client/src/hooks/useValuePacks.test.tsx`
- `client/src/hooks/useVariables.test.ts`
- `client/src/hooks/useWorkflows.test.ts`
- `client/src/pages/AgentWorkflows.test.tsx`
- `client/src/pages/BusinessCase.test.tsx`
- `client/src/pages/DecisionTrace.test.tsx`
- `client/src/pages/ExtractionEngine.test.tsx`
- `client/src/pages/GraphExplorer.test.tsx`
- `client/src/pages/ValuePacks.test.tsx`
- `client/src/pages/formulaBuilderLogic.test.ts`
- `client/src/stores/userTierStore.test.ts`
- `client/src/utils.test.ts`

**E2E Tests (9 files)**:
- `e2e/admin.spec.ts`
- `e2e/business-case.spec.ts`
- `e2e/command-center.spec.ts`
- `e2e/decision-trace.spec.ts`
- `e2e/extraction-engine.spec.ts`
- `e2e/formula-builder.spec.ts`
- `e2e/graph-explorer.spec.ts`
- `e2e/navigation.spec.ts`
- `e2e/value-tree-explorer.spec.ts`

### Coverage Configuration

**Python (per layer)**:
- Minimum coverage: 80%
- Source: `src/`
- Omit: `*/tests/*`, `*/migrations/*`
- Tool: pytest-cov

**Frontend**:
- Provider: v8
- Reporters: text, json, html
- Exclude: node_modules/, test/, **/*.d.ts, **/*.config.*

### CI Integration

**GitHub Actions**:
- `pr-checks.yml`: Runs lint, type-check, tests with coverage per layer
- `integration-tests.yml`: Cross-layer integration tests
- `security-gates.yml`: Security tests
- Coverage gate: `--cov-fail-under=80`

### Known Gaps

1. Layer 5 (Ground Truth): Test count unknown, needs verification
2. Layer 6 (Benchmarks): Test count unknown, needs verification
3. SDK tests: Not yet mapped
4. Some layers may have missing coverage for edge cases

## Audit Priority

Based on critical path analysis:
1. Layer 4 (Agents) - Core business logic
2. Layer 3 (Knowledge) - API contracts
3. Layer 2 (Extraction) - Data pipeline
4. Cross-layer contract tests
5. Frontend unit tests
6. Security tests
