# 03 — Domain Lifecycle

Source: Master Product Intent §3 (S1).

## Canonical domain chain

Exact order — 15 nodes:

```
Account -> Analysis Case -> Source -> Extracted Fact -> Pain Signal -> Value Hypothesis
-> Validated Value Driver -> Value Lever and Formula -> Evidence or Benchmark -> Scenario
-> ROI Snapshot -> Narrative -> Value Case Version -> Approval and Export -> Realization
```

Rule: "Every screen and API operates on this shared chain. Tabs may offer different views, but they cannot create contradictory model identities, field names, calculations, evidence records, or version histories."

The user-facing traversal of this chain is staged as the canonical journey J-1..J-10 — see `04_canonical-journey.md`.

## Domain artifacts — canonical meaning and authority

| Artifact | Canonical meaning | Authority and lifecycle |
|---|---|---|
| Account | Tenant-scoped customer or opportunity context | Server authority; authorization snapshot constrains access |
| Analysis Case | Durable container for one value-modeling effort | One canonical case ID across Intelligence, Studio, calculation, narrative, and deliverables |
| Signal | Account-specific operational pain, change, risk, or objective derived from a source | Generated candidate until accepted, edited, rejected, or marked for customer confirmation |
| Hypothesis | Proposed link from pain through capability to measurable outcome | Ranked candidate; human disposition required before promotion |
| Value Driver | Validated business or operational mechanism that produces value | Persistent graph object linked to source hypothesis, signal, evidence, confidence, and model version |
| Value Lever and Formula | Measurable quantity and governed expression that converts operational change into value | Must include units, time basis, valid variables, bounds, and formula lineage, or be explicitly non-financial |
| Evidence or Benchmark | Support for a fact, assumption, applicability claim, or value range | Versioned source reference with status, freshness, relevance, scope, and human decision |
| Scenario | Named set of model inputs and multipliers | Server-persisted, forkable, comparable, and tied to a model version |
| ROI Snapshot | Immutable calculation request, result, engine version, and lineage | Deterministic source of financial truth for a value-case version |
| Value Case Version | Narrative and visual decision artifact generated from one immutable input snapshot | draft, reviewed, approved, published, superseded; edits always create a new draft |
| Realization Record | Measured actual outcome compared with the approved forecast | Separate from the forecast; preserves baseline, cadence, source, owner, and history |

## Source of truth hierarchy

1. Verified backend authorization snapshot and authenticated request context define identity, tenant, account scope, roles, permissions, and entitlements.
2. Server-side case and domain records define authoritative business state. Object access checked against both tenant and parent account or case ownership.
3. Immutable model, calculation, narrative, approval, publication, and export versions define the reviewed record of decision.
4. Browser state stores navigation, presentation preferences, and safe caches only — never the sole source for a case, scenario, formula, approval, or publication state.
5. Generated suggestions and agent event streams are advisory until explicitly persisted and dispositioned under the relevant domain contract.

## Independent state dimensions

Lifecycle status and operational status remain independent (e.g., an approved model can later become stale while its immutable approval history remains valid for the prior version).

| Dimension | Canonical values | Required interpretation |
|---|---|---|
| Access | verifying, allowed, denied, expired | Protected content rendered only in allowed state |
| Content | loading, empty, ready, degraded, stale, error | Describes data quality/usability without changing lifecycle history |
| Operation | idle, generating, saving, retrying | Background work preserves last good version and exposes job or trace identity |
| Lifecycle | draft, in_review, changes_requested, approved, published, superseded | Review and publication operate on immutable versions |
| Synchronization | synced, dirty, conflict | Conflicts never silently overwrite work; compare, reload, or save a new version |

State-to-experience behavior requirements for these dimensions are normative in `05_experience-contract.md`.
