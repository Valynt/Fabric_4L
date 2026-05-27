# OpenClaw Skill Definition: Manufacturing Master

---

## Skill Identity

| Field | Value |
|---|---|
| **skill_name** | Manufacturing Master |
| **description** | Foundation intelligence pack for the manufacturing sector covering discrete, process, advanced, contract, and supply chain operations. Provides signal-to-hypothesis reasoning, KPI benchmarking, persona profiling, and value quantification for manufacturing enterprise sales and advisory engagements. |
| **version** | 1.0.0 |
| **domain** | industry |
| **pack_type** | master |
| **parent_master** | N/A |

---

## Triggers

The following natural-language query patterns should auto-load this skill:

1. "Analyze a manufacturer" or "Assess a manufacturing company"
2. "Manufacturing downtime signals" or "OEE improvement opportunity"
3. "Automotive EV supplier pain points" or "EV battery manufacturing challenges"
4. "Pharma production compliance gaps" or "FDA warning letter response"
5. "Contract manufacturing margin pressure" or "EMS/CMO cost optimization"
6. "Supply chain disruption in manufacturing" or "Supplier quality failures"
7. "Plant floor digital transformation" or "MES modernization opportunity"
8. "Manufacturing labor shortage" or "Skilled trades turnover"
9. "Process manufacturing yield improvement" or "Batch efficiency optimization"
10. "Food safety traceability gaps" or "FSMA compliance readiness"
11. "Manufacturing working capital release" or "Inventory optimization"
12. "Industrial equipment warranty costs" or "Field failure reduction"

---

## Reasoning Flow

### Step 1: Segment Classification
Identify the prospect's manufacturing segment using available signals:
- **Discrete**: Assembly, fabrication, machining, countable items (Automotive, Aerospace, Electronics, Industrial Equipment)
- **Process**: Formulation, blending, chemical transformation (Chemicals, Pharma, Food, Metals, Cement)
- **Advanced**: Technology-intensive, automation, AI/ML, digital twins (Semiconductors, Batteries, Additive, Photonics)
- **Contract**: Third-party production for brand owners (CMO, EMS, CDMO, Private Label)
- **Supply Chain Overlay**: Cross-functional capabilities spanning segments (Planning, Logistics, Quality, EHS)

Load the appropriate subpack if segment is clear:
- `discrete-mfg-v1` | `process-mfg-v1` | `advanced-mfg-v1` | `contract-mfg-v1` | `supply-chain-v1`

### Step 2: Signal Detection & Interpretation
Detect raw signals from public and proprietary sources:
- SEC filings (10-K risk factors, margin trends, capex changes)
- Job postings (role surges indicate strategic pivots or gaps)
- Regulatory databases (FDA warning letters, OSHA violations, EPA citations)
- News/press releases (M&A, plant openings, recalls, executive changes)
- Earnings call transcripts (strategic priorities, pain admissions)
- Credit ratings and financial stress indicators

Apply signal interpretation rules with confidence scoring. Each signal links to 1-4 business pains and maps to relevant KPIs.

### Step 3: Pain Identification & Prioritization
Map confirmed signals to the master pain library (25 pains). Prioritize by:
1. **Prevalence** (HIGH > MEDIUM > LOW)
2. **Confidence** (based on signal strength and source quality)
3. **Segment applicability** (relevance to prospect's sub-segment)
4. **Financial impact potential** (linked value driver magnitude)

Top master pains by prevalence and confidence:
- Unplanned Equipment Downtime (pain-001)
- Poor First Pass Yield / High Rework (pain-002)
- Inventory Overstock and Obsolescence (pain-003)
- Production Schedule Disruption (pain-004)
- Supplier Quality Failures and Delays (pain-005)
- Labor Shortage and Skill Gaps (pain-006)
- Poor Production Visibility and Data Silos (pain-010)
- Ineffective Production Planning and APS (pain-020)

### Step 4: KPI Benchmarking
Compare prospect's known or estimated KPIs against benchmark ranges. Flag gaps >20% from segment-appropriate benchmarks:
- OEE: World Class 85% vs. Average 60-65%
- First Pass Yield: World Class 95-98.5% vs. Average 70-85%
- Inventory Turns: 6-12 turns/year benchmark
- On-Time Delivery: 95-99% world class vs. 75-90% average
- Cost of Poor Quality: 5-15% world class vs. 10-25% average
- Downtime Percentage: <15% benchmark

### Step 5: Persona Mapping
Identify which personas are affected by confirmed pains and their decision influence:
- **Economic buyers**: COO, CFO, VP Supply Chain, CHRO, CSO
- **Technical buyers**: CIO, VP Quality, Maintenance Director, CISO
- **User buyers**: Plant Manager, Planning Director, VP Logistics, OpEx Lead

Match persona pressures to their trusted evidence types for message tailoring.

### Step 6: Value Hypothesis & Quantification
Build value hypotheses using linked value drivers and formulas:
1. **Downtime Reduction**: `(Baseline Downtime - Target) × Hourly Production Value`
2. **OEE Improvement**: `(Target OEE - Baseline OEE) × Hours × Hourly Value × Margin`
3. **Scrap Reduction**: `(Baseline Scrap - Target) × Material Spend × (1 - Recovery %)`
4. **Inventory Cash Release**: `(Baseline Days - Target Days) × (COGS/365) × WACC %`
5. **Throughput Uplift**: `(Target Throughput - Baseline) × Price × Market Absorption`
6. **Warranty Reduction**: `Baseline Warranty × Reduction % + Avoided Recall Risk`
7. **Energy Cost Reduction**: `(Baseline Intensity - Target) × Output × Energy Price`
8. **Safety Cost Reduction**: `TRIR Reduction × Hours × (Direct + Indirect Cost) + Insurance`

Apply confidence rules before presenting:
- Require validated baseline and target inputs
- Use ranges, not false precision
- Connect to one of four categories: Revenue Uplift, Cost Savings, Risk Reduction, Working Capital

### Step 7: Buying Trigger Alignment
Map current or recent triggers to urgency and timing:
- CRITICAL (0-3 months): Product recall, cybersecurity incident, major unplanned downtime, regulatory warning
- HIGH (0-6 months): Margin compression, customer audit failure, supply chain disruption, energy cost spike
- MEDIUM (6-18 months): New ERP/MES selection, CEO/COO change, sustainability-linked financing

### Step 8: Discovery & Validation
Use persona-targeted discovery questions to validate hypotheses and fill data gaps. Prioritize questions linked to confirmed pains and KPIs.

### Step 9: Objection Anticipation
Prepare responses for common objections using linked pain context and reframe strategies.

### Confidence Scoring Guidance
- **0.90-1.00**: CRITICAL — Regulatory violations, product recalls, public financial distress
- **0.75-0.89**: HIGH — Multiple corroborating signals, earnings mentions, job posting surges
- **0.60-0.74**: MEDIUM — Single signal, indirect evidence, industry-wide pattern applied to prospect
- **0.40-0.59**: LOW — Speculative, requires validation through discovery
- **<0.40**: Do not present externally; flag for internal research

---

## Inheritance Map

This is a **master skill** — no parent to load. Subpacks extend this foundation:

| Subpack | Segment | What It Adds |
|---|---|---|
| `discrete-mfg-v1` | Discrete Manufacturing | BOM-specific pains, routing optimization, work-in-process tracking, automotive/aerospace regulatory depth |
| `process-mfg-v1` | Process Manufacturing | Recipe management, batch consistency, yield optimization, continuous flow, chemical/pharma regulatory depth |
| `advanced-mfg-v1` | Advanced Manufacturing | Digital twin, AI/ML adoption, semiconductor/battery specific KPIs, rapid NPI cycles, capital intensity |
| `contract-mfg-v1` | Contract Manufacturing | Margin compression dynamics, customer compliance, capacity utilization, EMS/CMO/CDMO specific benchmarks |
| `supply-chain-v1` | Supply Chain Overlay | Cross-segment logistics, planning, inventory, procurement, EHS specialization |

**When to use master vs. subpack:**
- Use **master** when segment is unknown, prospect spans multiple segments, or a broad manufacturing conversation is needed
- Use **subpack** when segment is confirmed and depth > breadth is required
- Always load master first; subpacks overlay and specialize

---

## Structured Output Template

```json
{
  "skillLoaded": "manufacturing-master-v1",
  "analysisTimestamp": "2026-04-25T00:00:00Z",
  "prospect": {
    "name": "string",
    "segment": "Discrete | Process | Advanced | Contract | Supply Chain Overlay",
    "subSegment": "string",
    "revenueRange": "string",
    "geography": "string"
  },
  "signalsDetected": [
    {
      "signalId": "sig-xxx",
      "signalName": "string",
      "source": "string",
      "confidence": 0.0,
      "interpretedMeaning": "string",
      "linkedPains": ["pain-xxx"],
      "linkedKPIs": ["kpi-xxx"],
      "requiresConfirmation": ["string"]
    }
  ],
  "painsPrioritized": [
    {
      "painId": "pain-xxx",
      "painName": "string",
      "prevalence": "HIGH | MEDIUM | LOW",
      "confidence": "HIGH | MEDIUM | LOW",
      "symptomsObserved": ["string"],
      "affectedPersonas": ["pers-xxx"],
      "linkedKPIs": ["kpi-xxx"],
      "linkedValueDrivers": ["vdrv-xxx"],
      "financialImpactEstimate": {
        "category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital",
        "annualRangeUsd": "$X - $Y",
        "confidence": 0.0
      }
    }
  ],
  "kpisBenchmarked": [
    {
      "kpiId": "kpi-xxx",
      "kpiName": "string",
      "prospectValue": "number or estimated",
      "benchmarkRange": "string",
      "gap": "+/- X%",
      "gapSeverity": "CRITICAL | SIGNIFICANT | MODERATE | MINOR"
    }
  ],
  "personasActivated": [
    {
      "personaId": "pers-xxx",
      "personaName": "string",
      "role": "string",
      "influence": "economic | technical | user",
      "primaryPains": ["pain-xxx"],
      "pressures": ["string"],
      "trustedEvidence": ["string"],
      "discoveryQuestions": ["string"]
    }
  ],
  "valueHypotheses": [
    {
      "valueDriverId": "vdrv-xxx",
      "valueDriverName": "string",
      "category": "Revenue Uplift | Cost Savings | Risk Reduction | Working Capital",
      "formula": "string",
      "inputs": {
        "baseline": "number",
        "target": "number",
        "unitValue": "number"
      },
      "calculatedAnnualImpact": "$X - $Y",
      "confidence": 0.0,
      "supportingPains": ["pain-xxx"]
    }
  ],
  "buyingTriggers": [
    {
      "triggerId": "bt-xxx",
      "triggerName": "string",
      "urgency": "CRITICAL | HIGH | MEDIUM",
      "timingWindow": "string",
      "linkedPains": ["pain-xxx"]
    }
  ],
  "objectionsAnticipated": [
    {
      "objection": "string",
      "responseStrategy": "string",
      "linkedPains": ["pain-xxx"]
    }
  ],
  "recommendedNextActions": [
    "Discovery call with [persona] on [pain]",
    "Validate [KPI] baseline through [source]",
    "Present [value hypothesis] with [evidence type]"
  ],
  "overallConfidence": 0.0,
  "masterConfidenceExplanation": "string"
}
```

---

## Governance Metadata

| Field | Value |
|---|---|
| **confidence_level** | HIGH |
| **source_coverage** | Mixed (public filings, industry reports, regulatory databases, benchmarks) |
| **customer_facing_approval** | NO — Internal intelligence only. Do not share raw signal confidence scores or speculative pain mappings externally without validation. |
| **review_owner** | manufacturing-master-architect |
| **last_updated** | 2026-04-25 |
| **agent_swarm_id** | kimi-k2.6-elevated-swarm |

---

## Quick Reference

### Top 5 Pains

| Rank | Pain | ID | Prevalence | Top Symptom |
|---|---|---|---|---|
| 1 | Unplanned Equipment Downtime | pain-001 | HIGH | OEE below 60%, emergency work orders increasing |
| 2 | Poor First Pass Yield / High Rework | pain-002 | HIGH | First pass yield <85%, scrap rate >3% |
| 3 | Inventory Overstock and Obsolescence | pain-003 | HIGH | Inventory turns <6x, write-offs >1% of revenue |
| 4 | Production Schedule Disruption | pain-004 | HIGH | On-time delivery <85%, schedule attainment <80% |
| 5 | Supplier Quality Failures and Delays | pain-005 | HIGH | Supplier PPM >500, lead time variability >30% |

### Top 5 KPIs

| Rank | KPI | ID | Formula | Benchmark |
|---|---|---|---|---|
| 1 | Overall Equipment Effectiveness | kpi-oee | Availability × Performance × Quality | 60-85% (world class 85%) |
| 2 | First Pass Yield | kpi-fpy | Units Passing First Inspection / Total Units × 100 | 90-98% |
| 3 | Inventory Turns | kpi-inv-turns | COGS / Average Inventory Value | 6-12 turns/year |
| 4 | On-Time Delivery | kpi-otd | On-Time Orders / Total Orders × 100 | 95-99% |
| 5 | Cost of Poor Quality | kpi-copq | (Internal + External + Appraisal + Prevention) / Revenue | 5-15% |

### Top 3 Personas

| Rank | Persona | ID | Role | Influence | Trusted Evidence |
|---|---|---|---|---|---|
| 1 | COO | pers-coo | EVP Operations | Economic | 10-K risk factors, McKinsey/BCG, peer benchmarking |
| 2 | Plant Manager | pers-plant | Plant Manager/GM | User | OEE benchmarks, lean case studies, shift reports |
| 3 | CFO | pers-cfo | CFO/VP Finance | Economic | Industry benchmarks, APQC, SEC filings, ROI models |

### Key Value Formulas

| Formula | Expression | Required Inputs |
|---|---|---|
| **Downtime Cost Avoidance** | `(Baseline Downtime - Target Downtime) × Hourly Production Value` | Baseline downtime hours, target hours, hourly production value |
| **OEE Improvement Value** | `(Target OEE - Baseline OEE) × Hours × Hourly Value × Margin` | Baseline OEE, target OEE, available hours, hourly value, margin % |
| **Inventory Cash Release** | `(Baseline Days - Target Days) × (COGS/365) × WACC %` | Baseline days, target days, COGS, WACC |
| **Scrap Cost Reduction** | `(Baseline Scrap - Target Scrap) × Material Spend × (1 - Recovery %)` | Baseline scrap rate, target rate, annual material spend, recovery rate |
| **Throughput Revenue Uplift** | `(Target Throughput - Baseline) × Price × Market Absorption` | Baseline throughput, target, unit price, market absorption % |

---

*This SKILL.md is auto-generated from the Manufacturing Master ValuePack. Refer to `value-pack.json` for complete structured data and `signals-examples.ts` for reference implementations.*
