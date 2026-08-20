# Test-Debt Governance Inventory

## Scope

This document records the consolidation baseline, the canonical debt inventory,
and the deterministic remediation queue produced by
`scripts/ci/check_test_skip_governance.py`. Static scanning covers `tests/`, every
`services/**/tests/` directory, and `apps/web/e2e/`. Collection and runtime results
are supporting evidence rather than authorization for debt markers.

## Before consolidation (2026-08-18 UTC)

Measurements use Python 3.11.15 and elapsed wall-clock time from
`time.perf_counter()`. PyYAML was installed before measurement because all existing
governance commands require it.

| Control | Exit | Elapsed | Result |
| --- | ---: | ---: | --- |
| `python scripts/ci/check_test_skip_governance.py --write-report /tmp/test-debt-before/static.json` | 0 | 1.364 s | 287 markers detected in its narrow roots; 79 registrations, 51 matched IDs, 0 unregistered |
| `python scripts/ci/check_temporal_skips.py --baseline config/ci/temporal_skip_baseline.json --exclude tests/ci/test_temporal_skip_guard.py --json-out /tmp/test-debt-before/temporal.json` | 0 | 3.606 s | No net-new temporal violations after independent filtering |
| `python scripts/ci/check_test_skip_register_uniqueness.py` | 0 | 0.693 s | No duplicate `(path_pattern, marker, reason_pattern)` keys |
| Focused governance pytest command | blocked | 0.865 s | Collection stopped because the selected Python environment lacked `jsonschema`; installed before implementation validation |

A direct lexical census of the intended surfaces visited 1,499 source files and
found 419 skip/skipif forms, 20 xfail forms, no fixmes, and no focused markers. The
287-versus-439 marker difference demonstrates the prior static checker's service-test
blind spot. Lexical counts include scanner-characterization fixture strings and are
therefore a benchmark, not the final reconciled inventory.

## After consolidation

The authoritative evaluator scanned 1,499 files in 3.982 seconds end-to-end (3.326
seconds reported inside the evaluator) and reconciled 423 marker occurrences to 255
unique registrations. It reported zero unregistered, expired, forbidden, ambiguous,
duplicate, malformed, or stale entries. The focused 19-test governance suite passed
in 0.954 seconds.

| Marker | Occurrences |
| --- | ---: |
| `pytest.skip` | 303 |
| `pytest.mark.skip` / `skipif` | 87 |
| `pytest.mark.xfail` | 20 |
| `test.skip` | 13 |
| `test.fixme` | 0 |
| focused `.only` forms | 0 |

| Inventory group | Unique registrations |
| --- | ---: |
| P0 | 153 |
| P1 | 58 |
| P2 | 2 |
| VALID | 42 |

The prior controls consumed approximately 5.663 seconds when their three static
commands were run sequentially. The consolidated command consumed 3.982 seconds in
the same environment, but this phase does not claim an overall test-suite runtime
improvement: full pytest collection was blocked after 1.280 seconds because the local
Python environment lacks `pydantic_settings`. Static discovery does not depend on
that optional runtime import and remained fail-closed.

## Deterministic next remediation wave

The canonical risk ranking selects this first small tenant-isolation wave. Execute
these registrations in order, replacing each skip with explicit allowed and denied
characterization before moving to the next group:

1. `skip-044` and `skip-045` — cross-layer tenant behavior in
   `tests/security/test_cross_layer_tenant.py` (`@platform-security`).
2. `skip-048` — cross-tenant write denial in
   `tests/security/test_cross_tenant_write.py` (`@platform-security`).
3. `skip-053` — knowledge-tool tenant isolation in
   `tests/security/test_knowledge_tools_tenant_isolation.py`
   (`@platform-security`).
4. `skip-065` — tenant lifecycle security in
   `tests/security/test_tenant_lifecycle.py` (`@platform-security`).
5. `skip-107` and `skip-111` — hostile cross-tenant behavior at the Layer 2 and
   Layer 3 service boundaries (`@layer2-extraction-quality` and
   `@layer3-knowledge-quality`).

The full deterministic P0 queue is emitted as `remediation_queue` in
`artifacts/test-debt-governance.json`; it continues with Layer 3 tenant-context
extraction and Layer 4 tenant-isolation registrations before auth, security, gateway,
contract, golden-path, persistence, and release domains.

## Reproduction

```bash
python scripts/ci/check_test_skip_governance.py \
  --json-out artifacts/test-debt-governance.json \
  --md-out artifacts/test-debt-governance.md
python -m pytest --confcutdir=tests/ci -o addopts='' -q \
  tests/ci/test_test_skip_governance.py \
  tests/ci/test_temporal_skip_guard.py \
  tests/ci/test_check_test_skip_register_uniqueness.py \
  tests/ci/test_check_pytest_skip_governance.py
```
