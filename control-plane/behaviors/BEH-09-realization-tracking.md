# BEH-09: Realization tracking

```yaml
id: BEH-09
name: realization-tracking
journey_stage: J-10           # Track realization
stories: [VP-13, VP-14]
closes_gaps: [GAP-11]
rules: [R-2, R-7, R-8]
boundary: web -> api -> L3
components:
  - RealizationPage
  - RealizationRouter
  - RealizationRecordService   # versioned server records, owner/cadence/source
  - ForecastReference          # immutable approved forecast identity
primary_gates: [AG-02, AG-05]
```

## Product

A realization owner compares actual outcomes with the approved forecast so the team can prove and improve realized value — **without rewriting the original commitment** (VP-13; jobs 7; journey exit: "variance and learning visible and reusable under governed applicability rules").

Correct behavior, normatively:
- A Realization Record is separate from the forecast: it preserves baseline, targets, measures, sources, cadence, owner, and history; it is a versioned **server** record linked to the published case (domain lifecycle §5.2; closes the browser-local persistence class of GAP-11 for realization data).
- The approved forecast it measures against is immutable (R-7): variance analysis never mutates the published version or its ROI snapshot. Historical commitment, current actuals, and reforecast are clearly separate (VP-13 design).
- Forecast variance is a first-class product measure (§3.1): forecast vs actual is easy to understand; differences are understood and reduced over time, not hidden.
- Provenance continues post-publication: each actual measurement names its source, owner, cadence, and the exact forecast version it is compared against (R-8).
- Learnings feed reuse — validated drivers, formulas, evidence, benchmarks — under governed applicability checks (reusable asset rate, §3.1), never silent copy-forward.
- Activation ordering: VP-13 activates only after the published forecast identity and provenance contract are stable (delivery sequence §8.1.6) — i.e., after BEH-08's publication contract is closed.

## Architecture

```
 published value-case version (immutable, BEH-08)
        │  forecast identity: model v + ROI snapshot + approval hash
        ▼
 apps/web                          services/api
 ┌───────────────────────┐         ┌────────────────────────┐
 │ realization/           │────────▶│ routers/realization.py  │
 │  RealizationPage.tsx   │         │  baselines, targets,    │──▶ L3: deterministic
 │  baseline | target |   │◀────────│  measures, actuals,     │    variance math over
 │  actual | variance |   │ actuals │  cadence, owners,       │    stored inputs (R-4
 │  reforecast (separate) │         │  versioned history      │    semantics preserved)
 └───────────────────────┘         └────────────────────────┘
        history never rewritten — actuals append; reforecast forks with lineage
```

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/realization/RealizationPage.tsx` | Realization page | Baseline/target/actual entry; forecast-vs-actual comparison; variance view |
| `services/api/app/routers/realization.py` | Realization router | Versioned realization records; linkage to published case; scope enforcement |
| `services/api/app/routers/value_cases.py` | Value cases router | Published forecast identity referenced by realization records |
| `services/api/app/routers/versioning.py` | Versioning router | Version lineage for realization record history |
| `services/api/migrations/` | API DB migrations | Tenant-scoped realization tables and constraints |

### Inputs / outputs
- **In**: published case version reference (immutable forecast identity); baseline + target + measure definitions with source, cadence, owner; periodic actuals.
- **Out**: versioned realization records; variance computation (approved forecast vs measured actual over agreed period); reforecast drafts with explicit lineage; reusable-learning candidates with applicability checks.

### State transitions
- Record: `defined -> measuring -> variance-reported`; cadence drives append-only actuals; each reporting period is its own versioned record.
- Reforecast: creates a new draft version linked to the published forecast; the published forecast stays immutable (R-7).
- Lifecycle independence: the source case version remains `published`/`superseded` regardless of realization outcomes (independent state dimensions §5.4).

### Failure modes
- Actual submitted against a non-published or ambiguous forecast identity → rejected; measurement requires the exact immutable reference (R-6, R-7).
- Attempt to edit the approved forecast from realization surfaces → impossible; only new-version fork allowed.
- Missing cadence/owner/source on a measure → record incomplete and visibly so; no fabricated actuals (non-goal 3 applies post-sale too).
- Concurrent actuals submission → idempotent append with optimistic version check; conflicts return both identities (GAP-11 class).
- Cross-tenant forecast reference → denied before any data load.

## Verification

**Tests**
- Unit: variance computation determinism; append-only history; reforecast lineage; incomplete-measure rejection.
- Contract: realization route schemas; version-reference binding to published case identity.
- Integration (real persistence): records survive reload/restart; idempotent actuals; linkage integrity to the immutable forecast.
- Browser: define baseline/targets → record actuals → read variance → fork reforecast; historical commitment visibly separate from current actuals.

**Tenant-isolation assertions**
- Realization records scoped tenant + account + case; foreign case/version references denied (hostile suite).
- Variance reads never join across tenants; cache keys for realization views tenant-discriminated.

**Release gates**
- **AG-02 code-quality-and-tests** — unit/integration/browser coverage of records, variance, and lineage.
- **AG-05 tenant-isolation-and-behavior** — account-scope enforcement and cache isolation on realization reads/writes.
- **AG-06 production-readiness** — migration safety for realization tables; recoverability of authoritative records.

**Required evidence**
- EV: junit-and-json test-run evidence for record/variance/lineage suites.
- EV: contract-test results for realization schemas and forecast binding.
- EV: migration-safety report for realization persistence.
