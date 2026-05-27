# Process Manufacturing Subpack

## Skill Identity Block

| Field | Value |
|---|---|
| `skill_name` | Process Manufacturing Subpack |
| `description` | Vertical-specialized intelligence for process manufacturing covering chemicals, pharma, food/beverage, coatings, plastics, metals, pulp/paper, cement, and oil refining. Provides segment-specific pains, KPIs, signal rules, personas, formulas, benchmarks, and regulatory factors for enterprise advisory and sales engagements in formulation, blending, and chemical transformation operations. |
| `version` | 1.0.0 |
| `domain` | manufacturing / process-industries |
| `pack_type` | subpack |
| `parent_master` | manufacturing-master-v1 |

---

## Triggers

Auto-load this skill when queries match any of the following patterns:

1. **"pharma batch deviation"** - FDA 483 observations, cGMP compliance gaps, or batch record modernization in pharmaceutical operations
2. **"food safety recall prevention"** - FSMA compliance, lot traceability, electronic batch records, or contamination risk in food & beverage
3. **"chemical yield optimization"** - Yield shortfall to theoretical, PAT investment, APC/MPC deployment, or material balance gaps in chemicals or refining
4. **"cGMP compliance audit"** - ALCOA+ data integrity, electronic signatures, batch release acceleration, or CAPA cycle reduction
5. **"process safety management PSM"** - OSHA 1910.119, HAZOP revalidation, SIS modernization, or chemical plant asset integrity
6. **"reactor utilization scheduling"** - Batch reactor or fermenter underperformance, campaign optimization, or bioreactor throughput
7. **"environmental emissions reporting"** - EPA consent decree, Clean Air Act compliance, RCRA hazardous waste, or Scope 1/2/3 emissions automation
8. **"recipe formula version control"** - Multi-site recipe governance, ISA-88 batch management, or formula BOM synchronization
9. **"LIMS lab integration silos"** - Sample turnaround reduction, automatic out-of-spec alerting, or CoA generation automation
10. **"CIP SIP cleaning validation"** - Cleaning-in-place optimization, changeover time reduction, or sanitary validation in food/pharma
11. **"grade transition loss"** - Polymer or chemical campaign off-grade material, cross-contamination, or transition optimization
12. **"process manufacturing digital twin"** - APC, multivariate predictive control, digital twin, or Industry 4.0 in batch/continuous operations

---

## Reasoning Flow

### Step 1: Load Master First (Inheritance Protocol)
Always load `manufacturing-master-v1` before applying this subpack. The master provides:
- Base value driver framework (vdrv-downtime-reduction through vdrv-warranty-reduction)
- Base persona archetypes (pers-coo through pers-ops-ex, 17 personas)
- Evidence source taxonomy, formula templates, signal taxonomy, benchmark methodology, and governance framework

### Step 2: Segment Identification
Determine which process segment(s) apply to the target account:
- Chemicals & Specialty Chemicals
- Pharmaceuticals
- Food & Beverage
- Paints, Coatings & Adhesives
- Plastics & Polymers
- Metals & Steel
- Pulp & Paper
- Cement & Building Materials
- Oil Refining & Petrochemicals

Segment identification filters which pains, KPIs, signal rules, and regulatory factors are relevant. A multi-segment conglomerate (e.g., chemicals + refining) may activate multiple pain sets.

### Step 3: Signal Detection and Interpretation
Scan for raw signals from the 18 vertical-specific signal rules. High-priority signals include:
- **Regulatory enforcement signals** (sig-pm-001 FDA 483, sig-pm-005 EPA consent decree): Confidence 0.89-0.93; immediate buying trigger
- **Safety incidents** (sig-pm-003 CSB/OSHA events): Confidence 0.88; sector-wide investment wave predictor
- **Financial deterioration** (sig-pm-002 yield decline, sig-pm-014 margin compression): Confidence 0.80-0.84; cost-reduction program trigger
- **Strategic investments** (sig-pm-015 NDA submission, sig-pm-009 capacity expansion): Confidence 0.74-0.86; greenfield/validation window

**Confidence scoring guidance:**
- >= 0.90: CRITICAL confidence - act immediately, high urgency
- 0.80-0.89: HIGH confidence - strong hypothesis, confirm with 1-2 secondary signals
- 0.70-0.79: MEDIUM confidence - promising indicator, requires confirmation
- < 0.70: LOW confidence - exploratory, use for pattern building only

### Step 4: Pain-to-Persona Mapping
Map detected pains to the 6 vertical-specific personas and master personas:
- **pers-process-eng** (Process Engineer): Central technical buyer; involved in yield, deviation, parameter control, utility, and safety pains
- **pers-quality** (Quality Director): Regulatory readiness, batch records, deviations, spec breaches, LIMS gaps
- **pers-coo** (COO/Plant Operations): All operational pains; budget authority for >$500K investments
- **pers-batch-op** (Batch Operator): EBR adoption, alarm management, SOP adherence, training
- **pers-env-comp** (Environmental Compliance): EPA, water, emissions, waste, sustainability
- **pers-yield** (Yield Analyst): Yield optimization, material balance, PAT, spec control
- **pers-qa-metro** (QA Metrology Lead): LIMS integration, lab turnaround, CoA automation
- **pers-recipe** (Recipe Manager): Formula governance, version control, multi-site deployment

### Step 5: KPI Baseline and Benchmark Comparison
For each linked KPI, compare prospect performance against vertical benchmarks:
- Batch deviation rate: Pharma world-class <1.5%, chemicals average ~6%
- Yield variance: Pharma API target >-2%, specialty chemicals target >-3%
- Reactor utilization: Batch pharma benchmark >82%, chemicals >78%
- LIMS turnaround: Pharma world-class <8 hours, chemicals average ~24 hours
- Spec limit breaches: Benchmark <1% (vs. typical 0.5-8%)

Gaps exceeding 2x the benchmark range indicate acute pain and justify immediate engagement.

### Step 6: Value Hypothesis and Formula Application
Apply the 13 vertical-specific value formulas to quantify financial impact:
1. Select formula(s) linked to detected pains and KPI gaps
2. Populate inputs from publicly available or prospect-disclosed data
3. Calculate annual value range using confidence rules (validated MES data = 0.85, financial records = 0.90)
4. Cross-check against typical financial impact ranges from signals-examples.ts
5. Present as "conservative / expected / optimistic" scenarios

### Step 7: Buying Trigger Alignment
Match the account situation to the 14 buying triggers:
- CRITICAL triggers (0-6 months): FDA warning letter, product recall, EPA consent decree
- HIGH triggers (0-18 months): NDA approval, process safety incident, margin compression, water scarcity, PE acquisition
- MEDIUM triggers (6-24 months): ERP replacement, sustainability mandate, digital twin mandate, new executive hire

Urgency level determines sales motion speed, procurement path, and budget source.

---

## Inheritance Map

### Master Skill to Load First
**`manufacturing-master-v1`** must be loaded before this subpack. It provides:
- Universal manufacturing value drivers, personas, evidence taxonomy, and governance
- Base signal interpretation rules for generic manufacturing signals
- Cross-industry formula templates and benchmark methodology

### What This Subpack Adds
| Category | Master | This Subpack |
|---|---|---|
| Business Pains | Generic operational pains | 18 vertical-specific pains (batch deviation, yield shortfall, CIP inefficiency, LIMS silos, PSM gaps, etc.) |
| KPIs | Generic manufacturing KPIs | 23 process-specific KPIs with segment-adjusted benchmarks |
| Signal Rules | 30 base signals | 18 vertical-specialized signals (FDA 483, CSB incidents, PAT job postings, solvent spikes, etc.) |
| Personas | 17 base personas | 6 new personas (Process Engineer, Batch Operator, Environmental Compliance, Recipe Manager, Yield Analyst, QA Metrology Lead) |
| Formulas | 25 base templates | 13 vertical-specific formulas (batch deviation cost, yield improvement, EBR ROI, CIP optimization, etc.) |
| Benchmarks | Generic ranges | 18 segment-calibrated benchmarks (pharma deviation 1.5%, refining energy 150 kWh/bbl, etc.) |
| Regulatory | General compliance | 10 regs (cGMP, PSM, MACT, FSMA, RCRA, REACH, TSCA, etc.) |
| Technology | Generic systems | 13 process-specific systems (BMS, PAT, SIS, EMIS, APC, digital twin, etc.) |
| Buying Triggers | Generic procurement | 14 triggers with segment-specific urgency and budget source mapping |

### When to Use Master vs. Subpack
- **Use Master alone** when: The target is a general manufacturer with no clear process specialization; early qualification before segment identification; horizontal solution (e.g., generic ERP, basic MES) sale.
- **Use Subpack (with Master)** when: The target is in any of the 9 vertical segments; the conversation involves batch operations, chemical transformation, formulation, blending, or refining; regulatory compliance (FDA, EPA, OSHA) is mentioned; yield, deviation, or recipe control enters the discussion.

---

## Structured Output Template

```json
{
  "skillLoaded": "process-manufacturing-v1",
  "parentMasterLoaded": "manufacturing-master-v1",
  "analysisTimestamp": "2026-04-25T00:00:00Z",
  "segmentMatch": {
    "primarySegment": "Pharmaceuticals",
    "secondarySegments": ["Chemicals & Specialty Chemicals"],
    "segmentConfidence": 0.92
  },
  "signalsDetected": [
    {
      "signalId": "sig-pm-001",
      "signalName": "FDA Form 483 Observation Surge",
      "rawEvidence": ["FDA 483 issued 2026-03-15 citing 8 observations on batch records"],
      "confidenceScore": 0.93,
      "interpretedMeaning": "Critical cGMP compliance failure; electronic batch records, MES, and QMS modernization demand acute",
      "linkedPains": ["pain-pm-001", "pain-pm-004", "pain-pm-007"],
      "linkedKPIs": ["kpi-deviation-rate", "kpi-audit-findings", "kpi-capa-cycle-time"],
      "linkedBuyingTriggers": ["bt-pm-001", "bt-pm-004"],
      "requiresConfirmation": ["Warning letter follow-up", "Consent decree history", "Management quality commitment statements"]
    }
  ],
  "painsIdentified": [
    {
      "painId": "pain-pm-001",
      "painName": "Batch Deviation Causing Regulatory Enforcement",
      "severity": "HIGH",
      "prevalence": "HIGH",
      "affectedPersonas": ["pers-quality", "pers-process-eng", "pers-batch-op", "pers-coo"],
      "linkedKPIs": ["kpi-deviation-rate", "kpi-capa-cycle-time", "kpi-batch-efficiency", "kpi-audit-findings"],
      "linkedValueDrivers": ["vdrv-risk-reduction", "vdrv-yield-improvement", "vdrv-cost-savings"]
    }
  ],
  "kpisAnalyzed": [
    {
      "kpiId": "kpi-deviation-rate",
      "kpiName": "Batch Deviation Rate",
      "prospectValue": "12%",
      "benchmarkValue": "1.5%",
      "gap": "10.5 percentage points",
      "annualImpactEstimate": "$3,440,000"
    }
  ],
  "personasEngaged": [
    {
      "personaId": "pers-process-eng",
      "personaName": "Process Engineer",
      "relevanceScore": 0.95,
      "discoveryQuestions": ["dq-pm-001", "dq-pm-017"],
      "engagementPriority": 1
    }
  ],
  "valueHypotheses": [
    {
      "valueDriverId": "vdrv-batch-efficiency",
      "valueDriverName": "Batch Efficiency Improvement",
      "annualValueRange": { "min": 2000000, "max": 15000000, "currency": "USD" },
      "formulaApplied": "vf-pm-001",
      "confidence": 0.85,
      "keyAssumptions": ["Deviation root cause analysis is currently manual and paper-based", "Electronic batch records will halve transcription errors"]
    }
  ],
  "buyingTriggers": [
    {
      "triggerId": "bt-pm-001",
      "triggerName": "FDA Warning Letter or 483 Response Deadline",
      "urgencyLevel": "CRITICAL",
      "typicalTiming": "0-6 months",
      "budgetSource": "Compliance reserve or risk mitigation fund"
    }
  ],
  "regulatoryFactors": [
    {
      "regId": "reg-pm-001",
      "regulation": "FDA cGMP (21 CFR 210/211)",
      "applicability": "All pharmaceutical manufacturing, packaging, and holding",
      "penaltyExposure": "$100M+ consent decree potential; product seizure; criminal liability"
    }
  ],
  "recommendedActions": [
    "Confirm consent decree history and management quality commitment statements",
    "Quantify current batch deviation investigation hours and rejection rate",
    "Assess electronic batch record vendor landscape (Werum PAS-X, Siemens Opcenter, Emerson Syncade)",
    "Map LIMS integration status to MES/ERP for release cycle acceleration",
    "Prepare FDA 483 response timeline and validation-ready proposal"
  ],
  "overallConfidence": 0.88,
  "nextSteps": [
    "Schedule discovery call with Process Engineering and Quality leadership",
    "Request batch deviation trend data for last 12 months",
    "Validate budget authority with COO or VP Manufacturing"
  ]
}
```

---

## Governance Metadata

| Field | Value |
|---|---|
| **Confidence Level** | HIGH |
| **Source Coverage** | Mixed (public regulatory databases, membership-based industry standards, paid consulting reports, trade press) |
| **Customer-Facing Approval Status** | **false** - Not yet approved for direct customer-facing output without review |
| **Review Owner** | process-manufacturing-subpack-architect |
| **Last Updated** | 2026-04-25 |
| **Agent Swarm ID** | kimi-k2.6-elevated-swarm-s1.2 |
| **Parent Master Swarm ID** | kimi-k2.6-elevated-swarm |

### Evidence Source Confidence Breakdown
- **HIGH confidence sources:** FDA Warning Letter Database, EPA ECHO, CSB Reports, OSHA Establishment Search, AIChE Surveys, ISPE Baseline Guides, ISA-88/95 Standards, PDA Technical Reports
- **MEDIUM confidence sources:** Process Engineering Trade Publications, LNS Research, McKinsey Chemical Operations, Solomon Associates (paid/proprietary)
- **Confidence rules for formula inputs:** Validated MES/BMS data = 0.85; financial records = 0.90; time studies = 0.80; lab operations metrics = 0.80; HR records = 0.80; DOE-validated yield response = 0.75

---

## Quick Reference

### Top 5 Pains

| Rank | Pain ID | Pain Name | Prevalence | Top Segments |
|---|---|---|---|---|
| 1 | pain-pm-001 | Batch Deviation Causing Regulatory Enforcement | HIGH | Pharma, Chemicals, Food |
| 2 | pain-pm-002 | Recipe and Formula Version Control Gaps | HIGH | Chemicals, Food, Coatings, Plastics |
| 3 | pain-pm-003 | Yield Shortfall to Theoretical / Design | HIGH | Chemicals, Pharma, Refining, Plastics |
| 4 | pain-pm-004 | Manual Paper Batch Records and Data Integrity Gaps | HIGH | Pharma, Food, Chemicals |
| 5 | pain-pm-008 | Specification Limit Breaches and Off-Spec Product | HIGH | Chemicals, Plastics, Coatings, Refining |

### Top 5 KPIs

| Rank | KPI ID | KPI Name | Benchmark | Typical Range |
|---|---|---|---|---|
| 1 | kpi-deviation-rate | Batch Deviation Rate | <3% | 1-15% |
| 2 | kpi-yield-delta | Yield Variance to Theoretical | >-3% | -10 to -2% |
| 3 | kpi-reactor-util | Reactor Utilization | >80% | 55-85% |
| 4 | kpi-lims-turnaround | LIMS Sample Turnaround Time | <12 hours | 4-72 hours |
| 5 | kpi-spec-limit-breaches | Specification Limit Breach Rate | <1% | 0.5-8% |

### Top 3 Personas

| Rank | Persona ID | Persona Name | Role | Decision Influence |
|---|---|---|---|---|
| 1 | pers-process-eng | Process Engineer | Process Engineering Manager / Senior Process Engineer | Technical |
| 2 | pers-quality | Quality Director/VP | Quality Assurance / Regulatory Affairs | Technical / Budget |
| 3 | pers-coo | COO / Plant Operations Director | Chief Operating Officer / VP Manufacturing | Budget |

### Key Value Formulas

| Formula ID | Formula Name | Core Equation | Typical Annual Value |
|---|---|---|---|
| vf-pm-001 | Batch Deviation Cost Impact | `(Deviation Rate x Annual Batches x Avg Investigation Hours x Rate) + (Rejected Batches x Batch Revenue) + (Reprocessed Batches x Reprocessing Cost)` | $0.5M - $5M |
| vf-pm-002 | Yield Improvement Financial Value | `(Theoretical Yield - Baseline Actual Yield) x Annual Throughput x Material Cost x (1 - Scrap Recovery%) + Avoided Rework` | $1M - $8M |
| vf-pm-003 | Electronic Batch Records ROI | `(Labor Hours Eliminated x Hourly Rate) + (Release Acceleration Days x Daily Carry Cost) + (Deviation Reduction x Cost per Deviation) + Audit Prep Savings` | $0.5M - $2M |
| vf-pm-005 | Reactor Utilization Revenue Uplift | `(Target Utilization - Baseline) x Available Hours x Hourly Production Value x Market Absorption%` | $0.5M - $3M |
| vf-pm-008 | Environmental Compliance Automation Value | `(Manual Reporting FTE x Salary) + (Avoided Reportable Events x Avg Penalty) + Permit Renewal Savings + Emissions Trading Value` | $0.3M - $2M |
