# B2 Python Vulnerability Audit — 2026-05-14

## Summary

Audited 7 Python dependency surfaces (6 layer services via `uv.lock` + `services/api` via
`pyproject.toml`). One HIGH-severity vulnerability was found and resolved. All surfaces are
clean post-remediation.

| Surface | Before | After | Action |
|---|---|---|---|
| `services/layer1-ingestion` | ✅ Clean | ✅ Clean | None |
| `services/layer2-extraction` | ❌ CVE-2026-45134 (HIGH) | ✅ Clean | `langsmith` 0.7.32 → 0.8.4 |
| `services/layer3-knowledge` | ✅ Clean | ✅ Clean | None |
| `services/layer4-agents` | ✅ Clean | ✅ Clean | None |
| `services/layer5-ground-truth` | ✅ Clean | ✅ Clean | None |
| `services/layer6-benchmarks` | ✅ Clean | ✅ Clean | None |
| `services/api` | ✅ Clean (pyproject-only) | ✅ Clean | Tightened `python-multipart>=0.0.27` → `>=0.0.28` |

---

## Context

A prior commit (`212f7d1e`) had already bumped `urllib3` (2.6.3→2.7.0), `mako`
(1.3.11→1.3.12), `langchain-core` (1.3.0→1.4.0), and `python-multipart` (0.0.15→0.0.28)
across the layer services. Those packages are clean at their current versions.

The remaining vulnerability was `langsmith 0.7.32` in `layer2-extraction`, a transitive
dependency pulled in via `langchain-core → langsmith`. The `layer4-agents` service had
already resolved `langsmith 0.8.0` in its own lock; `layer2-extraction`'s lock was stale.

---

## Toolchain

- **Lockfile manager**: `uv 0.11.14`
- **Audit tool**: `pip-audit 2.10.0`
- **Advisory database**: PyPI / OSV

---

## Before-State Audit

### `services/layer1-ingestion`
```
No known vulnerabilities found
```

### `services/layer2-extraction`
```
Found 1 known vulnerability in 1 package
Name      Version ID             Fix Versions
--------- ------- -------------- ------------
langsmith 0.7.32  CVE-2026-45134 0.8.0
```

Advisory: **GHSA-3644-q5cj-c5c7** — LangSmith SDK: Public prompt pull deserializes
untrusted manifests without trust boundary warning. Severity: **HIGH**.

### `services/layer3-knowledge`
```
No known vulnerabilities found
```

### `services/layer4-agents`
```
No known vulnerabilities found
```

### `services/layer5-ground-truth`
```
No known vulnerabilities found
```

### `services/layer6-benchmarks`
```
No known vulnerabilities found
```

### `services/api` (pyproject-only, no lockfile)
```
No known vulnerabilities found
```
Declared deps audited directly from `pyproject.toml`. `python-multipart>=0.0.27` resolves
cleanly; `0.0.27` has no known CVEs per OSV. Lower bound tightened to `>=0.0.28` as a
preventive measure (0.0.28 is the current clean release).

---

## Remediation Actions

### 1. `services/layer2-extraction` — langsmith upgrade

**Command:**
```bash
cd services/layer2-extraction
uv lock --upgrade-package langsmith
```

**Result:** `langsmith v0.7.32 → v0.8.4`

`langsmith` is a transitive dependency (`langchain-core → langsmith`). No changes were
made to `pyproject.toml` — the constraint on `langchain>=0.3.0` already permits the
updated resolution. Only `uv.lock` was modified by the resolver.

**Lockfile re-export:**
```bash
uv export --locked --no-dev --format requirements-txt -o requirements.lock
```
`requirements.lock` now pins `langsmith==0.8.4`.

### 2. `services/api` — python-multipart lower bound

**File:** `services/api/pyproject.toml`

**Change:** `python-multipart>=0.0.27` → `python-multipart>=0.0.28`

`0.0.27` has no known CVEs, but `0.0.28` is the current clean release. Tightening the
lower bound prevents accidental resolution of `0.0.27` in future installs. No lockfile
exists for this service; the change is constraint-only.

---

## After-State Audit

### All 6 layer services
```
No known vulnerabilities found
```
(Verified via `uv export --no-dev --frozen --no-hashes | pip-audit -r /dev/stdin` per service.)

### `services/api`
```
No known vulnerabilities found
```

---

## Lightweight Source Verification

All services passed `python3 -m compileall` with no syntax errors:

| Service | Verified path | Result |
|---|---|---|
| `layer1-ingestion` | `src/` | ✅ OK |
| `layer2-extraction` | `src/` | ✅ OK |
| `layer3-knowledge` | `src/` | ✅ OK |
| `layer4-agents` | `src/` | ✅ OK |
| `layer5-ground-truth` | `src/` | ✅ OK |
| `layer6-benchmarks` | `src/` | ✅ OK |
| `services/api` | `app/` | ✅ OK |

Full app entrypoint imports were not run — services initialize Playwright, spaCy, Neo4j
clients, Redis queues, and settings requiring live secrets. Syntax/bytecode verification
is sufficient for a dependency-security PR.

---

## Lockfile Inventory

### Canonical lockfiles (uv.lock) — all updated or verified clean

| Service | uv.lock status |
|---|---|
| `layer1-ingestion` | unchanged (was clean) |
| `layer2-extraction` | **updated** — langsmith 0.7.32 → 0.8.4 |
| `layer3-knowledge` | unchanged (was clean) |
| `layer4-agents` | unchanged (was clean) |
| `layer5-ground-truth` | unchanged (was clean) |
| `layer6-benchmarks` | unchanged (was clean) |

### Derived lockfiles (requirements.lock)

| Service | requirements.lock type | Status |
|---|---|---|
| `layer1-ingestion` | pip-compile placeholder | Not regenerated — placeholder, not consumed by CI/Docker |
| `layer2-extraction` | uv export snapshot | **Regenerated** from updated uv.lock |
| `layer3-knowledge` | uv export snapshot | Unchanged (was clean) |
| `layer4-agents` | pip-compile placeholder | Not regenerated — placeholder, not consumed by CI/Docker |
| `layer5-ground-truth` | pip-compile placeholder | Not regenerated — placeholder, not consumed by CI/Docker |
| `layer6-benchmarks` | uv export snapshot | Unchanged (was clean) |

**Note:** `layer1-ingestion`, `layer4-agents`, and `layer5-ground-truth` have
`requirements.lock` files that are pip-compile placeholders containing boilerplate
instructions rather than resolved dependency pins. These are not consumed by CI or Docker
builds and were not modified. See follow-up item below.

---

## Exceptions

No exceptions required. All vulnerabilities were resolved.

**Exception format defined here for future use** (no prior B1 format existed in this repo):

```
Exception ID:          <B2-EXC-NNN>
Affected service:      <service path>
Affected package:      <name==version>
Advisory:              <CVE/GHSA ID>
Severity:              <CRITICAL|HIGH|MEDIUM|LOW>
Current version:       <x.y.z>
Required fix version:  <x.y.z>
Why fix is blocked:    <reason>
Risk level:            <ACCEPTED|DEFERRED>
Exposure assessment:   <attack surface description>
Compensating controls: <mitigations in place>
Owner:                 <team or individual>
Target remediation:    <date or milestone>
Tracking:              <issue/PR URL>
Validation evidence:   <pip-audit output or equivalent>
Approval:              <approver name/role>
Status:                <OPEN|RESOLVED>
```

---

## Follow-up Recommendations

1. **Standardize lockfile policy across all services.** Three services (`layer1-ingestion`,
   `layer4-agents`, `layer5-ground-truth`) have `requirements.lock` files that are
   pip-compile placeholders. These should either be regenerated as `uv export` snapshots
   (consistent with layer3 and layer6) or removed if no tooling consumes them. Tracking
   this separately avoids scope creep in security PRs.

2. **Add a lockfile for `services/api`.** This service has no `uv.lock`, making it
   impossible to pin transitive dependencies or produce a reproducible install. A `uv.lock`
   should be generated and committed as a follow-up.

3. **Add `pip-audit` to CI for Python services.** Currently there is no automated
   per-service Python vulnerability scan in `.github/workflows/`. Adding a step that runs
   `uv export | pip-audit` per service would catch regressions like the `langsmith` stale
   lock before they reach main.

---

## Files Changed

| File | Change |
|---|---|
| `services/layer2-extraction/uv.lock` | `langsmith` 0.7.32 → 0.8.4 (and transitive deps updated by resolver) |
| `services/layer2-extraction/requirements.lock` | Regenerated from updated uv.lock |
| `services/api/pyproject.toml` | `python-multipart>=0.0.27` → `>=0.0.28` |
| `reports/B2-python-vuln-audit-2026-05-14.md` | This report |
