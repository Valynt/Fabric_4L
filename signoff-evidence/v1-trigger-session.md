# V1.0.0 Trigger Session — Human Checklist

- **UTC:** 2026-08-11T05:30:00Z
- **Purpose:** the exact ordered checklist that ships v1.0.0. Every step references its packet by post-merge main URL (links resolve once the packets PR merges — see the PR for the pre-merge view).
- **Kept current:** re-validated against repo state on every goal turn.

Base URL: `https://github.com/bmsull560/Fabric_4L/blob/main/`

## Execution order

1. ~~**Publisher merges #1267** (V1-PROVISION-001)~~ — **DONE** 2026-08-11T05:25:59Z, merge commit `1388e683e`. All 8 required contexts SUCCESS on gates head `6e1d32c5328e9c89a8906d43c7a72a78a03edfdc` (verified 2026-08-11T05:27Z): Structural Preflight, contract-compliance, prod-readiness, mandatory-security-regression, behavior-tests, Layer 5 - Source Contract, Layer 5 - Tenant Isolation Regression, Layer 5 - Contract Shape Regression. #1256 closed by the repo owner with the staged-fix evidence comment. — [publisher-runbook.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/publisher-runbook.md) merged-table row 9.
2. **Publisher applies workflow patch 1 of 4** (one command): `git apply signoff-evidence/gates/workflow-patches/ci-tools-preflight-uv-version.patch`, human-opened PR, CODEOWNERS platform/security approval, merge. Unblocks CI Tools Image Preflight + Supply Chain Summary on all PRs. — [ci-tools-preflight-uv-version.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/workflow-patches/ci-tools-preflight-uv-version.md).
3. **Publisher applies workflow patches 2 and 3 of 4** (same workflow, disjoint hunks): `git apply signoff-evidence/gates/workflow-patches/ai-evals-path-filter.patch` and `git apply signoff-evidence/gates/workflow-patches/ai-evals-golden-traces-fail-closed.patch`, human-opened PR, merge; then close #1259 per its issue comment. Note: the fail-closed patch makes the missing golden-trace suite visible — author the suite (V1-EVALS-001) or the workflow owner re-scopes the job. — [ai-evals-path-filter.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/workflow-patches/ai-evals-path-filter.md), [ai-evals-golden-traces-fail-closed.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/workflow-patches/ai-evals-golden-traces-fail-closed.md).
4. **Author decomposes #1252** per the review packet's 4-PR split (claim-type taxonomy → gateway orchestration delegation → delegation router → Meridian suite); Publisher merges each after independent review. Do NOT merge #1252 as-is (blocking defects F-1/F-2). — [v1-routing-001-decomposition-review.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/v1-routing-001-decomposition-review.md).
5. **Publisher applies workflow patch 4 of 4 (V1-CI-001 stage 1)** — only after steps 3–4 land: informational nine-aggregate fan-in + `merge_group` triggers. Stages 3–4 (branch-protection convergence) stay human-sequenced after shadow parity. — [v1-ci-001.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/workflow-patches/v1-ci-001.md), [v1-ci-001-design.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/workflow-patches/v1-ci-001-design.md).
6. **Product + Release Management record `paid_billing_in_scope`** — recommendation: OUT of scope for v1.0.0 (PRR-007 exit criteria unmet for paid launch). — [paid-billing-scope.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/paid-billing-scope.md).
7. **Product + Platform Architecture record `live_llm_workflows_mandatory`** — recommendation: mandatory at RC certification of j02 only, conditional on step 3. — [live-llm-workflows.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/live-llm-workflows.md).
8. **Named authority records the j03 decision** — recommendation: descope to implemented same-tenant impersonation for v1.0.0. — [j03-support-admin.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/j03-support-admin.md).
9. **Risk owners sign waivers with expiry 2026-08-25** — PRR-002/003/006/008/010 drafts (schema-conformant); PRR-007 superseded by step 6. — [risk-waivers.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/risk-waivers.md).
10. **Platform/Infra provisions staging** — one signature provisions services + fixtures + env names. — [staging-environment-request.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/staging-environment-request.md).
11. **Run staging evidence in order**: #1257 DR drill (`make test-backup-drills`, `make check-migration-postgres-roundtrip`, WAL-G restore evidence) → #1260 golden path (`make certify-meridian-journey`, `make test-backend-integrated-release-smoke`, `pnpm --dir apps/web run test:e2e:live`) → #1261 observability (`pytest tests/observability tests/reliability tests/recovery` + receiver delivery). — [staging-environment-request.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/staging-environment-request.md) §2.4.
12. **Certifier runs canonical certification at the merged candidate SHA on staging**: `make validate-launch-contract && make release-baseline && CERTIFY_LIVE=1 make certify-release-candidate RELEASE_SHA=<sha> && make build-release-evidence RELEASE_SHA=<sha>`; independent reviewer confirms from a fresh read-only checkout. — [v1-certification.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/v1-certification.md) (current reds and named unblocks).
13. **Production Authority reviews the rollout brief** (digest-deploy requirement, rollback triggers, expand-contract window). — [production-authority-brief.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/production-authority-brief.md).
14. **Tag v1.0.0** with the drafted message (drafted at certification-green time; see §6 of the mission protocol).
15. **Production Authority deploys** per packet (f); rollback armed per the expand-contract window. — [production-authority-brief.md](https://github.com/bmsull560/Fabric_4L/blob/main/signoff-evidence/gates/production-authority-brief.md).
16. **Post-live:** confirm the five critical journeys on production; watch SLIs against contract targets (`monitoring/prometheus/alerting/rules.yml`).

## One-signature acknowledgment

```
Trigger session checklist reviewed; execution begins at step 1.
Name: ______________  Role: Release Management  Date (UTC): __________
```
