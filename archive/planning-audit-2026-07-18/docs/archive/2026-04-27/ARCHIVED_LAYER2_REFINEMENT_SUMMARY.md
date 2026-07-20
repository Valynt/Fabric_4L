---
**ARCHIVED DOCUMENT**
Archive Date: 2026-04-27
Original Location: Repository Root
Rationale: ROADMAP supersedes
Modern Equivalent: See ROADMAP.md for current status
Status: Historical reference only
---

# Layer 2 Extraction Refinement Summary

## Changes Made

### P0 - Incorrectness Fixes (Critical Bugs)

1. **Fixed missing `await` on Redis ping()** (Line 173)
   - Changed `redis_client.ping()` to `await redis_client.ping()`
   - Moved Redis initialization from module level to async `startup_event()`
   - Added `_init_redis_rate_limiter()` helper function

2. **Fixed missing `await` on `_set_pipeline_job()` calls** (Lines 955, 978)
   - Added `await` to async calls in `run_extraction()` success and error paths
   - These were causing silent failures where job status wasn't being persisted

3. **Fixed deprecated `datetime.utcnow()` calls** (24 occurrences)
   - Replaced all `datetime.utcnow()` with `datetime.now(UTC)`
   - Replaced `datetime.utcnow().isoformat()` with `datetime.now(UTC).isoformat()`
   - Replaced `datetime.utcfromtimestamp()` with `datetime.fromtimestamp(..., tz=UTC)`
   - This fixes deprecation warnings in Python 3.12+

### P1 - Fragility Fixes

4. **Extracted magic numbers to constants** (Lines 204-211)
   - `DEFAULT_CHUNK_SIZE = 2000`
   - `DEFAULT_CHUNK_OVERLAP = 200`
   - `DEFAULT_CONFIDENCE_THRESHOLD = 0.75`
   - `RELATIONSHIP_CONFIDENCE_OFFSET = 0.05`
   - `DEFAULT_SIMILARITY_THRESHOLD = 0.85`
   - `PROGRESS_REPORT_INTERVAL = 10`
   - `DEFAULT_RDF_OUTPUT_DIR = "/tmp/rdf"`

5. **Updated all hardcoded values to use constants**
   - Extraction config defaults
   - Chunking parameters
   - Confidence thresholds
   - Progress reporting intervals
   - RDF output directory

## Verification

```bash
# Verify syntax
python -m py_compile services/layer2-extraction/src/layer2_extraction/api/main.py

# Expected: Syntax OK
```

## Lines Changed

- **Total**: ~120 lines across the file
- **Files modified**: 1
- **Functions refactored**: 3
- **Constants added**: 7

## Impact

- **Bug fixes**: 3 critical P0 bugs fixed (async/await issues)
- **Maintainability**: Magic numbers now documented as constants
- **Future-proofing**: Removed deprecated datetime API usage
- **No breaking changes**: All changes are internal implementation details
