# SKILL.md — Public Sector Master Value Pack

<!-- OpenClaw-compatible skill definition for M5: Public Sector Master -->

## Skill Identity Block

| Attribute | Value |
|-----------|-------|
| **skill_name** | Public Sector Master Value Pack |
| **description** | Comprehensive reasoning foundation for B2G and public sector technology sales, solution architecture, and value engineering. Covers Federal Government, State & Local Government, Education & Public Institutions, Public Health & Human Services, and Public Infrastructure & Utilities plus cross-cutting technology and governance themes. Designed to identify mission-critical pains, quantify value through public-sector-appropriate KPIs, and guide account strategies across $6.8T+ in federal and $3.5T+ in state/local annual spending. |
| **version** | 1.0.0 |
| **domain** | industry |
| **pack_type** | master |
| **parent_master** | — (this is a master pack) |

---

## Triggers Section

Auto-load this skill when the user query matches any of the following natural language patterns:

1. "analyze a federal agency" or "federal government IT modernization"
2. "state government digital modernization" or "state agency digital transformation"
3. "public health Medicaid eligibility" or "Medicaid administrative complexity"
4. "local government infrastructure deferred maintenance" or "public works asset management"
5. "education institution enrollment decline" or "K-12 fiscal stress"
6. "public sector cybersecurity" or "government Zero Trust implementation"
7. "grant management compliance" or "federal grant drawdown optimization"
8. "citizen service friction" or "government call center backlog"
9. "transit ridership recovery" or "public transit revenue shortfall"
10. "water utility PFAS compliance" or "public infrastructure asset degradation"
11. "criminal justice case processing delays" or "court backlog jail overcrowding"
12. "B2G sales opportunity" or "government procurement cycle inefficiency"

---

## Reasoning Flow

### Step 1: Segment Classification

Determine which public sector segment(s) apply to the prospect/account:

- **A. Federal Government** — DoD, IC, DHS, Civilian, Treasury, HHS, DOT, DOE, EPA, DOL, DOJ, VA, NASA/NSF/NOAA
- **B. State & Local Government** — State agencies, counties, municipalities, DOTs, DMVs, PHAs, courts, public safety, EMAs
- **C. Education & Public Institutions** — K-12 districts, public universities, community colleges, workforce boards, libraries
- **D. Public Health & Human Services** — Medicaid SMAs, public health departments, child welfare, UI, SNAP, behavioral health, aging/disability
- **E. Public Infrastructure & Utilities** — Water/wastewater, transit, roads/bridges, airports/ports, energy authorities, broadband, smart city, 911
- **F. Cross-Cutting Technology** — Digital identity, citizen portals, case management, grants systems, procurement, cybersecurity, cloud, AI governance, accessibility, data interoperability

### Step 2: Signal Identification

Scan for raw signals across the 30 signal patterns defined in this pack. Prioritize signals with confidence >= 0.80.

**High-priority signal categories:**
- Legacy system maintenance (PS-SIG-001)
- Unpatched critical CVEs (PS-SIG-002)
- Case/claims backlog growth (PS-SIG-003)
- Rising improper payments (PS-SIG-004)
- Grant drawdown delays (PS-SIG-005)
- Critical workforce vacancies (PS-SIG-006)
- Procurement cycle extension (PS-SIG-007)
- Infrastructure asset degradation (PS-SIG-010)
- Repeat audit findings (PS-SIG-011)
- Water system violations (PS-SIG-018)
- Pre-trial jail overcrowding (PS-SIG-019)
- Zero Trust implementation lag (PS-SIG-030)

**Required confirmation for each signal:** budget documents, audit reports, system inventories, staffing data, or other primary evidence.

### Step 3: Pain Mapping

Map confirmed signals to the 25 defined pains. Use prevalence and confidence ratings to prioritize:

| Priority | Pains (Prevalence = HIGH) |
|----------|---------------------------|
| Critical | Legacy System Maintenance (PS-PAIN-001), Cybersecurity Vulnerability (PS-PAIN-002), Case Backlog (PS-PAIN-003), Fraud/Waste/Abuse (PS-PAIN-004), Grant Management Complexity (PS-PAIN-005), Workforce Shortage (PS-PAIN-006), Procurement Inefficiency (PS-PAIN-007), Data Silos (PS-PAIN-008), Citizen Service Friction (PS-PAIN-009), Infrastructure Degradation (PS-PAIN-010), Regulatory Compliance (PS-PAIN-011), Budget Volatility (PS-PAIN-012), Medicaid Complexity (PS-PAIN-016), Eligibility Errors (PS-PAIN-021), Water Infrastructure Gap (PS-PAIN-018) |
| Elevated | Emergency Preparedness (PS-PAIN-013), FOIA Backlogs (PS-PAIN-014), Enrollment Decline (PS-PAIN-015), Transit Ridership (PS-PAIN-017), Justice Delays (PS-PAIN-019), Acquisition Workforce (PS-PAIN-020), School Safety (PS-PAIN-022), Cloud Overrun (PS-PAIN-023), Broadband Gap (PS-PAIN-024), Pension Pressure (PS-PAIN-025) |

### Step 4: Persona Targeting

Identify the decision-makers and influencers affected by the mapped pains:

| Persona | Role | Primary Concerns |
|---------|------|------------------|
| PS-PERS-001: CIO | Agency IT leader | Modernization, cybersecurity, O&M ratio, workforce |
| PS-PERS-002: CFO/Comptroller | Financial leader | Audit opinion, budget execution, grant drawdown, compliance cost |
| PS-PERS-003: Program Director/Agency Head | Mission delivery | Outcomes, backlogs, statutory compliance, funding, scandal avoidance |
| PS-PERS-004: CISO | Security leader | Zero Trust, FISMA, incident reduction, supply chain |
| PS-PERS-005: Inspector General | Oversight | Waste/fraud identification, repeat findings, independence |
| PS-PERS-006: Budget/Grants Officer | Fiscal administration | Obligation rates, lapse avoidance, single audit, 2 CFR 200 |
| PS-PERS-007: Contracting Officer/KO | Procurement gatekeeper | On-time awards, protest avoidance, FAR compliance, best value |
| PS-PERS-008: Case Worker/Eligibility Specialist | Frontline delivery | Caseload accuracy, system usability, client dignity, burnout |
| PS-PERS-009: Public Works/Utility Director | Infrastructure operations | Asset reliability, regulatory compliance, rate stability, safety |
| PS-PERS-010: Superintendent/Provost | Education leader | Enrollment, accreditation, student success, fiscal sustainability |
| PS-PERS-011: Emergency Manager | Preparedness/response | Resilience, NIMS compliance, interoperable communications |
| PS-PERS-012: Chief Data Officer | Data strategy | Data-driven decisions, open data, privacy, AI governance |
| PS-PERS-013: Chief Acquisition Officer | Acquisition strategy | Workforce development, category management, protest reduction |
| PS-PERS-014: Elected Official/Board Member | Policy/oversight | Constituent satisfaction, fiscal responsibility, transparency |

### Step 5: KPI and Benchmark Alignment

For each confirmed pain, identify the relevant KPIs and compare against benchmarks:

**Confidence scoring guidance:**
- **HIGH (0.85–1.00):** Multiple confirming signals with primary source evidence (GAO, OIG, budget docs, system reports)
- **MEDIUM (0.60–0.84):** Single strong signal or secondary evidence (trade surveys, news reports, analyst estimates)
- **LOW (0.40–0.59):** Weak or circumstantial signals; speculative inference
- **REJECT (<0.40):** Insufficient evidence; do not include in output

### Step 6: Value Driver Selection

Map confirmed pains to value drivers using the 25 value drivers in this pack. Public sector value is expressed through:

1. **Mission Effectiveness** — improved program outcomes and citizen services
2. **Operational Efficiency** — reduced processing times, backlogs, and administrative overhead
3. **Cost Avoidance & Savings** — fraud/waste reduction, legacy O&M reduction, procurement optimization
4. **Risk Reduction** — cybersecurity, compliance, audit posture, disaster preparedness
5. **Transparency & Accountability** — open data, performance reporting, public trust
6. **Resource Optimization** — grant utilization, workforce productivity, asset utilization

### Step 7: Value Quantification

Apply the 25 value formulas (PS-VF-001 through PS-VF-025) to quantify opportunity size:

- Use actual data where available (budget docs, system reports, audit findings)
- Use benchmarks as proxies when actuals unavailable; downgrade confidence accordingly
- Express value in 3-year NPV or annual terms depending on formula
- Always annotate confidence level and data source for each calculation

### Step 8: Buying Trigger Alignment

Cross-reference account situation with the 25 buying triggers (PS-TRIG-001 through PS-TRIG-025). Triggers with CRITICAL or HIGH urgency create near-term procurement windows:

- **CRITICAL:** Cybersecurity incident, disaster declaration, breach notification law, shutdown/CR resolution
- **HIGH:** Audit finding with management direction, new grant award, regulatory deadline, leadership change, IT modernization mandate, legislative change, court order, technology EOL, formula fund release

### Step 9: Subpack Routing (if applicable)

This master pack provides the full reasoning foundation. If a subpack exists for a specific segment (e.g., Federal-Civilian, State-Medicaid, Education-K12), load the subpack after this master to get deeper segment-specific signals, pains, and benchmarks.

---

## Inheritance Map

*(This is a master pack — no parent required. Subpacks inherit from this master.)*

| Relationship | Guidance |
|-------------|----------|
| **Master → Subpack** | Load this master first for taxonomy, value drivers, and governance context. Then load segment-specific subpacks for deeper pain catalogs, segment benchmarks, and specialized personas. |
| **When to use master alone** | Early prospecting, cross-segment accounts, general B2G positioning, multi-jurisdictional opportunities. |
| **When to use master + subpack** | Named-account planning, proposal development, segment-specific RFP response, vertical marketing. |

---

## Structured Output Template

```json
{
  "skillLoaded": "public-sector-master-v1",
  "analysisTimestamp": "ISO-8601",
  "accountProfile": {
    "name": "string",
    "segment": "A-F",
    "subSegment": "string",
    "jurisdictionLevel": "federal | state | local | tribal | special-district",
    "annualBudgetScale": "string"
  },
  "signalsAnalysis": {
    "identifiedSignals": [
      {
        "signalId": "PS-SIG-###",
        "signalName": "string",
        "rawEvidence": ["string"],
        "confidence": 0.0,
        "confirmed": true | false,
        "linkedPains": ["PS-PAIN-###"],
        "linkedKPIs": ["PS-KPI-###"]
      }
    ],
    "overallSignalConfidence": 0.0
  },
  "painsAnalysis": {
    "identifiedPains": [
      {
        "painId": "PS-PAIN-###",
        "painName": "string",
        "prevalence": "HIGH | MEDIUM | LOW",
        "confidence": "HIGH | MEDIUM | LOW",
        "symptomsObserved": ["string"],
        "affectedPersonas": ["PS-PERS-###"],
        "linkedValueDrivers": ["string"],
        "sources": ["string"]
      }
    ],
    "topPain": "PS-PAIN-###"
  },
  "personaMap": {
    "primaryDecisionMaker": "PS-PERS-###",
    "economicBuyer": "PS-PERS-###",
    "technicalBuyer": "PS-PERS-###",
    "userChampion": "PS-PERS-###",
    "riskInfluencer": "PS-PERS-###"
  },
  "kpiBenchmarks": {
    "relevantKPIs": [
      {
        "kpiId": "PS-KPI-###",
        "kpiName": "string",
        "accountValue": "string | number | null",
        "benchmarkValue": "string | number",
        "benchmarkRange": "string",
        "varianceFromBenchmark": "string",
        "trend": "improving | stable | worsening | unknown"
      }
    ]
  },
  "valueHypothesis": {
    "valueDrivers": [
      {
        "driverId": "PS-VD-###",
        "driverCategory": "Cost Savings | Risk Reduction | Mission Effectiveness | Working Capital | Revenue Uplift",
        "quantifiedValue": {
          "annual": 0,
          "threeYearNPV": 0,
          "currency": "USD",
          "confidence": "HIGH | MEDIUM | LOW"
        },
        "formulaUsed": "PS-VF-###",
        "keyInputs": {}
      }
    ],
    "totalQuantifiedValue": {
      "annual": 0,
      "threeYearNPV": 0,
      "currency": "USD",
      "confidence": "HIGH | MEDIUM | LOW"
    }
  },
  "buyingTriggers": {
    "activeTriggers": [
      {
        "triggerId": "PS-TRIG-###",
        "triggerName": "string",
        "urgency": "CRITICAL | HIGH | MEDIUM | LOW",
        "timing": "string",
        "procurementImplication": "string"
      }
    ],
    "nextExpectedTrigger": "string | null"
  },
  "objectionReadiness": {
    "likelyObjections": [
      {
        "objectionId": "PS-OBJ-###",
        "objectionPattern": "string",
        "responseStrategy": "string",
        "validationNeeded": ["string"]
      }
    ]
  },
  "governance": {
    "overallConfidence": "HIGH | MEDIUM | LOW",
    "sourceCoverage": "string",
    "customerFacingApproval": true | false,
    "lastUpdated": "2026-04-25",
    "reviewOwner": "Master Pack Foundation Architect — Public Sector"
  }
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence level** | Medium (varies by segment; HIGH for federal benchmarks, MEDIUM for citizen experience, LOW for emerging areas like AI governance and smart city ROI) |
| **Source coverage** | Mixed — public budgets, GAO reports, IG audits, RFPs, vendor disclosures, academic research, trade association data (NASCIO, NASBO, APTA, ASCE, AWWA, KFF, NCES, etc.) |
| **Customer-facing approval status** | No — requires validation with live prospects before use in customer-facing proposals or presentations |
| **Review owner** | Master Pack Foundation Architect — Public Sector |
| **Last updated** | 2026-04-25 |
| **Next review date** | 2026-10-25 |

---

## Quick Reference

### Top 5 Pains

| ID | Pain | Prevalence | Primary Value Driver |
|----|------|------------|---------------------|
| PS-PAIN-001 | Legacy System Maintenance Burden | HIGH | Cost Savings + Risk Reduction |
| PS-PAIN-002 | Cybersecurity Vulnerability & Threat Exposure | HIGH | Risk Reduction + Cost Savings |
| PS-PAIN-003 | Case / Claims Backlog Accumulation | HIGH | Mission Effectiveness + Cost Savings |
| PS-PAIN-004 | Fraud, Waste, and Abuse in Benefit Programs | HIGH | Cost Savings + Risk Reduction + Revenue Uplift |
| PS-PAIN-005 | Grant Management & Compliance Complexity | HIGH | Working Capital + Cost Savings + Risk Reduction |

### Top 5 KPIs

| ID | KPI | Benchmark | Unit |
|----|-----|-----------|------|
| PS-KPI-001 | Legacy System O&M Ratio | <50% best practice; 72% federal median | Percentage |
| PS-KPI-003 | Mean Time to Patch Critical Vulnerabilities | <7 days best; 15 days CISA BOD | Days |
| PS-KPI-006 | Case Backlog Count | <5% of annual volume | Count |
| PS-KPI-008 | Improper Payment Rate | <2% OMB target; 8-15% Medicaid | Percentage |
| PS-KPI-009 | Grant Utilization Rate | >95% best practice; <90% lapse risk | Percentage |

### Top 3 Personas

| ID | Persona | Decision Influence | Primary Pressure |
|----|---------|-------------------|------------------|
| PS-PERS-001 | CIO | Technical (primary) + Economic (secondary) | FITARA, FISMA, TMF, workforce, cloud mandates |
| PS-PERS-002 | CFO/Comptroller | Economic (primary) + Technical (secondary) | OIG findings, A-123, GAO high-risk, grant lapse |
| PS-PERS-003 | Program Director/Agency Head | User (mission) + Economic (budget) | Congressional oversight, backlogs, budget constraints, court orders |

### Key Value Formulas

| ID | Formula | Use Case |
|----|---------|----------|
| PS-VF-001 | `V = (Current_OandM_Ratio - Target_OandM_Ratio) * Total_IT_Budget * 3_years` | Legacy O&M cost avoidance |
| PS-VF-002 | `V = (Baseline_Incident_Rate - Target_Incident_Rate) * Avg_Cost_Per_Incident * Endpoint_Count * Years` | Cybersecurity breach cost avoidance |
| PS-VF-003 | `V = (Baseline_Backlog - Target_Backlog) * Cost_Per_Case + Overtime_Avoidance + FTE_Avoidance` | Case backlog elimination value |
| PS-VF-004 | `V = Total_Program_Outlay * (Baseline_IP_Rate - Target_IP_Rate) * Recovery_Rate` | Improper payment reduction |
| PS-VF-005 | `V = Total_Grant_Award * (Baseline_Lapse_Rate - Target_Lapse_Rate)` | Grant lapse avoidance |

---

## Appendix: Subpack Segments

This master pack supports the following subpack segments (create/load subpacks for deeper vertical specialization):

- **Federal-Civilian** — GSA, SBA, State, Interior, Treasury, HHS, DOT, EPA, DOL, DOJ, VA
- **Federal-Defense** — DoD, IC, DHS
- **State-Executive** — Governor’s office, state cabinets
- **State-Medicaid** — SMAs, CMS compliance, eligibility
- **Local-Government** — Municipalities, counties, public safety, courts
- **Education-K12** — School districts, enrollment, state aid
- **Education-HigherEd** — Public universities, community colleges, research
- **Infrastructure-Water** — Utilities, PFAS, lead lines, SRF
- **Infrastructure-Transit** — Ridership recovery, farebox, NTD
- **Cross-Cutting-Cybersecurity** — Zero Trust, FISMA, CISA BODs
- **Cross-Cutting-Cloud** — FedRAMP, migration, optimization, repatriation
- **Cross-Cutting-AI** — EO 14110, responsible AI, algorithmic governance

---

*End of SKILL.md — Public Sector Master Value Pack (M5)*
