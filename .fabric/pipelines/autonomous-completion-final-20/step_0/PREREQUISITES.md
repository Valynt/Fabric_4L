# Step 0 prerequisites — met vs unmet

**Freeze SHA:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**CI inventory:** [ci_inventory.json](./ci_inventory.json) — PR Checks run 33970450342 **45/45 jobs**, pages 1–2 at `per_page=30`, `filter=all` (not `failed_only`). Prod Readiness run 33970450317 **16/16 jobs**, one page.

**Lane legend:** `prereq_maintenance` = repair the 80% / freeze; `ac20_feature` = missing-20% product work. These are not interchangeable.

Step 0 is **PARTIAL**. Unmet items below are **not** AC-20 features. H-STEP0-INCOMPLETE blocks Steps 2–6 (no Step 2 exception in force).

## Spec actions vs observed

| Spec action | Required for | Observed | Status | Lane |
|---|---|---|---|---|
| pin_toolchain_versions | freeze | Pins **recorded**, not rewritten. Python 3.11.15 vs 3.11.10; pnpm 10.18.1 vs P0 #1639 `>=10.34.5` | PARTIAL — drift flagged as GAP-9/10 | prereq_maintenance |
| lock_dependency_manifests | freeze | 17 lockfiles hashed in `lockfile_hash_manifest.json` | MET as snapshot | — |
| snapshot_database_schema_and_seed_data | freeze | **Not done** | UNMET | prereq_maintenance |
| capture_golden_baseline_run | freeze + Step 6 perf | CI proxy only. Local `make verify` not run. `coverage_pct`, `build_time`, `latency_p50`, `latency_p95` = null. Layer 3 coverage step **cancelled** (~30m) so even the CI proxy has no L3 coverage number | UNMET | prereq_maintenance |
| record_anchor_git_sha | freeze | `4bb4e14` | MET | — |
| produce container_image (OCI) | Step 6 `e2e_environment: step_0_container` | `container_image_reproducible == false`. Frontend **image build succeeded**; Trivy scan failed. layer1 deploy image separately failed on run 33970450291 | UNMET | prereq_maintenance |

## Spec completion criteria

| Criterion | Value | Blocks |
|---|---|---|
| `container_image_reproducible == true` | **false** | Steps 2–6 (not Step 1). No Step 2 exception. |
| `baseline_report_generated == true` | true (this file tree) | — |
| golden measurements present | **false** (nulls) | Steps 2–6 |

## PR Checks [run 33970450342](https://github.com/Valynt/Fabric_4L/actions/runs/33970450342) — complete pagination

Totals (45 jobs): **36 success, 6 failure, 1 cancelled, 2 skipped**.

### Underlying failures (independent causes)

| Job | ID | Page | Failing step | Class |
|---|---|---|---|---|
| Runtime Contract Tests (Services Up) | 101317925883 | 1 | Run runtime contract marker suite | environment-dependent (services-up) |
| Integration Tests (Docker) | 101317925894 | 1 | Fetch secrets from Infisical | environment-dependent (secrets/docker) |
| p0-e2e-gate | 101317925902 | 1 | Start deterministic E2E backend | environment-dependent (e2e) |
| Docker Image Build Verification (frontend) | 101317925990 | **2** | Run Trivy image scan (PR security stage) | image **build succeeded**; Trivy CVE gate failed (node-tar / tar family). Not a missing image. |

### Cancelled (must keep; `failed_only` drops this)

| Job | ID | Page | Cancelled step | Downstream |
|---|---|---|---|---|
| Layer 3 - Knowledge | 101317925680 | 1 | Run tests with coverage (~30m16s) | 02-code-quality-and-tests treats `layer3-checks=cancelled` as aggregate fail |

### Aggregates (failed because of children — not extra independent product-test failures)

| Job | ID | Page | What it actually failed on |
|---|---|---|---|
| Unified Readiness Gate | 101319028469 | **2** | Root-failure children: `docker-build-check`, `integration-checks`, `runtime-contract-checks`. Does not list `p0-e2e-gate`. |
| 02-code-quality-and-tests | 101321948028 | **2** | `Summarize code-quality and test gates` → `layer3-checks=cancelled`. Layer 1/2/4/5/6/frontend/shared **success**. |

Do **not** drop the page-2 failures by querying `failed_only`. Do **not** treat the two aggregates as a third and fourth suite. The blocking set under GAP-0 = block is the four underlying failures plus the Layer 3 cancellation (coverage gap), until the operator names a smaller set.

Skipped (PR-only on a main push, not failures): PR Overlap Guard, 09-change-risk-and-approval.

## Prod Readiness Gates [run 33970450317](https://github.com/Valynt/Fabric_4L/actions/runs/33970450317) — 16/16 jobs

Totals: **10 success, 6 failure**. Pagination complete (`per_page=100`).

### Underlying failures

`dependency-chaos`, `readiness-10`, `gate-engineering`, `release-policy` (canonical release gate).

### Aggregates / cascades

- `06-production-readiness` — `Summarize production-readiness gates`
- `prod-readiness` — `Download release artifacts` failed (cascade of missing child artifacts)

These are **release requirements** (GAP-18), not AC-20 feature nodes. Under GAP-0 = block they still halt Steps 2–6.

## What is *not* an AC-20 feature

Do not put these in the DAG as product nodes:

- The four underlying PR Checks failures and the Layer 3 cancellation
- Frontend Trivy CVEs (image exists)
- Prod Readiness underlying + aggregate jobs
- Reproducible OCI freeze image, schema/seed snapshot, golden p50/p95/coverage
- Python pin (GAP-10), pnpm floor (GAP-9 / #1645), nested lockfile (GAP-11)

Those are **prerequisite maintenance** of the 80%, or **release evidence**.
