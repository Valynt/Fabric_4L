# Level-10 Test Strategy

This document defines **HOW** the controls in `control_register.yaml` are proven. It MUST
NOT weaken any register requirement. Treat testing as an executable risk-control system:
every material failure mode maps to a test, an owner, an authoritative gate, an evidence
artifact, and a specific merge, release, or deployment decision.

## Level-10 outcome

Testing at Level 10 is:

- **Risk-based**, not coverage-driven.
- **Continuous**, from local dev through production.
- **Real** — executed against production-shaped dependencies where material.
- **Hostile** toward tenant isolation, authorization, migrations, and AI behavior.
- **Reproducible** from the exact source SHA, artifact digest, dependency locks, test seed,
  and environment definition.
- **Authoritative** — failed, missing, skipped, cancelled, stale, or inconclusive critical
  tests block the appropriate merge/release/deployment decision.
- **Production-proven** through at least 90 days of SLOs, synthetic journeys, deployments,
  rollback exercises, restore drills, and incident evidence.

## Test architecture — five environments

| Environment | Purpose | Dependencies |
|---|---|---|
| In-process | Fast unit, property, component, and policy tests | Mocks and deterministic fakes allowed |
| Container integration | Service integration and persistence behavior | Real pinned PostgreSQL, Redis, Neo4j, object storage |
| Ephemeral Kubernetes | Manifest, networking, deployment, migration, resilience testing | Production-like rendered manifests in kind |
| Certified staging | Full release-candidate validation | Same signed images and topology intended for production |
| Production | Synthetics, canaries, SLO validation, controlled drills | Real production infrastructure |

**Mocks are never sufficient evidence for release certification.**

## Test portfolio (20 areas)

The "Controls" column references the register entries each area proves. `AG-xx` means every
control under that gate.

| # | Test area | Required approach | Primary tools | Blocking gate | Controls |
|---|---|---|---|---|---|
| 1 | Static quality | Formatting, linting, type ratchets, complexity, dead-code and dependency-boundary checks | Ruff, mypy ratchet, ESLint, TypeScript, dependency-cruiser or equivalent | 02-code-quality-and-tests | CTRL-02-01..04, CTRL-02-10 |
| 2 | Unit behavior | Business invariants, state transitions, failures, retries, permissions, serialization | pytest, Vitest, React Testing Library | 02-code-quality-and-tests | CTRL-02-05, CTRL-02-09, CTRL-02-12 |
| 3 | Property testing | Generate malformed, extreme, reordered, duplicated, adversarial inputs | Hypothesis, fast-check | 02-code-quality-and-tests | CTRL-03-09 |
| 4 | Mutation testing | Prove critical tests detect meaningful logic changes | mutmut or cosmic-ray, StrykerJS | 02-code-quality-and-tests | CTRL-02-11 |
| 5 | API contracts | Generate tests from OpenAPI and detect incompatible changes | Schemathesis, OpenAPI diff, generated-client drift checks | 03-contract-compliance | CTRL-03-01..04, CTRL-03-10 |
| 6 | Cross-layer contracts | Verify L1–L6 request, response, event, error, tenancy, version semantics | pytest, JSON Schema, Pydantic, consumer contract fixtures | 03-contract-compliance | CTRL-03-05..08 |
| 7 | Service integration | Exercise services against real stores and queues | Testcontainers, Docker Compose, pytest | 02 and 03 | CTRL-02-07, CTRL-03-05..08 |
| 8 | Frontend components | Domain adapters, states, forms, authorization, cache behavior | Vitest, Testing Library, MSW | 02-code-quality-and-tests | CTRL-02-06, CTRL-05-02 |
| 9 | Browser journeys | Real user workflows across roles, tenants, browsers | Playwright, axe-core | 05-tenant-isolation-and-behavior | CTRL-02-08, CTRL-04-14, CTRL-05-03, CTRL-06-15, CTRL-06-16 |
| 10 | Security | SAST, secrets, dependencies, authenticated DAST, configuration and authorization testing | Semgrep, Gitleaks, Bandit, pip-audit, Trivy, OWASP ZAP | 04-security-gates | AG-04 (CTRL-04-01..17) |
| 11 | Tenant hostility | Attempt cross-tenant access across every storage and execution surface | pytest, Playwright, Schemathesis, custom hostile fixtures | 05-tenant-isolation-and-behavior | AG-05 (CTRL-05-01..14) |
| 12 | Migration safety | Fresh install, upgrade, compatibility, rollback window, data integrity, locks and backfills | Alembic, PostgreSQL, pytest, migration harness | 06-production-readiness | CTRL-06-12, CTRL-06-20, CTRL-06-25..36 |
| 13 | Kubernetes | Render, schema, policy, selector, securityContext, network validation | Helm/Kustomize, kubeconform, OPA/Conftest, kind | 06-production-readiness | CTRL-01-10, CTRL-06-01..08, CTRL-06-13 |
| 14 | Performance | Smoke, baseline, load, stress, spike, soak, capacity testing | k6 | 06-production-readiness | CTRL-06-21 |
| 15 | Resilience | Pod, network, dependency, DNS, resource, provider failures | Chaos Mesh, Toxiproxy | 06-production-readiness | CTRL-06-21 |
| 16 | Recovery | Automated backup, clean restore, rollback, integrity testing | WAL-G, pg_restore, application verification harness | 06-production-readiness | CTRL-06-17..19 |
| 17 | Supply chain | SBOM, vulnerability scanning, signing, provenance, admission | Trivy, Syft if needed, Cosign, OPA admission policy | 07-supply-chain-integrity | AG-07 (CTRL-07-01..12) |
| 18 | Observability | Validate telemetry, trace continuity, metrics, alerts, SLO rules | OpenTelemetry, Prometheus, promtool, Grafana, Jaeger/Tempo | 06-production-readiness | CTRL-06-09, CTRL-06-10, CTRL-06-22..24 |
| 19 | AI evaluation | Deterministic invariants, golden datasets, safety, quality, cost, provider degradation | L5 ground truth, L6 benchmark harness, pytest, PromptGuard | 02, 04, and 05 | CTRL-05-12, CTRL-02-11 (critical logic), AG-04 AI-facing checks |
| 20 | Evidence | Bind results to exact SHA, digest, environment, seed | JUnit, SARIF, Playwright traces, JSON evidence manifest | 08-release-evidence | AG-08 (CTRL-08-01..07) |

LLM-as-judge results MUST never be the sole blocking evidence; critical checks MUST also
include deterministic schema, policy, provenance, tool-use, and tenant-isolation assertions.

## Fabric_4L-specific coverage

- **API gateway** — backend-authoritative authorization snapshots; missing/expired/
  malformed/replayed/conflicting snapshots; tenant and account scope; rate limits, quotas,
  audit events, correlation IDs, error redaction; direct layer access denial;
  timeout/retry/circuit-breaker behavior; undocumented-route rejection.
- **Layer 1 ingestion and workers** — duplicate/out-of-order events; durable idempotency;
  queue-envelope tenant binding; backpressure and bounded queue growth; worker kill
  switches; retry and DLQ behavior; PostgreSQL or Redis interruption; crash between
  receipt, persistence, acknowledgment; no duplicated logical operation after recovery.
- **Layer 2 extraction** — malformed documents and encodings; oversized/deeply nested
  inputs; parser timeouts and resource limits; property-based extraction inputs;
  deterministic output schema; provenance preservation; tenant context through asynchronous
  extraction; partial extraction and retry semantics.
- **Layer 3 knowledge** — PostgreSQL and Neo4j consistency; transactional outbox or saga
  recovery; Cypher safety; tenant-scoped graph traversal; constraint and index presence;
  duplicate relationships and replay; reconciliation after partial write failure; graph and
  vector retrieval isolation.
- **Layer 4 agents** — LangGraph state transitions; tool allowlists and least privilege;
  approval requirements for irreversible actions; token/cost/step/time budgets; prompt
  injection and poisoned retrieval; provider timeout, malformed response, rate limiting;
  deterministic fallback behavior; explicit metadata identifying which tier answered and
  why; no silent heuristic or mock substitution; tenant-safe prompts, memory, traces, tool
  arguments.
- **Layer 5 ground truth and evidence** — evidence provenance and immutability;
  source-to-claim traceability; citation correctness; scoring calibration; stale or
  contradictory evidence behavior; tenant and account scope; deterministic golden datasets;
  human-reviewed evaluation samples.
- **Layer 6 benchmarks** — dataset versioning and leakage prevention; reproducible
  evaluation runs; quality, safety, latency, cost thresholds; regression confidence
  intervals; provider and model comparison; judge-model calibration against human
  judgments; fail-closed behavior when evaluations are missing.
- **Frontend and the ValuePilot canonical route MUST cover**: seller, reviewer, tenant
  administrator, unauthorized users; Tenant A success and Tenant B denial; account loading
  and switching; authorization loading/verified/denied/expired states; ROI input and
  calculation; evidence matching; value-case generation; version history and publishing;
  partial backend failure and retry; query-cache separation by identity, tenant, account,
  authorization discriminator; no raw DTO use past the adapter boundary; accessibility and
  keyboard operation; Chromium, Firefox, WebKit release coverage. Playwright screenshot
  comparison only from a pinned Linux environment.

## Tenant-hostility protocol

Canonical hostile dataset: Tenant A and Tenant B; real resources for both tenants;
shared-looking account names and identifiers; seller, reviewer, administrator, support
identities; expired and prior-session credentials; foreign object-storage objects; foreign
graph nodes and vector records; foreign queue messages; signed URLs that are valid,
expired, and already used.

For each protected operation, the test MUST verify:

1. Tenant A can access its own existing resource.
2. Tenant B's foreign resource is confirmed to exist.
3. Tenant A cannot read, mutate, delete, infer, or replay Tenant B's resource.
4. Denial occurs before sensitive data is loaded.
5. The audit event contains the acting tenant but does not leak foreign data.
6. Caches, traces, and error messages do not reveal resource existence.

**A random nonexistent ID returning 404 is not proof of tenant isolation.**

## Test-data and mocking policy

- **Allowed mocks**: pure unit tests; provider error simulation; time and randomness
  control; expensive LLM calls during fast lanes; unreachable failure branches.
- **Required real dependencies**: PostgreSQL constraints and migrations; Redis queue, TTL,
  idempotency behavior; Neo4j Cypher, constraints, graph traversal; object-storage prefix
  and signed-URL behavior; HTTP serialization and timeout behavior; Kubernetes routing and
  NetworkPolicies.
- **Rules**: every mock MUST implement the same contract as the production adapter; mock
  results MUST be explicitly tagged; production configuration MUST make mock activation
  structurally impossible; release certification MUST use real internal dependencies;
  external AI providers require controlled live release tests with budget caps.
- **Mocks are never sufficient evidence** for release certification.

## Execution lanes (8)

| Lane | Target duration | Contents | Decision |
|---|---|---|---|
| Developer changed-scope | Under 2 minutes | Formatting, lint, affected unit tests, type checks | Local feedback |
| Pull request fast lane | Under 15 minutes p95 | Static checks, unit, component, property, affected contracts | PR eligibility |
| Pull request complete lane | Under 30 minutes p95 | All layer tests, integrations, hostile tenancy, migration and manifest checks | Merge eligibility |
| Merge-group lane | Under 30 minutes p95 | Full authoritative merge suite against actual merged SHA | Merge authorization |
| Release-candidate lane | Under 90 minutes p95 | Ephemeral deployment, live E2E, DAST, performance smoke, artifact and migration certification | Release authorization |
| Nightly | Under 4 hours | Full fuzzing, mutation, cross-browser, extended AI evals, dependency scans | Feeds release evidence |
| Weekly | Defined per exercise | Soak, stress, chaos, backup restore, rollback rehearsal | Feeds release evidence |
| Production continuous | Always running | Synthetics, canaries, SLOs, artifact verification | Deployment and operating status |

Scheduled tests are not advisory: a failed or stale nightly/weekly critical result MUST
cause AG-08 (08-release-evidence) to block the next release.

## Performance and resilience requirements

- k6 checks carry functional assertions; thresholds carry authoritative pass/fail (checks
  alone do not necessarily fail a run; thresholds do).
- **Required profiles**: smoke (every release candidate); baseline; load (sustained 50
  RPS); burst (100 RPS); capacity (at least 3× expected launch peak); stress; soak;
  recovery.
- **Minimum thresholds**: application error rate < 0.5%; background-job success > 99.5%;
  no cross-tenant failure under load; no duplicate business operations; queue growth
  bounded; recovery within declared RTO; journey-specific p95 and p99 latency thresholds.
- **Chaos scenarios (12)**: gateway pod termination; worker termination mid-operation;
  PostgreSQL connection exhaustion; Redis interruption; Neo4j degradation; queue backlog;
  DNS failure; network latency and packet loss; LLM provider timeout and rate limiting;
  object-storage latency; expired credentials; partial node or availability-zone loss.

## Infrastructure test sequence

Per production overlay, the 10-step sequence: render Helm/Kustomize output → validate
Kubernetes schemas → apply OPA policies → verify workload and NetworkPolicy selectors →
deploy to kind → test connectivity and direct-access denial → run migrations → run smoke
and hostile journeys → verify metrics/traces/alerts → destroy environment cleanly. OPA
policy tests run with fail-on-empty behavior so CI cannot pass when no infrastructure-policy
tests were discovered.

**Required infrastructure policies (11)**: gateway-only public ingress; default-deny
networking; non-root containers; no privilege escalation; dropped Linux capabilities;
read-only root filesystem where compatible; resource requests and limits; approved
registries; digest-only images; required probes and disruption budgets; no plaintext
production secrets.

## Security and supply-chain test sequence

1. Semgrep and language-specific SAST. 2. Full-history and current-tree secret scanning.
3. Dependency review and vulnerability scanning. 4. Authenticated API and browser security
tests. 5. OWASP ZAP through the gateway. 6. Container and Kubernetes misconfiguration
scans. 7. SBOM generation. 8. Image signing and provenance. 9. Admission verification.
10. Independent penetration testing before GA.

## Observability as a test oracle

Tests assert operational effects: required spans emitted; HTTP, queue producer, queue
consumer, and agent spans form one trace; correlation IDs persist through L1–L6; audit
events identify actor, tenant, action, outcome; sensitive content does not enter telemetry;
required metrics increment; SLO recording rules evaluate; alerts fire and reach the correct
receiver; recovery clears the alert.

## Evidence field list (17 fields)

Every authoritative test run MUST retain all of the following; the record MUST validate
against `evidence_schema.json`:

```yaml
source_sha:
merge_group_sha:
artifact_digest:
workflow_run_id:
environment_id:
test_suite_version:
dependency_lock_hash:
random_seed:
started_at:
completed_at:
conclusion:
expected_test_count:
executed_test_count:
passed:
failed:
skipped:
artifacts:
```

Artifacts SHOULD include: JUnit results; coverage and mutation reports; SARIF; Schemathesis
reproduction cases; Playwright HTML reports and failure traces; ZAP reports; k6 metrics and
threshold results; Kubernetes rendered manifests; migration and restore reports; SBOMs and
signatures; chaos experiment results; trace and alert verification; exact test-data version.

**Freshness/zero-test rule**: no critical suite may pass with zero tests collected. During
certification, evidence MUST be no more than 24 hours old (see `levels.md`, Evidence
Freshness).

## Level-10 test metrics (targets)

Critical risks mapped to tests: 100% · Critical journeys tested end to end: 100% ·
Cross-tenant hostile operations denied: 100% · API operations represented in contract
tests: 100% · Deployable artifacts with SBOM and signature: 100% · Releases certified
against exact digest: 100% · Critical tests quarantined: 0 · Unregistered skips in required
suites: 0 · Required-suite flake rate: < 0.1% · CI infrastructure-caused failure rate:
< 0.5% · Merge fast-lane p95: < 15 min · Merge-group p95: < 30 min · Critical mutation
score: ≥ 85% · New critical-code branch coverage: ≥ 90% · Restore success: 3 consecutive
drills, then continuous · Proven RPO: ≤ 15 min · Proven RTO: ≤ 60 min · Production SLO
proof: ≥ 90 consecutive days · Failed or stale critical evidence accepted: 0.

Coverage is a ratchet and diagnostic signal, not the primary quality objective.
