# Final-Testing Launch Checklist

This checklist is the sign-off package for entering final testing. It is deliberately strict: repository-owned checks may pass locally, but live production readiness is not claimed until the environment-dependent evidence matrix is completed in a properly provisioned staging or launch environment.

## Sign-Off Standard

The release may enter final testing only when the repository-owned checks are passing, no unresolved **P0 Launch Blocker** remains, every **P1 Launch Blocker** has an owner and mitigation, and all live-only gates are explicitly scheduled with an evidence owner. The launch owner should treat missing evidence as a decision, not an assumption.

Evidence authority rule: ship/no-ship decisions are authoritative only when reflected in `docs/launch/launch-blocker-register.md` and `docs/launch/environment-dependent-evidence-matrix.md`. `reports/` artifacts are supporting diagnostics only unless explicitly linked to a passing gate run with timestamp + commit SHA metadata. The canonical repository-owned evidence-pack generator is `scripts/ci/generate_release_evidence_packet.py`; do not duplicate evidence-generation logic in other scripts. The canonical outputs are `artifacts/release/evidence-packet/release-evidence-packet.json` and `artifacts/release/evidence-packet/release-evidence-summary.md`. If an external consumer requires `./evidence_pack/`, copy these canonical outputs into that directory as an explicit wrapper/export step after generation.

| Gate | Owner | Required Evidence | Status Before Final Testing | Blocker Rule |
|---|---|---|---|---|
| Repository launch gate | Release captain | `python3 scripts/ci/validate_final_testing_launch_gate.py` output attached to release notes. | REQUIRED_PASS | P0 Launch Blocker if failing. |
| Production-readiness foundation validator | Release engineering | `python3 scripts/ci/validate_production_readiness_plan.py` passes. | REQUIRED_PASS | P0 Launch Blocker if P0 foundation is missing; P1 Launch Blocker for P1/P2 foundation drift. |
| Platform contract lint | Platform owner | `python3 scripts/ci/platform_contract_lint.py` reports zero errors and zero warnings. | REQUIRED_PASS | P0 Launch Blocker for errors in critical agent execution paths; P1 Launch Blocker for warnings without waiver. |
| Secret and artifact hygiene | Security owner | Launch artifacts contain no raw secrets, private keys, bearer tokens, or unredacted provider credentials. | REQUIRED_PASS | P0 Launch Blocker if a secret-like value is found. |
| Dependency coverage | Build owner | `python3 scripts/ci/check_dependabot_coverage.py` passes. | REQUIRED_PASS | P1 Launch Blocker if dependency manifests are uncovered. |
| Production-like E2E rehearsal | Test owner | Browser-executed critical workflow, real login, backend health, and persisted state evidence. | REQUIRES_ENVIRONMENT | P0 Launch Blocker until completed or removed from launch scope. |
| Rollback and restore drill | SRE owner | Redacted transcript of deploy rollback and data restore or restore simulation. | REQUIRES_ENVIRONMENT | P0 Launch Blocker if rollback cannot be executed. |
| Observability and paging | SRE owner | Dashboard links, alert receiver proof, on-call route, and log-redaction sample. | REQUIRES_ENVIRONMENT | P1 Launch Blocker unless launch owner accepts monitored workaround. |

## Launch-Blocker Classification

| Classification | Description | Required Action |
|---|---|---|
| P0 Launch Blocker | A release risk that can compromise security, data integrity, availability, rollback, or the primary user journey. | Fix, remove from scope, or obtain explicit launch-owner risk acceptance before final testing. |
| P1 Launch Blocker | A high-impact risk with bounded blast radius or a credible workaround. | Assign owner, mitigation, validation plan, and decision date before final testing. |
| P2 Follow-Up | A known improvement that does not materially increase launch risk when tracked. | Track with owner and post-launch target date. |

## Required Final-Testing Entry Decision

| Decision Field | Required Value Before Final Testing |
|---|---|
| Release candidate commit | Exact Git SHA under test. |
| P0 Launch Blockers | Zero open, or explicitly removed from launch scope. |
| P1 Launch Blockers | All owned with mitigations and decision dates. |
| Environment-only gates | All assigned to staging/live evidence owners. |
| Rollback owner | Named individual and backup. |
| On-call owner | Named individual and escalation path. |
| Go/no-go meeting | Scheduled before launch freeze lifts. |
