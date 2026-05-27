# SKILL.md — Infrastructure and Utilities Subpack (S5.5)

## Skill Identity Block

- **skill_name:** Infrastructure and Utilities Subpack (S5.5)
- **description:** Vertical-specialized value pack for public infrastructure and utilities agencies including water/wastewater, transit, roads/bridges, airports/ports, energy authorities, broadband, waste management, smart city, emergency communications, and grid modernization. Extends the Public Sector Master Pack with 18 vertical pains, 25 KPIs, 12 value formulas, 18 signal rules, 6 new personas, and 14 buying triggers.
- **version:** 1.0.0
- **domain:** Public Sector — Infrastructure & Utilities
- **pack_type:** subpack
- **parent_master:** public-sector-master-v1

---

## Triggers

Natural language query patterns that should auto-load this skill:

1. **Water main break rate** — "water main break rate per 100 miles", "water pipe replacement backlog", "boil water advisory analysis"
2. **Transit on-time performance** — "transit OTP below threshold", "bus ridership recovery", "transit operator vacancy impact"
3. **EPA consent decree compliance** — "EPA consent decree water utility", "sanitary sewer overflow enforcement", "wastewater CWA violation"
4. **Smart city IoT platform** — "smart city data silos", "municipal IoT integration", "digital twin city management"
5. **Grid modernization NERC CIP** — "grid modernization NERC CIP", "utility SCADA cybersecurity", "SAIDI SAIFI improvement"
6. **Bridge condition deterioration** — "structurally deficient bridge percentage", "NBI bridge backlog", "load posting bridge analysis"
7. **Airport Part 139 compliance** — "FAA Part 139 inspection findings", "ARFF response time", "airfield PCI runway condition"
8. **BEAD broadband deployment** — "BEAD subgrantee selection delay", "broadband cost per passing", "digital equity program"
9. **Fleet electrification** — "transit fleet electrification", "EV depot capacity", "ZEV mandate compliance"
10. **NextGen 911 transition** — "NG911 deployment status", "PSAP turnover crisis", "911 call answer time"
11. **PFAS emerging contaminant** — "PFAS MCL compliance", "water treatment GAC IX", "CWSRF loan pending"
12. **DER interconnection backlog** — "solar interconnection queue", "hosting capacity map utility", "FERC Order 2023"

---

## Reasoning Flow

### Step 1: Identify the Vertical Segment
Determine which infrastructure segment the prospect belongs to:
- Water Utilities / Wastewater
- Public Transit (Bus, Rail, Ferry)
- Roads / Bridges / Highways
- Airports / Port Authorities
- Public Energy / Municipal Utilities / Grid Modernization
- Broadband / Digital Equity
- Waste Management / Recycling
- Smart City / IoT
- Emergency Communications (911 / PSAP)

### Step 2: Load Master First, Then Subpack
1. **Load `public-sector-master-v1`** to establish base framework:
   - Value drivers (Revenue Uplift, Cost Savings, Risk Reduction, Mission Effectiveness, Working Capital)
   - Base personas (PS-PERS-001 through PS-PERS-012)
   - Evidence taxonomy and governance rules
   - Formula templates (PV, risk-adjusted, payback)

2. **Apply this subpack** for vertical enrichment:
   - Segment-specific pains, KPIs, benchmarks
   - Vertical personas (INF-PERS-001 to INF-PERS-006)
   - Technology systems and regulatory factors
   - Discovery questions and objection patterns

### Step 3: Signal Detection and Scoring
For the target account, scan for signals matching the 18 vertical signal rules (INF-SIG-001 to INF-SIG-018):

| Signal Category | Raw Pattern | Confidence |
|-----------------|-------------|------------|
| Water Main Break Escalation | Break rate >25/100 mi; repeat breaks >2/yr; CI age >50yr | 0.90 |
| Transit Reliability Decline | OTP <75% for 2+ quarters; vacancy >15%; farebox <20% | 0.88 |
| OT Cybersecurity Exposure | Flat OT network; default PLC passwords; no OT IDS; Win7/XP | 0.92 |
| Bridge Condition Deterioration | SD% >7%; load postings up; inspection backlog >12mo | 0.90 |
| Airport Part 139 Risk | Findings >2; ARFF >180s; PCI <70 primary | 0.88 |
| Broadband Deployment Blockers | Subgrantee delayed >6mo; permitting >50% schedule; MR >30% | 0.85 |
| Wastewater SSO/I-I Crisis | SSO >10/yr; I/I >50%; consent decree present | 0.92 |
| Fleet Electrification Blocked | EV procurement >12mo delay; depot capacity insufficient | 0.82 |
| Distribution Reliability Erosion | SAIDI >240; SAIFI >2.0; major events >5/yr; veg >30% | 0.90 |
| Smart City Integration Failure | Platforms >5 no central layer; twin stale >30d; uptime <90% | 0.78 |
| NextGen 911 Transition Lag | Text-to-911 not deployed; CAMA primary; GIS <95%; turnover >15% | 0.88 |
| Recycling Economics Collapse | Contamination >25%; commodity revenue down >30%; cost >tip fee | 0.85 |
| Port Throughput Bottleneck | Turn >75min; dwell >6d; chassis <85%; disputes increasing | 0.86 |
| Utility Affordability Crisis | Shutoff >5%; rate increase >5% for 3yr; delinquency >8% | 0.88 |
| Fare Revenue Leakage | Evasion >8%; revenue discrepancy >2%; citation collection <30% | 0.82 |
| PFAS Compliance Urgency | Detection >MCL; pilot not started; lab wait >30d; CWSRF >12mo | 0.90 |
| Airfield Pavement Failure Risk | PCI <70; FOD >2/yr; crack sealing backlog >12mo | 0.88 |
| DER Interconnection Grid Lock | Queue >1,000; review >180d; rejection >40%; no hosting map | 0.86 |

**Confidence scoring guidance:**
- **Confirmed (0.85–1.00):** Direct data from the prospect or peer-verified source (NTD, NBI, EPA SDWIS, NPDES DMR)
- **Likely (0.70–0.84):** Indirect signals (news, FOIA, regulatory filings) with multiple corroborating patterns
- **Possible (0.50–0.69):** Single-source signal; requires discovery question validation
- **Discard (<0.50):** Anecdotal or outdated (>2 years) without confirmation

### Step 4: Map to Pains, Personas, and KPIs
For each confirmed signal:
1. **Link to Pain** — Map to the corresponding INF-PAIN (e.g., INF-SIG-001 → INF-PAIN-001)
2. **Identify Affected Personas** — Which vertical personas (INF-PERS-xxx) and master personas (PS-PERS-xxx) are impacted
3. **Pull KPIs** — Reference the relevant INF-KPI with benchmark ranges
4. **Quantify Impact** — Apply the appropriate value formula (INF-VF-001 to INF-VF-012)

### Step 5: Value Hypothesis Construction
Build a value hypothesis using the subpack’s formula library:
1. Start with baseline KPI from benchmarks (INF-BENCH-xxx)
2. Define target state using best-practice thresholds
3. Apply the segment-specific value formula
4. Adjust confidence based on data availability
5. Cross-check with worked examples (INF-EX-001 to INF-EX-003)

### Step 6: Discovery and Objection Handling
- Use the 18 discovery questions (INF-DQ-001 to INF-DQ-018) to validate assumptions
- Prepare counters for the 9 common objections (INF-OBJ-001 to INF-OBJ-009)
- Reference regulatory deadlines (INF-REG-001 to INF-REG-010) to create urgency

### Step 7: Output Enrichment
Produce a structured Signals Analysis enrichment that references both master and subpack components.

---

## Inheritance Map

### Master Skill to Load First
**`public-sector-master-v1`** must be loaded before this subpack. The master provides:
- Base value driver framework (5 drivers)
- Base persona archetypes (12 personas)
- Evidence source taxonomy and governance
- Formula templates (PV, risk-adjusted, payback)
- Benchmark methodology and confidence scoring

### What This Subpack Adds
| Category | Count | Content |
|----------|-------|---------|
| Pains | 18 | Water breaks, transit OTP, OT cybersecurity, bridge SD, airport 139, BEAD broadband, SSO/I-I, fleet EV, grid SAIDI, smart city silos, NG911, recycling, ports, affordability, fare evasion, PFAS, airfield PCI, DER backlog |
| KPIs | 25 | Segment-specific operational and compliance metrics |
| Signal Rules | 18 | Quantified detection rules with confidence scores |
| Personas | 6 NEW | Water Director, Transit GM, Public Works Director, Grid Engineer, Airport Ops, Broadband Director |
| Value Formulas | 12 | Pre-built formulas for ROI calculation |
| Benchmarks | 18 | National medians and best-practice thresholds |
| Regulatory Factors | 10 | SDWA, CWA, FTA, FAA Part 139, NERC CIP, BEAD, NG911, IIJA/IRA |
| Technology Systems | 12 | SCADA, GIS/EAM, CMMS, ITS/AVL, AFC, ADMS, OMS, PMS, AOMS, FOD, Broadband Mapping, NG911 |
| Discovery Questions | 18 | Segment-specific qualification questions |
| Objections | 9 | CIP, rates, small system, grants, air-gap, equity, smart city failure, union, budget cycle |
| Buying Triggers | 14 | EPA enforcement, FAA findings, BEAD award, disruptions, cyber incidents, ZEV mandates, PFAS rule, rate cases, FTA review, NERC audit, NG911 plan, grant deadlines, climate directive, staffing crisis |

### When to Use Master vs. Subpack
- **Use Master alone** when the prospect is a generic public sector entity (state agency, municipal government, K-12, public safety) without clear infrastructure vertical focus
- **Use Subpack (always with Master)** when the prospect is:
  - A water/wastewater utility
  - A transit authority
  - A roads/bridges department
  - An airport or port authority
  - A public power utility or grid operator
  - A broadband authority
  - A smart city / IoT program
  - A 911/PSAP emergency communications center

---

## Structured Output Template

Expected JSON format for Signals Analysis enrichment:

```json
{
  "skillLoaded": "infrastructure-v1",
  "parentMaster": "public-sector-master-v1",
  "analysisTimestamp": "2025-01-21T00:00:00Z",
  "accountSegment": "Water Utilities",
  "signalsDetected": [
    {
      "signalId": "INF-SIG-001",
      "signalName": "Water Main Break Escalation",
      "rawEvidence": "Break rate 32/100 mi/year; 60% CI >50 years old",
      "confidenceScore": 0.92,
      "confidenceLevel": "Confirmed",
      "linkedPain": "INF-PAIN-001",
      "linkedKPIs": ["INF-KPI-001", "INF-KPI-003"],
      "linkedPersonas": ["INF-PERS-001", "PS-PERS-002"],
      "valueHypothesis": {
        "formulaId": "INF-VF-001",
        "baselineValue": 32,
        "targetValue": 15,
        "estimatedAnnualValue": 1425000,
        "currency": "USD",
        "confidence": "HIGH"
      }
    }
  ],
  "painsActivated": [
    {
      "painId": "INF-PAIN-001",
      "painName": "Water Main Break Rate Exceeding Tolerance",
      "severity": "HIGH",
      "prevalence": "HIGH",
      "valueDriverLinks": ["Cost Savings", "Risk Reduction"]
    }
  ],
  "personasActivated": [
    {
      "personaId": "INF-PERS-001",
      "personaName": "Water Utility Director / General Manager",
      "engagementPriority": 1
    }
  ],
  "kpisReferenced": [
    {
      "kpiId": "INF-KPI-001",
      "kpiName": "Water Main Break Rate",
      "observedValue": 32,
      "benchmarkMedian": 25,
      "benchmarkBest": 15,
      "unit": "Breaks per 100 miles/year"
    }
  ],
  "regulatoryFactors": [
    {
      "regId": "INF-REG-001",
      "regName": "Safe Drinking Water Act (SDWA)",
      "urgencyLevel": "MEDIUM",
      "deadlineProximity": "LCRR 2024; PFAS MCL 2024-2029"
    }
  ],
  "buyingTriggersMatched": [
    {
      "triggerId": "INF-BT-001",
      "triggerName": "EPA enforcement or consent decree",
      "timingWindow": "0-12 months",
      "applicable": false
    }
  ],
  "nextBestActions": [
    "Schedule discovery call with Water Utility Director using INF-DQ-001",
    "Prepare INF-OBJ-002 counter (rate affordability)",
    "Reference INF-EX-001 worked example for pipe replacement ROI"
  ]
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (Federal agency data — EPA, FTA, FHWA, FAA, EIA, NERC; Industry associations — AWWA, APTA, ASCE, SWANA; Research organizations — NREL, NENA, CISA; Vendor benchmarks) |
| **Customer-Facing Approval Status** | YES — Approved for customer-facing output |
| **Review Owner** | Infrastructure & Utilities Vertical Agent (Phase 2) |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | infra-utilities-swarm-001 |
| **Parent Master Swarm ID** | public-sector-master-swarm-001 |

---

## Quick Reference

### Top 5 Pains

| # | Pain ID | Pain Name | Prevalence | Confidence |
|---|---------|-----------|------------|------------|
| 1 | INF-PAIN-001 | Water Main Break Rate Exceeding Tolerance | HIGH | HIGH |
| 2 | INF-PAIN-002 | Transit On-Time Performance Below Threshold | HIGH | HIGH |
| 3 | INF-PAIN-003 | SCADA/OT Cybersecurity Exposure | HIGH | HIGH |
| 4 | INF-PAIN-007 | Wastewater Collection System I/I and SSOs | HIGH | HIGH |
| 5 | INF-PAIN-009 | Energy Distribution Grid Resilience & Outage Duration | HIGH | HIGH |

### Top 5 KPIs

| # | KPI ID | KPI Name | Benchmark (Best / Median / Fail) |
|---|--------|----------|-------------------------------|
| 1 | INF-KPI-001 | Water Main Break Rate | <15 / ~25 / >35 per 100 mi/yr |
| 2 | INF-KPI-004 | Transit On-Time Performance | >85% / 78% / <75% |
| 3 | INF-KPI-007 | OT Network Security Posture Score | >85 / ~50 / <50 (0-100) |
| 4 | INF-KPI-010 | Structurally Deficient Bridge Percentage | <5% / 7.1% / >8% |
| 5 | INF-KPI-025 | SAIDI (System Average Interruption Duration Index) | <100 min / ~198 min / >300 min/yr |

### Top 3 Personas

| # | Persona ID | Persona Name | Primary Decision Driver |
|---|------------|--------------|------------------------|
| 1 | INF-PERS-001 | Water Utility Director / General Manager | Technical + Economic (rate impact) |
| 2 | INF-PERS-002 | Transit Authority General Manager / CEO | Mission + Economic |
| 3 | INF-PERS-004 | Grid Modernization Engineer / Utility Engineering Director | Technical + Economic (rate impact) |

### Key Value Formulas

| Formula ID | Name | Output Unit | Confidence |
|------------|------|-------------|------------|
| INF-VF-001 | Water Main Break Cost Avoidance via Pipe Replacement | USD/year | HIGH |
| INF-VF-002 | Transit OTP Revenue Recovery | USD/year | MEDIUM |
| INF-VF-003 | OT Cybersecurity Risk Reduction Value | USD/year (NPV) | MEDIUM |
| INF-VF-007 | SSO/I-I Reduction Value | USD/year | HIGH |
| INF-VF-009 | Distribution Reliability Improvement Value | USD/year | HIGH |

---

*This SKILL.md is an OpenClaw-compatible skill definition. It references and extends the Public Sector Master Pack (`public-sector-master-v1`). Do not use this subpack without first loading the master pack. For full component definitions, see `value-pack.json` and `value-pack.md` in this directory.*
