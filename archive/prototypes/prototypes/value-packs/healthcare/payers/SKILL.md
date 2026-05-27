# Payers and Health Insurance Subpack (S3.2)

**skill_name:** Payers and Health Insurance Subpack (S3.2)
**description:** Vertical-specialized value intelligence for payers and health insurance organizations covering commercial plans, Medicare Advantage, Medicaid managed care, employer plans, TPAs, PBMs, dental/vision, stop-loss, and VBC/ACOs. Extends Healthcare Master ValuePack with payer-specific pains, KPIs, formulas, benchmarks, signals, personas, discovery questions, objections, technology systems, and regulatory factors.
**version:** 1.0.0
**domain:** healthcare / industry
**pack_type:** subpack
**parent_master:** healthcare-master-v1
**vertical_focus:** Commercial plans, Medicare Advantage, Medicaid managed care, employer plans, TPAs, PBMs, dental/vision, stop-loss, VBC/ACOs
**last_updated:** 2026-04-25

---

## Table of Contents

1. [Skill Identity Block](#skill-identity-block)
2. [Triggers](#triggers)
3. [Reasoning Flow](#reasoning-flow)
4. [Inheritance Map](#inheritance-map)
5. [Structured Output Template](#structured-output-template)
6. [Governance Metadata](#governance-metadata)
7. [Quick Reference](#quick-reference)

---

## Skill Identity Block

| Attribute | Value |
|-----------|-------|
| skill_name | Payers and Health Insurance Subpack (S3.2) |
| description | Vertical-specialized value intelligence for payers and health insurance organizations covering commercial plans, Medicare Advantage, Medicaid managed care, employer plans, TPAs, PBMs, dental/vision, stop-loss, and VBC/ACOs. Extends Healthcare Master ValuePack with payer-specific pains, KPIs, formulas, benchmarks, signals, personas, discovery questions, objections, technology systems, and regulatory factors. |
| version | 1.0.0 |
| domain | healthcare / industry |
| pack_type | subpack |
| parent_master | healthcare-master-v1 |
| vertical_focus | Commercial Health Plans, Medicare Advantage, Medicaid Managed Care, Employer-Sponsored Plans, Third-Party Administrators (TPAs), Pharmacy Benefit Managers (PBMs), Dental/Vision Plans, Stop-Loss Insurance, Value-Based Care Organizations, Accountable Care Organizations (ACOs) |
| agent_swarm_id | kimi-k2.6-swarm-payers-s3.2 |

---

## Triggers

The following natural language query patterns should auto-load this skill:

1. "Medicare Advantage Star rating analysis" — Quality underperformance, QBP bonus at risk, HEDIS gaps, CAHPS scores
2. "Medicaid churn reduction and MCO margin compression" — State rate pressure, MLR > 90%, encounter data quality, retroactive adjustments
3. "Claims denial rate and auto-adjudication gap" — Backlog > 10 days, first-pass resolution < 90%, manual touch rate high
4. "MLR compression below 85%" — Admin cost PMPM spike, SG&A bloat, competitive pricing pressure, reinsurance cost escalation
5. "Risk adjustment accuracy and RADV exposure" — RAF score gap > 0.08, HCC recapture < 85%, suspecting tool underutilization, RADV audit
6. "PBM drug cost escalation and rebate transparency" — Specialty spend > 45% of pharmacy budget, GDR < 84%, DIR fee drag, biosimilar adoption lag
7. "FWA detection gap and fraud recovery" — FWA detection rate < 1%, recovery ratio < 3:1, false positive rate > 90%, DOJ qui tam exposure
8. "Employer group RFP loss and commercial risk erosion" — RFP win rate < 30%, self-insured ASO migration > 10%, premium increase > 8%
9. "Network adequacy and provider contracting disputes" — OON rate > 8%, provider dispute rate > 5%, No Surprises Act arbitration backlog, directory accuracy < 85%
10. "Member churn and retention crisis" — Voluntary disenrollment > 12%, broker-driven churn > 40%, NPS < 25, digital engagement < 30%
11. "Value-based contracting and ACO shared savings shortfall" — Shared savings < 50% of target, TCC trend > benchmark + 2%, quality attainment < 70%, MSSP exit risk
12. "COB subrogation recovery gap" — Recovery rate < 60%, MSP compliance errors > 5%, conditional payment backlog > 90 days

---

## Reasoning Flow

### Step 1: Load Parent Master First (Inheritance Rule)

Before applying this subpack, ensure the **healthcare-master-v1** skill is loaded. The master provides:
- Value Driver Framework (Revenue Uplift / Cost Savings / Risk Reduction / Working Capital)
- Base Persona Archetypes (CFO, COO, Chief Strategy Officer, CISO, CCO)
- Evidence Source Types (10-K, CMS data, earnings calls, job postings, breach portals)
- Formula Templates (improvement x volume x unit value)
- Signal Source Taxonomy (financial, operational, regulatory, competitive)
- Benchmark Methodology (industry survey, government, financial ratings, academic)
- Governance Framework (confidence levels, validation rules, approval gates)

**When to use master vs. subpack:**
- Use **healthcare-master-v1** for general healthcare prospecting when the specific payer segment is unknown or the account spans providers, life sciences, and payers.
- Use **payers-v1 (this subpack)** when the account is confirmed as a payer or health insurance organization (MA plan, Medicaid MCO, commercial carrier, PBM, TPA, stop-loss carrier, ACO) and payer-specific economics apply.

### Step 2: Identify Payer Segment and Relevant Pains

Determine the primary business segments of the prospect:
- **Medicare Advantage / Part D** → Focus on PP001 (Stars), PP006 (Risk Adjustment), PP007 (Churn), PP018 (RADV)
- **Medicaid MCO** → Focus on PP008 (Margin Compression), PP005 (Care Gaps), PP016 (COB/Subrogation)
- **Commercial / Employer** → Focus on PP009 (RFP Loss), PP002 (MLR), PP011 (Network), PP015 (Digital Engagement)
- **PBM / Pharmacy** → Focus on PP010 (Drug Cost), PP017 (DIR Fees)
- **Stop-Loss / TPA** → Focus on PP012 (Premium Escalation), PP009 (Employer Erosion)
- **ACO / VBC** → Focus on PP014 (Shared Savings), PP005 (Care Gaps)

### Step 3: Signal Detection and Interpretation

Apply the 18 signal interpretation rules (PS001-PS018) to raw prospect data:

| Signal Source | What to Look For | Likely Pain | Confidence |
|--------------|------------------|-------------|------------|
| CMS Star Ratings | Decline 0.5+ stars or below 4.0 | PP001 | 0.91 |
| NAIC MLR Filing | Admin cost PMPM increase > 15% YoY | PP002 | 0.87 |
| CMS Sanctions Notice | CMP, marketing suspension, sanctions | PP013, PP018 | 0.93 |
| CMS Enrollment Data | Flat or declining quarterly enrollment | PP007 | 0.85 |
| NAIC Complaint Index | > 1.5x median for 2+ quarters | PP013 | 0.89 |
| State Procurement | Contract award to competitor or reduced service area | PP008 | 0.86 |
| PBM RFP / Termination | Client non-renewal or competitive RFP | PP010 | 0.84 |
| Stop-Loss Notifications | Claimant exceeding specific deductible | PP012 | 0.82 |
| RADV Audit Letter | CMS audit or conditional payment demand | PP018 | 0.94 |
| Employer Announcements | Plan switch or self-insured migration | PP009 | 0.88 |
| DOJ / Qui Tam | Unsealed whistleblower or settlement | PP004 | 0.92 |
| Network Provider Changes | > 5% terminated or not renewed | PP011 | 0.81 |
| NCQA / HEDIS Audit | Deferral or audit finding | PP005 | 0.90 |
| CMS Comment Letters | DIR / True OOP / counting rule comments | PP017 | 0.78 |
| Digital Vendor RFP | Member portal, app, or CRM RFP | PP015 | 0.76 |
| ACO Performance Data | Shared savings miss or provider exit | PP014 | 0.83 |
| COB Vendor Activity | Job postings or RFP for COB services | PP016 | 0.79 |
| Risk Adjustment Vendor Consolidation | In-house RA or vendor RFP | PP006 | 0.86 |

**Signal-to-Pain Confidence Scoring:**
- **HIGH (0.90-0.94):** Regulatory signals (CMS sanctions, RADV audit, DOJ action, NCQA finding) — direct government action
- **HIGH (0.85-0.89):** Financial/operational signals (Stars decline, MLR spike, complaint surge, enrollment plateau, employer defection)
- **MEDIUM (0.76-0.84):** Market/competitive signals (PBM RFP, ACO miss, stop-loss event, digital RFP, COB vendor search)
- Always validate signals with at least one corroborating source before customer-facing use.

### Step 4: Map to KPIs and Benchmarks

For each confirmed pain, pull the linked KPIs and compare against benchmarks:

| Pain | Primary KPIs | Benchmark | Typical Range |
|------|-------------|-----------|---------------|
| PP001 MA Stars | PK001, PK002, PK003, PK004 | > 4.0 stars | 3.0-4.5 |
| PP002 MLR Compression | PK005, PK006, PK007 | 80-88% | 80-90% |
| PP003 Claims Gap | PK008, PK009, PK010 | > 90% auto-adj, < 5 days | 78-92% |
| PP004 FWA Gap | PK011, PK012, PK013 | > 1.5% detection, > 6:1 recovery | 0.5-2.5% |
| PP005 Care Gaps | PK014, PK015, PK016 | > 70% closure, < 80 ED/1K | 45-75% |
| PP006 Risk Adjustment | PK017, PK018, PK019 | RAF gap < 0.05, recapture > 90% | 0.85-1.35 RAF |
| PP007 MA Churn | PK020, PK021, PK022 | < 10% disenrollment, NPS > 25 | 6-18% |
| PP008 Medicaid Margin | PK005, PK023, PK024 | MLR < 90%, encounter rejection < 10% | 85-93% |
| PP009 Employer Erosion | PK025, PK026, PK027 | Win rate > 35%, loss ratio < 78% | 20-45% |
| PP010 PBM Drug Cost | PK028, PK029, PK030 | GDR > 84%, specialty < 45% | 68-85% |
| PP011 Network Disputes | PK031, PK032, PK033 | OON < 5%, disputes < 3% | varies |
| PP012 Stop-Loss | PK034, PK035, PK036 | Premium trend < 10%, LASER < 10% | varies |
| PP013 Grievances | PK037, PK038, PK039 | Resolution < 20 days, overturn < 30% | 10-35 days |
| PP014 ACO Performance | PK040, PK041, PK042 | Savings > 75% target, attainment > 80% | varies |
| PP015 Digital Engagement | PK043, PK044, PK045 | Portal > 50%, app MAU > 25% | 15-45% |
| PP016 COB Recovery | PK046, PK047, PK048 | Recovery > 70%, MSP errors < 3% | varies |
| PP017 DIR Fees | PK049, PK050, PK051 | DIR drag < $8 PMPM | varies |
| PP018 RADV Compliance | PK052, PK053, PK054 | Error rate < 5%, invalidation < 10% | varies |

### Step 5: Map to Personas and Value Hypotheses

Use the signal pattern to identify which personas are most affected and which value driver category applies:

| Persona | Primary Pains | Value Driver Category | Discovery Questions |
|---------|--------------|----------------------|---------------------|
| Chief Medical Officer (Plan) | PP001, PP005, PP014, PP028 | Revenue Uplift + Cost Savings | PDQ001, PDQ017, PDQ012 |
| Chief Actuary | PP002, PP006, PP007, PP009, PP012 | Revenue Uplift + Cost Savings | PDQ002, PDQ004, PDQ006, PDQ010 |
| Network Contracting Director | PP011, PP022, PP034 | Risk Reduction + Cost Savings | PDQ009 |
| Grievances & Appeals Manager | PP013, PP025 | Risk Reduction | PDQ011 |
| Population Health Analyst | PP005, PP014, PP009 | Revenue Uplift + Cost Savings | PDQ012, PDQ017 |
| Risk Adjustment Director | PP006, PP018 | Revenue Uplift + Risk Reduction | PDQ004, PDQ016 |
| CFO (inherited from master) | PP002, PP004, PP008, PP009, PP010, PP016 | All categories | PDQ002, PDQ006, PDQ008 |
| COO (inherited from master) | PP002, PP003, PP008, PP016 | Cost Savings | PDQ003, PDQ011 |
| Chief Strategy Officer (inherited) | PP001, PP007, PP009, PP014 | Revenue Uplift | PDQ001, PDQ005, PDQ007 |

### Step 6: Calculate Value Using Pack Formulas

Apply the relevant formula based on confirmed pain and available inputs:

1. **PF001 — MA Stars Bonus Value:** `(Rating Improvement x Member Months x Bonus PMPM) + QBP Enhancement + Rebate Retention`
2. **PF002 — MLR Admin Cost Reduction:** `(Current Admin PMPM - Target) x Member Months + (SG&A Reduction x Premium Revenue)`
3. **PF003 — Claims Auto-Adjudication Value:** `(Volume x Manual Cost x Automation Lift %) + (Backlog Reduction x Interest Cost) + (Provider Satisfaction Impact)`
4. **PF004 — FWA Recovery Value:** `(Prepay Stopped x Avg Claim Value) + (Postpay Recovery x Recovery Rate) - (SIU Cost x (1 + Target ROI))`
5. **PF005 — Care Gap Closure Value:** `(Gaps Closed x Avg Cost per Gap) + (Preventable ED Avoided x Avg ED Cost) + (Stars Improvement x Bonus PMPM x Member Months)`
6. **PF006 — RAF Optimization Value:** `(Target RAF - Current RAF) x Member Months x Benchmark Rate x Coding Adjustment - RADV Penalty Risk`
7. **PF007 — Member Retention Value:** `(Churn Reduction x Member Months x LTV) + (Broker Churn Reduction x Acquisition Cost Savings)`
8. **PF008 — Medicaid MCO Margin Protection:** `(Encounter Rejection Reduction x Avg Claim Value x 12) + (Rate Appeal Success x Retroactive Adjustment) + (Admin Cap Efficiency)`
9. **PF009 — Employer Group Retention Value:** `(Group Retention Improvement x Group Premium) + (RFP Win Rate Improvement x Pipeline Value x Win Probability)`
10. **PF010 — PBM Drug Trend Management:** `(Specialty Trend Reduction x Specialty Spend) + (Biosimilar Adoption Increase x Brand Spend) + (DIR Fee Reduction x Part D Membership)`
11. **PF011 — Network Dispute Cost Avoidance:** `(Dispute Reduction x Avg Resolution Cost) + (No Surprises Act Arbitration Avoidance x Avg Arbitration Cost) + (Directory Accuracy Improvement x Complaint Cost)`
12. **PF012 — Grievance & Appeals Efficiency:** `(Resolution Time Reduction x FTE Cost) + (Overturn Rate Reduction x Avg Overturn Cost) + (CMP Avoidance x Probability)`

### Step 7: Confidence Scoring Guidance

| Confidence Level | Criteria | Action |
|----------------|----------|--------|
| **HIGH (0.90+)** | Multiple corroborating sources, quantified data, direct regulatory/financial reporting (CMS, NAIC, CAQH, NCQA) | Proceed with full value quantification and customer-facing messaging |
| **MEDIUM (0.80-0.89)** | Industry survey data, partial quantification, or single-source but authoritative (J.D. Power, KFF, McKinsey) | Proceed with caveats; validate with prospect-specific data before finalizing |
| **LOW (0.70-0.79)** | Estimates, directional indicators, or emerging trends with limited data | Use for discovery conversation openers only; do not cite specific values externally |

**Confidence Adjustment Rules:**
- Increase confidence by 0.05 if signal comes from primary regulatory source (CMS, NAIC, state DOI)
- Decrease confidence by 0.10 if relying solely on job postings or single news article
- Decrease confidence by 0.15 if the prospect's exact member count, premium volume, or RAF data is unavailable
- Require client validation before using organization-specific financial projections in proposals

---

## Inheritance Map

### Master Skill to Load First
**healthcare-master-v1** must be loaded before this subpack. The master provides the foundational framework that this subpack extends.

### What This Subpack Adds Beyond the Master

| Component | Master Provides | Subpack Adds |
|-----------|----------------|--------------|
| **Pains** | General healthcare pains (P006, P008, P010-P012, P017, P021-P022) | 18 payer-specific pains (PP001-PP018) covering MA Stars, MLR, claims adjudication, FWA, care gaps, risk adjustment, churn, Medicaid margin, employer erosion, PBM costs, network disputes, stop-loss, grievances, ACO performance, digital engagement, COB recovery, DIR fees, RADV compliance |
| **KPIs** | Base healthcare KPIs (K021-K023, K027-K029, K033-K042, K068-K073) | 54 payer-specific KPIs (PK001-PK054) covering Stars, HEDIS, MLR, claims, FWA, care gaps, RAF, churn, encounter data, employer metrics, pharmacy trends, network adequacy, stop-loss, grievances, ACO, digital engagement, COB, DIR, RADV |
| **Value Drivers** | Base drivers (V015, V019, V025, V029) | 36 payer-specific value drivers (PV001-PV036) with signal patterns, interpreted meanings, and required evidence |
| **Formulas** | Base formula templates | 12 quantified formulas (PF001-PF012) with example calculations, required inputs, and confidence rules |
| **Personas** | Base archetypes (CFO, COO, CSO, CISO, CCO) | 6 new vertical personas: Chief Medical Officer (Plan), Chief Actuary, Network Contracting Director, Grievances & Appeals Manager, Population Health Analyst, Risk Adjustment Director |
| **Signals** | Base signal taxonomy (S005, S012, S018, S030) | 18 payer-specific signal interpretation rules (PS001-PS018) with confidence scores and required confirmation |
| **Technology Systems** | Base systems (T016-T017) | 12 payer-specific systems (PT001-PT012): core admin, FWA/SIU, risk adjustment, HEDIS, member engagement, provider directory, VBC analytics, PBM, grievances, COB, prior auth, actuarial workbench |
| **Regulatory Factors** | Base regulations (REG001-REG004, REG011-REG012) | 10 payer-specific regulations (PREG001-PREG010): ACA 1557, CMS Stars, MLR reporting, CY 2025 Final Rule, NAIC RBC, state DOI, No Surprises Act, RADV, PBM transparency, HIPAA |
| **Buying Triggers** | — | 14 payer-specific buying triggers (PBT001-PBT014) with urgency, timing, linked pains, and procurement implications |
| **Discovery Questions** | — | 18 payer-specific discovery questions (PDQ001-PDQ018) mapped to personas and pains |
| **Objections** | — | 9 payer-specific objection patterns (POBJ001-POBJ009) with reframe strategies and supporting evidence |
| **Competitor Factors** | — | 8 payer-specific competitor factors (PCF001-PCF008) covering vertical integration, digital-native entrants, and market consolidation |
| **Worked Examples** | — | 3 worked examples: MA Star Rating Recovery, Medicaid MCO Operational Efficiency, Commercial Employer Group Retention + PBM Optimization |

### When to Use Master vs. Subpack

| Scenario | Use |
|----------|-----|
| Prospect is a multi-line health system with both hospital and insurance operations | Load **master first**, then **payers subpack** for the insurance division |
| Prospect is a standalone payer (e.g., Medicare Advantage plan, Medicaid MCO, commercial carrier) | Load **master** (brief), then **payers subpack** (primary) |
| Prospect is a provider organization with VBC contracts but no risk-bearing operations | Use **master only** or **provider subpack**; this subpack is NOT applicable |
| Prospect is a PBM, TPA, or stop-loss carrier | Load **master** (brief), then **payers subpack** (primary) |
| Cross-vertical account spanning pharma, provider, and payer | Load **master**, then relevant subpacks per division |

---

## Structured Output Template

### Signals Analysis Enrichment JSON

```json
{
  "pack_loaded": "payers-v1",
  "parent_master": "healthcare-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "prospect_segment": "Medicare Advantage | Medicaid MCO | Commercial | PBM | Stop-Loss | TPA | ACO",
  "signals_detected": [
    {
      "signal_id": "PS001",
      "signal_name": "CMS Star Rating Decline",
      "raw_evidence": "CMS 2025 Star Ratings show plan dropped from 4.0 to 3.5 stars",
      "interpreted_pain": "PP001 - Medicare Advantage Star Rating Erosion",
      "linked_kpis": ["PK001", "PK002", "PK003", "PK004"],
      "linked_value_drivers": ["PV001", "PV002"],
      "affected_personas": ["Chief Strategy Officer", "CMO (Plan)", "VP Quality", "Chief Actuary"],
      "confidence": 0.91,
      "required_confirmation": "HEDIS measure detail; CAHPS breakdown",
      "financial_outcome": "Revenue Uplift",
      "value_formula_applied": "PF001",
      "estimated_annual_value_usd": 183600000,
      "value_confidence": "HIGH"
    }
  ],
  "pains_confirmed": [
    {
      "pain_id": "PP001",
      "pain_name": "Medicare Advantage Star Rating Erosion",
      "severity": "HIGH",
      "symptoms_present": ["Star rating < 4.0", "HEDIS gap in 3+ domains", "QBP bonus at risk > $50M"],
      "prevalence": "HIGH",
      "confidence": "HIGH"
    }
  ],
  "kpis_assessed": [
    {
      "kpi_id": "PK001",
      "kpi_name": "Medicare Advantage Star Rating",
      "current_value": 3.5,
      "benchmark": "> 4.0",
      "gap": 0.5,
      "trend": "declining"
    }
  ],
  "personas_engaged": [
    {
      "persona": "CMO (Plan)",
      "relevance": "PRIMARY",
      "discovery_question": "PDQ001 - What is your current MA Star rating and which three measures moved most YoY?"
    }
  ],
  "value_summary": {
    "total_estimated_annual_value_usd": 183600000,
    "value_by_category": {
      "Revenue Uplift": 183600000,
      "Cost Savings": 0,
      "Risk Reduction": 0,
      "Working Capital": 0
    },
    "primary_formula": "PF001 - MA Stars Bonus Value",
    "implementation_cost_estimate_usd": 18000000,
    "net_3_year_value_usd": 496000000
  },
  "governance": {
    "confidence_level": "HIGH",
    "source_coverage": ["CMS 2025 Star Ratings", "CMS Medicare Advantage Rate Announcement", "McKinsey MA Stars Analysis 2024"],
    "customer_facing_approved": false,
    "validation_required": [
      "Verify current HEDIS measure-level gaps",
      "Validate CAHPS improvement feasibility",
      "Assess whether 0.5 star improvement is achievable in single measurement year"
    ]
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | High (pack-wide); individual signals range 0.76-0.94 |
| **Source Coverage** | Mixed — CMS data, NAIC financial reporting, NCQA HEDIS, CAQH Index, KFF surveys, J.D. Power studies, McKinsey analysis, industry benchmarks, DOJ/HCFAC reports, state DOI data |
| **Customer-Facing Approval Status** | No — internal intelligence asset; requires review before external use |
| **Review Owner** | payers-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Version** | 1.0.0 |
| **Agent Swarm ID** | kimi-k2.6-swarm-payers-s3.2 |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-healthcare-m3 |

### Confidence Flags Used

- **HIGH:** Multiple corroborating sources, quantified data, direct regulatory or financial reporting (CMS, NAIC, CAQH, NCQA)
- **MEDIUM:** Industry survey data, partial quantification, or single-source but authoritative (J.D. Power, KFF, McKinsey)
- **LOW:** Estimates, directional indicators, or emerging trends with limited data (digital engagement benchmarks, biosimilar adoption projections)

### Validation Required Before Customer Use

1. Verify current CMS Star Ratings and QBP tables against latest CMS announcements
2. Confirm MLR and admin cost benchmarks against NAIC/CAQH latest publications
3. Validate organization-specific member months, premium rates, and RAF scores before citing in proposals
4. Update Medicaid state rate and contract timelines quarterly
5. Review PBM contract terms and DIR structures for client-specific accuracy
6. Confirm RADV audit status and extrapolation methodology with client legal/compliance
7. Validate FWA recovery ratios against SIU internal tracking (often not public)
8. Update competitor landscape quarterly (M&A, market exits, new MA entrants)
9. Review signal rules for false positive rate against historical conversion data

---

## Quick Reference

### Top 5 Pains

| # | Pain | ID | Prevalence | Primary Financial Outcome |
|---|------|-----|-----------|--------------------------|
| 1 | **Medicare Advantage Star Rating Erosion** | PP001 | HIGH | Revenue Uplift |
| 2 | **Medical Loss Ratio (MLR) Compression Below 85%** | PP002 | HIGH | Cost Savings |
| 3 | **Care Gap Closure and HEDIS Underperformance** | PP005 | HIGH | Revenue Uplift |
| 4 | **Risk Adjustment Revenue Leakage and RADV Exposure** | PP006 | HIGH | Revenue Uplift |
| 5 | **Medicare Advantage Member Churn & Retention Crisis** | PP007 | HIGH | Revenue Uplift |

### Top 5 KPIs

| # | KPI | ID | Benchmark | Typical Range |
|---|-----|-----|-----------|---------------|
| 1 | **Medicare Advantage Star Rating** | PK001 | > 4.0 (bonus threshold) | 3.0-4.5 stars |
| 2 | **Medical Loss Ratio (MLR)** | PK005 | 80-88% (varies by market) | 80-90% |
| 3 | **Claims Auto-Adjudication Rate** | PK008 | > 90% (best practice) | 78-92% |
| 4 | **Care Gap Closure Rate** | PK014 | > 70% (best practice) | 45-75% |
| 5 | **Risk Adjustment Factor (RAF) Score** | PK017 | Gap vs. expected drives value | 0.85-1.35 |

### Top 3 Personas

| # | Persona | Primary Pains | Decision Influence |
|---|---------|--------------|-------------------|
| 1 | **Chief Actuary** | PP002, PP006, PP007, PP009, PP012 | Economic — controls pricing, reserves, financial projections; must validate all major financial commitments |
| 2 | **Chief Medical Officer (Plan)** | PP001, PP005, PP014 | Technical — drives clinical program design; needs CFO/CSO for budget |
| 3 | **Risk Adjustment Director** | PP006, PP018 | Technical — owns RAF methodology; needs CFO for budget; needs CMO for physician engagement |

### Key Value Formulas

| Formula | Expression | When to Use |
|---------|-----------|-------------|
| **PF001 — MA Stars Bonus Value** | `(Rating Improvement x Member Months x Bonus PMPM) + QBP Enhancement + Rebate Retention` | MA plan with Stars below 4.0 or declining |
| **PF002 — MLR Admin Cost Reduction** | `(Current Admin PMPM - Target) x Member Months + (SG&A Reduction x Premium Revenue)` | MLR > 87% with admin bloat |
| **PF006 — RAF Optimization Value** | `(Target RAF - Current RAF) x Member Months x Benchmark Rate x Coding Adjustment - RADV Penalty Risk` | RAF gap > 0.08 or RADV audit exposure |
| **PF007 — Member Retention Value** | `(Churn Reduction x Member Months x LTV) + (Broker Churn Reduction x Acquisition Cost Savings)` | Voluntary disenrollment > 12% |
| **PF010 — PBM Drug Trend Management** | `(Specialty Trend Reduction x Specialty Spend) + (Biosimilar Adoption Increase x Brand Spend) + (DIR Fee Reduction x Part D Membership)` | Specialty spend > 45% or DIR drag > $12 PMPM |

---

*End of SKILL.md for Payers and Health Insurance Subpack v1.0.0*
