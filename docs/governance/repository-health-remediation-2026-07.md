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
| SEC-001 | `VERIFIED_OPEN` | `.github/workflows/pr-checks.yml` is read-first, but `tests/ci/test_workflow_permissions.py` reports seven workflows without explicit top-level permissions and thirteen unallowlisted write grants. | `python -m pytest tests/ci/test_workflow_permissions.py -q`; workflow registry checks; required-check names unchanged. | One CI-permissions PR. |
| SEC-002 | `EXTERNAL_VERIFICATION_REQUIRED` | `docs/development/REPOWISE.md` documents safe storage and rotation; repository inspection cannot prove that the exposed credential was revoked. | Old credential rejected; replacement limited to the intended repository and tools; only redacted evidence recorded. | External rotation plus ledger-only evidence update. |
| TEST-001 | `IMPLEMENTED_UNVERIFIED` | Skip baselines, allowlist, register, checker tests, owner fields, and expiry fields exist. Focused checker tests pass, but the collection-backed Make target has not run in this audit. | `make check-pytest-skip-governance`; register uniqueness check; checker tests. | One test-governance PR only if a gate fails. |
| QUAL-001 | `VERIFIED_OPEN` | `scripts/ci/type_escape_ratchet.py` and its baseline exist, but the SDK generated tree is not excluded, there is no dedicated regression test, and no public Make/pnpm/PR entrypoint invokes the ratchet. | Dedicated unit tests; `make check-type-escape-ratchet`; `pnpm check:type-escapes`; structural PR wiring. | One type-ratchet PR. |
| ARCH-001 | `IMPLEMENTED_UNVERIFIED` | Large frontend and backend modules were split into state/schema/contract modules, but no focused characterization tests reference the extracted modules. | New frontend, Layer 1, Layer 4, and Layer 5 characterization tests plus contract/type checks. | Separate frontend and backend characterization PRs if write sets diverge. |
| DOC-001 | `INVALID` | Root `CODEOWNERS`, `RUNBOOK.md`, `TESTING.md`, and `THREAT_MODEL.md` exist; `.github/CODEOWNERS` is the GitHub source of truth. Missing root duplicates are not evidence that canonical nested documentation is absent. | Documentation link tests pass; root files remain lightweight indexes. | No duplicate root documents. |
| DOC-002 | `IMPLEMENTED_UNVERIFIED` | README no longer claims `make setup` starts infrastructure or applies migrations and links the canonical setup path. | Compare README with the `setup` target and `BUILD_SYSTEM.md`; docs tests pass. | Documentation PR only if drift remains. |
| CICD-001 | `VERIFIED_OPEN` | `DISCOVERY_MAP.md` routes CI work, but no `docs/development/CI_GATES.md` authoritative workflow classification exists. | Workflow inventory matches active YAML and documents trigger, classification, owner, command, dependencies, artifacts, and triage. | One CI-documentation PR. |
| REL-001 | `IMPLEMENTED_UNVERIFIED` | Root `RUNBOOK.md` and nested operational indexes exist. Link validity and first-response coverage remain to be checked. | Docs link tests and incident/runbook governance checks pass. | Documentation PR only for verified gaps. |
| AGENT-001 | `VERIFIED_OPEN` | Root and nested active docs reference `.windsurf/AGENTS.md`, but that file is absent. | Minimal registry exists and points to canonical instructions without copying them. | One agent-governance PR. |
| DX-001 | `IMPLEMENTED_UNVERIFIED` | `BUILD_SYSTEM.md`, `COMMANDS.md`, and `DISCOVERY_MAP.md` provide task-oriented command routing. | Docs command-map tests pass and CI gate mapping links back to these sources. | Close with CICD-001 evidence. |

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
