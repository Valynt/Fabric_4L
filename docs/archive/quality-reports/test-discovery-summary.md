# Test Quality Remediation - Discovery Summary

Generated: Apr 10, 2026

## Repository Structure

**Monorepo Layout:**
```
Fabric_4L/
├── services/          # Backend layers (1-6)
│   ├── layer1-ingestion/
│   ├── layer2-extraction/
│   ├── layer3-knowledge/    # Largest test suite
│   ├── layer4-agents/
│   ├── layer5-ground-truth/
│   └── layer6-benchmarks/
├── frontend/              # React + TypeScript
│   └── client/
└── packs/                 # Domain packs
```

## Test Frameworks

### Python Backend (Layers 1-5)
- **Framework:** pytest with pytest-asyncio
- **Config:** pyproject.toml per layer
- **Additional:** pytest.ini in layer3-knowledge, layer5-ground-truth
- **Coverage:** pytest-cov configured in CI

### Frontend
- **Framework:** Vitest (inferred from vite.config.ts)
- **Package Manager:** pnpm
- **E2E:** Playwright (referenced in skills)

## Test File Inventory

| Layer | Test Files | Key Files | Notes |
|-------|-----------|-----------|-------|
| L1 Ingestion | 4 | test_adapters.py, test_scheduler.py, test_models.py | Unit tests only |
| L2 Extraction | 3 | test_extraction.py, test_llm_extractor.py, **test_extract_and_ingest_pipeline.py** | Critical pipeline test |
| L3 Knowledge | 17 | test_e2e_pipeline.py, test_graphrag_endpoints.py, test_search_endpoints.py, test_health_endpoints.py | Largest suite, most complex |
| L4 Agents | 5 | test_checkpoint_resume.py, test_workflow_controls.py, test_interfaces_exports.py | Checkpoint/resume tests failing |
| L5 Ground Truth | 5 | test_state_machine.py, test_api.py, test_freshness_monitor.py | State machine tests |

**Total Python Test Files:** 34

## CI Integration

**GitHub Actions:**
- `integration-tests.yml` - Nightly full stack tests
- `pr-checks.yml` - PR validation
- `build-deploy.yml` - Deployment pipeline
- `smoke-gate.yml` - Smoke tests

**Critical Test Runs in CI:**
1. L2: `test_extract_and_ingest_pipeline.py` (mentioned in workflow)
2. L3: `test_e2e_pipeline.py` (mentioned in workflow)

## Known Issues (from Memory)

1. **L4 checkpoint/resume tests** - Fail during collection due to `ModuleNotFoundError` importing 'src'
2. **L3 e2e pipeline tests** - Fail on Neo4j Community (enterprise-only constraints)
3. **Logger misuse** - `logger.error` with structured kwargs (exception_type/path)

## Coverage Tools

- pytest-cov (configured in CI)
- Coverage artifacts uploaded per layer
- No coverage threshold enforcement detected

## Priority Targets for Audit

Based on criticality and known failures:

1. **Layer 2** - `test_extract_and_ingest_pipeline.py` (CI critical path)
2. **Layer 3** - `test_e2e_pipeline.py` (CI critical path, known failures)
3. **Layer 4** - `test_checkpoint_resume.py` (import errors)
4. **Layer 3** - `test_health_endpoints.py` (health checks are critical)
5. **Layer 5** - `test_state_machine.py` (core business logic)

## Gaps Identified

- Layer 6 has no test files detected
- Frontend test inventory incomplete (needs further discovery)
- No mutation testing detected
- Property-based testing not detected
