# Test Discovery Map - Value Fabric Repository

Generated: 2026-04-11

## Repository Structure

```
Fabric_4L/
├── services/           # Backend layers (Python)
│   ├── layer1-ingestion/   # 3 unit tests
│   ├── layer2-extraction/  # 3 test files
│   ├── layer3-knowledge/   # 15 test files
│   ├── layer4-agents/      # 5 test files
│   ├── layer5-ground-truth/# 4 test files
│   └── layer6-benchmarks/  # 1 test file
├── frontend/               # React + TypeScript
│   └── e2e/               # 3 Playwright specs
└── .github/workflows/     # CI configuration
```

## Python Test Inventory (30 files)

### Layer 1 - Ingestion (3 files, ~15 tests)
| File | Focus | Framework |
|------|-------|-----------|
| `tests/unit/test_adapters.py` | Adapter interfaces | pytest |
| `tests/unit/test_models.py` | SQLAlchemy models | pytest |
| `tests/unit/test_scheduler.py` | Celery/scheduling | pytest |

### Layer 2 - Extraction (3 files, ~25 tests)
| File | Focus | Framework |
|------|-------|-----------|
| `tests/test_extract_and_ingest_pipeline.py` | Pipeline orchestration | pytest-asyncio |
| `tests/test_extraction.py` | Entity/relationship extraction | pytest |
| `tests/test_llm_extractor.py` | LLM client/scoring | pytest |

### Layer 3 - Knowledge (15 files, ~80+ tests)
| File | Focus | Notes |
|------|-------|-------|
| `test_api.py` | API endpoints | |
| `test_config.py` | Settings/validation | 20+ tests |
| `test_config_import_surface.py` | Import contracts | 2 tests |
| `test_e2e_pipeline.py` | End-to-end | CI shows Neo4j issues |
| `test_exception_handlers.py` | Error handling | |
| `test_exceptions.py` | Custom exceptions | |
| `test_graphrag_endpoints.py` | GraphRAG API | |
| `test_health_endpoints.py` | Health checks | |
| `test_hybrid_search_api_compat.py` | Search API | |
| `test_ingestion.py` | Data ingestion | |
| `test_ingestion_endpoints.py` | Ingest API | |
| `test_neo4j_integration.py` | Database tests | |
| `test_required_field_validator.py` | Validation | |
| `test_retrieval.py` | Data retrieval | |
| `test_search_endpoints.py` | Search API | |
| `test_vector_e2e.py` | Vector store | |

### Layer 4 - Agents (5 files, ~25 tests)
| File | Focus | Notes |
|------|-------|-------|
| `test_checkpoint_resume.py` | Checkpoint/resume | CI shows import errors |
| `test_code_quality.py` | Code review TDD | |
| `test_interfaces_exports.py` | Public API surface | |
| `test_workflow_controls.py` | Workflow execution | |

### Layer 5 - Ground Truth (4 files)
| File | Focus |
|------|-------|
| `test_api.py` | API endpoints |
| `test_freshness_monitor.py` | Data freshness |
| `test_state_machine.py` | State transitions |

### Layer 6 - Benchmarks (1 file)
| File | Focus |
|------|-------|
| `test_benchmark_api.py` | Benchmark endpoints |

## Frontend Test Inventory

| File | Type | Framework |
|------|------|-----------|
| `e2e/command-center.spec.ts` | E2E | Playwright |
| `e2e/graph-explorer.spec.ts` | E2E | Playwright |
| `e2e/navigation.spec.ts` | E2E | Playwright |

**Unit Test Gap**: Frontend has Vitest in devDependencies but no `.test.ts` files found.

## CI Configuration

| Workflow | Purpose |
|----------|---------|
| `integration-tests.yml` | Nightly full-stack tests |
| `pr-checks.yml` | PR validation |
| `smoke-gate.yml` | Health checks |
| `build-deploy.yml` | Build verification |

## Coverage Configuration

| Layer | Tool | Target |
|-------|------|--------|
| L1-L6 | pytest-cov | 85% (L2) |
| Frontend | N/A | No coverage configured |

## Known Issues (from CI/logs)

1. **L4 Checkpoint Tests**: ModuleNotFoundError importing 'src'
2. **L3 E2E Tests**: Neo4j Community vs Enterprise constraint issues
3. **Frontend**: No unit tests (Vitest configured but unused)
4. **L2/L3 Integration**: API contract drift (per roadmap notes)

## Framework Versions

- pytest: 8.3+
- pytest-asyncio: 0.24+ (L2), 0.23+ (L3)
- pytest-cov: 6.0+ (L2), 4.1+ (L3)
- testcontainers: 4.8+
- Vitest: 2.1.4 (frontend)
- Playwright: 1.47.0
