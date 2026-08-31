# Phase 0 Gap Note — Sprint 1 (Stabilize & Ground Truth)

**Date:** 2026-08-29
**Branch:** `sprint-1-phase-0`
**Scope:** Evolution plan Sprint 1 / Phase 0 — stabilize CI ratchets and
establish ground truth. Code/config changes only; no service runtime changes.

## What this sprint changed (done, in-repo)

1. **Ratchet consolidation** — new aggregate Make target
   `check-health-ratchets` runs all fail-on-net-new health ratchets as a single
   entry point (16 ratchets + `check-risk-register`). Excludes live-DB and
   artifact-context checks (`check-migration-postgres-roundtrip`,
   `check-migration-status-artifacts`, `check-behavior-readiness-audit`) and
   per-layer typecheck ratchets. `.github/workflows/pr-checks.yml` now calls
   `make check-health-ratchets` once instead of separate type-escape /
   structural-fitness steps.
2. **WAL-G re-enablement (DR gap)** — `ENABLE_WALG_BACKUP: "true"` in
   `k8s/base/postgres-backup-cronjob.yaml` and `k8s/base/wal-g-config.yaml`;
   WAL archiving enabled in `k8s/base/postgres-patroni.yaml`
   (`archive_mode=on`, `archive_command=wal-g wal-push %p` via Patroni env
   parameters). pg_dump is demoted to cold-archive fallback (header comment
   updated). Note: the `dr-drill.yml` newline bug described in the sprint plan
   (merged `echo ... exit 1` near L79) was **not present** in the checked-in
   file — the backup-header check is already correctly structured; no change
   was made there.
3. **Risk register ground truth** — all 6 ACCEPTED risks (PRR-002, PRR-003,
   PRR-006, PRR-007, PRR-008, PRR-010) now carry `countersignature: MISSING`
   and `ground_truth_status: PENDING_COUNTERSIGNATURE`. New gate
   `scripts/ci/check_risk_register_countersignatures.py` (Make target
   `check-risk-register`, wired into `check-health-ratchets`) fails on
   un-countersigned ACCEPTED P0 risks, with
   `config/ci/risk_countersignature_baseline.json` grandfathering PRR-002,
   PRR-003, PRR-010 (fail-on-net-new).
4. **Phase 0 debt baseline snapshot** — `make debt-baseline-snapshot`
   aggregates the checked-in ratchet baselines into
   `config/ci/phase0_debt_baseline.json` (counts + source paths + snapshot
   date). Snapshot committed.
5. **ADR-027 shim remainder** — compatibility registry ground-truthed: the
   Layer 1 api.main shim and the deprecated tracer module no longer exist;
   their gate entries are annotated (GATE-COMPAT-005 marked
   `status: retired — module removed per ADR-027`), checks retained as
   tripwires. ADR-027 has a Phase 0 addendum.

## What remains — NON-code, requires humans/infra

Per the roadmap Phase 0 exit criteria, the following cannot be completed in a
code sprint and are owned outside this repo:

1. **Obtain the 6 countersignatures** (PRR-002, PRR-003, PRR-006, PRR-007,
   PRR-008, PRR-010) from their risk owners — or record documented P0→P1
   waivers. Until then the 3 P0s remain grandfathered in
   `config/ci/risk_countersignature_baseline.json`; removing an entry from the
   baseline without a countersignature will fail CI.
2. **Provision the persistent staging environment** required by PRR-003 /
   PRR-010 (full P0 Playwright journeys, aggregate gate with Redis, rollback
   rehearsal).
3. **Run the first restore drill against staging** and capture restore
   evidence (logs, checksums, runbook sign-off) — see the WAL-G
   post-enablement verification checklist in
   `k8s/base/postgres-backup-cronjob.yaml`.
4. **S3 bucket + IRSA role provisioning for WAL-G** — the S3 destination,
   bucket policy, and IAM role must exist before `wal-g backup-push` succeeds.
   The IRSA annotation on the `wal-g-backup` ServiceAccount is intentionally
   left to environment overlays (not base manifests).

## Exit-criteria tracking

| Phase 0 exit criterion | Status |
|---|---|
| Single health-ratchet entry point in CI | ✅ Done (`make check-health-ratchets`) |
| WAL-G active path configured in base manifests | ✅ Done (runtime verification pending infra) |
| Risk register countersignature ground truth + gate | ✅ Gate done; countersignatures pending owners |
| Debt baseline snapshot committed | ✅ `config/ci/phase0_debt_baseline.json` |
| ADR-027 shim remainder ground-truthed | ✅ Done |
| Countersignatures or P0→P1 waivers obtained | ⏳ Human action required |
| Persistent staging environment provisioned | ⏳ Infra action required |
| First restore drill executed with evidence | ⏳ Blocked on staging + S3/IRSA |
