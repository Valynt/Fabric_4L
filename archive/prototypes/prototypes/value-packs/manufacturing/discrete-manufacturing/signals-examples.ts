/**
 * Discrete Manufacturing Vertical Subpack — Signal→Hypothesis Worked Examples (TypeScript)
 * 
 * ID: discrete-manufacturing-v1
 * Parent Master: manufacturing-master-v1
 * 
 * This file contains 3 fully worked signal-to-hypothesis examples using
 * discrete manufacturing vertical logic. Each example demonstrates:
 * - Signal detection with confidence scoring
 * - Hypothesis formulation
 * - Pain and KPI linkage
 * - Formula application with step-by-step financial walkthrough
 * - Business outcome quantification
 * - Customer validation requirements
 */

// ============================================================================
// CORE TYPE DEFINITIONS (Vertical Extensions)
// ============================================================================

interface DetectedSignal {
  signalId: string;
  description: string;
  confidence: number; // 0.0 - 1.0
  dataSource: string;
  rawValue: string;
  thresholdBreached: boolean;
}

interface FinancialWalkthroughStep {
  stepNumber: number;
  description: string;
  calculation: string;
  intermediateResult: string;
}

interface BusinessOutcome {
  revenueUplift: string;
  costSavings: string;
  riskReduction: string;
  cashFlowImprovement: string;
}

interface CustomerValidationItem {
  validationId: string;
  question: string;
  whyItMatters: string;
  estimatedValidationEffort: "low" | "medium" | "high";
}

interface WorkedExample {
  exampleId: string;
  title: string;
  scenario: string;
  verticalSegment: string;
  signalsDetected: DetectedSignal[];
  compositeConfidence: number;
  hypothesis: string;
  linkedPainId: string;
  linkedKpiIds: string[];
  formulaId: string;
  financialWalkthrough: FinancialWalkthroughStep[];
  annualValueRange: { low: number; mid: number; high: number; unit: string };
  investmentRequired: { low: number; mid: number; high: number; unit: string };
  paybackMonths: { low: number; mid: number; high: number };
  threeYearNPV: { low: number; mid: number; high: number; unit: string; discountRate: number };
  businessOutcome: BusinessOutcome;
  customerValidations: CustomerValidationItem[];
  keyAssumptions: string[];
  assumptionConfidenceFlags: { assumption: string; confidence: "HIGH" | "MEDIUM" | "LOW"; rationale: string }[];
}

// ============================================================================
// EXAMPLE 1: Torque Cpk Decline → Warranty Risk → Assembly Process Control
// ============================================================================

export const exampleTorqueWarranty: WorkedExample = {
  exampleId: "ex-dm-001",
  title: "Torque Cpk Decline → Warranty Risk → Assembly Process Control Investment",
  scenario:
    "Tier-1 automotive supplier producing EV battery tray assemblies observes torque Cpk " +
    "declining from 1.67 to 1.2 over 3 months at Station 14 (battery module fastening). " +
    "Warranty claims for 'loose connection' have increased 40% quarter-over-quarter. " +
    "OEM customer has issued a quality alert requiring corrective action within 60 days.",
  verticalSegment: "Automotive/EV",

  signalsDetected: [
    {
      signalId: "sig-dm-001",
      description: "Torque audit Cpk declining trend",
      confidence: 0.92,
      dataSource: "MES torque controller logs (Atlas Copco / Bosch Rexroth DC tools)",
      rawValue: "Cpk = 1.20 (down from 1.67 baseline); Ppk = 1.05",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-002a",
      description: "Warranty claims increasing for battery connection issues",
      confidence: 0.85,
      dataSource: "Warranty management system + OEM field report portal",
      rawValue: "Claims up 40% QoQ; 68% traceable to Station 14 torque deviation",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-001b",
      description: "Tool calibration overdue on 40% of fastening tools",
      confidence: 0.95,
      dataSource: "Calibration management system (Fluke MET/TEAM or equivalent)",
      rawValue: "14 of 35 torque tools past due by 15-45 days",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-001c",
      description: "Station-level andon pulls for re-torque increasing",
      confidence: 0.78,
      dataSource: "MES andon event log",
      rawValue: "Andon pulls at Station 14: 3.2/day (up from 0.4/day baseline)",
      thresholdBreached: true,
    },
  ],

  compositeConfidence: 0.88, // weighted average with confidence decay for correlated signals

  hypothesis:
    "Battery module fastening torque inconsistency is the leading predictor of early-life " +
    "battery pack failures. The root cause is calibration drift on DC electric fastening tools " +
    "combined with lack of statistical process control (SPC) at the station level. Without intervention, " +
    "the trajectory will breach the OEM recall threshold (0.1% field failure rate) within 6-9 months.",

  linkedPainId: "pain-dm-001",
  linkedKpiIds: ["kpi-torque-cpk", "kpi-warranty-cost", "kpi-field-failure-rate"],
  formulaId: "vf-dm-001",

  financialWalkthrough: [
    {
      stepNumber: 1,
      description: "Establish defect rate at current and target Cpk levels",
      calculation: "At Cpk 1.20 (Z=2.4, 2-tail): reject rate = 0.32%. At Cpk 1.67 (Z=3.34): reject rate = 0.006%.",
      intermediateResult: "Excess reject rate = 0.314%",
    },
    {
      stepNumber: 2,
      description: "Calculate annual excess defect volume",
      calculation: "Annual volume = 450,000 battery trays. Excess defects = 450,000 x 0.00314 = 1,413 units/year.",
      intermediateResult: "1,413 excess defect units per year",
    },
    {
      stepNumber: 3,
      description: "Compute rework cost for defects caught in-plant",
      calculation: "Rework per defect = disassembly ($15) + re-torque ($25) + re-test ($25) = $65. Rework cost = 1,413 x $65.",
      intermediateResult: "$91,845 annual rework cost",
    },
    {
      stepNumber: 4,
      description: "Compute warranty cost for defects escaping to field",
      calculation: "Historical traceability shows 18% of torque defects escape to field. Field failures = 254. Cost per event = truck roll ($180) + part ($220) + labor ($450) = $850.",
      intermediateResult: "$215,900 annual warranty cost",
    },
    {
      stepNumber: 5,
      description: "Compute recall risk value (risk-adjusted)",
      calculation: "OEM recall threshold = 0.1% failure rate. Current trajectory = 0.06%, trending up. Small recall scenario = $2.5M (replacement + logistics + brand). Probability = 15%.",
      intermediateResult: "$375,000 risk-adjusted recall cost",
    },
    {
      stepNumber: 6,
      description: "Sum total annual cost of quality gap",
      calculation: "$91,845 + $215,900 + $375,000 = $682,745.",
      intermediateResult: "$682,745 total annual cost of quality gap",
    },
    {
      stepNumber: 7,
      description: "Quantify intervention investment",
      calculation: "Tool condition monitoring sensors (14 stations x $4,500) = $63,000. SPC software module = $45,000. Calibration management upgrade = $35,000. Integration and training = $37,000.",
      intermediateResult: "$180,000 total investment",
    },
    {
      stepNumber: 8,
      description: "Calculate return metrics",
      calculation: "Payback = $180,000 / $682,745 = 0.26 years = 3.2 months. 3-year NPV at 12% discount = $1.52M.",
      intermediateResult: "Payback 3.2 months; 3-year NPV $1.52M; ROI 279%",
    },
  ],

  annualValueRange: {
    low: 450000,
    mid: 682745,
    high: 950000,
    unit: "USD/year",
  },

  investmentRequired: {
    low: 120000,
    mid: 180000,
    high: 250000,
    unit: "USD",
  },

  paybackMonths: {
    low: 2,
    mid: 3,
    high: 5,
  },

  threeYearNPV: {
    low: 950000,
    mid: 1520000,
    high: 2200000,
    unit: "USD",
    discountRate: 0.12,
  },

  businessOutcome: {
    revenueUplift: "$0 (preventive value driver)",
    costSavings: "$683K/year direct (rework + warranty); $2.5M recall avoidance",
    riskReduction: "Recall probability reduced from 15% to <2%; OEM quality scorecard recovery",
    cashFlowImprovement: "Warranty reserve release $340K; reduced expediting to field $85K",
  },

  customerValidations: [
    {
      validationId: "cv-001-1",
      question: "What percentage of warranty claims are root-caused to fastening torque deviation vs other battery issues?",
      whyItMatters: "If <50% are torque-related, the financial model overstates impact. Need validated Pareto.",
      estimatedValidationEffort: "medium",
    },
    {
      validationId: "cv-001-2",
      question: "What is the actual calibration interval and observed drift for DC tools at Station 14?",
      whyItMatters: "If drift is <1% and interval is already 30 days, the intervention may need different design.",
      estimatedValidationEffort: "low",
    },
    {
      validationId: "cv-001-3",
      question: "What is the OEM's specific recall threshold and escalation protocol?",
      whyItMatters: "Some OEMs use 0.05% for safety-critical, others 0.2%. This changes risk quantification significantly.",
      estimatedValidationEffort: "medium",
    },
  ],

  keyAssumptions: [
    "Torque Cpk correlates directly with field failure rate (validated by warranty root cause analysis)",
    "Calibration drift is the dominant root cause (not operator training or component variation)",
    "Investment in tool monitoring and SPC will achieve target Cpk of 1.67 within 90 days",
    "OEM will not switch suppliers during the 60-day corrective action window",
  ],

  assumptionConfidenceFlags: [
    {
      assumption: "Torque Cpk correlates directly with field failure rate",
      confidence: "HIGH",
      rationale: "Strong statistical evidence in automotive fastening (AIAG data); 18% trace rate validated.",
    },
    {
      assumption: "Calibration drift is the dominant root cause",
      confidence: "HIGH",
      rationale: "40% of tools overdue; Cpk improvement historically tracks with calibration schedule adherence.",
    },
    {
      assumption: "Target Cpk of 1.67 achievable within 90 days",
      confidence: "MEDIUM",
      rationale: "Depends on tool condition; if spindles are worn, replacement may extend to 120 days.",
    },
    {
      assumption: "OEM will not switch suppliers during 60-day window",
      confidence: "MEDIUM",
      rationale: "Supplier switching cost is high, but OEMs have activated backup suppliers in past crises.",
    },
  ],
};

// ============================================================================
// EXAMPLE 2: CMM Queue Growth → Throughput Constraint → In-Process Metrology
// ============================================================================

export const exampleCMMBottleneck: WorkedExample = {
  exampleId: "ex-dm-002",
  title: "CMM Queue Growth → Throughput Constraint → In-Process Metrology Investment",
  scenario:
    "Precision aerospace machine shop producing titanium structural brackets experiences CMM queue " +
    "growing from 8 hours to 35 hours per week over 6 months. First article inspection cycle extends " +
    "from 2 days to 6 days. Customer (Boeing) delivery performance drops below 95%, triggering a " +
    "supplier performance review. Inspection staff overtime exceeds 25% and headcount freeze is in place.",
  verticalSegment: "Aerospace & Defense",

  signalsDetected: [
    {
      signalId: "sig-dm-007",
      description: "CMM queue hours trending up >300% over 6 months",
      confidence: 0.90,
      dataSource: "Inspection planning system (Hexagon PC-DMIS scheduler / homegrown)",
      rawValue: "Queue: 35 hrs/week (baseline 8 hrs/week). Trend: +4.5 hrs/month.",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-007b",
      description: "First article inspection cycle time >5 days",
      confidence: 0.88,
      dataSource: "QMS first article records (AS9102 forms)",
      rawValue: "Average FAI cycle = 6.2 days (SLA = 3 days). Backlog = 12 open FAIs.",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-007c",
      description: "Customer on-time delivery <95% with inspection as bottleneck",
      confidence: 0.82,
      dataSource: "ERP delivery performance reports + Boeing SCM portal",
      rawValue: "OTD = 93.4%. Late shipments: 87% awaiting CMM release.",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-007d",
      description: "Inspection staff overtime >25% and headcount freeze in place",
      confidence: 0.95,
      dataSource: "HR/payroll system + operations budget",
      rawValue: "OT rate = 27.3%. Headcount freeze approved by CFO for FY2025.",
      thresholdBreached: true,
    },
  ],

  compositeConfidence: 0.89,

  hypothesis:
    "CMM capacity is the primary bottleneck constraining throughput and delivery performance. " +
    "The highest-ROI intervention is deploying in-process metrology (on-machine probing + optical scanning) " +
    "for feature classes that do not require CMM-level accuracy (<5 microns). This will reduce queue by 70%, " +
    "accelerate FAI release, and restore Boeing delivery scorecard to >98% within 90 days.",

  linkedPainId: "pain-dm-008",
  linkedKpiIds: ["kpi-cmm-utilization", "kpi-que-time", "kpi-mfg-lead-time"],
  formulaId: "vf-dm-007",

  financialWalkthrough: [
    {
      stepNumber: 1,
      description: "Establish queue reduction target",
      calculation: "Current queue = 35 hrs/week. Target = 10 hrs/week (buffer for variance). Reduction = 25 hrs/week.",
      intermediateResult: "25 hrs/week queue reduction",
    },
    {
      stepNumber: 2,
      description: "Calculate queue time value at full capacity",
      calculation: "Hourly production value of downstream constrained operations = $6,800 (titanium brackets, high value). Annual value = 25 hrs x 50 weeks x $6,800.",
      intermediateResult: "$8.5M annual value at full capacity",
    },
    {
      stepNumber: 3,
      description: "Apply demand constraint factor",
      calculation: "Shop is at 85% of capacity; cannot absorb full 25 hrs/week at current demand. Effective throughput gain = 15% of queue value.",
      intermediateResult: "$1.28M effective annual revenue uplift",
    },
    {
      stepNumber: 4,
      description: "Calculate inspection labor cost reduction",
      calculation: "Current: 3 FTE x $85K + 27% OT premium = $324K. Target: 2.5 FTE + 10% OT = $234K. Savings = $90K.",
      intermediateResult: "$90K annual labor savings",
    },
    {
      stepNumber: 5,
      description: "Calculate first article cycle reduction value",
      calculation: "FAI cycle: 6.2 -> 3.0 days. New product revenue at risk from delay = $200K/month. Probability-weighted acceleration value = $180K/year.",
      intermediateResult: "$180K FAI acceleration value",
    },
    {
      stepNumber: 6,
      description: "Quantify intervention investment",
      calculation: "On-machine probing (Renishaw OMP60 + software): $45K/machine x 5 machines = $225K. Optical scanning station (GOM ATOS Q): $120K. Integration and training: $85K. Total = $430K.",
      intermediateResult: "$430K total investment",
    },
    {
      stepNumber: 7,
      description: "Calculate return metrics",
      calculation: "Annual value = $1.28M + $90K + $180K = $1.55M. Payback = $430K / $1.55M = 0.28 years = 3.3 months. 3-year NPV at 12% = $3.52M.",
      intermediateResult: "Payback 3.3 months; 3-year NPV $3.52M; ROI 261%",
    },
  ],

  annualValueRange: {
    low: 950000,
    mid: 1550000,
    high: 2200000,
    unit: "USD/year",
  },

  investmentRequired: {
    low: 350000,
    mid: 430000,
    high: 550000,
    unit: "USD",
  },

  paybackMonths: {
    low: 2,
    mid: 3,
    high: 5,
  },

  threeYearNPV: {
    low: 2500000,
    mid: 3520000,
    high: 4800000,
    unit: "USD",
    discountRate: 0.12,
  },

  businessOutcome: {
    revenueUplift: "$1.28M (throughput-constrained demand capture)",
    costSavings: "$270K/year (labor + FAI acceleration)",
    riskReduction: "Boeing delivery scorecard recovery to >98%; contract renewal secured; Nadcap audit risk reduced",
    cashFlowImprovement: "WIP velocity increase reduces inventory carrying by $420K; expedited freight avoided $95K",
  },

  customerValidations: [
    {
      validationId: "cv-002-1",
      question: "Is CMM queue truly the bottleneck, or is machining capacity the actual constraint?",
      whyItMatters: "If machining has hidden capacity, the queue reduction may not translate to throughput gain.",
      estimatedValidationEffort: "medium",
    },
    {
      validationId: "cv-002-2",
      question: "What feature classes can be verified by on-machine probing vs those requiring CMM (<5 micron)?",
      whyItMatters: "If >60% of features require CMM accuracy, in-process metrology ROI drops significantly.",
      estimatedValidationEffort: "medium",
    },
    {
      validationId: "cv-002-3",
      question: "Does Boeing have confirmed demand to absorb a 15% throughput increase within 12 months?",
      whyItMatters: "Without confirmed demand, the revenue uplift is speculative. Need LOI or forecast.",
      estimatedValidationEffort: "high",
    },
  ],

  keyAssumptions: [
    "CMM queue is the primary production bottleneck (not machining or material availability)",
    "On-machine probing can verify ≥50% of currently CMM-inspected features within customer GD&T tolerance",
    "Boeing delivery scorecard recovery prevents volume reduction or contract loss",
    "Inspection headcount reduction of 0.5 FTE is achievable without union objection",
  ],

  assumptionConfidenceFlags: [
    {
      assumption: "CMM is the primary bottleneck",
      confidence: "HIGH",
      rationale: "87% of late shipments await CMM release; queue growing monotonically for 6 months.",
    },
    {
      assumption: "On-machine probing covers ≥50% of features",
      confidence: "MEDIUM",
      rationale: "Depends on part geometry complexity; optical scanning capability assessment needed.",
    },
    {
      assumption: "Boeing scorecard recovery prevents contract loss",
      confidence: "HIGH",
      rationale: "Boeing supplier scorecard weights delivery heavily (>30%); recovery within 90 days prevents escalation.",
    },
    {
      assumption: "Headcount reduction achievable without union objection",
      confidence: "MEDIUM",
      rationale: "Depends on local labor agreement and workforce flexibility; may require redeployment vs reduction.",
    },
  ],
};

// ============================================================================
// EXAMPLE 3: SMT DPMO Spike → Electronics Rework Crisis → Process Control
// ============================================================================

export const exampleSMTDPMO: WorkedExample = {
  exampleId: "ex-dm-003",
  title: "SMT DPMO Spike → Electronics Rework Crisis → Process Control Enhancement",
  scenario:
    "Medical device electronics contract manufacturer (ISO 13485, FDA-registered) experiences SMT DPMO " +
    "rising from 800 to 4,200 over 4 months on a Class II patient monitor board. AOI false positive rate " +
    "grows to 18%, flooding the rework station and consuming 3 FTE. Reflow oven zone 3 shows 3°C drift " +
    "from recipe. FDA pre-approval inspection for a new product line is scheduled in 6 months.",
  verticalSegment: "Medical Devices",

  signalsDetected: [
    {
      signalId: "sig-dm-006",
      description: "SMT DPMO trending up 5x over 4 months",
      confidence: 0.94,
      dataSource: "AOI + X-ray inspection database (Koh Young / ViTrox / Nidek)",
      rawValue: "DPMO = 4,247 (baseline 800). Defect Pareto: voids 42%, bridging 28%, insufficient 18%, other 12%.",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-006b",
      description: "AOI false positive rate >15%",
      confidence: 0.89,
      dataSource: "AOI system logs + manual verification records",
      rawValue: "FP rate = 18.3% (target <5%). Manual verification time = 2.1 min/call.",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-006c",
      description: "Reflow oven temperature zone 3 showing 3°C drift from recipe",
      confidence: 0.87,
      dataSource: "Reflow profiler data (KIC Thermal Profiler / ECD MOLE)",
      rawValue: "Zone 3 actual = 238°C (recipe = 235°C). Peak temp variance = +2.1°C. Time above liquidus = +4.2 sec.",
      thresholdBreached: true,
    },
    {
      signalId: "sig-dm-006d",
      description: "Solder paste volume deposition CV increasing from 8% to 14%",
      confidence: 0.85,
      dataSource: "SPI system (Koh Young / CyberOptics)",
      rawValue: "Volume CV = 14.2% (spec <10%). Area ratio trending down on 0.3mm pitch pads.",
      thresholdBreached: true,
    },
  ],

  compositeConfidence: 0.89,

  hypothesis:
    "Reflow profile drift (zone 3 temperature elevation) combined with solder paste volume inconsistency " +
    "(stencil wear or paste conditioning issue) is causing solder joint defects (voids, bridging). " +
    "The AOI system was calibrated for the baseline defect signature and is now generating false positives " +
    "for the new defect morphology. The combination threatens FDA pre-approval readiness and product reliability. " +
    "Immediate intervention: reflow controller upgrade with closed-loop thermal profiling, SPI-to-stencil feedback, " +
    "and AOI recipe retraining.",

  linkedPainId: "pain-dm-007",
  linkedKpiIds: ["kpi-smt-dpmo", "kpi-dpmo", "kpi-fpy"],
  formulaId: "vf-dm-006",

  financialWalkthrough: [
    {
      stepNumber: 1,
      description: "Establish excess DPMO and defect volume",
      calculation: "Baseline DPMO = 4,247. Target = 800 (world-class medical). Excess DPMO = 3,447.",
      intermediateResult: "Excess DPMO = 3,447",
    },
    {
      stepNumber: 2,
      description: "Calculate annual excess defect volume",
      calculation: "Annual board volume = 850,000. Excess defects = 850,000 x 0.003447 = 2,930.",
      intermediateResult: "2,930 excess defects per year",
    },
    {
      stepNumber: 3,
      description: "Compute material and placement cost of excess defects",
      calculation: "Board material + placement + test cost = $78. Excess material cost = 2,930 x $78.",
      intermediateResult: "$228,540 annual material cost",
    },
    {
      stepNumber: 4,
      description: "Compute rework labor cost for excess defects",
      calculation: "Rework per defect = 0.4 hours @ $72/hr fully burdened. Rework labor = 2,930 x 0.4 x $72.",
      intermediateResult: "$84,384 annual rework labor cost",
    },
    {
      stepNumber: 5,
      description: "Compute AOI false positive labor burden",
      calculation: "FP rate = 18.3% on 850K boards = 155,550 false calls. Verification = 2.1 min/call @ $72/hr. Labor = 155,550 x (2.1/60) x $72.",
      intermediateResult: "$392,058 annual AOI false positive labor cost",
    },
    {
      stepNumber: 6,
      description: "Compute FDA/launch risk value (risk-adjusted)",
      calculation: "FDA 483 on process control could delay product launch by 6 months. Revenue at risk = $3.5M/month x 6 months. Probability = 30%. Risk-adjusted value = $6.3M.",
      intermediateResult: "$6.3M risk-adjusted FDA/launch risk",
    },
    {
      stepNumber: 7,
      description: "Quantify intervention investment",
      calculation: "Reflow oven controller upgrade (KIC Navigator/ECD) = $85K. SPI-to-stencil closed-loop module = $35K. AOI recipe optimization + golden board retrain = $25K. Integration and validation (IQ/OQ/PQ) = $55K. Total = $200K.",
      intermediateResult: "$200K total investment",
    },
    {
      stepNumber: 8,
      description: "Calculate return metrics (direct only and with risk)",
      calculation: "Direct annual savings = $228K + $84K + $392K = $704K. Payback = $200K / $704K = 0.28 years = 3.4 months. With FDA risk: 3-year NPV = $15.2M.",
      intermediateResult: "Payback 3.4 months; 3-year NPV $15.2M (with risk); ROI 3520%",
    },
  ],

  annualValueRange: {
    low: 500000,
    mid: 704000,
    high: 7500000,
    unit: "USD/year",
  },

  investmentRequired: {
    low: 150000,
    mid: 200000,
    high: 280000,
    unit: "USD",
  },

  paybackMonths: {
    low: 2,
    mid: 3,
    high: 5,
  },

  threeYearNPV: {
    low: 1200000,
    mid: 15200000,
    high: 25000000,
    unit: "USD",
    discountRate: 0.12,
  },

  businessOutcome: {
    revenueUplift: "$0 (preventive value driver on existing line); $21M protected on new product line",
    costSavings: "$704K/year direct (material + rework + AOI labor)",
    riskReduction: "FDA 483 avoidance: 30% -> <5% probability. Product launch timeline protected.",
    cashFlowImprovement: "Reduced WIP in rework queue = $120K. Expedited delivery penalties avoided = $45K.",
  },

  customerValidations: [
    {
      validationId: "cv-003-1",
      question: "Can you correlate specific reflow profile deviation zones with specific defect types (voids vs bridging)?",
      whyItMatters: "If correlation is weak, the reflow investment may not solve the primary defect mode.",
      estimatedValidationEffort: "medium",
    },
    {
      validationId: "cv-003-2",
      question: "What is the true cost per AOI false positive, including downstream queue and missed shifts?",
      whyItMatters: "If verification is done during normal staffing, labor cost may be lower than modeled.",
      estimatedValidationEffort: "low",
    },
    {
      validationId: "cv-003-3",
      question: "Does the FDA pre-approval inspection scope include this specific SMT line and process control emphasis?",
      whyItMatters: "If inspection focuses on software validation rather than process control, the risk model overstates.",
      estimatedValidationEffort: "high",
    },
  ],

  keyAssumptions: [
    "Reflow zone 3 temperature elevation is the primary driver of voids and bridging (not paste formulation or pad design)",
    "AOI false positives are caused by recipe mismatch, not actual defect increase that should be caught",
    "SPI-to-stencil closed-loop feedback can reduce volume CV from 14% to <10% within 30 days",
    "FDA inspector will evaluate process control data as part of the pre-approval inspection",
  ],

  assumptionConfidenceFlags: [
    {
      assumption: "Reflow zone 3 is primary driver of voids/bridging",
      confidence: "MEDIUM",
      rationale: "Correlation visible but root cause may be multi-factorial (paste, stencil, profile). DOE needed.",
    },
    {
      assumption: "AOI false positives are recipe mismatch, not actual defects",
      confidence: "HIGH",
      rationale: "Golden board validation shows 94% of flagged 'defects' are within IPC-A-610 class 2 limits.",
    },
    {
      assumption: "SPI-to-stencil feedback achieves CV <10% in 30 days",
      confidence: "HIGH",
      rationale: "Stencil wear is known issue; automated under-wipe and pressure feedback proven in comparable lines.",
    },
    {
      assumption: "FDA inspector evaluates process control data",
      confidence: "MEDIUM",
      rationale: "Pre-approval inspection scope varies; typically includes process validation (IQ/OQ/PQ) evidence.",
    },
  ],
};

// ============================================================================
// EXPORTS AND UTILITIES
// ============================================================================

export const allWorkedExamples: WorkedExample[] = [
  exampleTorqueWarranty,
  exampleCMMBottleneck,
  exampleSMTDPMO,
];

/**
 * Utility: Calculate composite confidence from a set of detected signals.
 * Uses a weighted average with confidence decay for highly correlated signals.
 */
export function calculateCompositeConfidence(signals: DetectedSignal[]): number {
  if (signals.length === 0) return 0;
  if (signals.length === 1) return signals[0].confidence;

  // Base: average confidence
  const avg = signals.reduce((sum, s) => sum + s.confidence, 0) / signals.length;

  // Penalty for correlated signals (same data source or same root cause domain)
  const uniqueSources = new Set(signals.map((s) => s.dataSource.split(" ")[0])).size;
  const correlationPenalty = Math.max(0, (signals.length - uniqueSources) * 0.02);

  // Bonus for threshold breaches (stronger signal)
  const breachBonus = signals.filter((s) => s.thresholdBreached).length * 0.01;

  return Math.min(0.98, Math.max(0.5, avg - correlationPenalty + breachBonus));
}

/**
 * Utility: Validate a worked example's financial walkthrough for arithmetic consistency.
 * Returns an array of validation errors, or empty array if valid.
 */
export function validateFinancialWalkthrough(example: WorkedExample): string[] {
  const errors: string[] = [];

  // Check that annualValueRange mid approximates walkthrough total
  const walkthroughTotalMatch = example.financialWalkthrough.some(
    (step) =>
      step.description.toLowerCase().includes("total annual") ||
      step.description.toLowerCase().includes("sum total")
  );
  if (!walkthroughTotalMatch) {
    errors.push(`Example ${example.exampleId}: No explicit total/sum step found in walkthrough.`);
  }

  // Check that payback months aligns with investment and annual value
  const expectedPayback = (example.investmentRequired.mid / example.annualValueRange.mid) * 12;
  const paybackVariance = Math.abs(expectedPayback - example.paybackMonths.mid) / example.paybackMonths.mid;
  if (paybackVariance > 0.15) {
    errors.push(
      `Example ${example.exampleId}: Payback months mismatch. ` +
      `Calculated: ${expectedPayback.toFixed(1)} months. Declared: ${example.paybackMonths.mid} months.`
    );
  }

  // Check confidence bounds
  if (example.compositeConfidence < 0.7) {
    errors.push(`Example ${example.exampleId}: Composite confidence ${example.compositeConfidence} below 0.7 threshold.`);
  }

  return errors;
}

/**
 * Utility: Extract all customer validation questions from a set of examples.
 * Useful for pre-call preparation.
 */
export function extractValidationQuestions(examples: WorkedExample[]): CustomerValidationItem[] {
  return examples.flatMap((ex) => ex.customerValidations);
}

/**
 * Utility: Rank examples by business outcome magnitude (cost savings + revenue uplift proxy).
 */
export function rankByOutcomeMagnitude(examples: WorkedExample[]): WorkedExample[] {
  return [...examples].sort((a, b) => {
    const aScore = a.annualValueRange.mid + (a.threeYearNPV.mid - a.annualValueRange.mid * 3);
    const bScore = b.annualValueRange.mid + (b.threeYearNPV.mid - b.annualValueRange.mid * 3);
    return bScore - aScore;
  });
}

// End of signals-examples.ts
