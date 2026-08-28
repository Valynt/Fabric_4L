# Flaky CI Mitigation Design

## Purpose

Apply the study's flakiness mitigations to Fabric_4L's CI in a way that never lets
flakiness, external dependency outages, or workflow dependency handling silently
weaken the merge gate. The design centers on three mitigations — flaky-test
lifecycle, external-dependency isolation, and workflow-dependency handling — but
each is governed so that coverage removal and outage bypass require human review and
always fail closed.

## Authority and boundaries

This phase builds on and extends the existing test-debt governance control plane
(`config/ci/test_skip_register.yaml` + `scripts/ci/check_test_skip_governance.py`).
It does **not** create a parallel registry or a second independent policy evaluator.

- Flaky/quarantine exclusions are expressed in the existing canonical register as
  entries with `marker: flaky` (or `quarantine`), `launch_gate: excluded`, and the
  full required field set below. The canonical evaluator remains the sole authority.
- `scripts/ci/flakiness_tracker.py` stays the detection engine; it never edits the
  register.
- `scripts/ci/classify_failure.py` and any new dependency-status tooling are
  detection/reporting only.

No workflow may modify a required-test exclusion automatically. A compromised or
noisy test run must not be able to remove coverage from the merge gate.

## 1. External-dependency handling (isolate without bypassing required coverage)

GitHub reports conditionally skipped jobs as successful even when they are required
checks; therefore an outage gate must never authorize skipping required
verification.

### Guiding rules

- Remote-dependent tests may skip only when they are explicitly **non-required,
  informational** coverage.
- **Required** verification must use hermetic local services, mocks, recorded
  fixtures, or controlled test containers. It is never skipped on an outage.
- If a **required** external dependency is unavailable, the final readiness gate must
  fail with a distinct `EXTERNAL_DEPENDENCY_UNAVAILABLE` classification.
- An unknown state — probe error, timeout, or malformed response — is **not**
  classified as safely down. Only a well-formed probe that unambiguously identifies
  the dependency as unavailable may be classified `down`.
- A status-page response is **evidence**, not authorization to bypass required tests.

### External dependency registry

Add `config/ci/external_dependencies.yaml` with one required field set per service:

- `service`: stable identifier;
- `classification`: `hermetic` | `controlled` | `third_party`;
- `consuming_jobs`: list of jobs/workflows that consume it;
- `coverage`: `required` | `informational`;
- `probe`: URL, expected status, and schema;
- `probe_timeout_seconds` and `retry_policy` (retries, backoff, total budget);
- `failure_owner`: accountable team/person for a hard `EXTERNAL_DEPENDENCY_UNAVAILABLE`;
- `hostname_allowlist`: approved hostnames only. No arbitrary PR-controlled URLs,
  no secrets, and the probe target must be validated against the allowlist before any
  network request.

### Gate semantics

- A `check-external-deps` step probes all registered services and writes
  `reports/external-dep-status.json` with a per-service conclusion
  (`up` | `down` | `unknown` | `unavailable_required`).
- `informational` consuming jobs whose dependency is unambiguously `down` may be
  marked skipped (safe — they are non-required).
- A `required` dependency that is `down`/`unknown` produces
  `EXTERNAL_DEPENDENCY_UNAVAILABLE`, surfaced to the final readiness gate, which
  fails. It is never a silent skip.

This follows the repo's fail-closed governance rule (docs/governance/
behavior-first-testing.md and the test-debt governance spec): required verification
that cannot run is a failure, not a passing result.

## 2. Flaky-test lifecycle (separate detection, registration, exclusion)

The registry alone is not auto-quarantine because it excludes tests only after a
human adds them. Use three explicit stages.

### Stage 1 — Detection
`flakiness_tracker.py` (existing) runs the suite N times and produces **statistically
credible candidates** (nodeid, pass rate, retry evidence). Detection output is
candidate evidence only.

### Stage 2 — Registration (automation proposes, never applies)
Automation opens a **proposed** registry change (PR) or a governance issue carrying
the evidence for each candidate. It does not edit `test_skip_register.yaml`.

### Stage 3 — Exclusion (quarantine only after review + ownership)
Quarantine begins only after a reviewer assigns ownership and merges the proposed
entry. Until then the test is not excluded from any gate.

### Required entry fields (flaky/quarantine entries in the canonical register)

- `id` (stable identity)
- `nodeid` (pytest node id)
- `owner` (accountable team/person)
- `introduced_or_detected_on`
- `expires_on` (time-boxed; a quarantined test is never indefinite)
- `issue` (tracking issue/PR reference)
- `failure_evidence` (report/artifact pointer with pass-rate + retry evidence)
- `affected_gate` (which launch gate / profile the exclusion applies to)
- `retry_count`
- `status` (e.g. `proposed` | `active` | `renewed` | `resolved`)

The existing register fields (`path_pattern`, `marker: flaky`, `classification`,
`disposition`, `launch_gate: excluded`, `remediation`) remain and are reconciled
together with these flaky-specific fields.

### Expired-entry behavior (fail closed, no silent re-enable)

An expired flaky entry fails `check-flaky-debt` **explicitly**. The evaluator never
silently re-enables the test and relies on its possibly flaky result to force
triage. The governance failure must clearly state that the **quarantine has expired**
and name the owner, nodeid, and due date. Resolution is a reviewed action:
renew with justification, or fix and remove the entry. Until then the gate blocks
(with the explicit `quarantine expired` code), keeping the merge gate fail-closed.

## 3. Narrow dependency-skip changes

GitHub already skips dependent jobs when a job in `needs` fails or is skipped. Explicit
`needs.<dep>.result != 'success'` conditions are therefore unnecessary for ordinary
jobs; they matter only where an existing `always()`/`failure()` overrides the default.

### Required approach

- **Inventory** every job using `always()`, `failure()`, or a custom result condition
  (existing inventory exists in `pr-checks.yml`; formalize it as a reviewed list).
- **Distinguish** aggregator/reporting jobs from executable test jobs.
- **Preserve** `always()` on final aggregators so failures remain visible in the PR
  required-check list.
- **Remove or constrain** `always()` only where it causes real downstream executable
  work to run after a failed prerequisite.
- **Final required aggregator** (`unified-readiness-gate` and the aggregate jobs) runs
  unconditionally (guarded aggregation, not bare `always()` for execution) and fails if
  any required job is failed, cancelled, skipped unexpectedly, or not executed.

Do not add redundant `needs.<dep>.result != 'success'` conditions across every job.

## 4. Cross-workflow dependencies as orchestration, not skipping

A `workflow_run` workflow is triggered regardless of the upstream conclusion; its jobs
then inspect `github.event.workflow_run.conclusion`.

### For deployment workflows (`build-deploy.yml`, `deploy.yml`, `certify-release-candidate.yml`, ...)

- Run deployment **only** when the triggering workflow concluded `success`.
- Add a companion **reporting job** for non-success conclusions so the reason is
  visible, rather than silently doing nothing.
- **Validate** the triggering workflow's branch, repository, event type, and head SHA
  before acting.
- **Never download or execute untrusted artifacts** from a privileged `workflow_run`
  without provenance validation (signature/hash/expected artifact name).
- Ensure required checks do not disappear or become silently successful because an
  entire workflow was filtered out by `paths:` filters — use `workflow_run` conclusion
  + provenance checks, and keep required-check visibility explicit.

## Components

- `config/ci/external_dependencies.yaml` — external dependency registry (new).
- `scripts/ci/external_dep_status.py` — pure probe + classification engine (new);
  returns typed conclusions; used by a `check-external-deps` CI step.
- `scripts/ci/flakiness_tracker.py` — unchanged detection engine (existing), enhanced
  only to emit candidate evidence consumable by the registration automation.
- `config/ci/test_skip_register.yaml` — extended schema for flaky/quarantine entries
  (adds the flaky-specific fields in §2).
- `scripts/ci/check_test_skip_governance.py` — canonical evaluator extended to emit a
  distinct `quarantine expired` code and to reject missing flaky evidence fields.
- `pr-checks.yml` + deployment workflows — targeted `always()`/result-condition
  corrections per §3 and §4, plus deployment orchestration per §4.

## Testing

- **Unit tests** (`tests/ci/`) for:
  - `external_dep_status.py`: probe parsing, allowlist enforcement, timeout/retry,
    `up`/`down`/`unknown`/`unavailable_required` classification, and the rule that an
    unknown/timeout/malformed response is never classified `down`.
  - Flaky registry validation: required-field completeness, expiry → explicit
    `quarantine expired`, no auto-re-enable.
- **Workflow-policy tests**: prove that skipped **required** coverage cannot produce a
  green readiness result. Specifically: a required dependency unavailable
  → `EXTERNAL_DEPENDENCY_UNAVAILABLE` and the readiness gate fails; an informational
  dependency down → job may skip; the final aggregator fails when any required job is
  failed/cancelled/skipped-unexpectedly/not-executed.

## Validation and rollout

1. Add failing characterization/workflow-policy tests for the approved behavior.
2. Implement the new/updated scripts and the registry schema until tests pass.
3. Extend the canonical evaluator with the `quarantine expired` code and field checks;
   reconcile existing flaky/quarantine markers already present in the repo.
4. Wire `check-external-deps` and the fail-closed readiness classification into
   `pr-checks.yml` and the deployment orchestration.
5. Run structural preflight, the relevant CI/governance suites, and the broadest
   feasible repository verification.

No runtime improvement is claimed unless measured. Any full-repository check blocked by
unavailable external services is reported with the exact command, failure, and residual
risk; it is not converted into a passing result.
