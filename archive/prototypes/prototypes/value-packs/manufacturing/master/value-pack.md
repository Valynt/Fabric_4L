# Manufacturing Master ValuePack

**ID:** `manufacturing-master-v1` | **Version:** 1.0.0 | **Domain:** Industry | **Pack Type:** Master | **Last Updated:** 2026-04-25

## Overview

The Manufacturing Master ValuePack is the foundational intelligence asset for the manufacturing sector ValuePack ecosystem. It provides signal-to-hypothesis reasoning, KPI benchmarking, persona profiling, and value quantification for enterprise sales and advisory engagements across discrete, process, advanced, contract, and supply chain operations.

**Subpacks:**
- `discrete-mfg-v1` — Discrete Manufacturing
- `process-mfg-v1` — Process Manufacturing
- `advanced-mfg-v1` — Advanced Manufacturing
- `contract-mfg-v1` — Contract and Outsourced Manufacturing
- `supply-chain-v1` — Supply Chain and Operations Specialties

---

## Type System / Interface Definitions

The following TypeScript-style interfaces define the schema for all components in this pack.

```typescript
interface Taxonomy {
  id: string;
  segment: string;
  subSegments: string[];
  description: string;
  typicalRevenueRange: string;
  geographicConcentration: string[];
}

interface BusinessPain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  affectedSegments: string[];
  affectedPersonas: string[];
  linkedKPIs: string[];
  linkedValueDrivers: string[];
  prevalence: "HIGH" | "MEDIUM" | "LOW";
  confidence: "HIGH" | "MEDIUM" | "LOW";
  sources: string[];
}

interface KPIDefinition {
  id: string;
  name: string;
  formula: string;
  unit: string;
  typicalRange: string;
  benchmarkRange: string;
  valueDriverLinks: string[];
  segmentApplicability: string[];
  calculationFrequency: string;
}

interface ValueDriverMap {
  id: string;
  name: string;
  category: "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
  description: string;
  linkedKPIs: string[];
  affectedPersonas: string[];
  valueMechanism: string;
}

interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: Array<{ condition: string; confidence: number }>;
  exampleCalculation: string;
}

interface Benchmark {
  id: string;
  name: string;
  value: string;
  range: string;
  unit: string;
  source: string;
  sourceType: string;
  segmentApplicability: string[];
  geographicScope: string;
  companySizeScope: string;
  confidence: string;
  dateSourced: string;
}

interface SignalInterpretationRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number;
  requiredConfirmationSignals: string[];
}

interface PersonaProfile {
  id: string;
  name: string;
  role: string;
  seniority: string;
  goals: string[];
  pressures: string[];
  trustedEvidence: string[];
  dislikedClaims: string[];
  decisionInfluence: "economic" | "technical" | "user";
}

interface BuyingTrigger {
  id: string;
  name: string;
  triggerEvent: string;
  urgencyLevel: string;
  typicalTiming: string;
  affectedSegments: string[];
  linkedPains: string[];
  procurementImplications: string;
}

interface TechnologySystem {
  id: string;
  name: string;
  category: string;
  description: string;
  typicalVendors: string[];
  segmentApplicability: string[];
  integrationPoints: string[];
}

interface RegulatoryFactor {
  id: string;
  name: string;
  regulation: string;
  applicability: string;
  deadline: string;
  penaltyForNonCompliance: string;
  affectedSegments: string[];
}

interface DiscoveryQuestion {
  id: string;
  name: string;
  questionText: string;
  targetPersonas: string[];
  linkedPains: string[];
  linkedKPIs: string[];
}

interface ObjectionPattern {
  id: string;
  name: string;
  description: string;
  responseStrategy: string;
  linkedPains: string[];
  typicalPersonas: string[];
}

interface CompetitiveFactor {
  id: string;
  factorName: string;
  description: string;
  impact: string;
  applicableSegments: string[];
}

interface ValueDomain {
  id: string;
  name: string;
  description: string;
  primaryValueDriver: string;
  linkedKPIs: string[];
  typicalFinancialImpact: string;
  applicableSegments: string[];
}

interface EvidenceSourceDefinition {
  id: string;
  name: string;
  description: string;
  sourceType: string;
  accessibility: string;
  updateFrequency: string;
  confidence: string;
  useFor: string[];
}

type MasterValuePack = {
  id: string;
  name: string;
  version: string;
  domain: "industry";
  packType: "master";
  description: string;
  taxonomies: Taxonomy[];
  pains: BusinessPain[];
  kpis: KPIDefinition[];
  valueDrivers: ValueDriverMap[];
  formulas: ValueFormula[];
  benchmarks: Benchmark[];
  signalRules: SignalInterpretationRule[];
  evidenceSources: EvidenceSourceDefinition[];
  buyingTriggers: BuyingTrigger[];
  personas: PersonaProfile[];
  discoveryQuestions: DiscoveryQuestion[];
  objections: ObjectionPattern[];
  technologySystems: TechnologySystem[];
  regulatoryFactors: RegulatoryFactor[];
  competitorFactors: CompetitiveFactor[];
  valueDomains: ValueDomain[];
  subpacks: string[];
  governance: {
    sourceCoverage: "public" | "mixed";
    confidence: "low" | "medium" | "high";
    lastUpdated: string;
    approvedForCustomerFacingOutput: boolean;
    reviewOwner: string;
    agentSwarmId: string;
  };
};
```

---

## 1. Taxonomies

### 1.1 Discrete Manufacturing
- **Sub-segments:** Automotive/EV, Aerospace & Defense, Industrial Equipment, Electronics & Semiconductors, Appliances & Consumer Durables, Medical Devices, Heavy Machinery, Robotics & Automation Equipment, Rail/Marine/Transportation Equipment
- **Description:** Production of distinct, countable items through assembly, fabrication, or machining. Characterized by BOM complexity, routing optimization, and work-in-process tracking.
- **Revenue Range:** $50M - $50B
- **Geographic Concentration:** Midwest US, Southern Germany, Japan, South Korea, Eastern China, Mexico

### 1.2 Process Manufacturing
- **Sub-segments:** Chemicals & Specialty Chemicals, Pharmaceuticals, Food & Beverage, Paints/Coatings/Adhesives, Plastics & Polymers, Metals & Steel, Pulp & Paper, Cement & Building Materials, Oil Refining & Petrochemicals
- **Description:** Production through formulation, blending, or chemical transformation. Characterized by recipe/formula management, batch consistency, yield optimization, and continuous flow operations.
- **Revenue Range:** $100M - $100B
- **Geographic Concentration:** US Gulf Coast, Northwest Europe, Middle East, China Coastal Provinces, India Gujarat/Maharashtra

### 1.3 Advanced Manufacturing
- **Sub-segments:** Additive Manufacturing/3D Printing, Semiconductor Fabrication, Battery Manufacturing, Clean Energy Equipment, Precision Machining, Photonics & Optics, Nanomaterials, Composite Materials, Smart Factory/Industry 4.0
- **Description:** Technology-intensive manufacturing leveraging automation, digital twins, AI/ML, and novel materials. High R&D intensity, rapid innovation cycles, and capital-intensive operations.
- **Revenue Range:** $20M - $10B
- **Geographic Concentration:** Taiwan, South Korea, US West Coast/Midwest, Israel, Switzerland, Japan

### 1.4 Contract and Outsourced Manufacturing
- **Sub-segments:** CMOs, EMS, CDMOs, Private Label Manufacturing, Packaging & Co-Packing, Toll Manufacturing, ODMs, OEMs
- **Description:** Third-party production for brand owners. Margin pressure, capacity utilization optimization, and customer compliance are defining characteristics.
- **Revenue Range:** $10M - $30B
- **Geographic Concentration:** China Pearl River Delta/Yangtze Delta, Mexico Border, Eastern Europe, Vietnam, Malaysia, Thailand

### 1.5 Supply Chain and Operations Specialties
- **Sub-segments:** Procurement & Sourcing, Supplier Quality Management, Production Planning & Scheduling, Inventory Optimization, Warehouse Operations, Logistics & Transportation, Maintenance & Reliability (MRO), Quality Assurance & Control, Safety & Environmental Compliance (EHS), Workforce Scheduling & Labor Planning
- **Description:** Cross-functional capabilities spanning all manufacturing segments. Focus on flow efficiency, cost optimization, risk mitigation, and operational excellence.
- **Revenue Range:** N/A - function overlay
- **Geographic Concentration:** Global - co-located with manufacturing concentrations

---

## 2. Business Pains (25)

| ID | Pain | Prevalence | Confidence | Top Segments |
|---|---|---|---|---|
| pain-001 | Unplanned Equipment Downtime | HIGH | HIGH | Discrete, Process, Advanced, Contract |
| pain-002 | Poor First Pass Yield / High Rework | HIGH | HIGH | All manufacturing |
| pain-003 | Inventory Overstock and Obsolescence | HIGH | HIGH | All |
| pain-004 | Production Schedule Disruption | HIGH | HIGH | Discrete, Process, Contract |
| pain-005 | Supplier Quality Failures and Delays | HIGH | HIGH | All |
| pain-006 | Labor Shortage and Skill Gaps | HIGH | HIGH | All |
| pain-007 | Energy Cost Escalation and Carbon Pressure | MEDIUM | HIGH | Process, Metals, Cement, Chemicals |
| pain-008 | Regulatory Compliance and Audit Burden | HIGH | HIGH | Pharma, Food, Chemicals, Medical, Aerospace |
| pain-009 | Warranty and Field Failure Costs | MEDIUM | HIGH | Automotive, Industrial, Appliances, Medical |
| pain-010 | Poor Production Visibility and Data Silos | HIGH | HIGH | All |
| pain-011 | Inefficient Changeover and Setup Times | MEDIUM | HIGH | Discrete, Food, Chemicals, Packaging |
| pain-012 | Capacity Constraint and Bottleneck Management | MEDIUM | HIGH | Discrete, Process, Contract |
| pain-013 | Forecast Inaccuracy and Demand Volatility | HIGH | HIGH | All |
| pain-014 | High Logistics and Transportation Costs | MEDIUM | HIGH | Food, Chemicals, Appliances |
| pain-015 | Workforce Safety and Incident Frequency | MEDIUM | HIGH | Discrete, Process, Metals, Cement |
| pain-016 | Inadequate Preventive Maintenance Programs | HIGH | HIGH | Discrete, Process, Advanced |
| pain-017 | Long Production Lead Times | MEDIUM | HIGH | Discrete, Process, Contract |
| pain-018 | Product Traceability and Genealogy Gaps | HIGH | HIGH | Pharma, Food, Medical, Automotive, Aerospace |
| pain-019 | Raw Material Cost Volatility and Sourcing Risk | MEDIUM | HIGH | Chemicals, Metals, Food, Plastics, Automotive |
| pain-020 | Ineffective Production Planning and APS | HIGH | HIGH | Discrete, Process, Contract |
| pain-021 | Poor New Product Introduction (NPI) Ramp | MEDIUM | MEDIUM | Automotive, Electronics, Medical, Consumer |
| pain-022 | Contract Manufacturing Margin Compression | HIGH | HIGH | CMO, EMS, CDMO, Private Label |
| pain-023 | MES/SCADA Legacy Modernization Debt | MEDIUM | HIGH | Discrete, Process, Advanced |
| pain-024 | Quality Management System Inefficiency | HIGH | HIGH | Pharma, Medical, Aerospace, Food |
| pain-025 | Sustainability Reporting and Scope 3 Complexity | MEDIUM | MEDIUM | All |

**Full Pain Details:** See `value-pack.json` for complete metadata including symptoms, affected personas, linked KPIs, and sources.

---

## 3. KPI Definitions (42)

| ID | KPI | Formula | Unit | Typical Range | Benchmark |
|---|---|---|---|---|---|
| kpi-oee | Overall Equipment Effectiveness | (Good Units × Ideal Cycle Time) / Planned Production Time OR Availability × Performance × Quality | % | 50-85% | 60-85% |
| kpi-mtbf | Mean Time Between Failures | Total Operating Time / Number of Failures | hours | 100-2000 | 500-1500 |
| kpi-mttr | Mean Time To Repair | Total Repair Time / Number of Repair Events | hours | 0.5-24 | 1-8 |
| kpi-downtime-pct | Downtime Percentage | (Downtime Hours / Scheduled Production Hours) × 100 | % | 5-30% | 5-15% |
| kpi-fpy | First Pass Yield | (Units Passing First Inspection / Total Units Produced) × 100 | % | 70-98% | 90-98% |
| kpi-scrap-rate | Scrap Rate | (Scrap Units / Total Units Started) × 100 | % | 0.5-10% | 0.5-3% |
| kpi-copq | Cost of Poor Quality | (Internal + External + Appraisal + Prevention Costs) / Revenue × 100 | % revenue | 5-30% | 5-15% |
| kpi-dpmo | Defects Per Million Opportunities | (Defects / Opportunities) × 1,000,000 | DPMO | 100-100,000 | <3,400 |
| kpi-inv-turns | Inventory Turns | COGS / Average Inventory Value | turns/year | 3-15 | 6-12 |
| kpi-inv-days | Inventory Days of Supply | Average Inventory / (COGS / 365) | days | 15-120 | 20-60 |
| kpi-wip-ratio | WIP to Total Inventory | WIP Value / Total Inventory Value × 100 | % | 10-40% | 15-30% |
| kpi-obsolescence-rate | Inventory Obsolescence | (Write-off / Average Inventory) × 100 | % | 0.5-5% | <1% |
| kpi-otd | On-Time Delivery | (On-Time Orders / Total Orders) × 100 | % | 60-98% | 95-99% |
| kpi-schedule-attainment | Schedule Attainment | (Actual Production / Planned Production) × 100 | % | 50-95% | 85-95% |
| kpi-throughput | Throughput | Total Units / Production Time | units/hour | Varies | Best demonstrated |
| kpi-expedite-cost | Expediting Cost | Rush Orders + Premium Freight + Overtime | $ or % COGS | 0.1-3% | <0.5% |
| kpi-supplier-ppm | Supplier PPM | (Defective Parts / Total Received) × 1,000,000 | PPM | 50-5000 | <500 |
| kpi-supplier-otd | Supplier On-Time | (On-Time Deliveries / Total Deliveries) × 100 | % | 70-98% | 95-98% |
| kpi-sqcr | Supplier Quality Complaint | (Quality Complaints / Total POs) × 100 | % | 0.5-10% | <2% |
| kpi-supplier-risk-score | Supplier Risk Score | Weighted composite of financial, operational, geopolitical risk | 0-100 | 20-80 | <40 |
| kpi-labor-prod | Labor Productivity | Output Value / Labor Hours | $/hour | Varies | Top quartile |
| kpi-ot-rate | Overtime Rate | (Overtime Hours / Total Hours) × 100 | % | 5-40% | <15% |
| kpi-turnover | Employee Turnover | (Employees Leaving / Average Headcount) × 100 | % annual | 5-50% | 8-15% |
| kpi-training-hours | Training Hours per Employee | Total Training Hours / Average Headcount | hours/year | 5-80 | 20-40 |
| kpi-energy-intensity | Energy Intensity | Total Energy / Output Units | kWh/unit | Varies | Best-in-class |
| kpi-carbon-intensity | Carbon Intensity | Total CO2e / Output Units | kg CO2e/unit | Varies | SBTi trajectory |
| kpi-utility-cost | Utility Cost per Unit | Total Utilities / Units Produced | $/unit | Varies | Top quartile |
| kpi-scope1-2-emissions | Scope 1 & 2 Emissions | Direct + purchased energy emissions | MT CO2e | Varies | SBTi-aligned |
| kpi-audit-findings | Regulatory Audit Findings | Count of findings per audit cycle | count | 0-25 | 0-3 |
| kpi-compliance-cost | Compliance Cost Ratio | Total Compliance / Revenue × 100 | % revenue | 0.5-8% | 1-3% |
| kpi-incident-rate | Incident Rate (TRIR) | (Recordable Injuries × 200,000) / Total Hours | per 100 FTE | 1.0-8.0 | <2.0 |
| kpi-capa-cycle-time | CAPA Cycle Time | Average Days from CAPA Open to Close | days | 15-180 | <30 |
| kpi-warranty-cost | Warranty Cost % | (Warranty Costs / Revenue) × 100 | % | 0.1-5% | <1% |
| kpi-field-failure-rate | Field Failure Rate | (Field Failures / Units in Service) × 100 | % | 0.05-3% | <0.5% |
| kpi-csat | Customer Satisfaction | Survey-based composite | 0-100 | 50-85 | >80 |
| kpi-data-latency | Production Data Latency | Event occurrence to report availability | minutes | 1-1440 | <5 |
| kpi-system-uptime | System Uptime | (Available Time / Scheduled Time) × 100 | % | 85-99.9% | >99.5% |
| kpi-decision-cycle-time | Decision Cycle Time | Signal detection to management action | hours | 1-168 | <4 |
| kpi-changeover-time | Changeover Time | Time to switch product runs | minutes | 15-480 | <60 |
| kpi-batch-efficiency | Batch Efficiency | (Actual Yield / Theoretical Yield) × 100 | % | 80-98% | >95% |
| kpi-bottleneck-util | Bottleneck Utilization | (Actual Output / Bottleneck Capacity) × 100 | % | 60-100% | 85-95% |
| kpi-capacity-util | Overall Capacity Utilization | (Actual Output / Maximum Sustainable) × 100 | % | 50-95% | 80-90% |

---

## 4. Value Drivers (10)

| ID | Value Driver | Category | Description |
|---|---|---|---|
| vdrv-downtime-reduction | Downtime Reduction | Cost Savings | Reducing unplanned equipment downtime through predictive maintenance, reliability engineering, and faster repair |
| vdrv-yield-improvement | Yield Improvement | Cost Savings | Improving first pass yield and reducing defect rates through process control, SPC, and quality analytics |
| vdrv-scrap-reduction | Scrap/Rework Reduction | Cost Savings | Systematic reduction of scrap, rework, and concession processing through root cause analysis |
| vdrv-throughput-improvement | Throughput Improvement | Revenue Uplift | Increasing effective production output without proportional capital investment |
| vdrv-labor-prod | Labor Productivity | Cost Savings | Increasing output per labor hour through automation, skills, and workflow optimization |
| vdrv-wc-improvement | Working Capital | Working Capital | Reducing cash tied in inventory, receivables, and WIP through better planning |
| vdrv-cost-savings | Direct Cost Reduction | Cost Savings | Broad operational cost reduction including energy, logistics, maintenance, overhead |
| vdrv-revenue-uplift | Revenue Uplift | Revenue Uplift | Top-line growth from improved delivery, capacity, NPI speed, and customer service |
| vdrv-risk-reduction | Risk/Compliance Reduction | Risk Reduction | Reducing regulatory, safety, supply chain, and quality risks |
| vdrv-warranty-reduction | Warranty Cost Reduction | Cost Savings | Reducing post-sale failures and warranty claims through design and process improvement |

---

## 5. Value Formulas (25)

See `value-pack.json` for complete formula definitions. Key formulas include:

1. **Downtime Cost Avoidance** — `(Baseline Downtime - Target Downtime) × Hourly Production Value`
2. **OEE Improvement Value** — `(Target OEE - Baseline OEE) × Hours × Hourly Value × Margin`
3. **Scrap Cost Reduction** — `(Baseline Scrap - Target Scrap) × Material Spend × (1 - Recovery %)`
4. **Inventory Reduction Cash Release** — `(Baseline Days - Target Days) × (COGS/365) × WACC %`
5. **Warranty Cost Reduction** — `Baseline Warranty × Reduction % + Avoided Recall Risk`
6. **Throughput Revenue Uplift** — `(Target Throughput - Baseline) × Price × Market Absorption`
7. **Energy Cost Reduction** — `(Baseline Intensity - Target) × Output × Energy Price`
8. **Predictive Maintenance ROI** — `Avoided Downtime + (PM Cost - Predictive Cost) + Asset Life Extension`
9. **Labor Productivity Improvement** — `Productivity Gain / Target × Labor Cost + Overtime Reduction`
10. **Safety Incident Cost Reduction** — `TRIR Reduction × Hours × (Direct + Indirect Cost) + Insurance`

Each formula includes required inputs, applicable segments, confidence rules, and example calculations.

---

## 6. Benchmarks (35)

| Benchmark | Value | Range | Source | Confidence |
|---|---|---|---|---|
| World Class OEE | 85% | 82-90% | OEE Industry Standard | HIGH |
| Average OEE - Discrete | 60% | 50-65% | Deloitte 2024 | HIGH |
| Average OEE - Process | 65% | 55-75% | Siemens | HIGH |
| First Pass Yield - Automotive | 95% | 92-98% | AIAG | HIGH |
| FPY - Pharma | 98.5% | 97-99.5% | FDA Guidance | HIGH |
| Inventory Turns - Consumer | 8 | 6-12 | APQC | HIGH |
| Inventory Turns - Food | 12 | 8-20 | CSCMP | HIGH |
| OTD - World Class | 98% | 95-99% | SCOR | HIGH |
| OTD - Average | 85% | 75-90% | Oliver Wight | HIGH |
| Scrap - Electronics | 1.5% | 0.5-3% | IPC | HIGH |
| COPQ - Average | 15% | 10-25% | ASQ | HIGH |
| COPQ - World Class | 5% | 3-7% | ASQ | HIGH |
| Labor Productivity Growth | 2.5% | 0-4% | BLS | HIGH |
| TRIR - Average | 2.8 | 2.0-4.0 | BLS | HIGH |
| TRIR - World Class | 0.5 | 0.1-1.0 | NSC | HIGH |
| Maintenance Cost - Best | 5% | 3-7% of RAV | SMRP | HIGH |
| PM Ratio | 80% | 70-85% | Plant Engineering | MEDIUM |
| Capacity Utilization US | 78% | 70-85% | Federal Reserve | HIGH |
| Changeover Time - SMED | <10 min | 5-30 | Shingo | HIGH |
| Forecast MAPE - Consumer | 25% | 15-35% | Gartner | HIGH |
| Supplier On-Time | 95% | 90-98% | ISM | HIGH |
| Supplier PPM - World Class | 100 | 50-250 | ASQ | HIGH |
| Warranty - Automotive | 1.5% | 1-3% revenue | Warranty Week | HIGH |
| Freight % Revenue | 8% | 5-12% | CSCMP | HIGH |
| Energy Intensity - Cement | 900 | 800-1100 kWh/ton | IEA | HIGH |
| Energy Intensity - Steel | 500 | 400-600 kWh/ton | World Steel | HIGH |
| CMO Gross Margin | 15% | 10-20% | IQVIA | HIGH |
| EMS Operating Margin | 3.5% | 2-6% | Circana | HIGH |
| Smart Factory Adoption | 35% | 20-50% | McKinsey | MEDIUM |
| OEE - Contract Mfg | 65% | 55-75% | Gartner | MEDIUM |

---

## 7. Signal Interpretation Rules (30)

| ID | Signal | Confidence | Linked Pains |
|---|---|---|---|
| sig-001 | Job surge for maintenance roles | 0.72 | Downtime, PM gaps |
| sig-002 | 10-K supply chain risk mention | 0.85 | Supplier failures, sourcing risk |
| sig-003 | Earnings margin compression | 0.80 | Downtime, quality, inventory, energy |
| sig-004 | FDA warning letter | 0.92 | Compliance, traceability, QMS |
| sig-005 | OSHA serious violation | 0.75 | Safety, compliance |
| sig-006 | ESG score downgrade | 0.78 | Energy, sustainability |
| sig-007 | Warranty reserve increase >20% | 0.82 | Warranty, NPI |
| sig-008 | Inventory growth > revenue growth | 0.76 | Inventory, forecast, planning |
| sig-009 | Capex cut >15% | 0.70 | Downtime, PM, legacy |
| sig-010 | New CIO from outside | 0.68 | Visibility, legacy |
| sig-011 | New COO from ops excellence | 0.74 | Changeover, bottleneck, lead time |
| sig-012 | Customer concentration >30% | 0.71 | Margin compression, capacity |
| sig-013 | R&D up, patents flat | 0.66 | NPI inefficiency |
| sig-014 | Union negotiation/strike | 0.73 | Labor, safety |
| sig-015 | Energy price spike >30% | 0.79 | Energy costs |
| sig-016 | Supplier bankruptcy | 0.88 | Sourcing crisis |
| sig-017 | Product recall | 0.90 | Quality, traceability |
| sig-018 | Sustainability-linked financing | 0.77 | Emissions, ESG |
| sig-019 | ERP implementation announced | 0.82 | Visibility, planning, legacy |
| sig-020 | PE acquisition | 0.85 | Downtime, inventory, labor, capacity |
| sig-021 | Cybersecurity incident | 0.86 | Visibility, legacy |
| sig-022 | Tariff/trade policy change | 0.75 | Sourcing, logistics |
| sig-023 | Board supply chain expert added | 0.70 | Sourcing, forecast |
| sig-024 | Gross margin declining 3+ quarters | 0.78 | Quality, inventory, energy, logistics |
| sig-025 | Production expansion announced | 0.72 | NPI, labor, planning |
| sig-026 | Backlog growth >30% | 0.76 | Bottleneck, throughput |
| sig-027 | IoT/digital twin job postings | 0.68 | Visibility, downtime |
| sig-028 | Quality certification suspension | 0.91 | Compliance, QMS |
| sig-029 | Increasing contract manufacturer use | 0.74 | Margin compression, supplier quality |
| sig-030 | NPS decline | 0.71 | Warranty, delivery |

---

## 8. Persona Profiles (17)

| ID | Persona | Role | Seniority | Influence | Trusted Evidence |
|---|---|---|---|---|---|
| pers-coo | COO | COO/EVP Operations | C-Suite | Economic | 10-K risk factors, McKinsey/BCG, peer benchmarking |
| pers-cfo | CFO | CFO/VP Finance | C-Suite | Economic | Industry benchmarks, APQC, SEC filings |
| pers-cio | CIO | CIO/CTO | C-Suite | Technical | Gartner MQs, reference architectures |
| pers-plant | Plant Manager | Plant Manager/GM | VP/Director | User | OEE benchmarks, lean case studies |
| pers-quality | VP Quality | VP QA/Director | VP/Director | Technical | FDA data, ISO certifications, ASQ |
| pers-maint | Maintenance Director | Dir Maintenance | Director/Manager | Technical | SMRP, RCM studies, OEM bulletins |
| pers-plan | Planning Director | Dir Production Planning | Director/Manager | User | APICS/SCOR, IBF benchmarks |
| pers-sc | VP Supply Chain | VP SC/Procurement | VP/Director | Economic | CSCMP, Gartner, ISM |
| pers-ehs | EHS Director | Dir EHS/Safety | Director/Manager | Technical | BLS, OSHA, NSC |
| pers-hr | VP HR | CHRO/VP HR | VP/Director | Economic | BLS, NAM, compensation surveys |
| pers-eng | VP Engineering | VP Eng/R&D | VP/Director | Technical | PDMA, Stage-Gate, patents |
| pers-csm | Customer Success | VP CS/Aftermarket | Director/Manager | User | Warranty Week, JD Power |
| pers-ciso | CISO | CISO/VP Security | VP/Director | Technical | NIST, SANS, CISA |
| pers-sustainability | CSO | CSO/VP Sustainability | VP/Director | Economic | CDP, SBTi, GRI |
| pers-proc | CPO | CPO/VP Procurement | VP/Director | Economic | ISM, Hackett, commodity indices |
| pers-logistics | VP Logistics | VP Logistics/Distribution | Director/Manager | User | CSCMP, WERC, freight indices |
| pers-ops-ex | OpEx Lead | OpEx Director/Lean MBB | Director/Manager | User | Shingo, Lean Enterprise Institute |

---

## 9. Buying Triggers (25)

| ID | Trigger | Urgency | Timing |
|---|---|---|---|
| bt-001 | Major unplanned downtime | HIGH | 0-3 months |
| bt-002 | New ERP/MES selection | HIGH | 6-18 months |
| bt-003 | New plant/line commissioning | HIGH | 12-24 months |
| bt-004 | Regulatory warning letter | CRITICAL | 0-6 months |
| bt-005 | PE acquisition | HIGH | 3-12 months |
| bt-006 | CEO/COO change | MEDIUM | 6-18 months |
| bt-007 | IPO preparation | MEDIUM | 12-24 months |
| bt-008 | Customer audit failure | HIGH | 0-6 months |
| bt-009 | Product recall | CRITICAL | 0-3 months |
| bt-010 | Margin compression crisis | HIGH | 0-6 months |
| bt-011 | Cybersecurity incident | CRITICAL | 0-3 months |
| bt-012 | Union negotiation | MEDIUM | 0-12 months |
| bt-013 | Supply chain disruption | HIGH | 0-6 months |
| bt-014 | Sustainability-linked financing | MEDIUM | 0-12 months |
| bt-015 | Customer sustainability scorecard | MEDIUM | 6-18 months |
| bt-016 | Aging workforce retirement | MEDIUM | 12-36 months |
| bt-017 | Capacity/backlog crisis | HIGH | 0-12 months |
| bt-018 | M&A integration | HIGH | 6-24 months |
| bt-019 | NPI launch delay | HIGH | 0-6 months |
| bt-020 | Digital transformation mandate | MEDIUM | 12-36 months |
| bt-021 | Tariff/trade policy change | MEDIUM | 0-12 months |
| bt-022 | Energy cost spike | HIGH | 0-6 months |
| bt-023 | Competitive factory opening | MEDIUM | 6-18 months |
| bt-024 | ISO/AS certification loss | CRITICAL | 0-6 months |
| bt-025 | Customer price-down mandate | HIGH | 0-12 months |

---

## 10. Technology Systems (20)

| ID | System | Category | Key Vendors |
|---|---|---|---|
| tech-001 | ERP | Business Management | SAP, Oracle, MS Dynamics, Infor |
| tech-002 | MES | Production Management | Siemens, Dassault, Rockwell, AVEVA |
| tech-003 | SCADA | Process Control | Siemens, AVEVA, GE, Ignition |
| tech-004 | DCS | Process Control | Honeywell, Yokogawa, Emerson, ABB |
| tech-005 | APS | Planning Optimization | Siemens, Dassault, PlanetTogether, o9 |
| tech-006 | WMS | Logistics | Blue Yonder, Manhattan, SAP EWM |
| tech-007 | TMS | Logistics | Blue Yonder, SAP TM, Oracle, project44 |
| tech-008 | QMS | Quality | MasterControl, IQVIA, SAP QM, EtQ |
| tech-009 | LIMS | Quality | LabWare, Thermo, STARLIMS |
| tech-010 | EAM/CMMS | Maintenance | SAP, IBM Maximo, Infor, IFS |
| tech-011 | Condition Monitoring | Maintenance | SKF, Emerson, Fluke, Uptake |
| tech-012 | IIoT Platform | Digital Infrastructure | Siemens MindSphere, PTC, GE |
| tech-013 | PLM | Engineering | Siemens, Dassault, PTC, Aras |
| tech-014 | SCP/S&OP | Planning | o9, Kinaxis, Blue Yonder, Anaplan |
| tech-015 | Additive Manufacturing | Advanced Mfg | EOS, Stratasys, 3D Systems, HP |
| tech-016 | Digital Twin | Advanced Mfg | Siemens, Dassault, Ansys, AVEVA |
| tech-017 | Robotics/Cobots | Automation | FANUC, ABB, KUKA, Universal Robots |
| tech-018 | AI Quality Inspection | Quality | Cognex, Keyence, Landing AI |
| tech-019 | EHS Platform | Compliance | Intelex, Enablon, VelocityEHS |
| tech-020 | Batch/Recipe Mgmt | Process Control | Siemens BRAUMAT, Emerson, Werum |

---

## 11. Regulatory Factors (20)

| ID | Regulation | Applicability | Penalty |
|---|---|---|---|
| reg-001 | OSHA 29 CFR 1910 | All US facilities | $15,625-$156,259 per violation |
| reg-002 | EPA Clean Air Act | Major emitters | $37,500+/day |
| reg-003 | EPA Clean Water Act | Discharging facilities | $66,086+/day |
| reg-004 | FDA cGMP (21 CFR 210/211) | Pharma, medical devices | $100M+ potential |
| reg-005 | FSMA (21 CFR 117) | Food facilities | $1,000-$500,000 + recall |
| reg-006 | EPA RCRA | Hazardous waste | $76,764/day |
| reg-007 | ISO 9001:2015 | Certification seekers | Customer exclusion |
| reg-008 | IATF 16949:2016 | Automotive suppliers | OEM exclusion |
| reg-009 | AS9100D | Aerospace suppliers | Contract ineligibility |
| reg-010 | EPA GHG Reporting | >25,000 MT CO2e | $37,500+/violation |
| reg-011 | SEC Climate Disclosure | Public companies | Shareholder litigation |
| reg-012 | OSHA PSM | High-hazard chemicals | $156,259 + criminal |
| reg-013 | EU REACH | Chemicals in EU | Market exclusion |
| reg-014 | Conflict Minerals (Dodd-Frank) | Public companies using 3TG | SEC enforcement |
| reg-015 | ISO 14001:2015 | Environmental cert seekers | Audit findings |
| reg-016 | NIST CSF | Critical infrastructure | CISA enforcement |
| reg-017 | EU CBAM | Imports to EU (steel, cement, etc.) | Carbon border tariff |
| reg-018 | CA Prop 65 | Products in California | $2,500+/day + lawsuits |
| reg-019 | EPA TSCA | Chemical manufacturers | $50,000/day |
| reg-020 | EU MDR | Medical devices in EU | CE loss, market exclusion |

---

## 12. Discovery Questions (20)

1. **OEE Measurement** — How do you currently measure and report OEE, and what is your plant-by-plant variation? *(COO, Plant Manager)*
2. **Unplanned Downtime Root Cause** — What percentage of unplanned downtime events have identified root causes? *(Plant Manager, Maintenance)*
3. **Quality Cost Visibility** — Can you quantify Cost of Poor Quality as % of revenue across four cost categories? *(Quality, CFO)*
4. **Inventory Segmentation** — How do you segment inventory and what % is slow-moving or obsolete? *(CFO, Supply Chain)*
5. **Schedule Attainment Drivers** — What are the top three reasons schedules are not attained? *(Planning, Plant)*
6. **Supplier Risk Exposure** — How many direct materials are single-sourced? *(Supply Chain, Procurement)*
7. **Labor Turnover and Skills** — What is annual turnover for skilled trades vs operators? *(HR, Plant)*
8. **Energy and Carbon Baseline** — Do you have validated Scope 1, 2, and 3 baselines? *(Sustainability, COO)*
9. **Compliance Audit Burden** — How many audits annually and what is prep/remediation cycle time? *(Quality, EHS)*
10. **Warranty Field Data** — How do you track field failure data and time-to-root-cause? *(Customer Success, Quality)*
11. **System Integration Landscape** — How many disconnected systems on the plant floor? *(CIO, Plant)*
12. **Changeover Measurement** — Have you implemented SMED? What is average changeover time by family? *(Plant, OpEx)*
13. **Bottleneck Identification** — Do you know your system constraint? *(COO, Planning)*
14. **Forecast Process Maturity** — What is your SKU-level MAPE? *(Planning, COO)*
15. **Logistics Cost Structure** — How do you allocate freight costs by modal mix? *(Logistics, CFO)*
16. **Maintenance Strategy** — What % is reactive vs preventive vs predictive? *(Maintenance, COO)*
17. **Lead Time Composition** — How is manufacturing lead time distributed across queue/setup/run/wait/move? *(Planning, Plant)*
18. **Traceability Coverage** — What % of volume has full electronic traceability? *(Quality, CIO)*
19. **CMO Margin Pressure** — How do you balance customer price-downs with input inflation? *(CFO, COO)*
20. **Digital Transformation Readiness** — Where are you on the Industry 4.0 maturity curve? *(CIO, COO)*

---

## 13. Objection Patterns (10)

| Objection | Response Strategy |
|---|---|
| We already have a system | Acknowledge; highlight integration gaps and data silos; offer complementary assessment |
| No budget this year | Reframe as self-funding through operational savings or working capital release |
| Show me the ROI | Provide peer case study; offer paid proof-of-concept with predefined metrics |
| We can build this internally | Compare 5-year TCO including maintenance and opportunity cost |
| Too disruptive to operations | Propose phased rollout on non-critical line; offer parallel running |
| We need to focus on other priorities | Connect to stated strategic priorities from earnings/press |
| Your solution is too expensive | Reframe total cost of inaction; offer modular pricing |
| We need to see it work here | Offer site-specific pilot with success criteria |
| Our data is not ready | Offer data readiness assessment; describe cleansing services |
| We tried this before and it failed | Acknowledge; diagnose root cause (usually change management); differentiate approach |

---

## 14. Competitor Factors (7)

1. **Vertical-Specific Platform Depth** — Specialized vendors command premium in pharma, food, aerospace
2. **Incumbent ERP/MES Lock-in** — SAP, Siemens, Dassault leverage relationships to bundle adjacent solutions
3. **Regional SI Relationships** — Local integrators influence vendor selection through trust
4. **Open Source/Low-Cost Alternatives** — Pressure pricing for basic connectivity; differentiate on analytics depth
5. **Hyperscaler Cloud Entry** — AWS, Azure, GCP building manufacturing verticals; compete at application layer
6. **PE-Backed Consolidation** — Full-suite platforms through acquisition pressure point solutions
7. **Customer Co-Development** — Large manufacturers building proprietary solutions; mid-market opportunity

---

## 15. Value Domains (10)

| Domain | Typical Financial Impact |
|---|---|
| Downtime Reduction | 15-25% unplanned downtime reduction; 5-15% OEE improvement |
| Yield Improvement | 2-5pp FPY improvement; 10-30% COPQ reduction |
| Scrap/Rework Reduction | 20-40% scrap/rework cost reduction |
| Throughput Improvement | 10-20% throughput increase; deferred capex $5M-$50M |
| Labor Productivity | 10-25% productivity gain; 20-40% OT reduction |
| Inventory/Working Capital | 20-40% inventory reduction; $5M-$100M cash release |
| Energy Efficiency | 10-30% energy cost reduction; 15-25% carbon improvement |
| Supplier Risk Reduction | 50-70% disruption reduction; 10-20% quality improvement |
| Warranty Cost Reduction | 20-40% warranty cost reduction; field failure halved |
| Compliance/Audit Readiness | 40-60% audit prep reduction; 30-50% CAPA improvement |

---

## 16. Evidence Sources (12)

| Source | Type | Frequency | Use For |
|---|---|---|---|
| SEC 10-K | Regulatory filing | Annual | Financial health, risk priorities |
| SEC 10-Q | Regulatory filing | Quarterly | Trend analysis, triggers |
| Earnings Call Transcripts | Earnings call | Quarterly | Strategic intent, priorities |
| Job Posting Data | Job market | Continuous | Growth signals, technology adoption |
| FDA Enforcement Database | Regulatory | Continuous | Quality crises, compliance gaps |
| OSHA Enforcement Data | Regulatory | Continuous | Safety culture, EHS triggers |
| Industry Association Reports | Industry assoc | Quarterly/Annual | Sector trends, benchmarks |
| Consulting Firm Research | Consulting | Annual | Benchmark data, best practices |
| Credit Rating Agency Reports | Financial | Continuous | Financial stress, risk profile |
| Trade Publications | Trade press | Monthly | Technology adoption, case studies |
| Patent Filings | IP database | Continuous | Innovation signals, NPI direction |
| News/Press Releases | News | Continuous | Event triggers, strategic direction |

---

## 17. Governance

| Field | Value |
|---|---|
| Source Coverage | Mixed (public filings, industry reports, benchmarks) |
| Confidence | High |
| Last Updated | 2026-04-25 |
| Approved for Customer-Facing | No (internal intelligence only) |
| Review Owner | manufacturing-master-architect |
| Agent Swarm ID | kimi-k2.6-elevated-swarm |

---

## 18. Usage Notes

### Signal-to-Hypothesis Workflow
1. **Detect** raw signal (e.g., job posting surge, 10-K risk factor)
2. **Interpret** using signal rules with confidence scoring
3. **Map** to linked pains and KPIs
4. **Identify** affected personas and their pressures
5. **Quantify** using value formulas with customer-specific inputs
6. **Validate** with discovery questions
7. **Address** anticipated objections

### Value Quantification Discipline
- Every formula requires validated baseline and target inputs
- Confidence rules must be checked before presenting to customer
- Use ranges rather than false precision
- Always connect to one of four value categories: Revenue Uplift, Cost Savings, Risk Reduction, Working Capital

### Segment Specialization Path
This Master Pack provides foundation intelligence. Subpacks provide:
- Segment-specific pain variants and prevalence
- Segment-tailored benchmarks and KPI weightings
- Segment-specific regulatory factors
- Segment-appropriate technology system priorities
- Segment-specific discovery questions

---

*End of Manufacturing Master ValuePack Reference Document*
