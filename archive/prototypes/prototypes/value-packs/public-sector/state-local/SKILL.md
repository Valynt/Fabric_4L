# SKILL.md — State and Local Government Value Subpack

---

## 1. Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | State and Local Government Value Subpack |
| **description** | Vertical-specialized value intelligence for State and Local Government agencies including DMVs, public safety, courts, tax/revenue, public works, housing authorities, and emergency management. Covers $3.5T+ combined annual spending across 50 states, 3,100+ counties, and 19,000+ municipalities. Identifies operational bottlenecks, citizen service gaps, and modernization opportunities with quantifiable ROI. |
| **version** | 1.0.0 |
| **domain** | Public Sector / State & Local Government |
| **pack_type** | subpack |
| **parent_master** | public-sector-master-v1 |

---

## 2. Triggers

The following natural language query patterns should auto-load this skill:

1. **"DMV wait time reduction"** — Identifies driver license and vehicle registration office throughput crises, appointment backlogs, and digital channel shift opportunities.
2. **"911 call answer rate"** — Targets PSAP staffing shortages, legacy CAD gaps, NG911 migration needs, and abandoned call reduction.
3. **"State tax modernization"** — Focuses on property tax CAMA systems, assessment accuracy, collection gap closure, and delinquency reduction.
4. **"Public safety CAD RMS"** — Addresses computer-aided dispatch and records management system modernization, uptime requirements, and interoperability.
5. **"Permitting automation"** — Targets building permit cycle time reduction, digital plan review, inspection scheduling, and developer experience.
6. **"Court case backlog"** — Identifies criminal/civil case disposition delays, e-filing gaps, pre-trial jail population drivers, and digital records fragmentation.
7. **"StateRAMP cybersecurity"** — Focuses on cloud vendor authorization gaps, ransomware exposure, and state/local cybersecurity program maturity.
8. **"Public works fleet management"** — Targets municipal fleet telematics, predictive maintenance, asset life-cycle optimization, and road condition management.
9. **"311 citizen service consolidation"** — Addresses multi-channel request duplication, work order routing gaps, and first-contact resolution improvement.
10. **"State procurement acceleration"** — Identifies procurement cycle elongation, sole-source dependency, bid protest rates, and vendor pool expansion.
11. **"Housing voucher backlog"** — Focuses on Section 8 waitlist management, HAP contract utilization, PHA SEMAP scores, and landlord retention.
12. **"Emergency management interoperability"** — Targets common operating picture gaps, radio interoperability, mutual aid resource deployment, and EOC platform integration.

---

## 3. Reasoning Flow

### Step 1: Inherit Master Framework
Before applying this subpack, ensure the **public-sector-master-v1** skill is loaded. The master provides:
- Value Driver Framework (Cost Savings, Risk Reduction, Mission Effectiveness, Working Capital, Revenue Uplift)
- Base Persona Archetypes (CIO, CISO, CFO, Program Director, Inspector General, Budget Officer)
- Formula Templates (NPV, annual savings, cost avoidance structures)
- Signal Source Taxonomy (budget docs, audit reports, RFPs, workforce data)
- Benchmark Methodology and Governance Framework

### Step 2: Identify Prospect Segment
Map the account to one or more state/local segments:
| Segment | Key Clues |
|---------|-----------|
| State-Level Executive Agency | Governor's cabinet, state departments, statewide IT |
| County Government | Board of commissioners, county manager, sheriff, tax assessor |
| Municipal / City Government | Mayor-council, city departments, 311 services |
| Public Works / DOT | Roads, bridges, water, fleet, state highway program |
| DMV / Motor Vehicle | Driver licensing, vehicle registration, ID issuance |
| Public Safety | Police, fire, EMS, PSAP, 911 dispatch |
| Courts / Justice | Trial courts, court administrator, clerk of court |
| Tax / Revenue | Property tax, sales tax, income tax administration |
| Housing Authority | Section 8 vouchers, public housing, PHA |
| Emergency Management | EMA, disaster preparedness, mutual aid coordination |

### Step 3: Detect Relevant Signals
Search for evidence matching the **18 signal rules** in this subpack. Priority signal sources:
- **NASCIO / AAMVA / NENA / IAAO** industry surveys and standards
- **State auditor / IG reports** (procurement, IT, tax gap findings)
- **Federal grant announcements** (IIJA, IRA, SLFRF, BEAD, FEMA)
- **Local news / 311 data / court statistics** (backlogs, wait times, complaints)
- **MS-ISAC / NASCIO cybersecurity reports** (ransomware, StateRAMP status)
- **Bond rating opinions / CAFR disclosures** (operational efficiency flags)
- **RFP / sole-source / protest records** (procurement friction)

### Step 4: Match Signals to Pains
Use the symptom thresholds defined in each pain to confirm relevance:

| Pain ID | Primary Symptom Thresholds |
|---------|---------------------------|
| SL-PAIN-101 | Wait time >60 min; Appointment backlog >4 weeks; Digital share <30% |
| SL-PAIN-102 | 911 answer rate <90% within 15 sec; Abandoned calls >5%; PSAP vacancy >15% |
| SL-PAIN-103 | Appeal rate >5%; Assessment-to-sale ratio outside 0.90-1.10; CAMA >15 years old |
| SL-PAIN-104 | Case disposition >180 days (criminal); E-filing <50%; Jail pre-trial >60% |
| SL-PAIN-105 | Pothole response >72 hours; Road condition <3.0/5; Liability claims increasing |
| SL-PAIN-106 | Procurement cycle >150 days (IT); Sole-source >15%; Protest rate >3% |
| SL-PAIN-107 | Waitlist >2 years; HAP utilization <95%; SEMAP score <80 |
| SL-PAIN-108 | Permit approval >60 days; Plan review backlog >30 days; Digital permits <30% |
| SL-PAIN-109 | No StateRAMP program; Cloud onboarding >12 months; Ransomware in past 24 months |
| SL-PAIN-110 | No common operating picture; Radio interoperability <80%; Resource deployment >4 hours |
| SL-PAIN-111 | Jail occupancy >90%; Pre-trial population >60%; Avg pre-trial stay >21 days |
| SL-PAIN-112 | Duplicate requests >10%; First-contact resolution <50%; Response variance >300% |
| SL-PAIN-113 | Fleet age >10 years; Breakdown rate >15%; Preventive maintenance <60% |
| SL-PAIN-114 | Collection rate <92% (sales tax); Delinquency >10%; Refund fraud >$5M |
| SL-PAIN-115 | No unified incentive database; Clawback <$1M; GASB 77 incomplete |
| SL-PAIN-116 | Open data updates <monthly; No API for >50% datasets; Records backlog >90 days |
| SL-PAIN-117 | Address conflicts >5%; No shared parcel fabric; GIS updated >annually |
| SL-PAIN-118 | UI system >20 years; Benefits delivery >21 days; ID verification backlog >30 days |

### Step 5: Map to Personas and Value Drivers
For each confirmed pain, identify the affected personas and primary value driver category:
- **City/State CIO** (SL-PERS-101): Technology, cybersecurity, digital transformation, legacy modernization
- **County Administrator / City Manager** (SL-PERS-102): Cross-departmental operations, budget, jail costs, procurement
- **Public Works Director** (SL-PERS-103): Infrastructure, fleet, asset management, road conditions
- **State Tax Commissioner / Revenue Director** (SL-PERS-104): Collections, assessments, incentives, fraud
- **Emergency Manager** (SL-PERS-105): 911, interoperability, disaster response, common operating picture
- **Court Administrator** (SL-PERS-106): Case management, e-filing, backlog, pre-trial diversion

### Step 6: Quantify Value Hypothesis
Apply the relevant **value formula** from this subpack (SL-VF-101 through SL-VF-113). Key formula selection guidance:
- **Cost Savings**: Use SL-VF-101 (DMV digital shift), SL-VF-104 (court backlog), SL-VF-105 (road maintenance), SL-VF-111 (jail diversion), SL-VF-112 (311 consolidation), SL-VF-113 (fleet telematics)
- **Revenue Uplift**: Use SL-VF-103 (tax collection), SL-VF-108 (permit digitalization)
- **Risk Reduction**: Use SL-VF-102 (911 PSAP), SL-VF-109 (StateRAMP), SL-VF-110 (EOC interoperability)
- **Working Capital**: Use SL-VF-106 (procurement acceleration), SL-VF-107 (PHA HAP utilization)

### Step 7: Confidence Scoring
Score each finding using the evidence quality and source reliability:

| Confidence Level | Criteria |
|------------------|----------|
| **HIGH** | Direct measurement available (queue reports, call detail records, jail population data, court CMS, procurement system); Source is authoritative (NENA, AAMVA, NCSC, NASPO, HUD, BJS, FHWA) |
| **MEDIUM** | Proxy measurement or industry estimate; Source is survey-based (APCO, APWA, ICMA) or city auditor report; Requires prospect validation |
| **LOW** | No direct data; Inferred from adjacent signals (news coverage, litigation, bond rating language); Must be validated before customer-facing use |

**Overall subpack confidence**: MEDIUM — While authoritative sources exist for most signals, data quality varies significantly by jurisdiction size and transparency. Customer-facing output requires prospect-specific validation.

---

## 4. Inheritance Map

### Master Skill to Load First
**public-sector-master-v1** — This master provides the foundational public sector value framework including:
- Five value driver categories (Cost Savings, Risk Reduction, Mission Effectiveness, Working Capital, Revenue Uplift)
- Base persona archetypes and budget authority models
- Evidence source taxonomy and confidence scoring methodology
- NPV and cost-avoidance formula templates
- Governance rules for customer-facing approval

### What This Subpack Adds
| Component | What the Subpack Adds Beyond Master |
|-----------|-------------------------------------|
| **Pains** | 18 vertical-specialized pains (DMV crisis, 911 answer rate, tax assessment inaccuracy, court backlog, road response delays, procurement cycle time, housing voucher backlog, permitting delays, StateRAMP gap, emergency interoperability, jail overcrowding, 311 fragmentation, fleet decay, tax collection gap, incentive tracking, open data obsolescence, county-municipal data sharing, UI modernization debt) |
| **KPIs** | 23 jurisdiction-specific KPIs with benchmark ranges (DMV wait time, 911 answer rate, assessment-to-sale ratio, court disposition time, pothole response time, procurement cycle time, HAP utilization, permit cycle time, StateRAMP coverage, jail occupancy, 311 duplication rate, fleet age, tax collection rate, etc.) |
| **Personas** | 6 vertical personas: City/State CIO, County Administrator/Manager, Public Works Director, State Tax Commissioner, Emergency Manager, Court Administrator |
| **Formulas** | 13 quantified value formulas with example calculations for state/local contexts |
| **Signal Rules** | 18 signal interpretation rules with required evidence checklists |
| **Benchmarks** | 18 benchmarks from AAMVA, NENA, IAAO, NCSC, NASPO, APWA, FHWA, HUD, Vera Institute, BJS |
| **Buying Triggers** | 14 trigger events specific to state/local political and funding cycles (new administration, ransomware, federal grants, audit findings, bond rating reviews, litigation, staff retirement, legislative mandates, referendums, federal compliance actions, infrastructure failures, vendor EOL, shared services initiatives, cyber insurance renewals) |

### When to Use Master vs. Subpack
| Scenario | Skill to Use |
|----------|-------------|
| General public sector account (federal, state, local, education, healthcare) with no segment identified | **Master only** |
| State or local government account with known segment (DMV, courts, public safety, etc.) | **Master + This Subpack** |
| Need to compare state/local prospects to federal benchmarks | **Master** for comparison framework, **Subpack** for state/local specifics |
| Municipal or county account with cross-departmental scope | **Master + This Subpack** (Subpack covers all municipal/county functions) |
| Account is a state university or K-12 district | **Master + Education Subpack** (not this subpack) |

---

## 5. Structured Output Template

The following JSON structure is the expected output format for Signals Analysis enrichment when this subpack is applied:

```json
{
  "skill_loaded": "state-local-v1",
  "parent_master": "public-sector-master-v1",
  "analysis_timestamp": "2026-01-15T12:00:00Z",
  "account_segment": "County Government Administration",
  "signals_detected": [
    {
      "signal_id": "SL-SR-101",
      "signal_name": "DMV Wait Time Crisis Signal",
      "confidence": "HIGH",
      "evidence_quality": "direct_measurement",
      "triggered_pains": ["SL-PAIN-101"],
      "affected_personas": ["SL-PERS-101", "SL-PERS-102"],
      "linked_kpis": ["SL-KPI-101", "SL-KPI-102"],
      "value_driver_category": "Cost Savings + Mission Effectiveness",
      "symptoms_observed": [
        "Wait time 78 minutes (threshold: >60)",
        "Appointment backlog 5.2 weeks (threshold: >4)"
      ],
      "data_sources": ["AAMVA State DMV Metrics", "State customer satisfaction report"],
      "value_formula_applied": "SL-VF-101",
      "estimated_annual_value": "$12.5M",
      "value_confidence": "MEDIUM",
      "buying_triggers_aligned": ["SL-BT-101", "SL-BT-104"]
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "SL-PERS-101",
      "persona_name": "City / State CIO",
      "relevance_score": 0.85,
      "primary_pains": ["SL-PAIN-101", "SL-PAIN-109"],
      "engagement_recommendation": "Lead with digital transformation ROI and StateRAMP authorization efficiency"
    }
  ],
  "priority_pains_ranked": [
    {
      "pain_id": "SL-PAIN-101",
      "pain_name": "DMV Wait Time and Throughput Crisis",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "business_impact": "citizen satisfaction + staff burnout + revenue velocity"
    }
  ],
  "governance_flags": {
    "customer_facing_approved": false,
    "requires_validation": true,
    "validation_items": ["Confirm wait time with prospect's DMV director", "Verify digital transaction volume"],
    "overall_confidence": "MEDIUM"
  }
}
```

---

## 6. Governance Metadata

| Field | Value |
|-------|-------|
| **Confidence Level** | MEDIUM — Authoritative sources exist for most signals, but data quality varies by jurisdiction size and transparency posture |
| **Source Coverage** | Mixed: NASCIO, NASPO, AAMVA, NENA, IAAO, NCSC, APWA, FHWA, HUD, MS-ISAC, Vera Institute, BJS, NACo, ICMA, GFOA, State auditor reports, Municipal surveys |
| **Customer-Facing Approval Status** | **No** — Requires validation with live prospects before external use |
| **Review Owner** | State-Local Vertical Subpack Architect — Public Sector Swarm |
| **Last Updated** | 2026-04-25 |
| **Next Review Cycle** | Quarterly or upon major federal grant program change |
| **Override Notes** | State IT O&M benchmark updated to NASCIO 2024; Time-to-hire narrowed to 75-135 days per 2024 ICMA survey |

---

## 7. Quick Reference

### Top 5 Pains

| # | Pain ID | Pain Name | Prevalence | Primary Value Driver |
|---|---------|-----------|------------|---------------------|
| 1 | SL-PAIN-101 | DMV Wait Time and Throughput Crisis | HIGH | Cost Savings + Mission Effectiveness |
| 2 | SL-PAIN-102 | 911 Call Answer Rate Below NENA Standard | HIGH | Risk Reduction + Mission Effectiveness |
| 3 | SL-PAIN-103 | Property Tax Assessment Inaccuracy and Appeal Surge | HIGH | Revenue Uplift + Cost Savings |
| 4 | SL-PAIN-104 | Court Case Backlog and Digital Records Fragmentation | HIGH | Cost Savings + Risk Reduction |
| 5 | SL-PAIN-108 | Building Permit and Code Enforcement Delays | HIGH | Revenue Uplift + Working Capital |

### Top 5 KPIs

| # | KPI ID | KPI Name | Benchmark | Unit |
|---|--------|----------|-----------|------|
| 1 | SL-KPI-101 | DMV Average Wait Time | <30 min acceptable, >60 min crisis | Minutes |
| 2 | SL-KPI-104 | 911 Call Answer Rate (15 seconds) | >90% NENA standard | Percentage |
| 3 | SL-KPI-107 | Property Tax Assessment-to-Sale Ratio | 0.90-1.10 (IAAO standard) | Ratio |
| 4 | SL-KPI-110 | Court Case Disposition Time | <180 days (criminal) | Days |
| 5 | SL-KPI-122 | Building Permit Cycle Time | <14 days best practice | Days |

### Top 3 Personas

| # | Persona ID | Persona | Decision Authority | Primary Pains |
|---|------------|---------|-------------------|---------------|
| 1 | SL-PERS-102 | County Administrator / County Manager | VERY HIGH (cross-departmental) | SL-PAIN-103, 104, 105, 111, 112, 113, 117 |
| 2 | SL-PERS-101 | City / State CIO | HIGH (technology, cybersecurity) | SL-PAIN-101, 106, 109, 112, 116 |
| 3 | SL-PERS-104 | State Tax Commissioner / Revenue Director | HIGH (tax systems, collections) | SL-PAIN-103, 114, 115, 118 |

### Key Value Formulas

| Formula ID | Name | Formula Summary | Typical Annual Value Range |
|------------|------|-----------------|---------------------------|
| SL-VF-101 | DMV Digital Channel Shift Value | `V = Transactions * Digital%_Delta * (WalkIn_Cost - Online_Cost) + Staff_Avoidance` | $5M–$75M |
| SL-VF-102 | 911 PSAP Staffing Optimization Value | `V = Abandonment_Delta * Call_Volume * Cost_Per_Call + Overtime_Reduction + Liability_Avoidance` | $2M–$10M |
| SL-VF-103 | Property Tax Collection Improvement | `V = Assessed_Value * Tax_Rate * Collection%_Delta + Appeal_Reduction_Value` | $2M–$20M |
| SL-VF-105 | Road Reactive-to-Preventive Maintenance Value | `V = (Reactive_Cost - Preventive_Cost) * Lane_Miles + Liability_Avoidance + Delay_Avoidance` | $10M–$100M |
| SL-VF-111 | Jail Per-Diem Cost Reduction via Diversion | `V = PreTrial_Delta * Daily_Cost * 365 - EM_Cost` | $1M–$10M |

---

## Appendix: Full ID Reference Table

| Category | ID Range | Count |
|----------|----------|-------|
| Pains | SL-PAIN-101 to SL-PAIN-118 | 18 |
| KPIs | SL-KPI-101 to SL-KPI-123 | 23 |
| Value Drivers | SL-VD-101 to SL-VD-106 | 6 |
| Formulas | SL-VF-101 to SL-VF-113 | 13 |
| Benchmarks | SL-BENCH-101 to SL-BENCH-118 | 18 |
| Signal Rules | SL-SR-101 to SL-SR-118 | 18 |
| Personas | SL-PERS-101 to SL-PERS-106 | 6 |
| Discovery Questions | SL-DQ-101 to SL-DQ-118 | 18 |
| Buying Triggers | SL-BT-101 to SL-BT-114 | 14 |
| Objection Patterns | SL-OBJ-101 to SL-OBJ-109 | 9 |

---

*This SKILL.md is auto-generated from value-pack.json and value-pack.md. For full detail, reference the parent pack files in the same directory. Do not modify value-pack.json or signals-examples.ts.*
