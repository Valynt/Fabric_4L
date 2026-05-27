# Discrete Manufacturing Subpack (S1.1)

## Skill Identity

- **skill_name:** Discrete Manufacturing Subpack
- **description:** Vertical intelligence subpack for Discrete Manufacturing covering Automotive/EV, aerospace, industrial equipment, electronics, medical devices, heavy machinery, robotics, and rail/marine. Adds 18 segment-specific pains, 25 specialized KPIs, 20 signal rules, 6 new personas (MRO Manager, Production Scheduler, Quality Engineer, Design Engineer, Warranty Analyst), 15 value formulas, 20 benchmarks, 12 regulatory factors, 15 technology systems, 20 discovery questions, 10 objection patterns, and 15 buying triggers.
- **version:** 1.0.0
- **domain:** industry
- **pack_type:** subpack
- **parent_master:** manufacturing-master-v1

---

## Triggers

Auto-load this subpack when the user query matches any of the following patterns:

1. **"analyze an automotive supplier"** or **"EV battery assembly signals"**
2. **"aerospace quality audit signals"** or **"Nadcap special process assessment"**
3. **"medical device FDA warning letter response"** or **"V&V backlog analysis"**
4. **"SMT solder defect signals"** or **"electronics contract manufacturer analysis"**
5. **"CNC tool wear prediction"** or **"CMM bottleneck elimination"**
6. **"welding porosity root cause"** or **"structural weld quality audit"**
7. **"additive manufacturing build failure"** or **"AM production qualification"**
8. **"sheet metal setup time reduction"** or **"press brake first article pass"**
9. **"robot cycle time optimization"** or **"collision avoidance in automation"**
10. **"component allocation crisis"** or **"semiconductor shortage expediting"**
11. **"digital thread CAD-to-machine gap"** or **"CAM programming efficiency"**
12. **"casting scrap reduction"** or **"foundry porosity prediction"**

---

## Reasoning Flow

### Step 1: Load Manufacturing Master First
Always begin by loading `manufacturing-master-v1` to establish the foundational framework:
- Base value driver taxonomy (revenue uplift, cost savings, risk reduction, working capital)
- Base personas (Plant Manager, Quality Manager, Operations Manager, Supply Chain Manager, CFO, HR Manager)
- Evidence taxonomy and confidence levels
- Formula templates (NPV, IRR, payback)
- Base signal rules (12 foundational rules)
- Benchmark methodology
- Governance framework

### Step 2: Apply Discrete Manufacturing Overlay
After master frameworks are loaded, apply this subpack as an additive layer:

#### 2a. Identify Segment Relevance
Map the target account to one or more vertical segments:
| Segment | Key Indicators |
|---------|---------------|
| Automotive/EV | OEM supplier status, EV battery/module production, torque-controlled assembly, IATF 16949 |
| Aerospace & Defense | Nadcap special processes, AS9100D, prime contracts (Boeing/Airbus), NDT operations |
| Electronics & Semiconductors | SMT/PCBA lines, IPC standards, AOI/SPI systems, semiconductor sourcing |
| Medical Devices | FDA 21 CFR Part 820, UDI, IQ/OQ/PQ validation, Class I-III production |
| Heavy Machinery | Casting/forging operations, welding structures, large-part machining |
| Industrial Equipment | Sheet metal fabrication, powder coating, machinery assembly |
| Robotics & Automation | Robot cell deployment, offline programming, path optimization |
| Rail/Marine | Safety-critical welding, NDT, large component assembly |

#### 2b. Detect Discrete-Specific Signals
Evaluate public, paid, and proprietary signals against the 20 vertical signal rules. Priority signals by severity:

| Severity | Signal | Confidence | Action |
|----------|--------|------------|--------|
| CRITICAL | EV battery thermal runaway incident | 0.93 | Immediate executive alert |
| CRITICAL | Nadcap audit non-conformance | 0.91 | COO/Quality VP engagement |
| CRITICAL | FDA 483 validation observation | 0.90 | CEO/Regulatory counsel |
| HIGH | Component allocation notice | 0.89 | Supply chain VP |
| HIGH | BOM revision mismatch | 0.88 | Engineering/ops review |
| HIGH | Cleanroom particle excursion | 0.88 | Plant manager/quality |
| HIGH | Foundry X-ray porosity cluster | 0.87 | Quality/process engineering |
| HIGH | Weld parameter deviation | 0.86 | Plant manager/EHS |
| HIGH | CAD revision not propagated | 0.86 | Engineering/IT |
| MEDIUM | Customer SCAR influx | 0.85 | Quality manager/coo |
| MEDIUM | SMT reflow profile drift | 0.85 | Electronics quality |
| MEDIUM | Torque calibration overdue | 0.84 | Quality/maintenance |
| MEDIUM | AM build failure repeat | 0.83 | Engineering/ops |
| MEDIUM | Andon activation spike | 0.82 | Plant manager |
| MEDIUM | CMM queue growth | 0.81 | Quality/planning |
| MEDIUM | CNC spindle load anomaly | 0.79 | Maintenance/quality |
| MEDIUM | Kitting error escalation | 0.78 | Production/planning |
| MEDIUM | AOI false positive spike | 0.77 | Electronics quality |
| MEDIUM | Robot collision log growth | 0.76 | Safety/plant manager |
| MEDIUM | Sheet metal springback deviation | 0.80 | Quality/setup |

#### 2c. Map Signals to Pains and KPIs
For each confirmed signal:
1. Identify the linked pain(s) from the 18 vertical pains
2. Retrieve the segment applicability filter
3. Map to affected personas
4. Pull the relevant KPIs and benchmark ranges
5. Assess current state vs. benchmark gap

#### 2d. Build Value Hypotheses
Apply the 15 vertical value formulas (VF-DM-001 through VF-DM-015) to translate pain into quantified business value:
- **Cost Savings:** Scrap reduction, rework avoidance, labor efficiency, expediting reduction
- **Risk Reduction:** Warranty cost avoidance, recall risk reduction, regulatory penalty avoidance, customer SCAR reduction
- **Revenue Uplift:** Throughput increase from bottleneck elimination, NPI acceleration, OEE improvement
- **Working Capital:** WIP reduction, inventory accuracy improvement, warranty reserve release

#### 2e. Confidence Scoring
| Confidence Level | Criteria |
|-----------------|----------|
| 0.90-1.00 | Multiple corroborating signals + proprietary data + benchmark alignment |
| 0.80-0.89 | Two or more signals aligned + public/regulatory evidence |
| 0.70-0.79 | Single strong signal + segment-typical pattern match |
| <0.70 | Hypothesis only; requires discovery validation |

Apply subpack-specific confidence rules:
- Require torque data from calibrated tools for warranty-related hypotheses (0.85)
- Require CMM queue time measurement for metrology investment hypotheses (0.85)
- Require weld data from WPS records for structural weld hypotheses (0.85)
- Require cleanroom baseline data for EV battery contamination hypotheses (0.75)
- Require V&V process mapping for medical device validation hypotheses (0.80)

#### 2f. Map to Personas and Discovery Questions
Route insights to the most relevant discrete personas:
- **Quality Engineer:** SPC, CAPA, audit readiness, customer SCAR response
- **MRO Manager:** Tool condition monitoring, predictive maintenance, asset life
- **Production Scheduler:** Line balance, takt time, changeover, kitting sequence
- **Design Engineer:** Digital thread, DFM, CAM programming, ECO propagation
- **Warranty Analyst:** Field failure prediction, warranty cost per unit, recall risk
- **Plant Manager:** OEE, safety, quality KPIs, on-time delivery, workforce

Use the 20 vertical discovery questions to validate hypotheses during prospect engagement.

---

## Inheritance Map

### Master Skill to Load First
**`manufacturing-master-v1`** — Required prerequisite. This subpack is an additive overlay only.

### What This Subpack Adds Beyond the Master

| Category | Master | Subpack Addition |
|----------|--------|-----------------|
| **Personas** | 6 base personas | +6 vertical personas: MRO Manager, Production Scheduler, Quality Engineer, Design Engineer, Warranty Analyst, enhanced Plant Manager |
| **Pains** | Generic manufacturing pains | +18 discrete-specific pains: torque inconsistency, BOM chaos, CNC tool wear, line balancing, weld porosity, SMT defects, CMM bottleneck, casting defects, kitting errors, robot inefficiency, AM failures, sheet metal accuracy, EV battery contamination, Nadcap failures, medical V&V backlog, supply chain allocation, digital thread gap |
| **KPIs** | Base 19 KPIs (OEE, scrap, DPMO, COPQ, etc.) | +25 vertical KPIs: torque Cpk, BOM accuracy, CMM utilization, first article pass, SMT DPMO, weld reject, kitting accuracy, robot OEE, casting scrap, coating Cpk, ECO cycle, CAM programming, line balance efficiency, Nadcap findings, battery failure, AM build success, sheet metal first pass, tool condition index, traceability, V&V cycle, sequence compliance, NDT findings, particulate count, press brake setup, firmware flash |
| **Signal Rules** | 12 base rules | +20 vertical signal rules: torque calibration surge, BOM mismatch, spindle load anomaly, andon spike, weld deviation, reflow drift, CMM queue, porosity cluster, kitting error, robot collision, AM failure pattern, springback deviation, thermal runaway, Nadcap NC, FDA 483, allocation notice, CAD-CAM gap, AOI false positive, SCAR influx, particle excursion |
| **Formulas** | 8 base formulas | +15 vertical formulas: torque quality cost, BOM error cost, tool monitoring value, line balance value, welding quality value, SMT quality, CMM elimination, casting scrap reduction, kitting accuracy, robot optimization, EV battery contamination cost, Nadcap readiness, V&V acceleration, sheet metal setup, digital thread value |
| **Regulatory Factors** | Generic ISO/EPA/OSHA | +12 segment-specific: IATF 16949, AS9100D, Nadcap, FDA 21 CFR 820/UDI, DO-178C/DO-254, AEC-Q100/Q200, RoHS/REACH, CE Machinery Directive, UL/CSA |
| **Technology Systems** | Generic ERP/MES/SCADA | +15 vertical systems: PLM, CAD/CAM, CMM software, SPC, AOI/vision, robot programming, tool management, TCM, welding data monitoring, AM management, QMS, andon, EWI, digital twin |
| **Benchmarks** | Generic manufacturing | +20 segment-specific benchmarks |

### When to Use Master vs. Subpack

| Scenario | Recommendation |
|----------|---------------|
| Account is a discrete manufacturer with identifiable vertical segment | **Load master + this subpack** |
| Account is a general manufacturer without clear segment focus | **Master only** |
| Account spans multiple discrete segments (e.g., automotive + aerospace divisions) | **Master + this subpack** with segment-specific pain isolation |
| Account is a process manufacturer (chemicals, food, pharma bulk) | **Master + Process Manufacturing Subpack** (not this one) |
| Early prospect research with limited data | **Master only**, then escalate to subpack when segment signals emerge |

---

## Structured Output Template

When this skill is applied, the agent must produce a **Signals Analysis Enrichment** object with the following structure:

```json
{
  "skillApplied": "discrete-manufacturing-v1",
  "parentMaster": "manufacturing-master-v1",
  "analysisTimestamp": "2025-01-28T00:00:00Z",
  "accountSegment": "Automotive/EV | Aerospace & Defense | Electronics & Semiconductors | Medical Devices | Heavy Machinery | Industrial Equipment | Robotics | Rail/Marine",
  "detectedSignals": [
    {
      "signalId": "sig-dm-001",
      "signalName": "Torque Tool Calibration Overdue Surge",
      "rawEvidence": "string describing the detected evidence",
      "evidenceSource": "public | paid | proprietary | regulatory",
      "confidenceScore": 0.84,
      "linkedPains": ["pain-dm-001"],
      "linkedKPIs": ["kpi-torque-cpk", "kpi-warranty-cost"],
      "confirmationRequired": ["Warranty claim categorization", "Field failure reports", "Torque audit results"]
    }
  ],
  "mappedPains": [
    {
      "painId": "pain-dm-001",
      "painName": "Warranty Claim Spike from Fastener Torque Inconsistency",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "affectedPersonas": ["pers-quality", "pers-plant", "pers-cfo"],
      "symptomsMatched": ["symptom-1", "symptom-2"]
    }
  ],
  "kpiAssessment": [
    {
      "kpiId": "kpi-torque-cpk",
      "kpiName": "Torque Process Capability (Cpk)",
      "currentStateEstimate": "1.2",
      "benchmarkTarget": ">1.67",
      "gapSeverity": "HIGH | MEDIUM | LOW",
      "valueDriverLinks": ["vdrv-warranty-reduction", "vdrv-risk-reduction"]
    }
  ],
  "valueHypotheses": [
    {
      "formulaId": "vf-dm-001",
      "formulaName": "Torque Quality Failure Cost",
      "annualValueEstimate": 2500000,
      "valueCategory": "cost-savings | risk-reduction | revenue-uplift | working-capital",
      "paybackEstimateMonths": 3.2,
      "npv3Year": 1520000,
      "confidence": 0.82,
      "customerValidationRequired": ["Validate warranty root cause", "Confirm torque tool drift data"]
    }
  ],
  "personaMapping": [
    {
      "personaId": "pers-qual-eng",
      "personaName": "Quality Engineer",
      "relevanceScore": 0.95,
      "recommendedDiscoveryQuestions": ["dq-dm-001", "dq-dm-005"],
      "engagementPriority": 1
    }
  ],
  "regulatoryFactors": [
    {
      "regId": "reg-dm-002",
      "regulation": "IATF 16949:2016",
      "applicable": true,
      "complianceRiskLevel": "HIGH | MEDIUM | LOW",
      "penaltyForNonCompliance": "OEM exclusion; cannot bid new programs"
    }
  ],
  "buyingTriggers": [
    {
      "triggerId": "bt-dm-002",
      "trigger": "Warranty claim spike triggers executive-level quality review",
      "timeSensitivity": "HIGH",
      "budgetAuthority": "CFO/COO",
      "linkedPains": ["pain-dm-001", "pain-dm-014"]
    }
  ],
  "overallConfidence": 0.85,
  "sourceCoverage": ["public", "paid", "proprietary"],
  "nextSteps": [
    "Validate warranty claim root cause distribution",
    "Confirm torque tool calibration interval and drift data",
    "Schedule discovery call with Quality Engineer"
  ]
}
```

---

## Governance Metadata

| Attribute | Value |
|-----------|-------|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public, paid, proprietary, regulatory) |
| **Customer-Facing Approval Status** | APPROVED |
| **Review Owner** | Discrete Manufacturing Vertical Intelligence Team |
| **Last Updated** | 2025-01-28 |
| **Version** | 1.0.0 |
| **Agent Swarm ID** | swarm-discrete-mfg-v1 |
| **Parent Master Swarm ID** | swarm-manufacturing-master-v1 |

---

## Quick Reference

### Top 5 Pains (by prevalence and impact)

| Rank | Pain | Key Symptom | Primary Segments |
|------|------|-------------|-----------------|
| 1 | **Warranty Claim Spike from Fastener Torque Inconsistency** | Torque audit pass rate <95%, field failures | Automotive/EV, Heavy Machinery, Rail/Marine |
| 2 | **BOM Explosion and Revision Chaos** | ECO cycle >5 days, wrong-part assembly >1/month | Automotive/EV, Electronics, Aerospace, Medical |
| 3 | **CNC Machine Tool Wear and Dimensional Drift** | CMM drift correlating to tool life, no TCM | Aerospace, Medical, Industrial |
| 4 | **Electronics SMT Placement Accuracy and Solder Defects** | SMT DPMO >2,000, AOI false positives >10% | Electronics, Medical, Automotive |
| 5 | **EV Battery Module Assembly Contamination** | Particle count >Class 8, early-life failures >0.5% | Automotive/EV |

### Top 5 KPIs (by value driver linkage)

| Rank | KPI | Benchmark | Formula | Key Value Driver |
|------|-----|-----------|---------|-----------------|
| 1 | **SMT Defects Per Million Opportunities (DPMO)** | <1,000 | (Defects/Opportunities) x 1,000,000 | Yield Improvement, Scrap Reduction |
| 2 | **Torque Process Capability (Cpk)** | >1.67 | min[(USL-Mean)/(3σ), (Mean-LSL)/(3σ)] | Warranty Reduction, Risk Reduction |
| 3 | **CMM Utilization Rate** | 70-85% | (Measurement Time/Available Time) x 100 | Throughput Improvement, Cost Savings |
| 4 | **Welding Reject Rate** | <1.5% | (Failing Welds/Total Welds) x 100 | Scrap Reduction, Risk Reduction |
| 5 | **EV Battery Pack Early Failure Rate** | <0.1% | (Failures in 90 days/Total shipped) x 100 | Warranty Reduction, Risk Reduction |

### Top 3 Personas (by decision influence)

| Rank | Persona | Influence | Primary Concerns |
|------|---------|-----------|-----------------|
| 1 | **Quality Engineer** | Technical | SPC, CAPA effectiveness, audit readiness, customer SCAR response |
| 2 | **Plant Manager** | User | P&L, safety/quality KPIs, on-time delivery, workforce capability |
| 3 | **MRO Manager** | Technical | Unplanned downtime, spare parts optimization, asset life extension |

### Key Value Formulas (quick lookup)

| Formula ID | Name | Output Unit | Typical Annual Value Range |
|------------|------|-------------|---------------------------|
| VF-DM-001 | Torque Quality Failure Cost | $/year | $500K - $5M |
| VF-DM-006 | SMT Quality Improvement | $/year | $1M - $15M |
| VF-DM-007 | CMM Bottleneck Elimination | $/year | $1M - $15M |
| VF-DM-011 | EV Battery Assembly Contamination Cost | $/year | $5M - $50M |
| VF-DM-013 | Medical Device V&V Acceleration | $/year | $5M - $20M |

---

## Companion Files

| File | Purpose |
|------|---------|
| `value-pack.json` | Machine-readable pack definition (pains, KPIs, signals, formulas, personas, benchmarks, regulatory, tech systems, questions, objections, triggers) |
| `value-pack.md` | Human-readable vertical subpack documentation with worked examples |
| `signals-examples.ts` | TypeScript signal enrichment examples for OpenClaw integration |

---

*End of SKILL.md — Discrete Manufacturing Subpack (S1.1)*
