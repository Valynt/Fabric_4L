# Step 0 prerequisites — met vs unmet

**Freeze SHA:** `4bb4e142c2ccbc56297de843e71534d956bb198f`  
**Captured:** 2026-09-05T15:20:00Z (original) / 2026-09-05T16:00:00Z (reconcile)  
**Lane legend:** `prereq_maintenance` = repair the 80% / freeze; `ac20_feature` = missing-20% product work. These are not interchangeable.

Step 0 is **PARTIAL**. Unmet items below are **not** AC-20 features.

## Spec actions vs observed

| Spec action | Required for | Observed | Status | Lane |
|---|---|---|---|---|
| pin_toolchain_versions | freeze | Pins **recorded**, not rewritten. Python 3.11.15 vs 3.11.10; pnpm 10.18.1 vs P0 #1639 `>=10.34.5` | PARTIAL — drift flagged as GAP-9/10 | prereq_maintenance (intent = GAP-9/10) |
| lock_dependency_manifests | freeze | 17 lockfiles hashed in `lockfile_hash_manifest.json` | MET as snapshot | — |
| snapshot_database_schema_and_seed_data | freeze | **Not done** | UNMET | prereq_maintenance |
| capture_golden_baseline_run | freeze + Step 6 perf | CI proxy only. Local `make verify` not run. `coverage_pct`, `build_time`, `latency_p50`, `latency_p95` = null | UNMET | prereq_maintenance |
| record_anchor_git_sha | freeze | `4bb4e14` | MET | — |
| produce container_image (OCI) | Step 6 `e2e_environment: step_0_container` | `container_image_reproducible == false`. docker CLI unused here; Build and Deploy failed on `Build Images (layer1-ingestion)` ([run 33970450291](https://github.com/Valynt/Fabric_4L/actions/runs/33970450291)) | UNMET | prereq_maintenance |

## Spec completion criteria

| Criterion | Value | Blocks |
|---|---|---|
| `container_image_reproducible == true` | **false** | Steps 3–6 (not Step 1) |
| `baseline_report_generated == true` | true (this file tree) | — |

## Existing suite on the 80% (H-RED-SUITE)

Operator GAP-0 = **block**. Re-query of failed jobs on 2026-09-05 (GitHub `failed_only`) vs original snapshot:

### PR Checks [run 33970450342](https://github.com/Valynt/Fabric_4L/actions/runs/33970450342)

| Job | Original snapshot | Re-query `failed_only` | Classification |
|---|---|---|---|
| Runtime Contract Tests (Services Up) | failed | **failed** (job 101317925883) | environment-dependent (services up) |
| Integration Tests (Docker) | failed | **failed** (job 101317925894) | environment-dependent (Docker) |
| p0-e2e-gate | failed | **failed** (job 101317925902) | environment-dependent (e2e) |
| Docker Image Build Verification (frontend) | listed failed | **not in failed_only** | likely skipped/needs; not confirmed as independent failure |
| Unified Readiness Gate | listed failed | **not in failed_only** | aggregator; not a distinct suite failure |
| 02-code-quality-and-tests | listed failed | **not in failed_only** | **unverified as a distinct fail** — do not treat as classified product-test red until a job log exists |

Confirmed red for GAP-0 block: the three Docker/e2e/runtime-contract jobs.

Green on the same SHA (unchanged): Critical Gates, Security Gates, Contract Compliance, Supply Chain Integrity, Zero Trust, Visual Regression, Bundle Analysis, L4 route-contract matrix.

### Prod Readiness Gates [run 33970450317](https://github.com/Valynt/Fabric_4L/actions/runs/33970450317)

`failed_only` confirmed six failed jobs: `dependency-chaos`, `readiness-10`, `gate-engineering`, `release-policy`, `06-production-readiness`, `prod-readiness`.

These are **readiness/release gates**, not the unit/integration suite. Under GAP-0 = block they still halt Steps 2–6. They are closer to **release requirements** (GAP-18) than to “write the missing 20%.”

Also failed on the SHA: Certify RC (33970450296), Build and Deploy / layer1 image (33970450291), Release Evidence Bundle (33970450297).

## What is *not* an AC-20 feature

Do not put these in the DAG as product nodes:

- Docker/e2e/runtime-contract redding on main
- layer1 image build failure
- Prod Readiness / Certify RC / Release Evidence
- Reproducible OCI freeze image
- Schema/seed snapshot
- p50/p95/coverage golden numbers
- Python pin reconciliation (GAP-10)
- pnpm floor (GAP-9 / #1645)
- Nested `apps/web/pnpm-lock.yaml` policy (GAP-11)

Those are **prerequisite maintenance** of the 80%, or **release evidence**, depending on the row.
