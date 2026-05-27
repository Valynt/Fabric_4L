# SKILL.md — Insurance Vertical Subpack

## Skill Identity Block

| Attribute | Value |
|---|---|
| `skill_name` | Insurance Vertical Subpack |
| `description` | Vertical-specialized value intelligence for the Insurance industry, covering P&C, Life, Health, Reinsurance, Specialty, Commercial Lines, Personal Lines, Claims, Underwriting, Actuarial, and Brokerage. Provides AI-driven discovery, qualification, and value articulation for enterprise technology and service providers targeting insurance carriers, reinsurers, MGAs, and brokers. |
| `version` | 1.0.0 |
| `domain` | industry |
| `pack_type` | subpack |
| `parent_master` | financial-services-master-v1 |
| `id` | insurance-v1 |

---

## Triggers

Use this skill when a query matches any of the following natural language patterns:

1. **"claims leakage reduction"** — Adjuster capacity crisis, LAE escalation, SIU recovery, or fraud detection gaps
2. **"underwriting cycle time"** — PAS modernization, rating engine deployment, STP rate improvement, or new business strain
3. **"catastrophe model accuracy"** — Cat variance reduction, geocoding gaps, real-time exposure aggregation, or secondary peril modeling
4. **"reinsurance optimization"** — Treaty placement efficiency, ceded premium reduction, exposure data quality, or capacity squeeze
5. **"IFRS 17 LDTI compliance"** — Actuarial transformation, regulatory capital reporting, or contract boundary systems
6. **"health insurance MLR pressure"** — Medical loss ratio optimization, prior authorization, or administrative cost bloat
7. **"cyber insurance underwriting"** — Cyber accumulation risk, silent cyber exposure, or ransomware-driven combined ratio crisis
8. **"insurance digital transformation"** — Agent portal, policyholder self-service, mobile app, or BMS modernization
9. **"insurance fraud detection"** — Pre-loss SIU analytics, application fraud, provider fraud, or subrogation gaps
10. **"workers compensation medical costs"** — WC medical inflation, nurse case management, or return-to-work delays
11. **"RBC ratio stress"** — Regulatory capital adequacy, surplus protection, or investment portfolio ALM stress
12. **"MGA oversight compliance"** — Delegated underwriting authority, program administrator audits, or binding authority breaches

---

## Reasoning Flow

### Step 1: Inherit Master Context First
Before applying Insurance Subpack reasoning, load the **financial-services-master-v1** skill to establish:
- Base financial services value driver framework (VD001–VD012)
- Cross-industry persona archetypes (CIO, CFO, CRO, CCO, Chief Actuary)
- Universal signal taxonomy (10-K, earnings call, regulatory filing patterns)
- Governance and confidence methodology

### Step 2: Identify Insurance Vertical Segment
Determine the prospect's primary segment to scope pain relevance:
- Property/Casualty (claims-heavy, cat-exposed)
- Life Insurance (new business, STP, ALM)
- Health Insurance (MLR, admin ratio, Stars)
- Reinsurance (treaty placement, exposure aggregation)
- Specialty (cyber, surety, MGA, commercial)
- Personal Lines (digital, telematics, UBI)
- Commercial Lines (BMS, agent enablement, MGA)

### Step 3: Signal Detection & Interpretation
Apply the **18 Insurance-Specific Signal Rules (ISR001–ISR018)** to detect active pain conditions:

| Signal | Source | Pattern | Likely Pain(s) |
|---|---|---|---|
| ISR001 | NAIC | RBC declining >50 bps YoY x 2 years | IP014, IP017 |
| ISR002 | A.M. Best | Rating downgrade + negative outlook | IP014, IP002 |
| ISR003 | 10-K / NAIC | Ceded premium growth >20% while net declining | IP003, IP007 |
| ISR004 | SERFF | Rate filing withdrawal/disapproval >30% | IP015, IP001 |
| ISR005 | LIMRA | Life sales declining >15% while market growing | IP004 |
| ISR006 | CMS | MA Star Rating declining below 4.0 | IP005 |
| ISR007 | Verisk | LAE ratio >3 points YoY + severity >inflation+5% | IP002, IP006 |
| ISR008 | NCCI | WC modifier >1.05 + medical trend >6% | IP010 |
| ISR009 | J.D. Power | Digital score declining + app rating <3.5 | IP013, IP008 |
| ISR010 | Broker reports | Treaty cost increase >25% + coverage compression | IP003, IP007 |
| ISR011 | FBI/NAIC | Fraud referral rate <2% + SIU staffing declining | IP006 |
| ISR012 | NOAA | Cat loss >30% surplus + model variance >40% | IP007, IP014 |
| ISR013 | Agent surveys | Agent NPS declining >10 points | IP008, IP015 |
| ISR014 | ORSA | Cyber risk top emerging + no accumulation model | IP018 |
| ISR015 | 10-K / Earnings call | Management citing legacy system constraints | IP001, IP008 |
| ISR016 | MGA audits | State DOI finding authority breaches | IP016 |
| ISR017 | Fed / NAIC | Unrealized losses >10% surplus + alternatives >15% | IP017, IP014 |
| ISR018 | InsurTech news | Competitor launches UBI/embedded insurance | IP015, IP013 |

**Confidence scoring:**
- **HIGH** (0.85–1.00): Regulatory filings (NAIC, SEC), rating agency actions, catastrophe events
- **MEDIUM** (0.60–0.85): Industry surveys, broker reports, competitive intelligence
- **LOW** (0.30–0.60): Media speculation, unverified social signals

### Step 4: Pain-to-Persona Mapping
For each detected signal, identify affected personas and map to subpack-specific personas (IPER001–IPER006):

| Pain ID | Primary Personas | Secondary Personas |
|---|---|---|
| IP001 (PAS Debt) | IPER005 (PAS Manager) | CIO, CUO (IPER001) |
| IP002 (Adjuster Crisis) | IPER002 (CCO) | CFO, Head of Talent |
| IP003 (Reinsurance Friction) | IPER003 (Head of Reinsurance/CRO) | CUO, CFO |
| IP004 (Life NB Strain) | IPER001 (CUO) | IPER006 (Actuarial Director), COO |
| IP005 (Health MLR) | Chief Medical Officer, CFO | COO, IPER006 |
| IP006 (Fraud Gaps) | IPER002 (CCO), Head of SIU | CRO, Head of Analytics |
| IP007 (Cat Model Gaps) | IPER003 (CRO), IPER006 (Actuarial) | IPER001 (CUO) |
| IP008 (BMS Obsolescence) | Chief Distribution Officer, IPER005 | CIO, Reinsurance Broker |
| IP009 (Billing Inefficiency) | CFO, Head of Billing | IPER005, COO |
| IP010 (WC Medical Cost) | IPER002 (CCO), IPER004 (Loss Control) | CUO, IPER006 |
| IP011 (ALM Hedging) | IPER006 (Actuarial), CIO | CFO, CRO |
| IP012 (Surety Inefficiency) | IPER001 (CUO), Surety Manager | CFO |
| IP013 (Digital Deficits) | Chief Digital Officer, CMO | IPER005, Head of CX |
| IP014 (RBC Stress) | CFO, IPER003 (CRO) | IPER006, CIO |
| IP015 (Rating Engine Legacy) | IPER001 (CUO), IPER006 | CIO, Head of Pricing |
| IP016 (MGA Oversight) | IPER001 (CUO), IPER003 (CRO) | Compliance VP |
| IP017 (ALM/Liquidity Stress) | CIO, CFO | IPER006, CRO |
| IP018 (Cyber Underwriting) | IPER003 (CRO), IPER001 (CUO) | Head of Cyber, IPER006 |

### Step 5: KPI Benchmarking & Value Hypothesis
Compare detected prospect KPIs against subpack benchmarks (IB001–IB026):
- If prospect KPI is in **Bottom Quartile** → Pain is acute; value hypothesis = competitive parity recovery
- If prospect KPI is **Below Median** → Pain is moderate; value hypothesis = best-practice alignment
- If prospect KPI is **Near Benchmark** → Pain is latent; value hypothesis = market leadership / next-gen capability

**Value hypothesis formulation template:**
> "Based on [signal evidence] and your [KPI] at [value] vs. benchmark [value], we estimate [value driver] could deliver [range] impact, equating to [$ estimate] over [time horizon]."

### Step 6: Cross-Reference Value Drivers
Link each confirmed pain to insurance-specific value drivers (IVD001–IVD036) and master value drivers (VD001–VD012) for comprehensive ROI modeling.

### Step 7: Confidence Scoring Guidance
Score the overall opportunity confidence as follows:

| Factor | Weight | Assessment |
|---|---|---|
| Signal strength | 30% | How many signals detected? How recent? |
| Data quality | 25% | Direct prospect data vs. inferred/industry proxy |
| Segment alignment | 20% | Pain relevance to prospect's primary lines |
| Persona accessibility | 15% | Can economic buyer be engaged? |
| Competitive urgency | 10% | Is there a buying trigger window open? |

**Overall confidence thresholds:**
- **HIGH (≥0.75):** Proceed with detailed value proposal and discovery call
- **MEDIUM (0.50–0.74):** Conduct discovery to validate assumptions
- **LOW (<0.50):** Monitor signals; nurture until confidence increases

---

## Inheritance Map

### Master Skill to Load First
**financial-services-master-v1** must be loaded before applying this subpack. The master provides:
- Universal financial services value driver framework
- Cross-industry personas (CIO, CFO, CRO, CCO, Chief Actuary, CCO/Compliance)
- Base signal taxonomy (10-K, earnings call, regulatory filing patterns)
- Governance methodology (confidence levels, source coverage, approval workflow)
- 9 master pains relevant to insurance (P006, P007, P010, P011, P017, P019, P021, P022, P023)
- 12 master KPIs (K018–K023, K063–K071)
- Master technology systems (TS006 PAS, TS007 Claims, TS020 Actuarial)
- Regulatory factors (RF003 SOX, RF007 GDPR, RF008 GLBA, RF009 IFRS 17/LDTI, RF010 SEC Cyber, RF013 SR 11-7)

### What This Subpack Adds
The Insurance Subpack extends the master with **vertical-specialized components only** — no master overrides:

| Component | Count | ID Range | Purpose |
|---|---|---|---|
| Insurance-Specific Pains | 18 | IP001–IP018 | Segment-level pain definitions with symptoms, personas, and KPI links |
| Insurance-Specific KPIs | 54 | IK001–IK054 | Benchmarked operational and financial metrics |
| Insurance-Specific Value Drivers | 36 | IVD001–IVD036 | Quantified impact ranges by segment |
| Insurance-Specific Formulas | 15 | IVF001–IVF015 | ROI calculation templates with confidence rules |
| Insurance-Specific Benchmarks | 26 | IB001–IB026 | Quartile-based performance benchmarks |
| Insurance-Specific Signal Rules | 18 | ISR001–ISR018 | Detection patterns from industry data sources |
| Insurance-Specific Personas | 6 | IPER001–IPER006 | CUO, CCO, Reinsurance/CRO, Loss Control, PAS Manager, Actuarial Director |
| Discovery Questions | 18 | IDQ001–IDQ018 | Segment-specific qualification questions |
| Objection Patterns | 9 | IOBJ001–IOBJ009 | Rebuttals for insurance-specific objections |
| Technology Systems | 15 | ITS001–ITS015 | Vendor landscape and integration maps |
| Regulatory Factors | 11 | IRF001–IRF011 | NAIC, CMS, IFRS 17/LDTI, state DOI, and climate rules |
| Buying Triggers | 15 | IBT001–IBT015 | Time-boxed events with probability and target personas |
| Worked Examples | 3 | IWE001–IWE003 | P&C claims, life new business, reinsurance scenarios |
| Competitor Factors | 6 | ICF001–ICF006 | InsurTech, embedded insurance, MGA disruption |
| Evidence Sources | 4 | IES001–IES004 | NAIC, A.M. Best, NCCI, Verisk/ISO |

### When to Use Master vs. Subpack

| Scenario | Use |
|---|---|
| Prospect is a bank or wealth manager with insurance subsidiary | Master only for parent; Subpack only for insurance subsidiary |
| Prospect is a pure-play insurance carrier, reinsurer, MGA, or broker | Master for base context + Subpack for all vertical depth |
| Query mentions "financial services" generally | Master only |
| Query mentions specific insurance lines, claims, underwriting, or actuarial | Master + Subpack |
| Need cross-industry comparison (e.g., insurance vs. banking) | Master as common framework + both subpacks |

---

## Structured Output Template

When this skill is applied, the enriched account/prospect output must conform to the following JSON structure:

```json
{
  "skill_applied": "insurance-v1",
  "parent_master": "financial-services-master-v1",
  "enrichment_timestamp": "2026-04-25T00:00:00Z",
  "segment_classification": {
    "primary_segment": "Property/Casualty | Life | Health | Reinsurance | Specialty | Commercial Lines | Personal Lines",
    "secondary_segments": [],
    "confidence": "HIGH | MEDIUM | LOW"
  },
  "signals_detected": [
    {
      "signal_id": "ISR001",
      "signal_name": "RBC Declining Trend",
      "source": "NAIC Financial Statement Database",
      "evidence": "RBC ratio 210% in 2024, 265% in 2023, 320% in 2022",
      "confidence": 0.92,
      "recency_days": 45
    }
  ],
  "active_pains": [
    {
      "pain_id": "IP014",
      "pain_name": "Insurance Regulatory Capital and RBC Stress",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "symptoms_matched": ["RBC ratio <250%", "surplus growth negative 2+ years"],
      "affected_personas": ["CFO", "CRO", "Chief Actuary", "Chief Investment Officer"],
      "linked_kpis": ["IK040", "IK041", "IK042"],
      "linked_value_drivers": ["IVD027", "IVD028"]
    }
  ],
  "kpi_benchmarks": [
    {
      "kpi_id": "IK040",
      "kpi_name": "RBC Ratio",
      "prospect_value": 210,
      "unit": "%",
      "typical_range": "250-450",
      "benchmark_range": "350-500",
      "quartile": "BOTTOM",
      "gap_to_median": -90
    }
  ],
  "persona_map": [
    {
      "persona_id": "IPER003",
      "persona_name": "Head of Reinsurance / CRO",
      "relevance": "HIGH",
      "engagement_priority": 1,
      "discovery_questions": ["IDQ004", "IDQ008", "IDQ014"],
      "likely_objections": ["IOBJ006"]
    }
  ],
  "value_hypotheses": [
    {
      "value_driver_id": "IVD027",
      "value_driver_name": "Capital Adequacy Improvement",
      "impact_category": "Risk Reduction",
      "estimated_range": "50-150 bps RBC improvement",
      "prospect_specific_estimate": "$12M-$45M capital cost avoidance over 3 years",
      "formula_ref": "IVF010",
      "confidence": "MEDIUM"
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "IBT012",
      "trigger_name": "RBC approaching company action level (200%)",
      "window_days": "30-90",
      "probability": 0.80,
      "target_personas": ["CRO", "Chief Actuary"]
    }
  ],
  "competitive_factors": [
    {
      "factor_id": "ICF003",
      "factor_name": "Reinsurance Capital Markets Convergence",
      "impact": "Traditional reinsurance pricing pressure; need for real-time exposure data to access ILS markets",
      "confidence": "HIGH"
    }
  ],
  "regulatory_factors": [
    {
      "reg_id": "IRF001",
      "reg_name": "NAIC Risk-Based Capital (RBC)",
      "applicability": "All US insurance carriers",
      "deadline": "Annual NAIC filing",
      "non_compliance_penalty": "Regulatory action level, mandatory capital plan, license restriction"
    }
  ],
  "technology_systems": [
    {
      "system_id": "ITS001",
      "system_name": "Underwriting Workbench",
      "category": "Underwriting",
      "vendors": ["Guidewire", "Duck Creek", "Insurity", "Majesco", "Snapsheet"]
    }
  ],
  "overall_confidence": 0.78,
  "next_actions": [
    "Schedule discovery call with CRO using IDQ014",
    "Validate RBC trend with NAIC filing data",
    "Prepare IVF010 value model with prospect surplus data"
  ]
}
```

---

## Governance Metadata

| Attribute | Value |
|---|---|
| **Confidence Level** | Medium (inherited master confidence HIGH; subpack additions range HIGH to MEDIUM based on segment specificity) |
| **Source Coverage** | Mixed: Public regulatory filings (NAIC, SEC, CMS, SERFF) + Proprietary industry data (A.M. Best, Verisk, LIMRA, NCCI, Novarica, Celent, Guy Carpenter) |
| **Customer-Facing Approval Status** | **Pending Review** — NOT approved for direct customer-facing output until review owner sign-off |
| **Review Owner** | Insurance Vertical Subpack Architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-s4.3-insurance |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-m4-financial-services |
| **Value Impact Categories** | Revenue Uplift (5-20% premium growth; 2-5 point CR improvement) — HIGH confidence; Cost Savings (20-50% claims, UW, admin) — HIGH confidence; Risk Reduction (30-50% cat variance; 50-150 bps RBC) — MEDIUM confidence; Working Capital (20-35% DSO; 30-50% reinsurance acceleration) — MEDIUM confidence |

---

## Quick Reference

### Top 5 Pains (by prevalence × confidence)

| Rank | Pain ID | Name | Prevalence | Confidence |
|---|---|---|---|---|
| 1 | IP002 | Claims Adjuster Capacity Crisis and Talent Shortage | HIGH | HIGH |
| 2 | IP001 | Policy Administration System Modernization Debt | HIGH | HIGH |
| 3 | IP014 | Insurance Regulatory Capital and RBC Stress | HIGH | HIGH |
| 4 | IP007 | Catastrophe Modeling and Exposure Management Data Gaps | HIGH | HIGH |
| 5 | IP005 | Health Insurance MLR Pressure and Administrative Cost Bloat | HIGH | HIGH |

### Top 5 KPIs (by cross-segment applicability)

| Rank | KPI ID | Name | Benchmark | Key Segments |
|---|---|---|---|---|
| 1 | IK004 | Claims Per Adjuster (Open Inventory) | 80-120 | P&C, Personal |
| 2 | IK040 | RBC Ratio | 350-500% | All insurance |
| 3 | IK010 | Life Insurance STP Rate | 50-75% | Life |
| 4 | IK013 | Health Insurance MLR | 82-85% | Health |
| 5 | IK019 | Cat Model Annual Variance | 5-15% | P&C, Reinsurance |

### Top 3 Personas (by decision influence and engagement frequency)

| Rank | Persona ID | Name | Role | Influence |
|---|---|---|---|---|
| 1 | IPER001 | Chief Underwriting Officer (CUO) | Pricing and risk selection | Economic |
| 2 | IPER002 | Chief Claims Officer (CCO) | Claims operations and SIU | Economic |
| 3 | IPER003 | Head of Reinsurance / CRO | Risk transfer and capital optimization | Economic |

### Key Value Formulas

| Formula ID | Name | Core Equation | Confidence Driver |
|---|---|---|---|
| IVF001 | Claims Leakage Cost Avoidance | `Annual Incurred Losses * Leakage Rate * Target Reduction % * (1 - Implementation Risk)` | External audit documented leakage rate |
| IVF003 | Reinsurance Cost Optimization | `GWP * (Current Ceded % - Target Ceded %) - Restructuring Cost` | Broker validated program structure |
| IVF007 | Cat Model Accuracy Improvement | `(Current Variance - Target Variance) / 100 * Avg Annual Cat Loss * Capital Cost Saving %` | Vendor (RMS/AIR) validated model |
| IVF010 | RBC Ratio Protection | `(Target RBC - Current RBC) / 100 * Surplus * (External Capital Cost % - Internal Cost %)` | NAIC filing with no qualifications |
| IVF012 | Cyber Insurance Profitability Recovery | `Cyber Earned Premium * (Target CR - Current CR) / 100 - Accumulation Model Investment` | Cyber book segmented and reserving validated |

---

*SKILL.md generated by Skills Packaging Agent from value-pack.json and value-pack.md. Do not modify value-pack.json or signals-examples.ts.*
