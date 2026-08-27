# CARGO-EVAL-001 — Evaluation Charter

Status: Draft — pending Product, Platform, and Security signatures. Not in force.  
Version: 1.0  
Date: 2026-08-26  
Cargo discovery workspace (not a Fabric tenant): Value (`7fd91cb7-5397-4dd3-acee-360df1af2570`)  
Binds: Master Intent Contract v1.2 + executable SHA (fill at sign) + POC candidate SHA (fill at sign)  
Supersedes: informal discovery notes; does not replace Evaluation User Stories v2.0

> Cargo supplies observations. Fabric determines their economic meaning.  
> This charter freezes protocol, allowlist, corpus, bars, and stop rules **before** any treatment output is reviewed.

---

## 1. Decision this charter authorizes

Determine whether Cargo creates enough additional, verifiable value on **one** approved Fabric account to justify a constrained multi-account pilot.

This charter does **not** authorize production rollout, default enablement, statistical generalizability, or attributable revenue claims.

Selected outcome on Day 14 must be one of: go to multi-account pilot / conditional continuation / no-go.

---

## 2. Scope lock

| Item | Frozen value |
|---|---|
| Tenants | One approved Fabric tenant UUID (fill at sign — not the Cargo workspace id) |
| Accounts | One representative Fabric account UUID (fill at sign — no placeholder ids) |
| Duration | 14 calendar days from signed date |
| Arms | Baseline (Fabric evidence only) vs treatment (same inputs + frozen Cargo snapshot) |
| Integration surface | Four read-only Cargo MCP servers only |
| Provider interface | `AccountIntelligenceProvider` |
| L1 output | `RawSnapshot` + `FetchBatch` (not `Observation`) |
| L2 output | Canonical Fabric `Observation` |
| Context Agent | Excluded from ingest, L3, live metrics |
| Native library RAG | Excluded |
| CRM write-back | Excluded |

Activation requires both the global integration flag and tenant/account eligibility. Entitlement is evaluated before permission. Both fail closed.

---

## 3. Approved slugs (green)

Exact allowlist. Any other slug is a defect if fetched or persisted on the live evaluation path.

| Slug | MCP server | Purpose | Default provenance after L2 |
|---|---|---|---|
| `cargo_match_business` | Company Intelligence | Domain / name → external identity candidate | TRACEABLE if source/domain present; else PARTIAL |
| `cargo_fetch_businesses` | Company Intelligence | Bounded company search | PARTIAL |
| `cargo_enrich_firmographics` | Company Intelligence | Revenue, employees, industry, HQ, locations | PARTIAL (money decimalized at L2) |
| `cargo_enrich_technographics` | Company Intelligence | Installed tech / platform list | PARTIAL |
| `cargo_funding_events` | Company Intelligence | Funding, M&A, leadership-change events + dates | TRACEABLE if source URL; else PARTIAL |
| `cargo_workforce_headcount` | Company Intelligence | Headcount **counts** only | PARTIAL |
| `cargo_website_changes` | Company Intelligence | Website change events; keyword diffs may sit in raw payload | TRACEABLE if page+timestamp; else PARTIAL |
| `cargo_competitive_mentions` | Company Intelligence | Named-competitor mentions as **leads** | OPAQUE until a source resolves |
| `cargo_match_prospect` | Lead Discovery | Person + **title/role** only | PARTIAL; PII via vault |

Slug strings are the only legal values on `FetchRequest.slugs` and `RawSnapshot.slug`.

Machine source of truth for tests and the adapter: `docs/cargo/allowlist.json`. If this table and that file disagree, the charter is unsigned / invalid.

Financial metrics that arrive **inside** a firmographics payload are allowed as raw bytes. They are not a separate slug. L2 emits decimal-string observations or quarantines floats.

---

## 4. Held (not fetched in this POC)

- Email / phone waterfalls  
- Sales Navigator volume search  
- Individual LinkedIn profile enrichment  
- Department-expansion or layoff **narratives**  
- Cargo Context Agent read/write  
- Native library file RAG  
- CRM write-back tools  

Held items require a new manifest version plus CARGO-EVAL-014 expansion. They must appear in tests only as **denied** cases.

---

## 5. Out (blocked on live path)

- Any Cargo ROI / savings / benefit / score used as Fabric meaning  
- ValuePack or hypothesis recommendation from Cargo  
- Cargo confidence copied to Fabric confidence  
- `strategic insights` prose treated as OBSERVED  
- Workforce **ratings**  
- Context Agent content in L3 or live metrics  
- Mocks (`ENRICHMENT_MOCK_MODE` or `source=mock`) in evaluation / production namespaces  
- Binary floats on Observation or financial wire  
- POC-local hasher, idempotency store, or error vocabulary  

---

## 6. Layer split (normative)

```
Cargo MCP (read-only)
        |
        v
L1 AccountIntelligenceProvider.fetch
        |  RawSnapshot (hash, region, slug, payload ref)
        v
L2 ACL / normalizer
        |  Observation (classification, provenance class, decimal money)
        v
L3 tenant-scoped knowledge
        v
L4 ValuePacks / hypotheses   L5 review   L6 baseline vs treatment
```

L1 must not emit `Observation`, `EnrichedAccountContext`, `ValueSignal`, `valueDriverTags`, KPI, ROI, or Fabric confidence.

L2 must leave `valueDriverTags` empty. Fabric matching attaches tags later.

Provenance class is an **L2** decision. L1 only captures raw timestamps, source ids, and `canonical_hash(raw)`.

Most enrichments start PARTIALLY_TRACEABLE. Ratings, narrative insights, and competitive prose start OPAQUE.

---

## 7. Paired task corpus (14 tasks)

Same account, same cutoff, identical governed model / ValuePack / prompts. Baseline frozen before treatment data enters a shared store.

| ID | Theme | Baseline evidence | Cargo increment under test |
|---|---|---|---|
| T01 | Account context | CRM + existing Fabric notes | Firmographics + HQ / locations / industry |
| T02 | Account context | Same | Company match + fetch confirmation |
| T03 | Strategic initiatives | Public site / filings already in Fabric | Funding / leadership event |
| T04 | Strategic initiatives | Same | Website-change event |
| T05 | Operational pain | Stated tech stack from customer conversation | Technographics delta |
| T06 | Operational pain | Same | Competitive mention as lead only |
| T07 | Change events | Known news already filed | Headcount count trend |
| T08 | Change events | Same | Acquisition / funding event |
| T09 | Stakeholder map | Known CRM contacts | Title / role discovery |
| T10 | Stakeholder map | Same | Additional economic-buyer vs champion titles |
| T11 | Value-driver discovery | Existing ValuePack match on current facts | Same match + frozen Cargo observations |
| T12 | Value-driver discovery | Same | Coverage lift without lowering semantic thresholds |
| T13 | Evidence-backed hypothesis | Baseline hypothesis pack | Pack citing incremental TRACEABLE / PARTIAL observations |
| T14 | Evidence-backed hypothesis | Same | Opaque leads visible but **not** supporting a final money claim |

Two independent reviewers. Differences greater than one rubric point are adjudicated. Reviewers never see arm labels.

---

## 8. Rubric and frozen bars

Rubric weights: factual correctness 25%, evidence/provenance 20%, account relevance 20%, incremental discovery 15%, economic usability 15%, clarity 5%.

Hard gates (non-compensable):

- 0 cross-tenant reads, writes, cache reuse, queue replay, disclosure  
- 0 unapproved PII uses or retention  
- 0 out-of-region calls/storage without explicit tenant policy flag  
- 0 materially false Cargo-introduced claims; 0 opaque-only financial claims  
- 0 Cargo fingerprints in baseline traces  
- 0 mocks on live evaluation / production paths  
- Kill switch stops calls and scheduled retries within one propagation interval  
- 100% pass on shared hash-vector fixtures; 0 POC-local hashers  
- 100% baseline completion during injected Cargo failure  

Value / ops bars (report numerators and denominators):

| Bar | Threshold |
|---|---|
| Quality | Treatment mean +8 on 100-point scale |
| Paired preference | Treatment wins ≥ 70% of pairs |
| Incremental utility | ≥ 5 accepted incremental signals |
| Evidence coverage | ≥ 95% of treatment factual claims have usable provenance |
| Value-driver coverage | ≥ 30% lift vs baseline |
| Analyst time | ≥ 25% drop in median time to approved output |
| Reliability | ≥ 95% success on eligible requests (exclude injected failures) |
| Economics | Projected steady-state benefit:cost ≥ 2:1 |

Thresholds cannot be moved after the first treatment output is reviewed.

---

## 9. Platform mechanisms (one implementation)

| Concern | Implementation |
|---|---|
| Hash | `value_fabric.shared.crypto.canonical.canonical_hash` (SHA-256 / RFC 8785) |
| Idempotency | `IdempotencyService` key `{tenant_id, l1.account_intelligence.fetch, client_request_id}`, TTL 72h |
| Errors | `ErrorEnvelope` + existing `ErrorCode` |
| Retries | 3 attempts, 2s exponential + jitter, honor Retry-After |
| Kill switch | `TenantKillSwitch.check_status` — UNKNOWN is 503, never allow |
| Secrets | shared secrets path; MCP via `mcp_gateway` only |
| Storage | `{tenant_id}/raw_snapshot/{snapshot_id}` |

---

## 10. Residency, privacy, budget

- Tenant region pin: fill at sign.  
- Every outbound provider call records `processing_region`.  
- Cross-region processing requires an explicit tenant policy flag.  
- Prospect email/phone are not on the allowlist. If a tool returns them they are vault-referenced or dropped, never stored inline.  
- Raw Cargo payloads and treatment-only derived records delete at the retention deadline unless a documented exception is signed.  
- Budget cap: fill USD at sign. Alert at 80%. Hard stop at 100%.  
- Engineering setup cost is reported separately from projected steady-state cost.

---

## 11. Version binding

Fill at signature. Day-14 decision record repeats this quadruple.

| Binding | Value |
|---|---|
| Intent contract | v1.2 |
| Executable contract SHA | _pending_ |
| POC candidate SHA | _pending_ |
| Manifest hash | SHA-256 / JCS of this charter file |

---

## 12. Immediate stop conditions

Copy of Evaluation User Stories §8.1. Any item stops the test:

1. Cross-tenant leak  
2. Unapproved PII / secrets / raw payloads in logs or UI  
3. License, DPA, retention, export, or residency terms cannot be met  
4. Provenance faked, stripped, or presented as verified when it is not  
5. Cargo number written into ROI, KPI, or customer claim  
6. Baseline / treatment isolation cannot be proven  
7. Spend 80% without review, or 100% at any point  
8. Unbounded retries, kill-switch failure, or Cargo outage breaking Fabric  
9. False Cargo claim on an approved deliverable  
10. Binary float, non-canonical hash, or POC-local idempotency/error mechanism on a money or provenance path  

---

## 13. Signatures

Signing means: green slugs only, L1 ≠ Observation, Context Agent out, bars frozen, hard gates non-compensable.

| Role | Name | Disposition | Date | Notes |
|---|---|---|---|---|
| Product / Evaluation Owner | | Approve / Reject / Conditional | | |
| Platform | | | | |
| Security | | | | |
| Governance | | | | |
| Architecture | | | | |

Charter is not in force until Product + Platform + Security have signed and the version-binding row is complete.

Do not start Task 3 (`cargo/adapter.py`, live MCP, treatment runs) until this block is signed.
