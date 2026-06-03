# Type Safety Ratchet Plan (Gap 4)

**Date:** 2026-04-19  
**Status:** Baseline established for Layer 4, Makefile ratchet in place

## Principle
A "ratchet" prevents regression while allowing incremental improvement. The repo cannot get worse, only better.

## Current State

| Layer | Baseline Errors | Config Location | Strictness |
|-------|-----------------|-----------------|------------|
| L1 Ingestion | ~45 | pyproject.toml | Relaxed (untyped defs allowed) |
| L2 Extraction | ~30 | pyproject.toml | Strict |
| L3 Knowledge | ~85 | pyproject.toml | Strict |
| L4 Agents | ~52 | pyproject.toml | Moderate (ratchet set) |
| L5 Ground Truth | ~15 | pyproject.toml | Strict |
| L6 Benchmarks | ~5 | pyproject.toml | Minimal |

## Ratchet Mechanisms

### 1. Makefile Non-Regression
`make typecheck` fails fast on first error - no new type errors can be introduced.

### 2. Per-Layer pyproject.toml
Each layer now has explicit mypy configuration:
- `warn_return_any = true` - catches unsafe returns
- `warn_unused_configs = true` - catches config drift
- `show_error_codes = true` - enables targeted fixes

### 3. CI Enforcement
PR checks run mypy on each layer - new errors block merge.

## Improvement Strategy

### Phase 1: High-Churn Modules (Next 2 weeks)
Target modules with frequent changes to maximize safety ROI:
1. `layer4-agents/src/api/main.py` - startup/dependency logic
2. `layer4-agents/src/engine/executor.py` - orchestration
3. `shared/identity/middleware.py` - security path

### Phase 2: Cross-Layer Contracts (Next month)
1. Add type stubs for shared modules
2. Enable `disallow_untyped_defs` for new files only
3. Gradually tighten layer-by-layer

### Phase 3: Full Strictness (Future)
Enable `--strict` for all layers once baseline is clean.

## Measuring Progress

Track error count weekly:
```bash
make typecheck 2>&1 | grep -c "error:"
```

Target: Reduce by 10% per sprint without blocking development.

## Success Criteria
- Zero new type errors introduced in PRs
- Existing error count decreases by 20% per month
- `disallow_untyped_defs = true` enabled for 3+ layers
