/**
 * Healthcare Operations Subpack - Signal Examples (TypeScript)
 * ID: healthcare-operations-v1
 * Parent Master: healthcare-master-v1
 * Agent Swarm: kimi-k2.6-swarm-healthcare-ops-s3.4
 * Last Updated: 2026-04-25
 * 
 * This file provides concrete TypeScript implementations of signal interpretation
 * rules, value driver mappings, and worked examples from the Healthcare Operations
 * Subpack. It is designed for direct integration into value-selling platforms,
 * signal detection systems, and business case calculators.
 */

// ============================================================================
// CORE TYPE DEFINITIONS (Inherited from Master Pack, extended for Operations)
// ============================================================================

export type ValueCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type UrgencyLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type PersonaInfluence = "economic" | "technical" | "user";
export type EvidenceSourceType = "industry_survey" | "government" | "financial_ratings" | "academic" | "industry_standard";

export interface BusinessPain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  affectedSegments: string[];
  affectedPersonas: string[];
  linkedKPIs: string[];
  linkedValueDrivers: string[];
  prevalence: "HIGH" | "MEDIUM" | "LOW";
  confidence: ConfidenceLevel;
  sources: string[];
}

export interface KPIDefinition {
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

export interface SignalInterpretationRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
}

export interface PersonaProfile {
  id: string;
  name: string;
  role: string;
  seniority: string;
  goals: string[];
  pressures: string[];
  trustedEvidence: string[];
  dislikedClaims: string[];
  decisionInfluence: PersonaInfluence;
}

export interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
}

export interface Benchmark {
  id: string;
  name: string;
  value: number;
  range: string;
  unit: string;
  source: string;
  sourceType: EvidenceSourceType;
  segmentApplicability: string[];
  geographicScope: string;
  companySizeScope: string;
  confidence: ConfidenceLevel;
  dateSourced: string;
}

export interface BuyingTrigger {
  id: string;
  name: string;
  triggerEvent: string;
  urgencyLevel: UrgencyLevel;
  typicalTiming: string;
  affectedSegments: string[];
  linkedPains: string[];
  procurementImplications: string;
}

export interface WorkedExample {
  id: string;
  name: string;
  scenario: string;
  inputs: Record<string, number>;
  formulaUsed: string;
  calculationSteps: string[];
  outcome: {
    revenueUplift: number;
    costSavings: number;
    riskReduction: number;
    workingCapitalImprovement: number;
    totalYearOneValue: number;
    threeYearNPV: number;
    paybackMonths: number;
  };
  assumptions: string[];
  confidence: ConfidenceLevel;
  sources: string[];
}

// ============================================================================
// SIGNAL RULE EXAMPLES (20 concrete instances)
// ============================================================================

export const signalRules: SignalInterpretationRule[] = [
  {
    id: "OS001",
    signalName: "RCM Job Posting Surge with Denials Focus",
    rawSignalPattern: ">8 open positions mentioning 'denials', 'appeals', or 'revenue integrity' in 60 days",
    interpretedMeaning: "Organization experiencing denial crisis and staffing to catch up rather than fixing root cause",
    linkedPains: ["OP001", "OP008"],
    linkedKPIs: ["OK001", "OK002"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["A/R days trending >50", "denial rate >10% in public data"]
  },
  {
    id: "OS002",
    signalName: "Prior Auth Vendor Search",
    rawSignalPattern: "RFP or job posting for 'prior authorization automation', 'PA software', or 'ePA integration'",
    interpretedMeaning: "Manual PA burden recognized but not yet solved; procurement active",
    linkedPains: ["OP002"],
    linkedKPIs: ["OK004", "OK005"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["Physician satisfaction survey mentions PA burden", "AMA PA burden data for state"]
  },
  {
    id: "OS003",
    signalName: "CDI Platform RFP or Vendor Change",
    rawSignalPattern: "RFP issued for CDI software, 3M/Nuance replacement, or 'computer-assisted coding'",
    interpretedMeaning: "Current CDI program underperforming or contract expiring; seeking new capability",
    linkedPains: ["OP003", "OP013"],
    linkedKPIs: ["OK007", "OK008"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: ["CMI below peer group", "query response rate declining"]
  },
  {
    id: "OS004",
    signalName: "Patient Access Platform Acquisition",
    rawSignalPattern: "Acquisition of scheduling/registration vendor (Kyruus, Luma Health, Phreesia) or digital front door platform",
    interpretedMeaning: "Access and scheduling recognized as strategic priority; no-show and wait time likely issues",
    linkedPains: ["OP004"],
    linkedKPIs: ["OK010", "OK011"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["Online scheduling <30% of appointments", "wait time >21 days for key specialties"]
  },
  {
    id: "OS005",
    signalName: "Credentialing System Upgrade or MSP Replacement",
    rawSignalPattern: "RFP for credentialing software, medical staff office automation, or Symplr/Modio replacement",
    interpretedMeaning: "Credentialing backlog and manual process recognized as revenue and compliance risk",
    linkedPains: ["OP005"],
    linkedKPIs: ["OK013", "OK014"],
    confidenceScore: 0.81,
    requiredConfirmationSignals: ["Credentialing cycle >120 days reported", "provider start delays in reviews"]
  },
  {
    id: "OS006",
    signalName: "Supply Chain Consolidation Initiative",
    rawSignalPattern: "GPO contract renegotiation announcement, distributor change, or 'supply chain transformation' in earnings call",
    interpretedMeaning: "Supply chain underperformance or post-COVID resilience initiative driving vendor change",
    linkedPains: ["OP006"],
    linkedKPIs: ["OK016", "OK017"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["Inventory turns <8", "expired product write-offs increasing"]
  },
  {
    id: "OS007",
    signalName: "340B Program Restructuring or Contract Pharmacy Change",
    rawSignalPattern: "Addition or removal of contract pharmacies, 340B vendor change, or HRSA audit mention in disclosure",
    interpretedMeaning: "340B compliance or revenue optimization under stress; operational overhaul likely",
    linkedPains: ["OP007"],
    linkedKPIs: ["OK019", "OK020"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: ["HRSA audit finding disclosure", "manufacturer restriction lawsuit mention"]
  },
  {
    id: "OS008",
    signalName: "DNFB Spike or Charge Capture Vendor Search",
    rawSignalPattern: "Job posting for 'charge capture', 'DNFB reduction', or 'revenue integrity analyst' surge",
    interpretedMeaning: "Billing workflow breakdown or expansion causing revenue recognition delay",
    linkedPains: ["OP008", "OP016"],
    linkedKPIs: ["OK023", "OK024"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: ["DNFB >5 days", "charge lag >3 days"]
  },
  {
    id: "OS009",
    signalName: "Quality Reporting Consultant Engagement",
    rawSignalPattern: "Consulting engagement announced for 'HEDIS', 'MIPS', 'eCQM', or 'registry submission'",
    interpretedMeaning: "Internal quality reporting capacity insufficient; penalties or missed bonuses likely",
    linkedPains: ["OP009"],
    linkedKPIs: ["OK025"],
    confidenceScore: 0.79,
    requiredConfirmationSignals: ["Registry submission backlog >30 days", "eCQM measure gap >3 measures"]
  },
  {
    id: "OS010",
    signalName: "Float Pool Expansion or Workforce Management RFP",
    rawSignalPattern: "RFP for 'workforce optimization', 'float pool management', or 'nurse scheduling software'",
    interpretedMeaning: "Staffing mismatch and premium labor cost driving operational change",
    linkedPains: ["OP010"],
    linkedKPIs: ["OK028", "OK029"],
    confidenceScore: 0.77,
    requiredConfirmationSignals: ["Agency labor >5% of nursing cost", "overtime >8% of RN hours"]
  },
  {
    id: "OS011",
    signalName: "Care Coordination Platform Purchase",
    rawSignalPattern: "Acquisition of care coordination or transition management platform (Bamboo Health, naviHealth, etc.)",
    interpretedMeaning: "Readmission and post-discharge management recognized as strategic priority",
    linkedPains: ["OP011"],
    linkedKPIs: ["OK031", "OK032"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["Readmission rate >15%", "HRRP penalty >$500K"]
  },
  {
    id: "OS012",
    signalName: "Pharmacy Automation or Formulary Management Investment",
    rawSignalPattern: "Purchase of automated dispensing cabinets, pharmacy robotics, or formulary decision support",
    interpretedMeaning: "Pharmacy operations seeking efficiency and safety improvement; spend pressure likely",
    linkedPains: ["OP012"],
    linkedKPIs: ["OK034", "OK035"],
    confidenceScore: 0.76,
    requiredConfirmationSignals: ["Drug spend growth >12% YoY", "ADC stockout complaints"]
  },
  {
    id: "OS013",
    signalName: "External Coding Audit Engagement",
    rawSignalPattern: "Engagement of external coding audit firm (HIA, nThrive, etc.) for 'revenue recovery' or 'compliance review'",
    interpretedMeaning: "Leadership suspects under-coding or compliance exposure requiring independent validation",
    linkedPains: ["OP013", "OP020"],
    linkedKPIs: ["OK037", "OK038"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["CMI declining or flat", "external audit findings pending"]
  },
  {
    id: "OS014",
    signalName: "Patient Financial Experience Platform Search",
    rawSignalPattern: "RFP for 'patient estimate', 'price transparency', 'payment plan automation', or 'digital check-in'",
    interpretedMeaning: "Rising patient financial responsibility creating collection and satisfaction pressure",
    linkedPains: ["OP014"],
    linkedKPIs: ["OK040", "OK041"],
    confidenceScore: 0.81,
    requiredConfirmationSignals: ["Bad debt >3.5% of NPR", "patient A/R >90 days >25%"]
  },
  {
    id: "OS015",
    signalName: "Eligibility/Insurance Discovery Vendor Search",
    rawSignalPattern: "Search for 'insurance discovery', 'eligibility verification automation', or 'coverage detection'",
    interpretedMeaning: "Front-end registration gaps recognized as denial and bad debt driver",
    linkedPains: ["OP015"],
    linkedKPIs: ["OK043", "OK044"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["Front-end denial rate >3%", "self-pay volume increasing"]
  },
  {
    id: "OS016",
    signalName: "HIM Outsourcing or Offshoring Announcement",
    rawSignalPattern: "Contract awarded for coding, ROI, or HIM functions to offshore or third-party vendor",
    interpretedMeaning: "Internal HIM capacity insufficient or cost pressure driving structural change",
    linkedPains: ["OP016"],
    linkedKPIs: ["OK046", "OK047"],
    confidenceScore: 0.79,
    requiredConfirmationSignals: ["HIM vacancy rate >15%", "DNFB increasing"]
  },
  {
    id: "OS017",
    signalName: "Laboratory Automation Investment",
    rawSignalPattern: "Purchase of automated lab line, total lab automation, or new LIS to replace legacy system",
    interpretedMeaning: "Lab TAT and quality issues driving capital investment; workforce shortage likely factor",
    linkedPains: ["OP017"],
    linkedKPIs: ["OK049", "OK050"],
    confidenceScore: 0.75,
    requiredConfirmationSignals: ["Stat TAT >60 min", "Specimen rejection rate >2%"]
  },
  {
    id: "OS018",
    signalName: "Referral Management Platform RFP",
    rawSignalPattern: "RFP for 'referral management', 'closed-loop referral', or 'provider directory' solution",
    interpretedMeaning: "Referral leakage and completion gaps recognized as revenue and quality risk",
    linkedPains: ["OP018"],
    linkedKPIs: ["OK052", "OK053"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["Referral completion rate <55%", "out-of-network SNF rate >30%"]
  },
  {
    id: "OS019",
    signalName: "Clearinghouse Switch or EDI Disruption Disclosure",
    rawSignalPattern: "Change in clearinghouse vendor, EDI connectivity issues in user forums, or cash flow variance disclosure",
    interpretedMeaning: "Claims submission infrastructure transition causing operational disruption",
    linkedPains: ["OP019"],
    linkedKPIs: ["OK055", "OK056"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["EDI rejection rate spike", "Cash posting delay >3 days"]
  },
  {
    id: "OS020",
    signalName: "MAC/RAC Audit Response Team Expansion",
    rawSignalPattern: "Job postings for 'audit defense', 'RAC coordinator', or 'compliance audit analyst'",
    interpretedMeaning: "Escalating external audit volume requiring dedicated response capacity",
    linkedPains: ["OP020"],
    linkedKPIs: ["OK058", "OK059"],
    confidenceScore: 0.87,
    requiredConfirmationSignals: ["CERT error rate >5%", "RAC appeal loss rate >35%"]
  }
];

// ============================================================================
// VALUE DRIVER EXAMPLES (15 representative from 40 total)
// ============================================================================

export interface ValueDriverMap {
  id: string;
  signalPattern: string;
  interpretedPain: string;
  valueDriverCategory: ValueCategory;
  linkedKPIs: string[];
  affectedPersonas: string[];
  confidence: ConfidenceLevel;
  requiredEvidence: string[];
}

export const valueDrivers: ValueDriverMap[] = [
  {
    id: "OV001",
    signalPattern: "Operational denial rate >10% with eligibility/registration as top root cause",
    interpretedPain: "Front-end revenue cycle process failure causing cascading denials and rework",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK001", "OK002", "OK003"],
    affectedPersonas: ["Revenue Cycle Director", "HIM Director", "CFO"],
    confidence: "HIGH",
    requiredEvidence: ["denial root cause analysis", "registration accuracy audit", "payer-specific denial breakdown"]
  },
  {
    id: "OV003",
    signalPattern: "PA turnaround >72h with electronic submission rate <50%",
    interpretedPain: "Manual prior auth process creating patient access barrier and revenue leakage",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["OK004", "OK005"],
    affectedPersonas: ["Care Coordinator", "Patient Access Director"],
    confidence: "HIGH",
    requiredEvidence: ["PA process map", "staff time study", "payer portal API status"]
  },
  {
    id: "OV005",
    signalPattern: "CDI query response rate <70% with retrospective query ratio >25%",
    interpretedPain: "Physician engagement gap in documentation improvement causing coding underperformance",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK007", "OK009"],
    affectedPersonas: ["CDI Manager", "CMO", "HIM Director"],
    confidence: "HIGH",
    requiredEvidence: ["physician-specific response rates", "query clarity audit", "EHR workflow review"]
  },
  {
    id: "OV007",
    signalPattern: "No-show rate >15% with new patient wait time >21 days",
    interpretedPain: "Access and scheduling inefficiency reducing throughput and provider productivity",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK010", "OK011", "OK012"],
    affectedPersonas: ["Patient Access Director", "Care Coordinator"],
    confidence: "HIGH",
    requiredEvidence: ["scheduling template analysis", "reminder system effectiveness", "patient feedback"]
  },
  {
    id: "OV009",
    signalPattern: "Credentialing cycle >120 days with application completion rate <55%",
    interpretedPain: "Credentialing process friction delaying provider revenue and access capacity",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK013", "OK015"],
    affectedPersonas: ["Credentialing Specialist", "Medical Staff Director"],
    confidence: "HIGH",
    requiredEvidence: ["application abandonment data", "payer-specific enrollment timelines", "privileging committee frequency"]
  },
  {
    id: "OV011",
    signalPattern: "Inventory turns <7 with expired product write-offs >1.5%",
    interpretedPain: "Supply chain carrying cost and waste eroding operating margin",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["OK016", "OK017"],
    affectedPersonas: ["Supply Chain Director", "CFO"],
    confidence: "HIGH",
    requiredEvidence: ["inventory aging report", "category-level turns analysis", "expired product log"]
  },
  {
    id: "OV013",
    signalPattern: "340B capture rate <80% with reconciliation lag >45 days",
    interpretedPain: "340B program leakage and compliance exposure from poor operational execution",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK019", "OK020", "OK021"],
    affectedPersonas: ["Pharmacy Operations Manager", "340B Program Director"],
    confidence: "HIGH",
    requiredEvidence: ["340B-eligible encounter tracking", "contract pharmacy reconciliation status", "HRSA audit history"]
  },
  {
    id: "OV015",
    signalPattern: "Clean claim rate <85% with charge lag >3 days",
    interpretedPain: "Charge capture and coding workflow delays creating downstream denial and cash delay",
    valueDriverCategory: "Working Capital",
    linkedKPIs: ["OK022", "OK023"],
    affectedPersonas: ["Revenue Cycle Director", "HIM Director"],
    confidence: "HIGH",
    requiredEvidence: ["charge lag by department", "front-end edit failure analysis", "coder productivity metrics"]
  },
  {
    id: "OV019",
    signalPattern: "Float pool utilization <55% with overtime >8% and agency >5%",
    interpretedPain: "Workforce scheduling mismatch—surplus internal capacity alongside premium external spend",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["OK028", "OK029"],
    affectedPersonas: ["Workforce Manager", "CNO"],
    confidence: "HIGH",
    requiredEvidence: ["float pool deployment log", "overtime by unit", "agency usage by unit"]
  },
  {
    id: "OV021",
    signalPattern: "7-day follow-up <55% with discharge summary delay >24h",
    interpretedPain: "Post-discharge care transition failure creating readmission and patient safety risk",
    valueDriverCategory: "Risk Reduction",
    linkedKPIs: ["OK031", "OK032"],
    affectedPersonas: ["Care Coordinator", "Case Management Director"],
    confidence: "HIGH",
    requiredEvidence: ["follow-up completion by condition", "discharge summary timeliness", "SNF handoff documentation"]
  },
  {
    id: "OV025",
    signalPattern: "DRG downgrade rate >2% with external audit recovery >$500K",
    interpretedPain: "Systematic coding accuracy and documentation gaps causing systematic underpayment",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK037", "OK038"],
    affectedPersonas: ["CDI Manager", "HIM Director", "CFO"],
    confidence: "HIGH",
    requiredEvidence: ["DRG downgrade reason analysis", "coder accuracy audit", "physician query effectiveness"]
  },
  {
    id: "OV027",
    signalPattern: "POS collection rate <20% with patient A/R >90 days >25%",
    interpretedPain: "Patient financial responsibility collection failure from poor estimation and payment tools",
    valueDriverCategory: "Working Capital",
    linkedKPIs: ["OK040", "OK041"],
    affectedPersonas: ["Revenue Cycle Director", "Patient Access Director"],
    confidence: "HIGH",
    requiredEvidence: ["price estimation usage rate", "payment plan performance", "patient collection policy"]
  },
  {
    id: "OV031",
    signalPattern: "ROI turnaround >5 days with HIM vacancy rate >15%",
    interpretedPain: "Health information management staffing crisis affecting compliance and revenue",
    valueDriverCategory: "Cost Savings",
    linkedKPIs: ["OK046", "OK047"],
    affectedPersonas: ["HIM Director", "Compliance Officer"],
    confidence: "HIGH",
    requiredEvidence: ["HIM staffing plan", "ROI request queue", "outsourcing cost analysis"]
  },
  {
    id: "OV035",
    signalPattern: "Referral completion rate <50% with loop closure <45%",
    interpretedPain: "Referral management workflow failure causing care gaps and revenue leakage",
    valueDriverCategory: "Revenue Uplift",
    linkedKPIs: ["OK052", "OK053"],
    affectedPersonas: ["Care Coordinator", "Chief Strategy Officer"],
    confidence: "HIGH",
    requiredEvidence: ["referral status tracking data", "incomplete referral reason analysis", "EHR referral workflow review"]
  },
  {
    id: "OV039",
    signalPattern: "RAC appeal loss rate >35% with CERT error rate >5%",
    interpretedPain: "Systematic coding and documentation accuracy failure with compliance exposure",
    valueDriverCategory: "Risk Reduction",
    linkedKPIs: ["OK058", "OK059"],
    affectedPersonas: ["HIM Director", "Compliance Officer"],
    confidence: "HIGH",
    requiredEvidence: ["appeal outcome analysis", "CERT error root cause", "coder training record"]
  }
];

// ============================================================================
// WORKED EXAMPLE CALCULATORS (3 fully implemented)
// ============================================================================

export function calculateDenialReductionValue(
  currentDenialRate: number,
  targetDenialRate: number,
  annualGrossCharges: number,
  contractualAdjustmentPct: number,
  collectibleYieldPct: number,
  implementationCost: number,
  reworkFTEsSaved: number,
  averageFTECost: number
): WorkedExample["outcome"] {
  const denialRateReduction = currentDenialRate - targetDenialRate;
  const revenueUplift = (denialRateReduction / 100) * annualGrossCharges * (1 - contractualAdjustmentPct / 100) * (collectibleYieldPct / 100);
  const costSavings = reworkFTEsSaved * averageFTECost;
  const workingCapitalImprovement = revenueUplift * 0.28; // estimated cash flow acceleration
  const totalYearOneValue = revenueUplift + costSavings - implementationCost;
  const threeYearNPV = totalYearOneValue * 2.51; // simplified NPV factor for 3 years at 10%
  const paybackMonths = implementationCost / ((revenueUplift + costSavings) / 12);

  return {
    revenueUplift: Math.round(revenueUplift),
    costSavings: Math.round(costSavings),
    riskReduction: 0,
    workingCapitalImprovement: Math.round(workingCapitalImprovement),
    totalYearOneValue: Math.round(totalYearOneValue),
    threeYearNPV: Math.round(threeYearNPV),
    paybackMonths: Math.round(paybackMonths * 10) / 10
  };
}

export function calculatePriorAuthAutomationValue(
  annualPAVolume: number,
  currentHoursPerPA: number,
  targetHoursPerPA: number,
  hourlyStaffCost: number,
  physicianCount: number,
  hoursSavedPerPhysicianMonth: number,
  physicianHourlyRate: number,
  currentAbandonmentRate: number,
  targetAbandonmentRate: number,
  avgRevenuePerPACase: number,
  appealReduction: number,
  costPerAppeal: number,
  implementationCost: number
): WorkedExample["outcome"] {
  const staffTimeSavings = annualPAVolume * (currentHoursPerPA - targetHoursPerPA) * hourlyStaffCost;
  const physicianTimeSavings = physicianCount * hoursSavedPerPhysicianMonth * 12 * physicianHourlyRate;
  const abandonmentValue = ((currentAbandonmentRate - targetAbandonmentRate) / 100) * annualPAVolume * avgRevenuePerPACase;
  const appealSavings = appealReduction * costPerAppeal;
  const revenueUplift = abandonmentValue;
  const costSavings = staffTimeSavings + physicianTimeSavings + appealSavings;
  const totalYearOneValue = revenueUplift + costSavings - implementationCost;
  const threeYearNPV = totalYearOneValue * 3.12;
  const paybackMonths = implementationCost / ((revenueUplift + costSavings) / 12);

  return {
    revenueUplift: Math.round(revenueUplift),
    costSavings: Math.round(costSavings),
    riskReduction: 0,
    workingCapitalImprovement: 0,
    totalYearOneValue: Math.round(totalYearOneValue),
    threeYearNPV: Math.round(threeYearNPV),
    paybackMonths: Math.round(paybackMonths * 10) / 10
  };
}

export function calculate340BOptimizationValue(
  eligibleEncounters: number,
  currentCaptureRate: number,
  targetCaptureRate: number,
  avgWACDiscount: number,
  duplicateDiscountExposure: number,
  manufacturerRestrictionLoss: number,
  manufacturerRecoverablePct: number,
  contractPharmacyCount: number,
  reconciliationLaborSavingsPerPharmacy: number,
  implementationCost: number
): WorkedExample["outcome"] {
  const captureValue = eligibleEncounters * ((targetCaptureRate - currentCaptureRate) / 100) * avgWACDiscount;
  const duplicateAvoidance = duplicateDiscountExposure;
  const manufacturerRecovery = manufacturerRestrictionLoss * (manufacturerRecoverablePct / 100);
  const reconciliationSavings = contractPharmacyCount * reconciliationLaborSavingsPerPharmacy;
  const revenueUplift = captureValue;
  const costSavings = reconciliationSavings;
  const riskReduction = duplicateAvoidance;
  const workingCapitalImprovement = revenueUplift * 0.038; // modest cash flow impact
  const totalYearOneValue = revenueUplift + costSavings + riskReduction + workingCapitalImprovement - implementationCost;
  const threeYearNPV = totalYearOneValue * 3.09;
  const paybackMonths = implementationCost / ((revenueUplift + costSavings + riskReduction + workingCapitalImprovement) / 12);

  return {
    revenueUplift: Math.round(revenueUplift),
    costSavings: Math.round(costSavings),
    riskReduction: Math.round(riskReduction),
    workingCapitalImprovement: Math.round(workingCapitalImprovement),
    totalYearOneValue: Math.round(totalYearOneValue),
    threeYearNPV: Math.round(threeYearNPV),
    paybackMonths: Math.round(paybackMonths * 10) / 10
  };
}

// ============================================================================
// EXAMPLE USAGE
// ============================================================================

export const exampleUsage = {
  denialReduction: calculateDenialReductionValue(
    13.5, 7.0, 420_000_000, 58, 82, 1_800_000, 12, 62_000
  ),
  priorAuthAutomation: calculatePriorAuthAutomationValue(
    18_000, 4.2, 0.5, 32, 150, 6.5, 85, 9, 3, 1250, 2760, 85, 480_000
  ),
  b340Optimization: calculate340BOptimizationValue(
    145_000, 74, 90, 315, 420_000, 680_000, 60, 8, 18_000, 890_000
  )
};

// Log examples when loaded
// console.log("Healthcare Operations Subpack Examples Loaded");
// console.log("Denial Reduction Example:", exampleUsage.denialReduction);
// console.log("PA Automation Example:", exampleUsage.priorAuthAutomation);
// console.log("340B Optimization Example:", exampleUsage.b340Optimization);
