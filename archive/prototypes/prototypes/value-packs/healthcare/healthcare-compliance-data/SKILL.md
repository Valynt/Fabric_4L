# SKILL.md — Healthcare Compliance and Data Subpack (S3.5)

---

## Skill Identity Block

| Field | Value |
|-------|-------|
| **skill_name** | Healthcare Compliance and Data ValuePack (S3.5) |
| **description** | Vertical-specialized intelligence for healthcare compliance, data privacy, interoperability, and security. Covers HIPAA breach response, HITRUST certification, FHIR API governance, patient identity management, consent platforms, audit integrity, FWA detection, medical coding compliance, de-identification, state privacy law fragmentation, cloud security, and AI/ML model governance. |
| **version** | 1.0.0 |
| **domain** | Healthcare |
| **pack_type** | subpack |
| **parent_master** | healthcare-master-v1 |

---

## Triggers

Auto-load this skill when the user query contains any of the following patterns:

1. "HIPAA breach notification" — breach response, OCR compliance, incident backlog
2. "FHIR API interoperability" — patient access APIs, ONC Cures Act, information blocking
3. "HITRUST certification gap" — CSF r2/i1 readiness, control gaps, attestation delays
4. "patient identity matching" — MPI/EMPI duplicates, overlays, registration errors
5. "healthcare data monetization" — de-identification, research data sharing, AI training datasets
6. "healthcare compliance and data" — general compliance intelligence, audit readiness
7. "consent management fragmentation" — revoke propagation, accounting of disclosures
8. "fraud waste abuse detection" — FWA scheme detection, SIU optimization, prepay savings
9. "medical coding compliance" — ICD-10/CPT/DRG accuracy, RAC/MAC defense
10. "healthcare ransomware recovery" — RTO, backup restoration, business continuity
11. "state privacy law fragmentation" — CCPA/CPRA/VCDPA/MHMDA multi-state compliance
12. "healthcare SaaS SOC 2 audit" — ISO 27001, customer certification requirements

---

## Reasoning Flow

### Step 1: Load Parent Master First
Before applying this subpack, ensure the **healthcare-master-v1** skill is loaded. The master provides:
- Base segment taxonomy (5 segments, 85 sub-segments)
- 54 base value drivers, 14 base personas, 25 base formulas
- Financial outcome mapping framework (Revenue Uplift, Cost Savings, Risk Reduction, Working Capital)
- Governance methodology (confidence flags, validation rules)

### Step 2: Identify Relevant Signals
Scan for any of the 20 vertical signal rules (CS001–CS020). Priority signals with highest confidence:
- **CS009** — Ransomware Incident Disclosure (0.96 confidence)
- **CS001** — HHS OCR Breach Portal Listing (0.95)
- **CS008** — FWA Whistleblower/Qui Tam Filing (0.94)
- **CS004** — ONC Information Blocking Complaint Filed (0.92)
- **CS007** — Third-Party Breach Notification (0.91)

Signal triage logic:
- If **breach or ransomware** signal present → prioritize CP001, CP010, CP016
- If **HITRUST expiration or failure** → prioritize CP003
- If **FHIR downtime or complaint** → prioritize CP002, CP011
- If **MPI job surge or billing errors** → prioritize CP004
- If **FWA whistleblower or coding job surge** → prioritize CP007, CP008

### Step 3: Match Signals to Pains and KPIs
For each confirmed signal, map to the corresponding pain(s) and linked KPIs using the subpack's cross-reference tables. Example mappings:

| Signal | Pain(s) | Primary KPIs |
|--------|---------|--------------|
| OCR Breach Portal (CS001) | CP001, CP010 | CK001, CK002, CK003 |
| HITRUST Expiration (CS002) | CP003 | CK007, CK008, CK009 |
| FHIR Downtime (CS003) | CP002, CP011 | CK004, CK005, CK006 |
| MPI Duplicate Surge (CS005) | CP004 | CK010, CK011, CK012 |
| Consent Platform RFP (CS006) | CP005, CP012 | CK013, CK014, CK015 |

### Step 4: Interpret Using Value Drivers
Apply the 39 vertical value drivers (CV001–CV039) to translate signal patterns into financially meaningful outcomes. Each driver specifies:
- **Value Driver Category**: Revenue Uplift, Cost Savings, Risk Reduction, or Working Capital
- **Affected Personas**: Which decision-makers to engage
- **Required Evidence**: What documentation to request during discovery
- **Confidence Level**: HIGH/MEDIUM/LOW based on source corroboration

### Step 5: Map to Personas
Engage the 6 domain-specific personas added by this subpack:
1. **Chief Privacy Officer (CPO)** — privacy strategy, state law navigation, de-identification
2. **HITRUST Assessor / Security Framework Lead** — certification readiness, gap remediation
3. **FHIR Integration Engineer / Interoperability Architect** — API governance, HL7-to-FHIR migration
4. **Compliance Auditor (Internal/External)** — coding audits, DRG validation, RAC/MAC defense
5. **Patient Identity Architect / EMPI Lead** — MPI strategy, matching algorithms, registration
6. **Security Operations Lead (Healthcare SOC)** — 24x7 coverage, PHI monitoring, ransomware response

Plus master personas: CISO, CIO, CFO, Chief Compliance Officer, General Counsel, CMIO, COO.

### Step 6: Quantify with Value Formulas
Apply the 15 vertical formulas (CF001–CF015) to build financially defensible value hypotheses:
- **CF001** — HIPAA Breach Cost Avoidance
- **CF002** — HITRUST Certification Contract Protection
- **CF003** — FHIR API Compliance Penalty Avoidance
- **CF004** — MPI Duplicate Reduction Value
- **CF005** — Consent Management Automation ROI
- **CF006** — Audit Trail Integrity Legal Discovery Savings
- **CF007** — FWA Detection Investment Return
- **CF008** — Coding Compliance Audit Defense Value
- **CF009** — De-identification Throughput Revenue Unlock
- **CF010** — Third-Party Risk Management Cost Avoidance
- **CF011** — State Privacy Law Compliance Consolidation
- **CF012** — Ransomware Recovery Time Reduction Value
- **CF013** — SOC Coverage Extension Value
- **CF014** — HL7-to-FHIR Modernization Savings
- **CF015** — AI Model Governance Risk Reduction

### Step 7: Confidence Scoring
Score each finding using the subpack's confidence framework:
- **HIGH (0.85–1.0)**: Multiple corroborating sources, quantified data, direct regulatory/financial reporting. Use for customer-facing proposals.
- **MEDIUM (0.70–0.84)**: Industry survey data, partial quantification, or single-source but authoritative. Use for internal prioritization.
- **LOW (0.50–0.69)**: Estimates, directional indicators, or emerging trends with limited data. Flag for further validation.

Before customer-facing use, validate:
1. Current HIPAA/OCR benchmarks against latest HHS publications
2. HITRUST CSF version (r2 vs. i1) and customer-specific requirements
3. Organization-specific breach cost estimates
4. FHIR benchmarks quarterly (ONC, CMS rulemaking)
5. Signal rules false positive rate against historical data
6. State-specific regulatory deadlines (CCPA, CPRA, VCDPA, MHMDA)
7. Cloud security posture against customer architecture

---

## Inheritance Map

### Parent Master
| Attribute | Reference |
|-----------|-----------|
| **Master Skill** | `healthcare-master-v1` |
| **Load Order** | Master FIRST, then this subpack |
| **Inheritance Type** | Extension (adds vertical specialization) |

### What This Subpack Adds
| Component | Master Base | Subpack Addition |
|-----------|-------------|------------------|
| Pains | 0 (master has general) | 20 vertical pains (CP001–CP020) |
| KPIs | 0 | 25 vertical KPIs (CK001–CK025) |
| Value Drivers | 54 base | +39 vertical = 93 total |
| Formulas | 25 base | +15 vertical = 40 total |
| Benchmarks | 35 base | +20 vertical = 55 total |
| Signal Rules | 30 base | +20 vertical = 50 total |
| Personas | 14 base | +6 vertical = 20 total |
| Evidence Sources | 15 base | +12 vertical = 27 total |
| Buying Triggers | 0 | 15 vertical (CBT001–CBT015) |
| Regulatory Factors | 12 base | +12 vertical = 24 total |
| Technology Systems | 0 | 15 vertical (CT001–CT015) |
| Discovery Questions | Base framework | +20 vertical (CDQ001–CDQ020) |
| Objection Patterns | Base framework | +10 vertical (COBJ001–COBJ010) |
| Competitor Factors | Base framework | +5 vertical (CCF001–CCF005) |

### When to Use Master vs. Subpack
| Scenario | Use |
|----------|-----|
| General healthcare market context, no specific compliance signal | Master only |
| HIPAA, HITRUST, FHIR, patient identity, consent, audit, FWA, coding, or data privacy signals detected | **Master + This Subpack** |
| SaaS vendor with SOC 2/ISO 27001 healthcare requirements | **Master + This Subpack** |
| Cloud EHR migration or AI/ML governance | **Master + This Subpack** |
| State privacy law multi-state operations | **Master + This Subpack** |

---

## Structured Output Template

### Signals Analysis Enrichment (JSON)

```json
{
  "skill_loaded": "healthcare-compliance-v1",
  "parent_master": "healthcare-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "prospect_segment": "Care Delivery (Providers) | Payers | Life Sciences | Regulated Healthcare Data",
  "detected_signals": [
    {
      "signal_id": "CS001",
      "signal_name": "HHS OCR Breach Portal Listing",
      "confidence": 0.95,
      "linked_pains": ["CP001", "CP010"],
      "linked_kpis": ["CK001", "CK003"],
      "status": "confirmed"
    }
  ],
  "active_pains": [
    {
      "pain_id": "CP001",
      "pain_name": "HIPAA Breach Notification Backlog",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "affected_personas": ["Chief Privacy Officer", "CISO", "Chief Compliance Officer"],
      "linked_kpis": ["CK001", "CK002", "CK003"],
      "linked_value_drivers": ["CV001", "CV002"],
      "symptoms_matched": ["breach discovery-to-notification > 45 days", "incident tickets > 500 open"]
    }
  ],
  "relevant_kpis": [
    {
      "kpi_id": "CK001",
      "kpi_name": "Breach Discovery-to-Notification Time",
      "current_value": 52,
      "unit": "days",
      "benchmark": "<30 days (best); >60 days (OCR violation)",
      "gap_assessment": "CRITICAL — exceeds 60-day OCR window"
    }
  ],
  "value_hypotheses": [
    {
      "driver_id": "CV001",
      "category": "Risk Reduction",
      "formula_id": "CF001",
      "formula_name": "HIPAA Breach Cost Avoidance",
      "estimated_annual_value": "$30M (expected value)",
      "confidence": "HIGH",
      "key_assumptions": [
        "Current 4 breaches/year reduced to 1",
        "Average cost per breach = $10.93M (IBM benchmark)"
      ]
    }
  ],
  "recommended_personas": [
    {
      "persona_id": "CPER001",
      "persona_name": "Chief Privacy Officer (CPO)",
      "engagement_priority": 1,
      "discovery_questions": ["CDQ001", "CDQ005", "CDQ011"]
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "CBT001",
      "trigger_name": "HHS OCR Breach Notification Received",
      "urgency": "CRITICAL",
      "timing": "Immediate; RFP 15-30 days",
      "action": "Activate breach response playbook; position incident management + automation"
    }
  ],
  "competitor_factors": [
    {
      "factor_id": "CCF001",
      "factor_name": "Epic Systems FHIR and Care Everywhere Dominance",
      "impact": "Buyers default to Epic-native interoperability; third-party FHIR tools must prove differentiation",
      "mitigation": "Position API governance, monitoring, and non-Epic connectivity"
    }
  ],
  "governance": {
    "confidence_level": "High",
    "source_coverage": "Mixed (public filings, government data, industry surveys, proprietary benchmarks)",
    "customer_facing_approval": false,
    "review_owner": "healthcare-compliance-subpack-architect",
    "last_updated": "2026-04-25",
    "validation_required": [
      "Verify current HIPAA/OCR benchmarks against latest HHS publications",
      "Confirm HITRUST CSF version (r2 vs. i1)",
      "Validate breach cost estimates before proposals",
      "Update FHIR benchmarks quarterly"
    ]
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | High |
| **Source Coverage** | Mixed (public filings, government data, industry surveys, proprietary benchmarks) |
| **Customer-Facing Approval** | **No** — internal intelligence asset; requires review before external use |
| **Review Owner** | healthcare-compliance-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-swarm-healthcare-s3.5 |
| **Parent Master Swarm ID** | kimi-k2.6-swarm-healthcare-m3 |

### Confidence Flags
- **HIGH**: Multiple corroborating sources, quantified data, direct regulatory or financial reporting
- **MEDIUM**: Industry survey data, partial quantification, or single-source but authoritative
- **LOW**: Estimates, directional indicators, or emerging trends with limited data

### Validation Required Before Customer Use
1. Verify current HIPAA/OCR benchmarks against latest HHS publications
2. Confirm HITRUST CSF version (r2 vs. i1) and customer-specific requirements
3. Validate organization-specific breach cost estimates before citing in proposals
4. Update FHIR and interoperability benchmarks quarterly (ONC, CMS rulemaking)
5. Review signal rules for false positive rate against historical conversion data
6. Confirm state-specific regulatory deadlines (CCPA, CPRA, VCDPA, MHMDA, etc.)
7. Validate cloud security posture against customer-specific architecture

---

## Quick Reference

### Top 5 Pains
| # | Pain | ID | Prevalence | Confidence |
|---|------|----|------------|------------|
| 1 | HIPAA Breach Notification Backlog | CP001 | HIGH | HIGH |
| 2 | Patient Identity Duplication and MPI Collisions | CP004 | HIGH | HIGH |
| 3 | Third-Party/Business Associate Risk Overflow | CP010 | HIGH | HIGH |
| 4 | Medical Coding Compliance and Upcoding Exposure | CP008 | HIGH | HIGH |
| 5 | Legacy HL7 v2 Interface Brittleness | CP015 | HIGH | HIGH |

### Top 5 KPIs
| # | KPI | ID | Unit | Benchmark |
|---|-----|----|------|-----------|
| 1 | Breach Discovery-to-Notification Time | CK001 | days | <30 (best); >60 (OCR violation) |
| 2 | MPI Duplicate Rate | CK010 | % | <3% (best); >5% (clinical safety risk) |
| 3 | HITRUST CSF Overall Score | CK007 | score | >80 (certification); <70 (significant gaps) |
| 4 | FWA Recovery Ratio | CK019 | ratio | >6:1 (best); <3:1 (unsustainable) |
| 5 | FHIR API Uptime (Patient Access) | CK004 | % | >99.9% (best); <99.5% (compliance risk) |

### Top 3 Personas
| # | Persona | ID | Primary Role |
|---|---------|----|--------------|
| 1 | Chief Privacy Officer (CPO) | CPER001 | Privacy strategy, HIPAA, state law, de-identification |
| 2 | CISO | (master) | Security posture, breach response, vendor risk |
| 3 | FHIR Integration Engineer | CPER003 | API governance, HL7-to-FHIR migration, interoperability |

### Key Value Formulas
| # | Formula | ID | Category | Example Output |
|---|---------|----|----------|----------------|
| 1 | HIPAA Breach Cost Avoidance | CF001 | Risk Reduction | $30M EV annually |
| 2 | HITRUST Certification Contract Protection | CF002 | Revenue Uplift | $8.75M annually |
| 3 | MPI Duplicate Reduction Value | CF004 | Cost Savings | $5.4M annually |
| 4 | FWA Detection Investment Return | CF007 | Cost Savings | $8M net annually |
| 5 | Ransomware Recovery Time Reduction | CF012 | Risk Reduction | $35.6M per incident |

---

*This subpack is a vertical-specialized ADDITION to the Healthcare Master ValuePack. Do NOT duplicate master content. Reference master components by ID when needed.*
