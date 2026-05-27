# Runtime Intelligence Model: Data Requirements & Enhancement Opportunities

## Executive Summary

The Value Fabric runtime intelligence model (as defined in `value_pack_runtime_selection_decision.md` and `Architecture.md`) has strong structural foundations: a 6-layer pipeline, deterministic pack resolution, graph-backed knowledge retrieval, agentic workflows, and ground truth validation. However, **the model is currently evidence-hungry at every stage** — it knows *how* to reason but lacks the proprietary, temporal, and contextual data sets needed to make that reasoning sharp at runtime.

This document maps the gap between what the architecture can do and what it needs to do it well, organized by the runtime workflow stages.

---

## 1. Gap Analysis by Runtime Stage

### 1.1 Signal Extraction (ContextExtractionAgent → Layer 2)

**What the architecture does well:**
- Ontology-guided entity extraction (Capability, UseCase, Persona, ValueDriver)
- Evidence artifact collection with provenance
- Confidence scoring

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Account financial baselines** (revenue, OpEx, headcount, margins) | Without actuals, signals are qualitative guesses. A $2B manufacturer with 8% EBITDA has different priorities than one with 22%. | P0 |
| **Technology stack fingerprint** (ERP, CRM, MES, etc.) | Signals about "SaaS sprawl" or "legacy modernization" are hollow without knowing what's actually installed. BuiltWith/StackShare-style data. | P0 |
| **Job posting velocity & sentiment** | Leading indicator of investment direction, hiring pain, and strategic priorities. 30% YoY increase in "Salesforce admin" posts = CRM expansion signal. | P1 |
| **Earnings call transcript NLP features** (sentiment, keyword velocity, forward guidance) | Pack signal definitions pattern-match on mentions, but lack sentiment trajectory. "Downtime" with increasingly negative tone quarter-over-quarter is a different signal than a single mention. | P1 |
| **Regulatory deadline tracking** (e.g., "T+1 settlement May 2024", "EU AI Act Aug 2026") | Pack rules know *what* regulations exist, but not *when* compliance windows close for a specific account. Creates urgency signals. | P1 |
| **News/event stream with entity extraction** | M&A, executive changes, product launches, legal actions — real-time signal triggers. Currently manual or missing. | P1 |
| **Glassdoor/employee sentiment trends** | Leading indicator of operational pain. Declining culture scores + hiring freeze = cost pressure signal. | P2 |

**Recommended enhancement:**
A pre-built **Account Intelligence Profile** that assembles baselines before any signal extraction begins. This profile becomes the "known facts" context window for every agent call.

```
AccountProfile = {
  financial_baseline: { revenue, ebitda, opex_breakdown, headcount, growth_rate },
  tech_stack: [{ system, vendor, category, install_date, refresh_cycle }],
  key_executives: [{ name, title, tenure, background }],
  recent_events: [{ date, type, description, source }],
  hiring_velocity: { current_openings, yoy_change, top_roles, locations },
  competitive_position: { market_share, key_competitors, recent_wins_losses }
}
```

---

### 1.2 Evidence Matching (EvidenceArtifact + EvidenceMatch)

**What the architecture does well:**
- Structured evidence collection with trust scoring
- Match relationships to signals, opportunities, assumptions

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Customer's own product portfolio** | Evidence matching needs to know what *your* company sells to match signals to relevant capabilities. A signal about " claims processing backlog" only matters if you have claims automation products. | P0 |
| **Case study / testimonial repository** | Pre-matched evidence: "We reduced claims processing by 47% for SimilarCorp" is the strongest evidence match. Needs structured case study DB with outcomes, industries, personas. | P0 |
| **Win/loss record with root cause coding** | Historical evidence of what worked. Pattern: "When signal X + persona Y + use case Z, we won 73% of the time." Enables Bayesian confidence. | P1 |
| **Competitive displacement data** | Which competitor weaknesses correlate with wins. "When target has VendorX with >3 support tickets, win rate = 68%." | P1 |
| **Third-party analyst validation** (Gartner, Forrester, IDC) | External evidence for ground truth. "Gartner rates us Leader in Magic Quadrant" validates capability claims. | P2 |
| **Peer comparison datasets** (Layer 6 currently has limited seed data) | Evidence strength increases when you can say "your OEE is 62%, peer median is 78%, top quartile is 85%." | P1 |

**Recommended enhancement:**
An **Evidence Library** — a curated, vector-indexed repository of customer-proven outcomes, case studies, analyst validations, and competitive intelligence that feeds directly into the EvidenceMatch scoring algorithm.

---

### 1.3 Opportunity Seeding (OpportunityFinder)

**What the architecture does well:**
- Pack-informed opportunity generation via use case mapping
- Confidence scoring

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Customer propensity scores** | Historical conversion patterns by account profile. "Accounts with signal A + B + C in Manufacturing have 4.2x higher close rate." | P0 |
| **Whitespace mapping** (installed base vs. full portfolio) | What does the customer already own? What's the gap? This is the #1 opportunity source in existing account management. | P0 |
| **Competitive account penetration** | What competitors are installed where. Share-of-wallet estimates. | P1 |
| **Buying cycle timing** | When does this account typically budget, procure, sign? Fiscal year alignment. | P1 |
| **Persona engagement history** | Which personas have we engaged? What's their sentiment? Who is the champion? Who is the blocker? | P1 |
| **Prior opportunity outcomes** | Did we pursue this opportunity before? What happened? Prevents重复 effort and surfaces "resurrected" opportunities with new context. | P2 |

**Recommended enhancement:**
A **Customer Lifecycle Data Model** that tracks engagement, purchase history, competitive landscape, and propensity scores per account. This feeds the OpportunityFinder with account-specific priors.

---

### 1.4 Impact Quantification (FinancialModelingAgent)

**What the architecture does well:**
- Formula evaluation with variable substitution
- Monte Carlo sensitivity analysis
- Benchmark validation (Layer 6)

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Customer-specific financial inputs** | Formulas are templates. They need actuals: "your current CAC is $X, your current churn is Y%, your ARPU is $Z." Without this, outputs are ranges so wide they're not actionable. | P0 |
| **Validated formula coefficients** | Pack formulas use generic coefficients ("typically 15-25%"). Customer-validated coefficients ("our customers in this segment average 22%") dramatically improve accuracy. | P0 |
| **Time-series performance data** | Trends matter. "Churn went from 4% to 7% over 6 months" triggers a different formula than a static 7%. | P1 |
| **Regional cost adjustments** | Labor rates, energy costs, regulatory costs vary 5-10x by region. Formulas need geo-specific adjustment tables. | P1 |
| **Customer size band calibration** | A formula that produces $50M value for a Fortune 50 account may produce $500K for a mid-market account. Size-band scaling factors. | P1 |
| **Historical realization data** | "We projected $10M, customer realized $8.5M" — this calibration loop improves future formula accuracy. | P2 |

**Recommended enhancement:**
A **Formula Calibration Engine** that maintains validated coefficient tables by industry, segment, company size, and region. These coefficients update from realization data over time.

---

### 1.5 Value Tree Construction

**What the architecture does well:**
- Hierarchical node structure (strategic_outcome → value_driver → use_case → kpi → formula → assumption)
- Graph-based traversal

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Pre-built value tree templates by pack** | Value trees shouldn't be built from scratch every time. Each pack should ship 3-5 "starter" value trees for common scenarios (e.g., "ERP consolidation in manufacturing"). | P0 |
| **Assumption libraries with defaults** | Every value tree needs assumptions. Starting from blank is slow. Default assumptions per pack with confidence bands accelerate tree construction. | P1 |
| **Stakeholder-specific tree views** | CFO wants financial rollup. COO wants operational KPIs. CIO wants technical dependencies. Same tree, filtered views by persona. | P1 |
| **Cross-pack value tree composition** | When an account has multiple packs (e.g., Manufacturing + SaaS), value trees should compose. Needs cross-pack dependency mapping. | P2 |

---

### 1.6 Ground Truth Validation (Layer 5)

**What the architecture does well:**
- TruthObject state machine (EXTRACTED → SUPPORTED → CORROBORATED → APPROVED → OPERATIONALIZED)
- Evidence-backed claims
- Maturity ladder

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Customer-validated outcome database** | The highest-confidence ground truth: what did the customer actually achieve? Post-implementation measurement data. | P0 |
| **Analyst-validated benchmark sets** | Ground truth from third-party analysts (Gartner, Forrester) with citation chains. | P1 |
| **Peer corroboration network** | "3 other customers in the same segment reported similar results" = automatic CORROBORATED status. | P1 |
| **Dispute resolution log** | When claims are DISPUTED, what was the resolution? Prevents repeated false claims. | P2 |

---

### 1.7 Pack Resolution & Selection

**What the architecture does well:**
- Deterministic resolution: Account override > Tenant default > Global
- Effective Pack Context tracking

**What it's missing:**

| Missing Data | Why It Matters | Priority |
|---|---|---|
| **Multi-industry account disambiguation** | Conglomerates (e.g., Samsung, Berkshire Hathaway) span multiple packs. The model needs sub-entity resolution (division, subsidiary, geography). | P1 |
| **Dynamic pack suggestion** | Based on account data, suggest which pack to use. "This account is 80% Manufacturing, 15% Financial Services, 5% Healthcare — recommend Manufacturing Master with FS supplement." | P1 |
| **Pack performance analytics** | Which packs produce the highest-confidence outputs? Which have the most validated opportunities? Data-driven pack prioritization. | P2 |

---

## 2. Data Architecture Implications

### 2.1 New Tables/Collections Required

```sql
-- Account Intelligence Profile (new, populated by Layer 1 enrichment)
account_profiles:
  account_id, tenant_id,
  financial_baseline jsonb,        -- revenue, ebitda, margins, headcount
  tech_stack jsonb,                -- [{system, vendor, category, install_date}]
  key_executives jsonb,            -- [{name, title, tenure}]
  hiring_velocity jsonb,           -- {openings, yoy_change, top_roles}
  recent_events jsonb,             -- [{date, type, description, source}]
  competitive_position jsonb,      -- {market_share, competitors, wins_losses}
  last_refreshed_at timestamp

-- Evidence Library (curated, manually + AI populated)
evidence_library:
  evidence_id, tenant_id (nullable for global),
  evidence_type: case_study | testimonial | analyst_quote | win_record | benchmark_validation,
  title, summary, outcome_value, outcome_unit,
  account_industry, account_segment, account_size_band,
  related_product_ids, related_use_case_ids,
  source_url, trust_score, validation_status,
  embedding vector(1536)

-- Customer Lifecycle (CRM-integrated)
customer_lifecycle:
  account_id, tenant_id,
  engagement_history jsonb,        -- [{date, type, persona, sentiment}]
  purchase_history jsonb,          -- [{product, date, value, renewal_date}]
  whitespace_map jsonb,            -- [{product, status: owned|target|competitor}]
  competitive_penetration jsonb,   -- [{competitor, products, estimated_share}]
  buying_cycle jsonb,              -- {fiscal_year_end, typical_procure_months, budget_cycle}
  propensity_scores jsonb          -- [{use_case, score, confidence, last_updated}]

-- Formula Calibration (learned over time)
formula_calibration:
  formula_id, pack_id,
  segment, company_size_band, region,
  coefficient_name, default_value, validated_value,
  validated_by_count, realization_data jsonb,
  confidence_level, last_updated

-- Value Tree Templates (pack-shipped)
value_tree_templates:
  template_id, pack_id, name, description,
  template_structure jsonb,        -- pre-built node hierarchy
  starter_assumptions jsonb,       -- default assumptions with confidence bands
  applicable_segments[],
  popularity_score, success_rate

-- Realization Tracking (post-implementation)
realization_outcomes:
  outcome_id, account_id, tenant_id, opportunity_id,
  projected_value, realized_value, variance_pct,
  measurement_method, measured_by, measured_at,
  formula_calibration_feedback jsonb
```

### 2.2 Vector Store Additions

Current vector store scope: Evidence artifacts, pack descriptions, use cases, persona language, formula descriptions, benchmarks, past business cases.

**Additions:**
- Account profiles (for semantic account similarity / peer matching)
- Case studies and testimonials (for evidence matching)
- Win/loss records (for opportunity scoring)
- Value tree templates (for semantic template matching)
- Realization outcomes (for formula calibration)

### 2.3 Graph Layer Additions

Current graph: Capability → UseCase → Persona → ValueDriver → Formula → Industry → GroundTruth

**Additions:**
- `:Account` node (sub-entity of `:Industry`)
- `:Product` node (your portfolio)
- `:Competitor` node
- `:Evidence` node (linked to `:GroundTruth`)
- `:Realization` node (post-implementation outcomes)

New relationships:
- `(Account)-[:HAS_TECH_STACK]->(Capability)`
- `(Account)-[:COMPETES_WITH]->(Competitor)`
- `(Account)-[:USES_PRODUCT]->(Product)`
- `(GroundTruth)-[:VALIDATED_BY]->(Evidence)`
- `(Formula)-[:CALIBRATED_BY]->(Realization)`

---

## 3. Priority Roadmap

### Phase 1 (Immediate — Blocks Core Workflow)

1. **Account Intelligence Profile** — Build enrichment pipeline (Layer 1 extension) to populate financial baselines, tech stack, and executive data for every target account.
2. **Customer Product Portfolio** — Load your product catalog into the knowledge graph so agents know what you sell.
3. **Case Study / Testimonial Repository** — Structure 20-50 top customer outcomes as EvidenceLibrary entries.
4. **Value Tree Templates** — Build 3 starter templates per master pack (15 total).

### Phase 2 (Short-term — Drives Accuracy)

5. **Formula Calibration Tables** — Initialize with pack benchmark data; populate from realization tracking.
6. **Customer Lifecycle Integration** — CRM connector (Salesforce/HubSpot) for engagement history, purchase data, whitespace.
7. **Peer Comparison Datasets** — Expand Layer 6 with segment-specific benchmarks (need external data licensing).
8. **Win/Loss Coding** — Historical deal analysis with signal → outcome mapping.

### Phase 3 (Medium-term — Drives Scale)

9. **Realization Tracking Loop** — Post-implementation measurement workflow feeding formula calibration.
10. **Multi-pack Composition** — Cross-pack value tree composition for conglomerates.
11. **Dynamic Pack Suggestion** — ML model for automatic pack recommendation based on account data.
12. **Propensity Scoring** — Learned conversion models per pack/use case.

---

## 4. External Data Sources to License/Integrate

| Source | Data | Layer | Cost |
|--------|------|-------|------|
| **BuiltWith / SimilarTech** | Technology stack detection | Layer 1 | $$ |
| **LinkedIn Sales Navigator API** | Executive changes, hiring data | Layer 1 | $$$ |
| **SEC EDGAR (free)** | Financial filings, 10-K/10-Q | Layer 1 | Free |
| **NewsAPI / GDELT** | News and event stream | Layer 1 | $ |
| **Glassdoor API** | Employee sentiment | Layer 1 | $$ |
| **Craft.co / ZoomInfo** | Company intelligence | Layer 1 | $$$ |
| **Gartner/Forrester APIs** | Analyst validations | Layer 5 | $$$$ |
| **IBISWorld / Euromonitor** | Industry benchmarks | Layer 6 | $$$ |
| **Dun & Bradstreet** | Firmographics, credit data | Layer 1 | $$$ |
| **Crunchbase** | Funding, M&A, competitor intel | Layer 1 | $$ |

---

## 5. Summary: Top 10 Highest-Impact Data Investments

| Rank | Data Investment | Impact | Effort |
|------|----------------|--------|--------|
| 1 | Account financial baselines + tech stack | Turns signals from guesses into precision targeting | Medium |
| 2 | Customer product portfolio in graph | Enables signal-to-capability matching | Low |
| 3 | Case study / testimonial evidence library | Dramatically strengthens evidence matching | Medium |
| 4 | Value tree templates by pack | Accelerates tree construction 10x | Low |
| 5 | CRM integration (engagement + purchase history) | Powers whitespace and propensity scoring | Medium |
| 6 | Formula calibration tables | Reduces output variance, increases credibility | Medium |
| 7 | Peer comparison datasets (Layer 6 expansion) | Grounds quantification in reality | High |
| 8 | Win/loss record with signal coding | Enables learning loop for opportunity scoring | Medium |
| 9 | Hiring velocity + executive change feeds | Adds leading indicators to signal extraction | Low |
| 10 | Realization tracking + feedback loop | Closes the learning cycle | Medium |

---

*Generated: 2026-04-26*
*Context: Value Fabric Runtime Intelligence Model v1.0*
