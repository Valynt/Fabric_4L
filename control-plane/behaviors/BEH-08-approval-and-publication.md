# BEH-08: Approval & publication

```yaml
id: BEH-08
name: approval-and-publication
journey_stage: J-9            # Review, approve, publish, and export
stories: [VP-12, VP-14]
closes_gaps: [GAP-07, GAP-08, GAP-10, GAP-11]
rules: [R-3, R-5, R-6, R-7]
boundary: web -> api -> L4 -> L5
components:
  - ReviewGateChecklist        # actionable readiness checklist
  - VersionHistoryPage
  - GovernanceSurfaces         # audit log, change history, compliance
  - ReviewsRouter
  - GovernanceRouter
  - VersioningRouter
  - PublicationService         # immutability, lineage, export packaging
primary_gates: [AG-04, AG-05]
```

## Product

An authorized approver governs the customer-facing value case so that **only complete and authorized versions are released**, and what is released is immutable, auditable, and exportable with provenance (VP-12; jobs 6; journey exit).

Correct behavior, normatively:
- Review operates on an **immutable snapshot**: inputs, assumptions, formulas, units, ranges, evidence/claim references, financial results, narrative, model version, source freshness, authorization scope (UX §5.3).
- Approval records actor, role, timestamp, version, content hash, rationale (§7.2.4). Approve / request-changes (anchored comments) / reject follow verified permission.
- **An approved or published version is immutable.** Any later edit creates a new draft with explicit lineage; approved history is never mutated (R-7).
- Publish and export stay disabled until: exact version approved + authorization verified + evidence policy passed (GAP-10 enforcement) + financial claims traceable + no material stale or degraded state (convergence decision 7; R-5).
- One canonical lifecycle — `draft, in_review, changes_requested, approved, published, superseded` — serves Studio, Narrative, Deliverables, approval, publication, export, and realization (GAP-07; §5.4 Lifecycle).
- Exports are created only from approved immutable versions, stored under tenant-prefixed object paths with provenance manifest and audit event (§7.4.7).
- The UI presents readiness as an actionable gate checklist with direct navigation to each blocker; publication/export/tenant-switch actions require explicit confirmation naming account and version scope (UX §5.3.5, §5.5.5).
- Review state, comments, and approvals are server-persisted with version and conflict handling — never browser-local (GAP-11).

## Architecture

```
 apps/web                          services/api                 governance
 ┌───────────────────────┐         ┌───────────────────────┐
 │ gate checklist (in     │         │ routers/reviews.py     │──▶ L5: evidence policy +
 │  case surfaces)        │────────▶│ routers/governance.py  │    publication readiness
 │ VersionHistoryPage.tsx │         │ routers/versioning.py  │    (GAP-10 pass expr)
 │ GovernanceAuditLog.tsx │◀────────│ routers/value_cases.py │
 │ GovernanceChangeHistory│  gates  └───────────────────────┘         │
 │ GovernanceCompliance   │                    │                     ▼
 └───────────────────────┘                     ▼            immutable version +
                                     L4 governed approval      lineage + content hash
                                     workflow (human gate)            │
                                                              export: tenant-prefixed
                                                              object path + provenance
                                                              manifest + audit event
```

## Implementation

### Verified anchors

| Path | What it is | Role in this behavior |
|---|---|---|
| `apps/web/src/pages/VersionHistoryPage.tsx` | Version history page | Draft/approved/published/superseded lineage; version comparison |
| `apps/web/src/pages/GovernanceAuditLog.tsx` | Audit log page | Who did what, in which scope — approval and export audit trail |
| `apps/web/src/pages/GovernanceChangeHistory.tsx` | Change history page | Versioned change lineage with rationale |
| `apps/web/src/pages/GovernanceCompliance.tsx` | Compliance page | Readiness posture across gates |
| `apps/web/src/pages/GovernanceEvidence.tsx` | Governance evidence page | Evidence state feeding the publication gate (BEH-05) |
| `services/api/app/routers/reviews.py` | Reviews router | Review commands: approve / request changes / reject with anchored comments |
| `services/api/app/routers/governance.py` | Governance router | Gate evaluation, readiness checklist, audit queries |
| `services/api/app/routers/versioning.py` | Versioning router | Immutable version CRUD, lineage, content hash |
| `services/api/app/routers/value_cases.py` | Value cases router | Lifecycle transitions on the canonical case record |
| `services/layer5-ground-truth/src/layer5_ground_truth/api/governance_router.py` | L5 governance API | Publication-readiness evaluation; enforced evidence policy |
| `contracts/tool-manifests/document_export.json` | Tool manifest | Export contract: artifact bound to approved version |

### Inputs / outputs
- **In**: immutable version under review; reviewer identity + verified permission; review commands; publish/export commands with explicit account+version confirmation.
- **Out**: lifecycle transition with full audit record (actor, role, timestamp, version, content hash, rationale); on publish — immutable published version; on export — tenant-prefixed artifact + provenance manifest + audit event.

### State transitions
- Lifecycle: `draft -> in_review -> approved | changes_requested`; `approved -> published`; new edit on approved → new `draft` with lineage; newer publish supersedes prior (`published -> superseded`), history immutable.
- Synchronization: `conflict` on concurrent review/edit → compare, reload, or save-as-new-version; never silent overwrite.
- Access: any scope uncertainty during publish/export → fail closed, no partial artifact (R-6).

### Failure modes
- Publication attempted with open authorization, evidence, freshness, or review blocker → denied with named blockers (governed publication rate stays 100%).
- Evidence policy absent/unresolved → gate fails closed; never auto-pass (GAP-10).
- Materially degraded or stale state at publish time → blocked until recalculation/re-review (R-5, §7.2.6).
- Export of a non-approved or mutated version → impossible by construction; export path accepts only content-hash-verified immutable versions (R-7).
- Concurrent approval race → single-winner via optimistic version check; losing actor gets conflict with both identities.

## Verification

**Tests**
- Unit: lifecycle state machine (all transitions + illegal-transition rejection), approval record completeness, lineage-on-edit, checklist derivation from gate states.
- Contract: review/governance/versioning route schemas; `document_export.json` binding to approved version + content hash.
- Integration (real persistence + object storage): immutability (attempted mutation of approved version fails), export artifact placement under tenant-prefixed path with provenance manifest, audit-event emission per transition.
- Browser: full review → approve → publish → export journey with gate checklist; confirmation dialog states account + version; denied/expired roles see no publish affordance.
- Golden path: this behavior is the terminus of the fresh-account candidate-SHA-bound certification journey (GAP-12 control under AG-06).

**Tenant-isolation assertions**
- Publish/export re-verify authorization at execution time, not at page load; expired or switched sessions denied mid-flow.
- Export artifacts: cross-tenant signed-URL access denied; export and deletion isolation controls under AG-05; object keys tenant-prefixed and provenance-bound.
- Audit events record acting tenant/actor without leaking foreign data.

**Release gates**
- **AG-04 security-gates** — route authentication/authorization checks on review/publish/export routes; role-based security journeys; production mock-mode prohibition on gates.
- **AG-05 tenant-isolation-and-behavior** — export/deletion isolation, signed-URL expiry/replay protection, support-impersonation scope.
- **AG-06 production-readiness** — Full ValuePilot golden-path certification (GAP-12) ends here: fresh account → approved export on real services.
- **AG-08 release-evidence** — in-product approval records mirror release evidence discipline: actor, version, hash, timestamp, immutable retention.

**Required evidence**
- EV: junit-and-json test-run evidence for lifecycle/immutability suites.
- EV: Playwright traces for the approve→publish→export journey incl. permission states.
- EV: golden-path certification record (environment + commit/digest + observation time bound).
- EV: export artifact + provenance manifest samples bound to the certified version.
