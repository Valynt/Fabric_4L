# Repository Health Remediation — July 2026

This ledger reconciles the repository-health audit supplied on 2026-07-15 with
the current `main` branch. It is the source of truth for closure status; the
original audit remains input evidence rather than an implementation checklist.

## Status Model

| Status | Meaning |
| --- | --- |
| `VERIFIED_OPEN` | Current repository or external evidence proves work remains. |
| `IMPLEMENTED_UNVERIFIED` | A remediation landed, but its acceptance gate has not passed in this audit. |
| `VERIFIED_CLOSED` | The remediation and its acceptance evidence both exist. |
| `INVALID` | Current repository evidence disproves the original finding. |
| `EXTERNAL_VERIFICATION_REQUIRED` | Closure depends on state outside the repository. |

## Finding Ledger

| ID | Status | Current evidence | Closure gate | Delivery |
| --- | --- | --- | --- | --- |
| SEC-001 | `VERIFIED_CLOSED` | PR #1000 merged least-privilege workflow defaults and job-scoped writes; the permission and registry gates pass on the merged baseline. | `python -m pytest tests/ci/test_workflow_permissions.py -q`; workflow registry checks; required-check names unchanged. | PR #1000. |
| SEC-002 | `EXTERNAL_VERIFICATION_REQUIRED` | `docs/development/REPOWISE.md` documents safe storage and rotation; repository inspection cannot prove that the exposed credential was revoked. | Old credential rejected; replacement limited to the intended repository and tools; only redacted evidence recorded. | External rotation plus ledger-only evidence update. |
| TEST-001 | `VERIFIED_CLOSED` | The collection-backed skip gate passed with three owned, classified, unexpired allowlisted skips; register uniqueness and all twelve checker tests passed. | `make check-pytest-skip-governance`; register uniqueness check; checker tests. | Evidence-only closure; no code PR required. |
| QUAL-001 | `VERIFIED_CLOSED` | PR #1003 excludes generated SDK code, adds tested Make/pnpm entrypoints, and wires the ratchet into structural preflight. The gate passed with 6,829 approved occurrences and no net-new escapes. | Dedicated unit tests; `make check-type-escape-ratchet`; `pnpm check:type-escapes`; structural PR wiring. | PR #1003. |
| ARCH-001 | `VERIFIED_OPEN` | PR #1005 repaired a schema-extraction import regression and restored collection of all twelve focused analysis-route tests. Executing an individual async route test still exceeds a 10-second timeout inside ASGI request handling, so characterization is not execution-verified. | Diagnose the route-test hang; execute focused Layer 4 characterization; then complete frontend, Layer 1, and Layer 5 characterization and contract/type checks. | PR #1005 plus follow-up characterization work. |
| DOC-001 | `INVALID` | Root `CODEOWNERS`, `RUNBOOK.md`, `TESTING.md`, and `THREAT_MODEL.md` exist; `.github/CODEOWNERS` is the GitHub source of truth. Missing root duplicates are not evidence that canonical nested documentation is absent. | Documentation link tests pass; root files remain lightweight indexes. | No duplicate root documents. |
| DOC-002 | `IMPLEMENTED_UNVERIFIED` | A second README command table still overstated `make setup`; PR #1002 corrects it and adds a passing documentation contract, but the PR remains unmerged. | Compare README with the `setup` target and `BUILD_SYSTEM.md`; docs tests pass on merged main. | PR #1002. |
| CICD-001 | `VERIFIED_CLOSED` | PR #1004 merged generated `CI_GATES.md` coverage for all active workflows, removed the formally retired smoke workflow, and wired documentation drift into the registry gate. | Workflow inventory matches active YAML and documents trigger, classification, owner, command, dependencies, artifacts, and triage. | PR #1004. |
| REL-001 | `VERIFIED_CLOSED` | Both `pnpm ops:runbooks:lint` and `pnpm ops:incident:check` pass; the documentation command-map suite also passes. | Docs link tests and incident/runbook governance checks pass. | Evidence-only closure; no code PR required. |
| AGENT-001 | `VERIFIED_CLOSED` | PR #1001 added the minimal `.windsurf/AGENTS.md` registry and canonical-instruction pointers with documentation contract coverage. | Minimal registry exists and points to canonical instructions without copying them. | PR #1001. |
| DX-001 | `VERIFIED_CLOSED` | The command-map suite passes and merged PR #1004 links CI classification back into `DISCOVERY_MAP.md`. | Docs command-map tests pass and CI gate mapping links back to these sources. | PR #1004 plus evidence-only closure. |

## Baseline Evidence

The initial focused run on branch `audit/repository-health-remediation` used:

```text
python -m pytest \
  tests/ci/test_workflow_permissions.py \
  tests/ci/test_check_pytest_skip_governance.py \
  tests/ci/test_test_skip_governance.py -q
```

Result: 15 tests collected, 13 passed, and 2 workflow-permission tests failed.
The failures are assigned to SEC-001; they are not treated as regressions caused
by the remediation branch.

## Closure Evidence — 2026-07-15

- SEC-001: PR #1000 merged; workflow-permission tests passed (3/3) after rebasing dependent work onto merged main.
- TEST-001: collection-backed gate passed; register uniqueness passed; checker tests passed (12/12).
- QUAL-001: PR #1003 merged; focused/docs tests passed (32/32), Make and pnpm ratchets passed, and workflow drift gates passed.
- AGENT-001: PR #1001 merged; focused agent registry and command-map tests passed (30/30).
- CICD-001: PR #1004 merged; combined CI governance suite passed (54/54) and both workflow drift gates passed.
- REL-001 and DX-001: runbook lint, incident governance, and command-map tests passed (28/28).
- ARCH-001: PR #1005 merged and collection succeeds, but focused async route execution timed out; finding remains open.
- DOC-002: PR #1002 is open and ready, but closure requires merge plus mainline documentation tests.
- SEC-002: external credential revocation remains unverifiable from repository state.

## Execution Order

1. SEC-001 — restore a trustworthy least-privilege workflow baseline.
2. AGENT-001 and DOC-002 verification — make instructions and setup reliable.
3. TEST-001 and QUAL-001 — make skip and type-debt gates executable.
4. CICD-001, REL-001, and DX-001 — complete operational discoverability.
5. ARCH-001 — characterize and repair hotspot extractions behind stable gates.
6. Re-run the weighted audit and the production-readiness ladder.

Each verified-open finding is delivered independently. A finding moves to
`VERIFIED_CLOSED` only when its stated closure command or external evidence is
recorded; a merged implementation alone is insufficient.
