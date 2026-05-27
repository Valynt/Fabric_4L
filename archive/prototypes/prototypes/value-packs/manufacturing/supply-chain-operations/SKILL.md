# SKILL.md — Supply Chain and Operations Subpack

## 1. Skill Identity Block

| Field | Value |
|---|---|
| **skill_name** | Supply Chain and Operations ValuePack |
| **description** | Vertical-specialized intelligence for supply chain and operations functions within manufacturing. Covers procurement, supplier quality, production planning, inventory optimization, warehousing, logistics, MRO, quality assurance, and EHS compliance. Extends the Manufacturing Master with signal rules, KPIs, benchmarks, value formulas, personas, and discovery workflows tuned for flow efficiency, cost optimization, risk mitigation, and operational excellence. |
| **version** | 1.0.0 |
| **domain** | Industry — Manufacturing |
| **pack_type** | subpack |
| **parent_master** | manufacturing-master-v1 |

---

## 2. Triggers — Natural Language Query Patterns

Auto-load this skill when user queries include:

1. **"supplier quality PPM spike"** — Detect supplier defect crises, incoming inspection backlogs, and customer scorecard penalties
2. **"MRO inventory optimization"** — Identify spare parts availability gaps, obsolescence, and emergency purchase spikes
3. **"warehouse labor productivity"** — Surface warehouse throughput, slotting, cube utilization, and order accuracy issues
4. **"logistics cost reduction"** — Trigger on freight inflation, modal optimization, carrier performance, and last-mile failures
5. **"S&OP process maturity"** — Assess demand planning, forecast accuracy, and supply-demand alignment gaps
6. **"cross-border logistics delay"** — Flag customs complexity, lead time variability, and trade policy disruptions
7. **"production planning constraints"** — Detect finite capacity gaps, plan attainment shortfalls, and APS needs
8. **"EHS compliance audit readiness"** — Surface incident reporting lags, permit-to-work gaps, and OSHA/EPA exposure
9. **"safety stock misalignment"** — Identify fill rate degradation, stockout concentration, and excess C-class inventory
10. **"procurement maverick spend"** — Find off-contract buying, catalog gaps, and supplier collaboration platform needs
11. **"backorder escalation"** — Detect customer penalties, expediting costs, and OTD failures
12. **"conflict minerals traceability"** — Flag CMRT gaps, smelter validation needs, and ESG transparency requirements

---

## 3. Reasoning Flow

### Step 1 — Master Pre-load (REQUIRED)
Before applying this subpack, load `manufacturing-master-v1` to establish:
- Base segment taxonomy (Discrete, Process, Automotive/EV, etc.)
- 10 value drivers and their calculation frameworks
- 17 base persona archetypes
- Evidence source taxonomy and confidence methodology
- Signal taxonomy and detection patterns
- Benchmark range methodology

### Step 2 — Prospect / Account Signal Detection
Scan for signals specific to SC&Ops functions:
- **Procurement signals:** Maverick spend ratio, contract compliance, SRM platform RFP, supplier portal usage
- **Supplier quality signals:** PPM spikes, scorecard update frequency, incoming inspection backlog
- **Planning signals:** APS job postings, S&OP maturity assessment, forecast MAPE, plan attainment
- **Inventory signals:** Fill rate, stockout rate, safety stock days, write-offs, obsolescence rate
- **Warehouse signals:** WMS replacement, space expansion, labor turnover, cube utilization
- **Logistics signals:** Freight rate index, carrier OTD, perfect order decline, cross-dock volume
- **MRO signals:** Emergency purchase spike, critical parts availability, asset downtime
- **EHS signals:** OSHA violations, EHS platform RFP, incident reporting lag, audit prep duration
- **Regulatory signals:** Tariff changes, UFLPA enforcement, REACH/Conflict Minerals inquiries

Use confidence thresholds 0.78–0.95 for geopolitical and logistics signals (higher than general manufacturing 0.65–0.85) due to real-time freight and customs data availability.

### Step 3 — Pain Mapping
Map detected signals to one or more of the 18 subpack pains:
- Signal `sco-sig-001` (Supplier PPM spike) → **sco-pain-001** or **sco-pain-005**
- Signal `sco-sig-002` (MRO emergency purchase spike) → **sco-pain-002**
- Signal `sco-sig-003` (Warehouse expansion) → **sco-pain-003**
- Signal `sco-sig-008` (Backorder rate >5%) → **sco-pain-010**, **sco-pain-017**
- Signal `sco-sig-015` (Tariff change) → **sco-pain-006**, **sco-pain-001**

Cross-reference with master pains to avoid duplication. If a signal maps to both master and subpack pains, prefer the subpack pain if the account has explicit SC&Ops roles.

### Step 4 — Persona Activation
Identify which personas are under pressure from the mapped pains:

| Persona | Primary Pains | Discovery Angle |
|---|---|---|
| Supplier Quality Engineer (pers-sqe) | sco-pain-001, 005, 013, 015 | PPM trending, VDA 6.3, scorecard automation |
| Supply Chain Planner (pers-scm) | sco-pain-004, 007, 010, 017 | MRP exceptions, finite capacity, forecast bias |
| EHS Manager (pers-ehs-mgr) | sco-pain-008 | OSHA TRIR, permit-to-work, incident lag |
| Warehouse Supervisor (pers-whs) | sco-pain-003, 009, 012, 018 | Cube utilization, pick path, dock-to-stock |
| MRO Buyer (pers-mro) | sco-pain-002 | Criticality ranking, availability rate |
| Demand Planner (pers-dp) | sco-pain-004, 010 | MAPE, FVA, consensus process |
| Logistics Manager (pers-logistics) | sco-pain-006, 009, 014 | Carrier scorecards, modal mix, freight audit |
| Procurement Manager (pers-proc) | sco-pain-011, 016 | Contract compliance, maverick redirect |

Supplement with master personas (pers-coo, pers-cfo, pers-cio, pers-quality, pers-maint, pers-plant) as secondary influencers.

### Step 5 — KPI Interpretation
For each mapped pain, pull the linked KPIs and compare against benchmarks:

| KPI | Typical Range | Benchmark | Confidence |
|---|---|---|---|
| Order Fill Rate | 85–99% | 97–99.5% | HIGH |
| MRO Parts Availability | 70–95% | 95–98% | HIGH |
| Warehouse Productivity | 50–200 units/hr | 150–300 units/hr | MEDIUM |
| Forecast MAPE (Consumer/Industrial) | 20–35% | 25% | HIGH |
| Dock-to-Stock Time | 2–72 hours | <4 hours | HIGH |
| Perfect Order Rate | 80–95% | 95–99% | HIGH |
| Backorder Rate | 0.5–10% | <1% | HIGH |
| Maverick Spend Ratio | 10–40% | <10% | HIGH |

Gap size = (Actual – Benchmark) or (Benchmark – Actual) depending on direction. Larger gaps indicate higher priority.

### Step 6 — Value Hypothesis Formation
Select the appropriate value formula from the 12 vertical formulas:

1. **sco-form-001** — Safety Stock Optimization (Working Capital + Revenue)
2. **sco-form-002** — Supplier PPM Reduction (Cost Savings + Risk)
3. **sco-form-003** — MRO Inventory Optimization (WC + Downtime Avoidance)
4. **sco-form-004** — Warehouse Productivity (Labor Cost + Accuracy)
5. **sco-form-005** — Freight Cost Reduction (Modal + Consolidation + Audit)
6. **sco-form-006** — Demand Planning Improvement (Inventory + Obsolescence + Expediting)
7. **sco-form-007** — EHS Incident Cost Reduction (TRIR + Insurance + Admin)
8. **sco-form-008** — Cross-Dock / Flow-Through (Handling + Storage + Carrying)
9. **sco-form-009** — Perfect Order Improvement (Retention + Chargebacks)
10. **sco-form-010** — Maverick Spend Reduction (Contract discount + Process)
11. **sco-form-011** — Schedule Attainment (Throughput + OT + Expediting)
12. **sco-form-012** — Dock-to-Stock Velocity (Detention + Production + Labor)

Apply confidence rules before presenting:
- HIGH (0.80–0.88): Validated baselines, historical data >12 months, customer penalty structure known
- MEDIUM (0.60–0.79): Partial data, estimated inputs, no customer scorecard details
- LOW (<0.60): No segmentation, no historical tracking, all estimates

### Step 7 — Confidence Scoring Guidance

| Condition | Confidence | Action |
|---|---|---|
| ≥3 signals confirmed with direct evidence | HIGH (0.85+) | Proceed to discovery call with full hypothesis |
| 2 signals, one with primary evidence | MEDIUM (0.70–0.84) | Qualify with discovery questions before quantification |
| 1 signal, inferred from segment prevalence | LOW (0.55–0.69) | Use as conversation opener, avoid specific claims |
| Signal conflicts with known account technology | MEDIUM–LOW | Flag for manual review; may indicate recent investment |

### Step 8 — Buying Trigger Timing
Align urgency with detected triggers:

| Trigger | Urgency | Timing |
|---|---|---|
| Supplier PPM crisis / scorecard red | HIGH | 0–6 months |
| Major downtime from MRO stockout | CRITICAL | 0–3 months |
| WMS end-of-life | HIGH | 6–18 months |
| Freight budget overrun >15% | HIGH | 0–6 months |
| OSHA serious violation | CRITICAL | 0–6 months |
| Customer mandates portal/traceability | HIGH | 3–12 months |
| Backorder rate triggers business review | HIGH | 0–6 months |
| Inventory write-off >2% | HIGH | 0–6 months |

---

## 4. Inheritance Map

### Master Skill to Load First
**`manufacturing-master-v1`** must be loaded before this subpack to provide:
- 5 manufacturing segment definitions
- 10 base value drivers (Revenue Uplift, Cost Savings, Risk Reduction, Working Capital, etc.)
- 17 base persona archetypes (COO, CFO, CIO, Plant Manager, Quality Director, etc.)
- Evidence source taxonomy and confidence framework
- Formula template structure and range-based benchmark methodology
- Signal taxonomy (detection patterns, confidence rules)
- Governance framework (source coverage, approval workflow)

### What This Subpack Adds
| Component | Master | Subpack Addition |
|---|---|---|
| Pains | 12 base | +18 SC&Ops-specific pains |
| KPIs | 15 base | +22 vertical-specialized KPIs |
| Value Drivers | 10 base | +5 vertical extensions (supplier risk, logistics cost, warehouse efficiency, planning accuracy, MRO optimization) |
| Personas | 17 base | +6 new personas (SQE, SC Planner, EHS Manager, Warehouse Supervisor, MRO Buyer, Demand Planner) |
| Formulas | 8 base templates | +12 vertical formulas with full expressions and worked examples |
| Benchmarks | 12 base | +18 vertical benchmarks |
| Signal Rules | 15 base | +18 vertical signal rules (higher confidence thresholds for logistics/geopolitical) |
| Technology Systems | 8 base | +14 SC&Ops-specific systems (APS, WMS, TMS, SRM, EAM, QMS, EHS, Control Tower, etc.) |
| Regulatory Factors | 6 base | +10 vertical regulations (Conflict Minerals, REACH, UFLPA, CBAM, FSMA, IATF 16949, etc.) |
| Discovery Questions | 12 base | +18 vertical questions |
| Objection Patterns | 6 base | +9 vertical responses |
| Buying Triggers | 8 base | +14 vertical triggers |

### When to Use Master vs. Subpack
| Scenario | Skill to Load |
|---|---|
| Broad manufacturing account intelligence, no specific SC&Ops signals | Master only |
| Prospect has SC&Ops roles, procurement/logistics/planing job postings, warehouse/MRO technology signals | **Both** — Master first, then this subpack |
| Explicit query about freight costs, MRO stockouts, supplier quality, warehouse productivity | **Both** — Subpack provides depth, Master provides context |
| Account is primarily EHS or quality-regulated (chemicals, food, medical devices) | **Both** — Subpack regulatory factors essential |
| Multi-site manufacturing with distribution centers | **Both** — Subpack warehouse/logistics coverage required |

---

## 5. Structured Output Template

When enriching a Signals Analysis for an account, output the following JSON structure:

```json
{
  "skill_loaded": "supply-chain-operations-v1",
  "parent_master": "manufacturing-master-v1",
  "account_segment": "Discrete Manufacturing | Process Manufacturing | Automotive/EV | etc.",
  "enrichment_timestamp": "2026-04-25T00:00:00Z",
  "signals_detected": [
    {
      "signal_id": "sco-sig-001",
      "signal_name": "Supplier PPM spike >3x baseline",
      "confidence": 0.88,
      "evidence": ["public citation or data point"],
      "linked_pains": ["sco-pain-001", "sco-pain-005"],
      "linked_kpis": ["kpi-supplier-ppm", "kpi-supplier-scorecard"],
      "affected_personas": ["pers-sqe", "pers-sc", "pers-coo"],
      "urgency": "HIGH",
      "timing_months": "0-6"
    }
  ],
  "pains_matched": [
    {
      "pain_id": "sco-pain-001",
      "pain_name": "Supplier PPM Spike from Geopolitical Disruption",
      "prevalence": "HIGH",
      "confidence": "HIGH",
      "symptoms_present": ["symptom 1", "symptom 2"],
      "value_driver_links": ["vdrv-risk-reduction", "vdrv-cost-savings"]
    }
  ],
  "kpis_assessed": [
    {
      "kpi_id": "kpi-supplier-ppm",
      "kpi_name": "Supplier PPM",
      "actual_value": "3200",
      "benchmark": "<500",
      "gap_direction": "above_benchmark",
      "gap_severity": "critical"
    }
  ],
  "personas_activated": [
    {
      "persona_id": "pers-sqe",
      "persona_name": "Supplier Quality Engineer",
      "priority": 1,
      "discovery_questions": ["question ref"],
      "pressure_points": ["PPM crisis", "customer scorecard red"]
    }
  ],
  "value_hypotheses": [
    {
      "formula_id": "sco-form-002",
      "formula_name": "Supplier PPM Reduction Financial Impact",
      "estimated_value_usd": 6000000,
      "value_range_usd": [4800000, 7200000],
      "confidence": 0.88,
      "value_category": "Cost Savings",
      "required_inputs_for_validation": ["baseline_ppm", "target_ppm", "annual_parts_received", "cost_per_defect"]
    }
  ],
  "buying_triggers": [
    {
      "trigger_id": "sco-bt-001",
      "trigger_name": "Supplier PPM crisis / customer scorecard red",
      "urgency": "HIGH",
      "timing": "0-6 months"
    }
  ],
  "technology_gaps": [
    {
      "system_category": "QMS - Supplier Module",
      "gap_indicator": "No automated supplier KPI collection",
      "likely_solutions": ["MasterControl", "ETQ", "SAP QM", "Arena"]
    }
  ],
  "regulatory_exposure": [
    {
      "regulation_id": "sco-reg-001",
      "regulation_name": "Conflict Minerals (Dodd-Frank / EU 2017/821)",
      "applicability": "Public companies using 3TG",
      "penalty": "SEC enforcement, customer exclusion",
      "relevant": true
    }
  ],
  "overall_confidence": 0.85,
  "next_best_actions": [
    "Schedule discovery call with SQE and SC Manager",
    "Request 12-month PPM trending data",
    "Validate customer penalty structure"
  ]
}
```

---

## 6. Governance Metadata

| Field | Value |
|---|---|
| **Confidence Level** | High |
| **Source Coverage** | Mixed (public filings, industry reports, benchmarks, government data, trade associations) |
| **Customer-Facing Approval Status** | No — internal intelligence only |
| **Review Owner** | supply-chain-ops-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm |
| **Parent Master Swarm ID** | manufacturing-master-swarm |

---

## 7. Quick Reference

### Top 5 Pains (by Prevalence & Impact)

| # | Pain | Prevalence | Key Symptom |
|---|---|---|---|
| 1 | **Supplier PPM Spike from Geopolitical Disruption** | HIGH | Supplier PPM >2,000 from alternate sources |
| 2 | **MRO Inventory Obsolescence and Stockouts** | HIGH | MRO parts availability <85% for critical assets |
| 3 | **Ineffective Demand Planning and S&OP** | HIGH | Forecast MAPE >40% at SKU level |
| 4 | **Production Planning System unable to Handle Constraints** | HIGH | Plan attainment <70% |
| 5 | **Freight Cost Inflation and Poor Modal Optimization** | HIGH | Freight cost growth >CPI + 5% annually |

### Top 5 KPIs

| # | KPI | Benchmark | Driver |
|---|---|---|---|
| 1 | **Order Fill Rate** | 97–99.5% | Revenue Uplift, Working Capital |
| 2 | **MRO Parts Availability** | 95–98% | Downtime Reduction, Cost Savings |
| 3 | **Warehouse Productivity** | 150–300 units/hr | Cost Savings, Throughput |
| 4 | **Perfect Order Rate** | 95–99% | Revenue Uplift, Cost Savings, Risk |
| 5 | **Supplier Scorecard Composite** | 85–95 | Risk Reduction, Cost Savings |

### Top 3 Personas

| # | Persona | Role | Trusted Evidence |
|---|---|---|---|
| 1 | **Supplier Quality Engineer (pers-sqe)** | Supplier Quality Assurance and Development | AIAG Core Tools, PPM trending, VDA 6.3, PPAP evidence |
| 2 | **Supply Chain Planner (pers-scm)** | Production Planning, Scheduling, Materials | APICS/ASCM, finite capacity benchmarks, MRP exception reports |
| 3 | **Warehouse Supervisor (pers-whs)** | DC/Warehouse Operations | WERC metrics, labor standards, RF accuracy data |

### Key Value Formulas

| Formula | Primary Output | Quick Estimate |
|---|---|---|
| **Safety Stock Optimization** (sco-form-001) | WC release + stockout reduction | ~4–6% of COGS in working capital release |
| **Supplier PPM Reduction** (sco-form-002) | Defect cost avoidance | $260/defect × defects avoided + penalties |
| **MRO Optimization** (sco-form-003) | Cash + downtime avoidance | 20–30% MRO inventory reduction + 10–15% downtime reduction |
| **Freight Cost Reduction** (sco-form-005) | Transportation savings | 8–15% of freight spend via modal + consolidation + audit |
| **Warehouse Productivity** (sco-form-004) | Labor + accuracy savings | 30–50% pick productivity improvement |

---

## 8. Companion Files

| File | Purpose |
|---|---|
| `value-pack.json` | Full structured data — pains, KPIs, formulas, benchmarks, personas, signals, regulations, technologies |
| `value-pack.md` | Human-readable reference — complete tables, discovery questions, objection patterns, worked examples, competitor factors |
| `signals-examples.ts` | (if present) TypeScript type definitions and example signal payloads for integration |

---

*End of SKILL.md — Supply Chain and Operations Subpack*
