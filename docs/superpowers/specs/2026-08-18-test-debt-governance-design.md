# Test-Debt Governance Consolidation Design

## Purpose

Fabric_4L will use one fail-closed control plane for test skips, expected failures,
Playwright fixmes, and focused-test markers. The consolidation makes existing debt
measurable and actionable without combining this governance change with broad test
remediation or test-directory restructuring.

## Authority and boundaries

`config/ci/test_skip_register.yaml` is the only human-maintained test-debt
inventory. `scripts/ci/check_test_skip_governance.py` is the sole policy evaluator
and report producer. Existing Make targets and command names may remain as thin
compatibility delegates, but they must not parse alternate inventories or implement
independent policy.

Static repository scanning is authoritative for debt discovery. Pytest collection
and runtime output is subordinate evidence used for metrics and reconciliation; it
cannot authorize a marker that is absent from the canonical register.

This phase does not reorganize test directories, rewrite service suites, remove
legitimate environment-dependent exceptions, or remediate hundreds of existing
markers. Small test or configuration fixes are permitted only when required to
establish and prove the consolidated governance behavior.

## Canonical register model

Every governed exception has these required fields:

- `id`: globally unique stable identity;
- `path_pattern`: exact test ownership surface, expressed as a repository-relative
  path or narrowly bounded glob;
- `marker`: supported pytest or Playwright debt marker;
- `reason_pattern`: a non-empty expression that identifies the governed marker;
- `reason`: human-readable policy rationale;
- `classification`: one of `valid_environment_limitation`,
  `temporary_bug_waiver`, `obsolete_test`, or `unacceptable_coverage_gap`;
- `severity`: one of `P0`, `P1`, or `P2`;
- `launch_gate`: one of `mandatory`, `optional`, or `excluded`;
- `owner`: accountable team or person;
- `remediation.ticket_id`, `remediation.work_item`, and `remediation.due_on`;
- `expires_on`: last date on which the exception remains valid; and
- `disposition`: one of `retain`, `remove`, `repair`, or
  `replace_with_characterization`.

`VALID` is a derived inventory group for legitimate environment limitations with
the `retain` disposition. It is not a severity and cannot hide the risk ranking of
other debt.

The evaluator rejects missing fields, empty ownership or rationale, malformed dates
or patterns, expired entries, duplicate identities, duplicate reconciliation keys,
unsupported enum values, conflicting due and expiry dates, invalid
classification/disposition combinations, and overly broad or out-of-scope paths.
One finding must match exactly one active entry; zero matches are unregistered debt
and multiple matches are ambiguous governance.

## Repository coverage

The evaluator discovers test-bearing files under these intentional surfaces:

- `tests/`, including contract, security, release, CI, and governance suites;
- every `services/**/tests/` directory, including nested harness suites; and
- `apps/web/e2e/`.

Supported source extensions cover Python and the JavaScript/TypeScript variants used
by Playwright. Explicit exclusions cover version-control metadata, dependency trees,
virtual environments, caches, build products, coverage output, Playwright reports,
and generated test results. Scanner-characterization fixture text is isolated by the
tests rather than excluded through production path blind spots.

The scanner recognizes `pytest.skip`, pytest skip/skipif and xfail decorators,
Playwright `test.skip` and `test.fixme`, and suite/test skip forms already governed by
the repository. `test.only`, `describe.only`, and `it.only` are always forbidden and
cannot be registered.

## Policy and fail-closed behavior

The authoritative evaluator performs, in one run:

1. register schema and semantic validation;
2. repository test-surface discovery;
3. static marker detection;
4. exact entry-to-finding reconciliation;
5. duplicate, ambiguity, expiry, temporal-language, and stale/orphan checks;
6. focused-marker and critical-path enforcement;
7. runtime/collection evidence reconciliation when evidence is supplied;
8. inventory, metrics, and deterministic remediation ranking; and
9. structured JSON, Markdown, console, and GitHub-step-summary reporting.

Stable machine-readable violation codes identify every failure category. Net-new
unregistered debt, expired or malformed registrations, duplicate or ambiguous
matches, stale/orphan entries, forbidden focused markers, prohibited critical-path
debt, and markers exposed in previously unscanned service locations fail the gate.
Warnings never replace these failures.

Critical-path detection covers security, tenant isolation, authentication and
authorization, API gateway behavior, cross-layer contracts, golden-path journeys,
persistence/security boundaries, and release certification. Critical paths cannot
use `obsolete_test`, indefinite waivers, or dispositions that merely retain an
unacceptable coverage gap. A legitimate environment limitation must identify a real
optional external capability; it cannot disguise a dependency required by the CI or
release profile that runs the test.

Temporal language and dates in marker reasons are governed by the register's ticket,
due date, and expiry rather than by a separate temporal baseline. Existing pytest
skip allowlists and baselines are migrated into the canonical register before their
independent policy role is removed.

## Components

The evaluator remains one command but separates focused internal units for register
loading, source discovery, marker scanning, reconciliation, policy evaluation,
ranking, and rendering. These units exchange typed findings, register entries,
violations, and reports so characterization tests can exercise real policy without
shelling out for every case.

Legacy temporal, uniqueness, and collection-governance commands become delegates to
the canonical evaluator or are removed after every caller is migrated. Compatibility
delegates forward relevant paths and output options and return the authoritative
exit status. They define no markers, classifications, scan roots, thresholds,
allowlists, or waiver behavior.

## Reports, inventory, and remediation ranking

The JSON report is the machine-readable authority and includes a schema version,
command metadata, elapsed governance time, scanned surfaces and files, detected
marker totals by type, registered totals by classification/severity/launch gate/
owner/disposition, reconciliation counts, runtime evidence metrics, violations with
stable codes, and ranked inventory.

The Markdown report renders the same information for reviewers. Inventory groups are:

- `P0`: critical-path coverage gaps and mandatory launch blockers;
- `P1`: important executable debt;
- `P2`: cleanup, obsolete, or low-risk debt; and
- `VALID`: legitimate retained environment-dependent exceptions.

P0 remediation ranking is deterministic. It orders by critical-path domain risk,
then mandatory launch relevance, classification risk, due/expiry date, path, and
entry identity. The next-wave queue highlights a small executable set with emphasis
on tenant isolation, authn/authz, gateway behavior, contracts, golden journeys,
persistence/security boundaries, and release certification. This generated queue
must be sufficient for a later agent to begin remediation without another
repository-wide discovery pass.

## Characterization testing

Temporary-repository fixtures prove both allowed and denied behavior through the
real evaluator.

Allowed cases cover a complete non-expired legitimate exception, a recognized
environment limitation, and an owned/ticketed/time-boxed temporary waiver in a path
where policy permits it.

Denied cases cover an unregistered marker, expired or malformed registration,
duplicate identity or reconciliation key, ambiguous match, focused marker, unknown
classification or severity, stale/orphan registration, prohibited critical-path
debt, and an attempted bypass from a previously unscanned service test directory.
Assertions use violation codes and exit outcomes rather than fragile prose.

Compatibility tests prove delegates return the canonical evaluator's decision and
contain no independent policy. Migration tests demonstrate that every exception
formerly accepted by an allowlist or baseline is represented in the canonical
register before those alternate data sources are removed.

## CI integration and rollout

Makefile, package scripts, structural preflight, pull-request checks, and
production-readiness profiles converge on the authoritative command. Existing
public target names are retained only when useful for compatibility and invoke the
same evaluator.

Rollout is fail-closed:

1. capture baseline timings and counts from all existing controls;
2. add failing characterization tests for the approved policy;
3. implement the canonical evaluator until the tests pass;
4. migrate alternate inventory data into the register;
5. compare old and new results and resolve any strictness regression;
6. switch callers to the authoritative evaluator;
7. remove or subordinate duplicate policy and inventories; and
8. capture post-change metrics and generate the remediation queue.

## Validation and evidence

Validation runs governance characterization tests first, then the authoritative
repository scan, compatibility targets, relevant CI/governance suites, structural
preflight and production-readiness integrations, and the broadest feasible
repository verification. Before/after evidence records collection time where
practical, relevant suite runtime, skip/xfail/fixme counts, registered counts by
classification/severity, duplicate and stale counts, and governance execution time.

No runtime improvement is claimed unless measured. Any full-repository check blocked
by unavailable external services or tools is reported with the exact command,
failure, and residual risk; it is not converted into a passing result.
