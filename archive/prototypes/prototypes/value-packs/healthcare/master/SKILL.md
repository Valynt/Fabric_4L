# SKILL.md — Healthcare Master ValuePack (M3)

<!--
OpenClaw Skill Manifest
Compatible with: kimi-k2.6-swarm-healthcare-m3
Pack Type: Master
-->

---

## 1. Skill Identity

| Attribute | Value |
|-----------|-------|
| **skill_name** | Healthcare Master ValuePack |
| **description** | Comprehensive value intelligence foundation for the healthcare industry spanning care delivery, payers, life sciences, operations, and regulated data/compliance. Enables precise diagnosis of business pains, quantification of improvement opportunities, and contextual discovery across health systems, health plans, pharma, biotech, medical devices, and healthcare technology. |
| **version** | 1.0.0 |
| **domain** | industry |
| **pack_type** | master |
| **parent_master** | — |

---

## 2. Triggers

Use this skill when a user query matches any of the following natural-language patterns:

1. **"Analyze a health system / hospital / health network"**
2. **"Hospital revenue cycle pain points"** or **"RCM denial signals"**
3. **"Payer claims denial / adjudication analysis"**
4. **"Medicare Advantage Star Rating erosion"** or **"MA plan quality gaps"**
5. **"Healthcare workforce / nurse staffing crisis"**
6. **"Clinical trial recruitment failure"** or **"pharma R&D timeline risk"**
7. **"HIPAA breach exposure"** or **"healthcare cybersecurity posture"**
8. **"Prior authorization bottleneck"** or **"PA automation opportunity"**
9. **"340B program compliance"** or **"pharmacy revenue optimization"**
10. **"Length of stay reduction"** or **"bed capacity / throughput analysis"**
11. **"Healthcare supply chain disruption"** or **"medical device post-market vigilance"**
12. **"FHIR interoperability gap"** or **"ONC Cures Act compliance"**

---

## 3. Reasoning Flow

### Step 1 — Segment Identification
Determine which of the five primary segments the prospect belongs to:
- **Care Delivery (Providers)** — Hospitals, AMCs, clinics, ASCs, telehealth, behavioral health, post-acute
- **Payers and Health Insurance** — Commercial, MA, Medicaid, PBMs, TPAs, ACOs
- **Life Sciences** — Pharma, biotech, devices, diagnostics, CROs, CDMOs
- **Healthcare Operations** — RCM, claims, CDI, workforce, supply chain, pharmacy
- **Regulated Healthcare Data and Compliance** — HIPAA, HITRUST, FHIR, FWA, data privacy

Use the taxonomy in `value-pack.json` to confirm sub-segment alignment (revenue range, geographic concentration, and operational model).

### Step 2 — Signal Collection & Triage
Gather publicly observable and account-specific signals:
- **Financial:** 10-K / earnings call transcripts, bond ratings, operating margin trends
- **Quality / Regulatory:** CMS Hospital Compare, CMS Star Ratings, HHS OCR breach portal, FDA Warning Letters
- **Operational:** Job posting surges, leadership changes, M&A activity, contract rebid notices
- **Technology:** EHR vendor, interoperability certifications, cybersecurity disclosures

Cross-reference signals against the **30 Signal Interpretation Rules** in `value-pack.json`. Each rule maps a raw signal pattern to an interpreted meaning, confidence score (0.0–1.0), and linked business pains.

### Step 3 — Pain Diagnosis
Match confirmed signals to the **25 Business Pains** using the linked signal→pain mappings. For each matched pain:
- Verify at least **2+ symptoms** are present (from the pain's symptom list)
- Confirm segment applicability
- Note prevalence (HIGH / MEDIUM / LOW) and confidence (HIGH / MEDIUM / LOW)

**Confidence scoring guidance:**
- **≥ 0.85:** Multiple corroborating sources, quantified financial/quality data, direct regulatory reporting
- **0.70–0.84:** Industry survey data, partial quantification, single authoritative source
- **< 0.70:** Estimates, directional indicators, emerging trends with limited data

### Step 4 — KPI Quantification
For each diagnosed pain, identify the relevant KPIs from the **82 KPI definitions** in the pack. Use benchmark ranges to assess severity:
- **Green:** Within or better than benchmark
- **Yellow:** Outside benchmark but not yet critical
- **Red:** Beyond crisis threshold (see individual KPI benchmark ranges)

### Step 5 — Persona Mapping
Identify the affected executive personas using the **14 Persona Profiles**. For each persona:
- Match their pressures and goals to the diagnosed pains
- Select discovery questions (from the 20 Discovery Questions) that align with their trusted evidence preferences
- Flag objections they are likely to raise (from the 10 Objection Patterns)

### Step 6 — Value Hypothesis Construction
Translate pains + KPI gaps into financially meaningful outcomes using the **four value categories**:
- **Revenue Uplift** — Denial reduction, referral leakage recovery, RAF optimization, MA Stars bonus
- **Cost Savings** — LOS reduction, contract labor substitution, auto-adjudication, supply chain optimization
- **Risk Reduction** — HIPAA breach avoidance, FDA compliance, HRRP penalty avoidance, DOJ settlement prevention
- **Working Capital / Cash Flow** — A/R days reduction, days cash on hand improvement, collection acceleration

Apply the **25 Value Formulas** to estimate annualized financial impact. Required inputs are listed per formula; do not project without confirming at least 60% of inputs with the prospect.

### Step 7 — Subpack Recommendation
If the analysis reveals deep specialization in a single segment, recommend loading the appropriate subpack for enriched specificity:
- **Providers / Care Delivery** (`providers-v1`)
- **Payers & Health Insurance** (`payers-v1`)
- **Life Sciences** (`life-sciences-v1`)
- **Healthcare Operations** (`healthcare-ops-v1`)
- **Healthcare Compliance & Data** (`healthcare-compliance-v1`)

---

## 4. Inheritance Map

*(Not applicable — this is a Master pack. Subpacks inherit from this master as documented in Section 19 of `value-pack.md` and the `subpackMapping` table in `value-pack.json`.)*

When a user loads a subpack:
- **Master is always loaded first** to establish taxonomy, governance, and cross-segment KPIs.
- The subpack **overrides or extends** segment-specific pains, KPIs, benchmarks, and discovery questions.
- **Use master** for multi-segment accounts, conglomerates, or initial triage.
- **Use subpack** for deep-dive analysis on a single segment after master triage is complete.

---

## 5. Structured Output Template

When enriching a prospect or account with Signals Analysis, produce a JSON object conforming to this structure:

```json
{
  "skill_loaded": "healthcare-master-v1",
  "analysis_timestamp": "ISO-8601",
  "prospect": {
    "name": "string",
    "segment": "Care Delivery (Providers) | Payers and Health Insurance | Life Sciences | Healthcare Operations | Regulated Healthcare Data and Compliance",
    "sub_segments": ["string"],
    "estimated_revenue_range": "string"
  },
  "signals_detected": [
    {
      "signal_id": "S###",
      "signal_name": "string",
      "raw_evidence": "string | url | excerpt",
      "confidence_score": 0.0,
      "linked_pains": ["P###"],
      "linked_kpis": ["K###"],
      "confirmation_required": ["string"]
    }
  ],
  "pains_diagnosed": [
    {
      "pain_id": "P###",
      "pain_name": "string",
      "prevalence": "HIGH | MEDIUM | LOW",
      "confidence": "HIGH | MEDIUM | LOW",
      "symptoms_observed": ["string"],
      "symptoms_confirmed_count": 0,
      "affected_personas": ["string"],
      "linked_kpis": ["K###"],
      "linked_value_drivers": ["V###"],
      "financial_category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital"
    }
  ],
  "kpis_assessed": [
    {
      "kpi_id": "K###",
      "kpi_name": "string",
      "observed_value": "number | string",
      "benchmark_range": "string",
      "severity": "green | yellow | red",
      "trend": "improving | stable | worsening | unknown"
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "PER###",
      "name": "string",
      "role": "string",
      "influence_type": "economic | technical | user",
      "relevant_pains": ["P###"],
      "recommended_discovery_questions": ["DQ###"],
      "likely_objections": ["OBJ###"]
    }
  ],
  "value_hypotheses": [
    {
      "value_driver_id": "V###",
      "category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital",
      "hypothesis": "string",
      "formula_id": "F### | null",
      "estimated_annual_impact_usd": "number | null",
      "confidence": "HIGH | MEDIUM | LOW",
      "required_inputs_confirmed": 0,
      "required_inputs_total": 0
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "BT###",
      "trigger_event": "string",
      "urgency": "CRITICAL | HIGH | MEDIUM | LOW",
      "typical_timing": "string",
      "procurement_implications": "string"
    }
  ],
  "recommended_subpack": "string | null",
  "next_steps": ["string"],
  "governance": {
    "overall_confidence": "HIGH | MEDIUM | LOW",
    "source_coverage": ["ES###"],
    "customer_facing_ready": false,
    "review_owner": "healthcare-master-architect",
    "last_updated": "2026-04-25"
  }
}
```

---

## 6. Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | High |
| **Source Coverage** | Mixed — public filings (10-K, 8-K), government data (CMS, FDA, HHS OCR), industry surveys (HFMA, HIMSS, AHA, NSI), proprietary benchmarks (Kaufman Hall, Crowe, Press Ganey), and regulatory publications |
| **Customer-Facing Approval Status** | **No** — Internal intelligence asset; requires review before external use |
| **Review Owner** | healthcare-master-architect |
| **Last Updated** | 2026-04-25 |
| **Version** | 1.0.0 |
| **Agent Swarm ID** | kimi-k2.6-swarm-healthcare-m3 |

### Confidence Flags
- **HIGH:** Multiple corroborating sources, quantified data, direct regulatory or financial reporting
- **MEDIUM:** Industry survey data, partial quantification, or single-source but authoritative
- **LOW:** Estimates, directional indicators, or emerging trends with limited data

### Validation Required Before Customer Use
1. Verify current benchmarks against latest HFMA, CMS, and CAQH publications
2. Confirm state-specific regulatory deadlines (staffing ratios, price transparency)
3. Validate organization-specific financial metrics before citing in proposals
4. Update competitor landscape quarterly (M&A, market exits, new entrants)
5. Review signal rules for false positive rate against historical conversion data

---

## 7. Quick Reference

### Top 5 Pains (by prevalence & impact)

| # | ID | Pain | Primary Segments | Key Symptom |
|---|----|------|------------------|-------------|
| 1 | P001 | Revenue Cycle Denial Rate Escalation | Providers, Operations | Denial rate > 8%; A/R days > 50 |
| 2 | P003 | Nurse Staffing Crisis and Premium Labor Dependency | Providers | Travel nurse expense > 5% of labor budget |
| 3 | P005 | Operating Margin Compression | Providers | Operating margin < 2% for > 2 years |
| 4 | P011 | Medicare Advantage Star Rating Erosion | Payers | Star rating < 4.0 or declining YoY |
| 5 | P017 | Cybersecurity / HIPAA Breach Exposure | Providers, Payers, Compliance | Security incidents > 2 per quarter |

### Top 5 KPIs (universal health indicators)

| # | ID | KPI | Benchmark | Segment |
|---|----|-----|-----------|---------|
| 1 | K001 | Net Days in A/R | 30–45 days (top quartile) | Providers, Operations |
| 2 | K002 | Initial Denial Rate | < 8% (best practice) | Providers, Operations |
| 3 | K006 | Average LOS | Within 0.95–1.05 of expected by DRG | Providers |
| 4 | K010 | Nurse Turnover Rate | < 15% (top quartile) | Providers |
| 5 | K018 | Operating EBITDA Margin | > 5% (strong); < 0% (distress) | Providers |

### Top 3 Personas (by decision frequency)

| # | ID | Persona | Influence | Primary Pains |
|---|----|---------|-----------|---------------|
| 1 | PER001 | Chief Financial Officer (CFO) | Economic | P001, P003, P005, P008, P012 |
| 2 | PER002 | Chief Operating Officer (COO) | Economic | P002, P003, P005, P006, P016 |
| 3 | PER003 | Chief Medical Officer (CMO) | Technical | P002, P004, P009, P019, P022 |

### Key Value Formulas (representative)

| ID | Formula | Example Output |
|----|---------|----------------|
| F001 | Denial Reduction Value | `(12% – 6%) × $500M × 0.40 × 0.85 = $10.2M` annually |
| F002 | LOS Reduction Value | `(5.2 – 4.5) × 25,000 × $2,400 = $42.0M` annually |
| F003 | Nurse Turnover Cost Avoidance | `(22% – 15%) × 1,200 × $78,000 = $6.55M` annually |
| F009 | Risk Adjustment Revenue Capture | `0.13 × 120,000 × $950 × 0.955 = $14.2M` annually |
| F012 | MA Stars Bonus Value | `0.5 × 1.2M × $85 + $12M = $63M` annually |

---

## 8. File Manifest

Files co-located with this skill (preserve as-is):

| File | Purpose |
|------|---------|
| `value-pack.json` | Machine-parseable master data (pains, KPIs, value drivers, benchmarks, signals, personas, triggers, formulas, taxonomies) |
| `value-pack.md` | Human-readable reference documentation with full tables and descriptions |
| `SKILL.md` | *(this file)* OpenClaw skill manifest for agent swarm loading |

*(Note: `signals-examples.ts` is not present in this master directory; create or load from subpacks as needed.)*

---

*End of SKILL.md — Healthcare Master ValuePack v1.0.0*
