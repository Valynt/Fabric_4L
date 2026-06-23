# Test Quality Discovery Report

Generated: 2026-04-18

## Testing Landscape Overview

### Repository Structure
```
Fabric_4L/
├── services/          # Backend (Python)
│   ├── layer1-ingestion/
│   ├── layer2-extraction/
│   ├── layer3-knowledge/
│   ├── layer4-agents/
│   ├── layer5-ground-truth/
│   └── layer6-benchmarks/
├── frontend/              # Frontend (TypeScript/React)
│   └── client/
├── packs/                 # Domain packs (Python tests)
├── sdk/python/            # SDK (Python tests)
└── tests/                 # Cross-layer tests
```

### Test Frameworks

| Layer | Framework | Config | Markers |
|-------|-----------|--------|---------|
| Layer 1 | pytest + pytest-asyncio | pyproject.toml | unit, integration, slow, requires_redis |
| Layer 2 | pytest + pytest-asyncio | pyproject.toml | unit, integration |
| Layer 3 | pytest + pytest-asyncio | pytest.ini | unit, integration, slow, requires_redis, requires_neo4j |
| Layer 4 | pytest + pytest-asyncio | pyproject.toml | unit, integration |
| Layer 5 | pytest | pytest.ini | unit, integration |
| Layer 6 | pytest | pyproject.toml | (benchmarks) |
| Frontend | Vitest + React Testing Library | package.json | - |
| Frontend E2E | Playwright | playwright.config.ts | - |

### Test Counts

| Category | Count |
|----------|-------|
| Python tests (value-fabric) | ~65+ files |
| TypeScript tests (frontend) | 32 files |
| Pack tests | 21 files |
| Cross-layer tests | 15+ files |
| **Total** | **130+ test files** |

### CI Integration

- **PR Checks**: `.github/workflows/pr-checks.yml`
- **Integration Tests**: `.github/workflows/integration-tests.yml`
- **Test Reporting**: `.github/workflows/test-reporting.yml`
- **E2E Tests**: Playwright via `pnpm test:e2e`

### Coverage Tools

- **Python**: pytest-cov (configured in pyproject.toml)
- **Frontend**: Vitest coverage (via --coverage flag)

### Known Gaps

1. **Layer 2**: ModuleNotFoundError during test collection (import 'src' issue)
2. **Layer 3**: Neo4j Community vs Enterprise compatibility issues
3. **Frontend**: GraphExplorer.test.tsx has pre-existing failures
4. **Cross-layer**: Some contract tests may have drift

## Sample Test Quality Assessment

### Layer 1 - test_adapters.py
- **Score**: 28/35 (Good)
- **Strengths**: Clear naming, proper async handling, mocking boundaries
- **Issues**: Some magic numbers (date_range_days = 365), minimal edge case coverage

### Frontend - useValuePacks.test.tsx
- **Score**: 30/35 (Excellent)
- **Strengths**: Good factory helper (createMockResponse), proper async handling, error state coverage
- **Issues**: Minor - could use userEvent instead of fireEvent (already addressed by user)

## Next Steps

Proceed to Phase 2: Audit - evaluate all test files against the 7 principles.
