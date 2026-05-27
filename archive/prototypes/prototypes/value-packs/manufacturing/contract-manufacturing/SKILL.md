# Contract Manufacturing Subpack

## Skill Identity Block

- **skill_name**: Contract Manufacturing Subpack
- **description**: Vertical-specialized intelligence for CMOs, EMS, CDMOs, private label, co-packing, toll manufacturing, ODMs, and OEMs. Covers customer-mandated compliance, multi-site consolidation, customer audit readiness, margin compression, technology transfer, and multi-tenant operational models. Extends the Manufacturing Master ValuePack with segment-specific pains, KPIs, benchmarks, personas, signal rules, and value formulas.
- **version**: 1.0.0
- **domain**: manufacturing / contract manufacturing
- **pack_type**: subpack
- **parent_master**: manufacturing-master-v1

---

## Triggers

Use this skill when the user query involves any of the following natural language patterns:

1. **CMO customer audit readiness** — e.g., "help a CMO prepare for FDA customer audits", "audit finding closure delays"
2. **EMS margin compression** — e.g., "EMS losing margin on price-down mandates", "electronics contract manufacturer profitability"
3. **CDMO tech transfer delays** — e.g., "pharma CDMO technology transfer taking too long", "knowledge loss during tech transfer"
4. **Toll manufacturing capacity** — e.g., "toll manufacturer yield reconciliation", "multi-site toll operations consolidation"
5. **Customer concentration risk** — e.g., "top customer >70% of revenue", "contract renewal at risk"
6. **Customer portal and data exchange friction** — e.g., "too many customer portals", "manual scorecard prep"
7. **Co-packing or private label NPI delays** — e.g., "private label artwork approval backlog", "co-packing changeover downtime"
8. **Regulatory inspection readiness gaps** — e.g., "FDA 483 observations rising", "batch record review cycle too long"
9. **Customer-owned inventory disputes** — e.g., "consignment reconciliation issues", "excess obsolete customer inventory"
10. **Contract amendment overload** — e.g., "quality agreement management fragmentation", "SLA penalties increasing"
11. **On-Time-In-Full (OTIF) performance gaps** — e.g., "customer chargebacks for late delivery", "OTIF below 90%"
12. **Multi-site standardization** — e.g., "OEE variance across acquired sites", "ERP consolidation after M&A"

---

## Reasoning Flow

### Step 1: Load Parent Master First
Before applying this subpack, load **manufacturing-master-v1** to establish the base framework:
- Value Driver Framework (10 drivers: downtime, yield, scrap, throughput, labor, working capital, cost, revenue, risk, warranty)
- Base Persona Archetypes (17 personas from COO to OpEx)
- Evidence Source Taxonomy (12 source types)
- Formula Templates (25 base formulas)
- Signal Source Taxonomy (30 base signals)
- Benchmark Methodology (range-based with source attribution)
- Governance Framework (confidence scoring, approval gates, review cycles)

### Step 2: Identify Segment & Persona Fit
Determine which contract manufacturing segment(s) apply:
- **CMOs** (Contract Manufacturing Organizations) — pharma, chemical, consumer goods
- **EMS** (Electronics Manufacturing Services) — PCB assembly, box build, testing
- **CDMOs** (Contract Development & Manufacturing Organizations) — pharma/life sciences with R&D-to-manufacturing
- **Private Label** — branded products manufactured for retailers
- **Co-Packing** — packaging and assembly services
- **Toll Manufacturing** — processing customer-owned materials
- **ODMs** (Original Design Manufacturers) — design + manufacture
- **OEMs** (Original Equipment Manufacturers) — branded contract production

Identify which vertical personas are likely in scope:
- `pers-cm-001` Customer Quality Auditor (technical influence)
- `pers-cm-002` Contract/Commercial Manager (economic influence)
- `pers-cm-003` Site Director / GM (user influence)
- `pers-cm-004` Technology Transfer Manager (technical influence)
- `pers-cm-005` Customer Program Manager (user influence)
- `pers-cm-006` Costing Analyst / Quoting Manager (economic influence)

Also map to inherited master personas (COO, CFO, CIO, Quality, Plant Manager, etc.).

### Step 3: Detect & Interpret Signals
Apply the 18 vertical signal rules (`sig-cm-001` through `sig-cm-018`) to evidence:

| Signal | Confidence | Key Confirmation Evidence |
|---|---|---|
| Customer Audit Finding Surge | 0.85 | Audit reports, repeat finding trend, customer escalation |
| Customer Portal Integration Job Postings | 0.78 | Job boards, customer count growth, IT budget |
| Technology Transfer Staff Expansion | 0.82 | Hiring data, customer pipeline, capacity expansion |
| Quote Win Rate Decline | 0.80 | CRM data, competitor pricing, customer feedback |
| Customer Concentration Risk Disclosure | 0.88 | 10-K filing, revenue breakdown, renewal timeline |
| Multi-Site Acquisition or Expansion | 0.84 | Press releases, integration timeline, platform decisions |
| Regulatory Inspection Observation Increase | 0.90 | FDA 483/EMA findings, CAPA history, inspection schedule |
| Customer OTIF Penalty Increase | 0.83 | Earnings disclosures, penalty categorization, root cause |
| EBR Implementation Signal | 0.79 | Job postings for EBR/MES validation, vendor selection |
| Co-Packing Line Investment | 0.76 | CapEx announcements, line type, customer pipeline |
| Customer-Owned Inventory Write-Off | 0.81 | Financial disclosures, inventory aging, contract liability |
| Toll Manufacturing Margin Compression | 0.77 | Earnings, toll fee structure, yield variance |
| Serialization or Track-and-Trace Mandate | 0.87 | Regulatory deadline, customer scope, readiness |
| QBR Preparation Job Surge | 0.74 | Hiring patterns, customer count, report types |
| Capacity Commitment Miss Pattern | 0.80 | Operational data, demand volatility, planning maturity |
| Cold Chain or GDP Non-Compliance | 0.89 | Excursion events, monitoring system age, GDP audits |
| Customer Contract Renewal at Risk | 0.86 | Customer dual-sourcing, competitive bidding, satisfaction |
| Private Label NPI Pipeline Surge | 0.78 | Brief volume, NPI backlog, artwork capacity |

**Confidence Scoring Guidance:**
- A single signal with confidence ≥0.85 triggers hypothesis generation
- Two or more corroborating signals (sum or cluster) push overall confidence to HIGH
- Always triangulate with at least one primary signal + one confirmation source before presenting
- Downgrade confidence by 0.10 if evidence is >12 months old

### Step 4: Map Signals to Pains
For each confirmed signal, map to linked vertical pains (`pain-cm-001` through `pain-cm-018`).

Top pain-to-signal mapping:
- **Customer Audit Finding Closure Delays** (`pain-cm-001`) ← `sig-cm-001`, `sig-cm-007`
- **Technology Transfer Delays** (`pain-cm-003`) ← `sig-cm-003`, `sig-cm-018`
- **Customer Concentration & Renewal Risk** (`pain-cm-007`) ← `sig-cm-005`, `sig-cm-017`
- **OTIF Performance Gaps** (`pain-cm-017`) ← `sig-cm-008`, `sig-cm-015`
- **Regulatory Inspection Readiness** (`pain-cm-009`) ← `sig-cm-007`, `sig-cm-016`

### Step 5: Link to KPIs & Benchmarks
For each identified pain, pull the linked vertical KPIs (`kpi-cm-001` through `kpi-cm-022`) and compare against benchmarks (`bench-cm-001` through `bench-cm-018`).

Example mapping:
| Pain | Primary KPI | Typical Range | Benchmark | Gap = Value Oppty |
|---|---|---|---|---|
| Audit closure delays | `kpi-cm-001` Customer Audit Score | 60-95% | >90% | Score gap × contract value at risk |
| Tech transfer delays | `kpi-cm-004` Tech Transfer Cycle | 90-270 days | 90-150 days | Days saved × revenue/month |
| Customer concentration | `kpi-cm-003` Concentration Index | 0.15-0.80 | <0.25 | Volatility cost + pipeline value |
| OTIF gaps | `kpi-cm-021` OTIF to Customer | 75-98% | >98% | Chargeback + retention + expedite |

### Step 6: Quantify with Vertical Formulas
Apply the 13 vertical formulas (`vf-cm-001` through `vf-cm-013`) with validated customer inputs.

Value quantification discipline:
1. Every formula requires validated baseline and target inputs
2. Use ranges rather than false precision
3. Always connect to one of four value categories: Revenue Uplift, Cost Savings, Risk Reduction, Working Capital
4. Check confidence rules before presenting to customer
5. For subpack formulas, require customer-specific data (e.g., actual audit findings, contract values, transfer volumes)

### Step 7: Validate with Discovery Questions
Use the 18 vertical discovery questions (`dq-cm-001` through `dq-cm-018`) to validate hypotheses and gather inputs for formulas.

Key questions by persona:
- **Quality / Auditor**: "What is your average customer audit score, and what % are repeat findings?"
- **CIO / Site Director**: "How many ERP instances across sites, and how do you consolidate reporting?"
- **Tech Transfer Manager**: "Average tech transfer cycle time, and where are bottlenecks?"
- **Contract Manager**: "How many active quality agreements, and what's the amendment rate?"
- **CFO / Costing Analyst**: "Quote win rate, and how often do actuals exceed quotes by >10%?"
- **Customer Program Manager**: "How many monthly escalations, and top three root causes?"

### Step 8: Address Objections
Apply the 9 vertical objection patterns (`obj-cm-001` through `obj-cm-009`):
- "Customer mandates our current system" → Position as augmentation; demonstrate integration
- "Our customers won't pay for upgrades" → Quantify cost of inaction; offer gain-sharing
- "Each customer is too unique" → Standardize underlying processes with configurable overlays
- "We need customer approval for any change" → Map to customer benefit; pilot on non-critical product
- "Toll operations have zero margin" → Focus on reconciliation accuracy and dispute avoidance
- "Our data is too fragmented" → Propose customer-agnostic data lake with semantic layers
- "We're already compliant" → Reframe to competitive advantage; quantify cost of passing audits
- "Small site, can't justify enterprise solution" → Offer SaaS pricing; narrow scope
- "Customer is building in-house" → Position as indispensable; quantify switching cost

### Step 9: Prioritize Buying Triggers
Apply urgency/timing from the 14 vertical buying triggers (`bt-cm-001` through `bt-cm-014`):

| Urgency | Trigger | Timing |
|---|---|---|
| CRITICAL | Customer audit failure or conditional pass | 0-3 months |
| CRITICAL | Customer contract non-renewal notice | 0-6 months |
| CRITICAL | Regulatory inspection warning letter | 0-3 months |
| HIGH | New customer qualification mandate | 3-9 months |
| HIGH | Multi-site acquisition integration | 6-18 months |
| HIGH | Serialization regulatory deadline | 0-12 months |
| HIGH | Major customer price-down mandate | 0-6 months |
| HIGH | Customer scorecard decline trend | 0-6 months |
| MEDIUM | Technology transfer volume surge | 3-12 months |
| MEDIUM | ERP end-of-life or unsupported version | 6-18 months |

---

## Inheritance Map

### Master Skill to Load First
**`manufacturing-master-v1`** must be loaded before this subpack. The master provides:
- 10 base value drivers (downtime, yield, scrap, throughput, labor, working capital, cost, revenue, risk, warranty)
- 17 base personas (COO, CFO, CIO, Plant Manager, Quality, Maintenance, Planning, SC, EHS, HR, Engineering, CSM, CISO, Sustainability, Procurement, Logistics, OpEx)
- 12 evidence source types
- 25 base formula templates
- 30 base signal rules
- Range-based benchmark methodology
- Governance framework (confidence scoring, approval gates, review cycles)

### What This Subpack Adds
This subpack creates **vertical-specialized components** that extend the master:
- **18 Vertical Pains** (`pain-cm-001` through `pain-cm-018`) — segment-specific (CMO, EMS, CDMO, toll, co-pack, private label)
- **22 Vertical KPIs** (`kpi-cm-001` through `kpi-cm-022`) — customer-centric metrics (audit scores, portal latency, tech transfer cycle, QBR prep hours)
- **18 Vertical Signal Rules** (`sig-cm-001` through `sig-cm-018`) — contract-manufacturing-specific triggers
- **6 Vertical Personas** (`pers-cm-001` through `pers-cm-006`) — roles unique to contract mfg (Customer Quality Auditor, Contract Manager, Site Director, Tech Transfer Manager, Customer Program Manager, Costing Analyst)
- **13 Vertical Formulas** (`vf-cm-001` through `vf-cm-013`) — value quantification for audit remediation, ERP consolidation, tech transfer acceleration, inventory reconciliation, etc.
- **18 Vertical Benchmarks** (`bench-cm-001` through `bench-cm-018`) — contract-mfg-specific ranges
- **10 Regulatory Factors** (`reg-cm-001` through `reg-cm-010`) — FDA cGMP, ICH Q7, EU GDP, DSCSA, EU MDR, FSMA, conflict minerals, CBAM, customer ESG
- **13 Technology Systems** (`tech-cm-001` through `tech-cm-013`) — multi-tenant MES, customer portals, eQMS, EBR, serialization, CLM, etc.
- **18 Discovery Questions**, **9 Objection Patterns**, **14 Buying Triggers**

### Overridden Components
| Component | Override | Impact |
|---|---|---|
| `kpi-capacity-util` benchmark range | Widened from 50-95% to 45-90% | Reflects customer-demand-driven utilization volatility |
| `pain-022` Margin Compression | Expanded to EMS, toll, and CDMO specifics | More precise margin dynamics |
| `vdrv-revenue-uplift` | Extended with contract renewal value, toll fee escalation, qualification win rate | Captures contract-mfg revenue mechanisms |

### When to Use Master vs. Subpack
- **Use `manufacturing-master-v1` alone** when the prospect is a generic discrete or process manufacturer with no third-party production model
- **Use this subpack** when the prospect operates as CMO, EMS, CDMO, toll manufacturer, co-packer, private label, ODM, or OEM serving external customers
- **Always load both** for contract manufacturers; the subpack inherits and extends the master

---

## Structured Output Template

The expected JSON output for a Signals Analysis enrichment using this skill:

```json
{
  "skill_applied": "contract-manufacturing-v1",
  "parent_master": "manufacturing-master-v1",
  "analysis_timestamp": "2026-04-25T00:00:00Z",
  "confidence": "HIGH",
  "segments_identified": ["CMO", "CDMO"],
  "signals_detected": [
    {
      "signal_id": "sig-cm-001",
      "signal_name": "Customer Audit Finding Surge",
      "confidence": 0.85,
      "evidence": ["FDA 483 observations increased 60% YoY", "Customer X audit: 18 findings, 7 repeat"],
      "linked_pains": ["pain-cm-001", "pain-cm-004", "pain-cm-009"],
      "linked_kpis": ["kpi-cm-001", "kpi-capa-cycle-time", "kpi-cm-007"]
    }
  ],
  "pains_prioritized": [
    {
      "pain_id": "pain-cm-001",
      "pain_name": "Customer Audit Finding Closure Delays",
      "prevalence": "HIGH",
      "affected_personas": ["pers-quality", "pers-cm-001", "pers-cm-003", "pers-coo"],
      "value_driver": "vdrv-risk-reduction",
      "quantified_value": {
        "formula_id": "vf-cm-001",
        "annual_value_usd": 850000,
        "value_range_usd": [500000, 1200000],
        "confidence": 0.85
      }
    }
  ],
  "kpis_benchmarked": [
    {
      "kpi_id": "kpi-cm-001",
      "kpi_name": "Customer Audit Score",
      "current_value": 72,
      "target_value": 92,
      "benchmark_world_class": 95,
      "gap_opportunity": "20-point improvement worth $0.5M-$1.2M in contract retention"
    }
  ],
  "personas_engaged": [
    {
      "persona_id": "pers-cm-001",
      "persona_name": "Customer Quality Auditor",
      "influence": "technical",
      "priority_discovery_questions": ["dq-cm-001", "dq-cm-009"]
    }
  ],
  "buying_triggers_active": [
    {
      "trigger_id": "bt-cm-001",
      "trigger_name": "Customer audit failure or conditional pass",
      "urgency": "CRITICAL",
      "timing_months": "0-3"
    }
  ],
  "objections_anticipated": ["obj-cm-003", "obj-cm-007"],
  "regulatory_factors": ["reg-cm-001", "reg-cm-005"],
  "technology_gaps": ["tech-cm-003", "tech-cm-005", "tech-cm-012"],
  "next_best_actions": [
    "Schedule discovery call with Quality Director and Site GM",
    "Request customer audit scorecard for last 4 audits",
    "Validate CAPA cycle time and repeat finding rate",
    "Prepare eQMS + EBR consolidation business case"
  ]
}
```

---

## Governance Metadata

| Field | Value |
|---|---|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public filings, industry reports, benchmarks, regulatory databases, audit consortium data) |
| **Customer-Facing Approval Status** | NOT APPROVED — Internal intelligence only |
| **Review Owner** | contract-manufacturing-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-s1.4 |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

**Approval Gate Rules:**
- All value quantifications must pass confidence rules before external presentation
- Benchmark ranges must include source attribution
- Regulatory penalty values must be sourced from official guidance or legal review
- Customer-facing output requires explicit approval from review owner

---

## Quick Reference

### Top 5 Pains (by prevalence & business impact)

| # | Pain | ID | Prevalence | Primary Value Driver |
|---|---|---|---|---|
| 1 | **Customer Audit Finding Closure Delays** | `pain-cm-001` | HIGH | Risk Reduction + Revenue Uplift |
| 2 | **Technology Transfer Delays and Knowledge Loss** | `pain-cm-003` | HIGH | Revenue Uplift + Cost Savings |
| 3 | **Customer Concentration and Contract Renewal Risk** | `pain-cm-007` | HIGH | Revenue Uplift + Risk Reduction |
| 4 | **On-Time-In-Full (OTIF) Performance Gaps** | `pain-cm-017` | HIGH | Revenue Uplift + Cost Savings + Risk Reduction |
| 5 | **Regulatory Inspection Readiness Gaps** | `pain-cm-009` | HIGH | Risk Reduction + Cost Savings |

### Top 5 KPIs (most diagnostic)

| # | KPI | ID | Benchmark | Typical Range |
|---|---|---|---|---|
| 1 | **Customer Audit Score** | `kpi-cm-001` | >90% | 60-95% |
| 2 | **OTIF to Customer** | `kpi-cm-021` | >98% | 75-98% |
| 3 | **Technology Transfer Cycle Time** | `kpi-cm-004` | 90-150 days | 90-270 days |
| 4 | **Customer NCR Rate** | `kpi-cm-007` | <500 PPM | 100-5000 PPM |
| 5 | **Customer Concentration Index** | `kpi-cm-003` | <0.25 | 0.15-0.80 |

### Top 3 Personas (highest engagement priority)

| # | Persona | ID | Influence | Key Pressure |
|---|---|---|---|---|
| 1 | **Site Director / GM** | `pers-cm-003` | User | Multi-customer priority conflicts + EBITDA targets |
| 2 | **Customer Quality Auditor** | `pers-cm-001` | Technical | Repeat findings + regulatory follow-up obligations |
| 3 | **Contract/Commercial Manager** | `pers-cm-002` | Economic | Annual price-down mandates + SLA penalty exposure |

### Key Value Formulas

| Formula | ID | Output | Core Inputs |
|---|---|---|---|
| Customer Audit Finding Remediation Value | `vf-cm-001` | $/year | Findings count, cost/finding, contract value at risk, QBR hours |
| Technology Transfer Acceleration Value | `vf-cm-003` | $/year | Cycle days saved, revenue/transfer/month, transfer volume, ramp yield gain |
| OTIF Improvement and Chargeback Avoidance | `vf-cm-010` | $/year | OTIF % gain, revenue, chargeback rate, retention value, expedite cost |
| Customer-Owned Inventory Reconciliation Value | `vf-cm-005` | $/year | Dispute reduction, E&O avoidance, visibility labor savings |
| Batch Record Digitization Value | `vf-cm-009` | $/year | Review hours saved, error reduction, release acceleration cash benefit |

---

*End of Contract Manufacturing Subpack SKILL.md*
