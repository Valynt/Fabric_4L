# Life Sciences Vertical Subpack (S3.3) - SKILL.md

## Skill Identity Block

| Field | Value |
|-------|-------|
| `skill_name` | Life Sciences Vertical Subpack (S3.3) |
| `description` | Specialized value-selling intelligence for pharma, biotech, medical devices, diagnostics, CROs, CDMOs, genomics, cell/gene therapy, and digital therapeutics. Covers the full R&D-to-commercialization lifecycle with 18 vertical pains, 22 KPIs, 12 value formulas, 18 signal rules, 6 specialized personas, 14 buying triggers, and 9 objection reframe strategies. |
| `version` | 1.0.0 |
| `domain` | Life Sciences / Healthcare |
| `pack_type` | subpack |
| `parent_master` | healthcare-master-v1 |
| `last_updated` | 2026-04-25 |

---

## Triggers

Auto-load this skill when queries match any of the following patterns (8-12 required):

1. **"clinical trial enrollment delay"** - Phase 2/3 enrollment behind target, screen failure >30%, site activation bottlenecks
2. **"FDA CRL CMC deficiency"** - Complete Response Letter with Chemistry, Manufacturing, and Controls gaps; regulatory submission rejection
3. **"pharmacovigilance case processing"** - ICSR backlog, SAE reporting timeliness <99%, PV inspection findings, EMA PRAC referral
4. **"cell gene therapy manufacturing"** - CGT scale-up failure, vein-to-vein time >45 days, batch success rate <75%, COGS >$80K/dose
5. **"digital therapeutics FDA pathway"** - DTx de novo/510(k) clearance without CPT/HCPCS code, payer coverage gaps, reimbursement denial
6. **"biosimilar competitive erosion"** - Loss of exclusivity within 36 months for >$500M product, patent cliff defense strategy
7. **"eTMF inspection readiness gap"** - eTMF completeness <92%, FDA Form 483 on TMF, paper-to-electronic migration incomplete
8. **"manufacturing deviation batch failure"** - Deviation rate >3%, OOS >1.5%, repeat deviation >20%, batch release >21 days
9. **"companion diagnostic co-development"** - CDx approval lag >6 months behind drug BLA, assay validation failure, biomarker strategy changes
10. **"real-world evidence generation latency"** - RWE publications <2/year per asset, data access agreements >9 months, HTA restriction >30%
11. **"CDMO quality transfer failure"** - Tech transfer >12 months, first-pass success <60%, batch rejection >3%, no real-time visibility
12. **"GxP data integrity ALCOA+ gap"** - FDA Warning Letter with data integrity citation, shared logins in GxP systems, audit trail review gaps

---

## Reasoning Flow

### Step 1: Master Skill Loading (REQUIRED)

Before applying this subpack, ensure `healthcare-master-v1` is loaded. The master provides:
- Base value driver framework (V001-V054) with four financially meaningful outcome categories
- Base persona archetypes (PER001-PER014): CFO, COO, CMO, CIO, CISO, VP Quality, Head of Clinical Development, etc.
- Evidence source taxonomy (ES001-ES015): 10-K, earnings calls, FDA letters, job postings, ClinicalTrials.gov
- Formula templates (F001-F025) for clinical trial acceleration, breach cost avoidance, etc.
- Signal source taxonomy (S001-S030) and benchmark methodology (B001-B035)
- Governance framework with confidence flags and validation requirements

### Step 2: Prospect Classification

Determine the Life Sciences sub-segment:

| Sub-Segment | Revenue Range | Key Differentiator |
|-------------|---------------|-------------------|
| Branded Small Molecule Pharma | $1B-$90B | NCE pipeline, LOE risk, CMC scale |
| Generic / Biosimilar | $100M-$20B | Post-LOE manufacturing, price erosion |
| Biotechnology (mAbs, CGT) | $50M-$45B | Large molecule complexity, CGT novelty |
| Medical Devices (Class I/II/III) | $10M-$30B | QSR/ISO compliance, PMA/510(k) pathways |
| IVD / Companion Diagnostics | $20M-$10B | CDx co-development, analytical validation |
| CROs | $50M-$15B | Trial execution capacity, data portability |
| CDMOs | $100M-$25B | Tech transfer success, batch quality |
| Genomics / NGS | $10M-$5B | Turnaround time, VUS rate, CLIA/CAP |
| Cell & Gene Therapy Developers | $5M-$2B | Autologous scale, vein-to-vein time |
| Clinical Laboratory Services | $10M-$8B | Accreditation, quality, throughput |
| Digital Therapeutics / SaMD | $1M-$500M | FDA clearance, reimbursement, HCP awareness |

### Step 3: Signal Identification

Gather signals from prioritized evidence sources:

| Priority | Source | Signal | Confidence |
|----------|--------|--------|------------|
| P0 | FDA Warning Letters / CRL Database | GMP/QSR citation, CMC deficiency | 0.94 |
| P0 | ClinicalTrials.gov | Suspended/terminated Phase 2/3 trial | 0.92 |
| P0 | Manufacturing Site Import Alert | FDA IA or OAI status | 0.94 |
| P1 | Orange Book / Purple Book | Biosimilar approval for reference product | 0.92 |
| P1 | EMA PRAC Signal Referral | Safety review initiation | 0.88 |
| P1 | 10-K / Investor Decks | R&D restructuring, site closure | 0.84 |
| P2 | Job Postings / RFPs | eTMF migration lead, PV platform RFP | 0.78 |
| P2 | Conference Disclosures | ICH E6(R3) readiness gap | 0.70 |

Apply signal confirmation rules: each primary signal requires at least one corroborating signal before HIGH confidence pain assignment.

### Step 4: Pain-to-KPI Mapping

For each identified signal, map to vertical pains and KPIs:

| Signal | Pain | KPIs | Formula |
|--------|------|------|---------|
| Enrollment <75% at 50% time | LS-P001 | LS-K001, LS-K002, LS-K003 | LS-F001 |
| CRL with CMC deficiency | LS-P002 | LS-K005, LS-K008 | LS-F003 |
| PV backlog + inspection | LS-P003 | LS-K006, LS-K007, LS-K020 | LS-F002 |
| Deviation rate >3% | LS-P005 | LS-K009, LS-K010 | LS-F004 |
| eTMF completeness <92% | LS-P006 | LS-K011, LS-K012 | LS-F005 |
| LOE <36 months for top product | LS-P008 | LS-K015, LS-K016, LS-K021 | LS-F006 |
| CGT V2V >45 days | LS-P011 | LS-K018 | LS-F009 |
| CDMO first-pass <60% | LS-P016 | LS-K022, LS-K009 | LS-F007 |

### Step 5: Persona Targeting

Use the vertical personas for technical validation and user-level influence:

| Persona | Role | Influence | Primary Pains |
|---------|------|-----------|---------------|
| Clinical Trial Manager | Site ops, enrollment, eTMF | User | LS-P001, LS-P006 |
| Regulatory Affairs Director | Submissions, CMC integration | Technical | LS-P002, LS-P004, LS-P010 |
| CMC Director | Manufacturing, COGS, tech transfer | Technical | LS-P005, LS-P011, LS-P016 |
| PV / Drug Safety Officer | Case processing, compliance | Technical | LS-P003 |
| Medical Affairs Lead | KOL engagement, RWE, access | Technical | LS-P012, LS-P014, LS-P017 |
| Biostatistician / Data Science Lead | CDISC, analytics, AI/ML | Technical | LS-P018, LS-P012 |

Combine with master personas for economic authority: CFO (all cost/risk quantifications), Chief Strategy Officer (portfolio/LOE), CMO (clinical pipeline), COO (manufacturing).

### Step 6: Value Hypothesis Formulation

Map each confirmed pain to one of four financially meaningful outcomes:

| Category | When to Apply | Example Formula |
|----------|---------------|----------------|
| **Revenue Uplift** | Timeline acceleration, label expansion, LOE defense, CDx alignment, DTx reimbursement | LS-F001, LS-F006, LS-F008, LS-F010, LS-F012 |
| **Cost Savings** | Deviation reduction, PV processing efficiency, site activation optimization, CGT COGS reduction | LS-F002, LS-F004, LS-F009, LS-F011 |
| **Risk Reduction** | CRL avoidance, Warning Letter prevention, inspection readiness, data integrity, EMA referral | LS-F003, LS-F005, LS-F007 |
| **Working Capital / Cash Flow** | Batch release acceleration, CDMO on-time delivery, API dual-sourcing | LS-F004 (release), LS-F007 (oversight) |

### Step 7: Confidence Scoring

Assign confidence per pain using the subpack governance rules:

| Level | Criteria | Actions |
|-------|----------|---------|
| **HIGH** | Multiple corroborating sources, quantified internal data, direct regulatory/financial reporting | Proceed with customer-facing quantification |
| **MEDIUM** | Industry survey data, partial quantification, single authoritative source | Use with directional framing; validate with customer before proposal |
| **LOW** | Estimates, emerging trends, limited precedent (DTx reimbursement, ICH E6(R3) readiness) | Flag as hypothesis; require discovery validation |

**Mandatory validation before customer use:**
1. Verify current FDA/EMA inspection metrics against latest agency publications
2. Confirm organization-specific clinical trial cost data (varies 3-5x by therapeutic area)
3. Validate manufacturing deviation and batch COGS with customer actuals
4. Update biosimilar erosion benchmarks quarterly
5. Review CGT manufacturing benchmarks against latest ARM data
6. Confirm ICH E6(R3) finalization status before referencing timelines
7. Validate PV case volumes and processing costs with customer
8. Review DTx reimbursement landscape quarterly

---

## Inheritance Map

### Load Order
1. **Primary:** `healthcare-master-v1` - Must be loaded first for base taxonomy, personas, evidence types, formula templates, and governance
2. **Secondary:** `life-sciences-v1` (this skill) - Loaded when prospect operates in any Life Sciences sub-segment

### What This Subpack Adds Beyond the Master

| Component | Master | Subpack Addition |
|-----------|--------|------------------|
| Pains | General healthcare (RCM, care delivery, payer) | 18 R&D-to-commercialization pains (enrollment, CMC, PV, manufacturing, CDx, CGT, DTx) |
| KPIs | Master K043-K052 (clinical ops, quality) | 22 vertical KPIs with batch/site-level granularity, PV-specific, CGT-specific, RWE-specific |
| Signal Rules | S001-S030 (general FDA, earnings, job postings) | 18 rules for ClinicalTrials.gov, CRL, Warning Letters, Orange Book, EMA PRAC, CDMO disputes |
| Personas | PER001-PER014 (general healthcare C-suite) | 6 vertical personas (Trial Manager, Regulatory Affairs, CMC, PV, Medical Affairs, Biostatistician) |
| Formulas | F001-F025 (general denial, LOS, readmission) | 12 formulas for trial NPV, PV efficiency, CRL risk, deviation cost, CGT scale-up, RWE speed-to-label |
| Benchmarks | B001-B035 (general industry) | 18 life-sciences-specific benchmarks from Tufts, IQVIA, ISPE, ARM |
| Regulatory | General healthcare compliance | 10 vertical regulations (21 CFR 11, ICH E6(R3), EU MDR/IVDR, DSCSA, GVP, SaMD) |
| Tech Systems | General EHR, ERP, RCM | 12 systems (CTMS, eTMF, PV Safety, RIM, MES, ELN, Signal Detection) |
| Discovery Questions | General healthcare discovery | 18 questions mapped to enrollment, CMC, PV, manufacturing, CDx, CGT, DTx, genomics |
| Objections | General healthcare objections | 9 objections specific to GxP validation, Veeva/Oracle incumbency, CRO dependency, AI in GxP |
| Buying Triggers | General healthcare triggers | 14 triggers (CRL, Warning Letter, enrollment crisis, LOE, CGT capacity, CDMO failure, DTx clearance) |

### When to Use Master vs. Subpack

| Scenario | Use |
|----------|-----|
| Prospect is a hospital system, payer, or health system | Master only |
| Prospect is a CRO serving pharma but with IT/ops pain | Master + Subpack (CRO overlaps) |
| Prospect is pharma, biotech, device, CDMO, genomics lab, DTx | Master + this Subpack |
| Value conversation is about clinical trial enrollment | Subpack (LS-P001, LS-F001) |
| Value conversation is about hospital readmissions | Master only (not applicable) |
| Conversation spans clinical + commercial + manufacturing | Master + Subpack full stack |

---

## Structured Output Template

### Signals Analysis Enrichment (JSON)

```json
{
  "enrichment_id": "ls-signals-{timestamp}",
  "master_skill": "healthcare-master-v1",
  "subpack_skill": "life-sciences-v1",
  "prospect": {
    "name": "string",
    "sub_segment": "Branded Pharma | Generic/Biosimilar | Biotech | Medical Device | IVD/CDx | CRO | CDMO | Genomics | CGT | Lab Services | DTx/SaMD",
    "revenue_range_usd": "string"
  },
  "signals_detected": [
    {
      "signal_id": "LS-S001",
      "signal_name": "string",
      "raw_evidence": "string",
      "confidence_score": 0.0,
      "corroborated": true,
      "linked_pains": ["LS-P001"],
      "linked_kpis": ["LS-K001"],
      "linked_personas": ["Clinical Trial Manager", "Head of Clinical Development"]
    }
  ],
  "pains_confirmed": [
    {
      "pain_id": "LS-P001",
      "pain_name": "string",
      "confidence": "HIGH | MEDIUM | LOW",
      "prevalence": "HIGH | MEDIUM | LOW",
      "symptoms_present": ["string"],
      "affected_personas": ["string"],
      "linked_kpis": ["LS-K001"],
      "linked_value_drivers": ["V029"],
      "discovery_questions": ["LS-DQ001"]
    }
  ],
  "kpis_assessed": [
    {
      "kpi_id": "LS-K001",
      "kpi_name": "string",
      "prospect_value": 0.0,
      "benchmark_value": 0.0,
      "benchmark_range": "string",
      "gap_direction": "above | below | at",
      "gap_severity": "minor | moderate | critical"
    }
  ],
  "value_hypotheses": [
    {
      "hypothesis_id": "VH-001",
      "value_driver_category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital Improvement",
      "formula_id": "LS-F001",
      "formula_name": "string",
      "inputs": {},
      "quantified_value_usd": 0.0,
      "confidence": "HIGH | MEDIUM | LOW",
      "target_personas": ["string"],
      "buying_triggers": ["LS-BT001"],
      "objections_foreseen": ["LS-OBJ001"]
    }
  ],
  "buying_triggers_active": [
    {
      "trigger_id": "LS-BT001",
      "trigger_name": "string",
      "urgency": "CRITICAL | HIGH | MEDIUM",
      "timing": "string",
      "procurement_implications": "string"
    }
  ],
  "governance": {
    "overall_confidence": "HIGH | MEDIUM | LOW",
    "source_coverage": "mixed | strong | limited",
    "customer_facing_approved": false,
    "validation_required": ["string"],
    "last_updated": "2026-04-25",
    "review_owner": "life-sciences-subpack-architect"
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | High (subpack-wide); individual pains range HIGH to MEDIUM |
| **Source Coverage** | Mixed (FDA/EMA public data, industry surveys [Tufts, IQVIA, ISPE], proprietary benchmarks [Citeline, Evaluate Pharma], academic research) |
| **Customer-Facing Approval Status** | **No** - Internal intelligence asset; requires review before external use |
| **Review Owner** | life-sciences-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-healthcare-s3.3 |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-healthcare-m3 |

### Validation Requirements Before Customer Use

1. Verify current FDA/EMA inspection metrics and guidance against latest agency publications
2. Confirm organization-specific clinical trial cost data before using in proposals (varies 3-5x by therapeutic area)
3. Validate manufacturing deviation and batch COGS data with customer actuals before quantifying value
4. Update biosimilar erosion benchmarks quarterly (market dynamics shift rapidly post-LOE)
5. Review CGT manufacturing benchmarks against latest Alliance for Regenerative Medicine data
6. Confirm state of ICH E6(R3) finalization before referencing implementation timelines
7. Validate PV case volumes and processing costs with customer before ROI claims
8. Review DTx reimbursement landscape quarterly (payer policy evolving rapidly)

---

## Quick Reference

### Top 5 Pains

| ID | Pain | Prevalence | Confidence | Primary Persona |
|----|------|------------|------------|----------------|
| LS-P001 | Clinical Trial Enrollment Delay and Screen Failure | HIGH | HIGH | Clinical Trial Manager |
| LS-P003 | Pharmacovigilance Case Processing Backlog | HIGH | HIGH | PV / Drug Safety Officer |
| LS-P004 | Regulatory Submission Timeline Overrun (NDA/BLA/510k) | HIGH | HIGH | Regulatory Affairs Director |
| LS-P007 | Supply Chain Single-Source API / Raw Material Dependency | HIGH | HIGH | Head of Supply Chain |
| LS-P008 | Biosimilar / Generic Competitive Erosion for Blockbusters | HIGH | HIGH | Chief Strategy Officer |

### Top 5 KPIs

| ID | KPI | Benchmark | Typical Range | Unit |
|----|-----|-----------|---------------|------|
| LS-K001 | Clinical Trial Enrollment Rate vs. Plan | >85% at 50% elapsed time | 60-110 | % |
| LS-K005 | Regulatory Submission Cycle Time | 0-30 days on-time; >90 at risk | 0-180 | days |
| LS-K009 | Manufacturing Deviation Rate | <2% best practice; <3% acceptable | 1-8 | % |
| LS-K006 | PV ICSR Processing Time | <14 days expedited; <10 best | 3-20 | days |
| LS-K018 | Cell/Gene Therapy Manufacturing Success Rate | >85% best; >75% acceptable | 60-90 | % |

### Top 3 Personas

| ID | Persona | Role | Influence | Primary Pains |
|----|---------|------|-----------|---------------|
| LS-PER001 | Clinical Trial Manager / Site Operations Lead | Enrollment, eTMF, site ops | User | LS-P001, LS-P006 |
| LS-PER002 | Regulatory Affairs Director / VP | Submissions, CMC integration | Technical | LS-P002, LS-P004, LS-P010 |
| LS-PER003 | CMC Director / Manufacturing Sciences Lead | Quality, COGS, tech transfer | Technical | LS-P005, LS-P011, LS-P016 |

### Key Value Formulas

| ID | Formula | Output | When to Use |
|----|---------|--------|-------------|
| LS-F001 | Clinical Trial Acceleration NPV | USD | Enrollment gap with known peak revenue and patent life |
| LS-F002 | PV Case Processing Efficiency | USD annually | ICSR volume >5,000/year, processing >10 days, inspection risk |
| LS-F003 | Regulatory Submission Timeline Risk | USD | Phase 3 asset with known peak sales, submission delay >1 month |
| LS-F004 | Manufacturing Deviation Cost | USD annually | Deviation rate tracked in QMS, batch-level COGS known |
| LS-F006 | Patent Cliff Revenue Defense | USD | LOE within 24 months, erosion history exists for molecule class |

### Critical Buying Triggers (Urgency = CRITICAL or HIGH)

| ID | Trigger | Urgency | Timing | Linked Pains |
|----|---------|---------|--------|--------------|
| LS-BT001 | FDA CRL Received | CRITICAL | Immediate; 15-30 day response | LS-P002, LS-P004, LS-P005 |
| LS-BT002 | FDA Warning Letter or Import Alert | CRITICAL | Immediate; 15 working day response | LS-P005, LS-P009, LS-P015, LS-P016 |
| LS-BT003 | Clinical Trial Enrollment Crisis (>20% Behind) | HIGH | 30-60 days vendor selection | LS-P001 |
| LS-BT004 | PV Inspection Finding or EMA PRAC Referral | HIGH | 30-60 days CAPA; tech 45-90 days | LS-P003 |
| LS-BT005 | LOE within 24 Months for Top Product | HIGH | 6-18 months strategic response | LS-P008, LS-P013 |
| LS-BT009 | CGT Commercial Manufacturing Capacity Constraint | HIGH | Immediate patient access risk | LS-P011 |
| LS-BT011 | CDMO Quality Transfer Failure or Contract Dispute | HIGH | Immediate supply risk | LS-P016, LS-P005, LS-P007 |

### Essential Regulatory Deadlines

| ID | Regulation | Deadline | Penalty |
|----|-----------|----------|---------|
| LS-REG004 | ICH E6(R3) GCP | Finalization 2025-2026; implementation 2026-2028 | Increased QbD inspection focus |
| LS-REG005 | EU MDR/IVDR | Transition to 2026-2028 | Market withdrawal; EUR 500K-5M |
| LS-REG008 | FDA DSCSA | Enforcement began Nov 2023 | Criminal/civil penalties; $10K-$1M+ |
| LS-REG010 | FDA SaMD / DTx Guidance | Ongoing; Pre-Cert pilot evolving | Marketing hold; de novo rejection |

---

*End of Life Sciences Vertical Subpack SKILL.md*
