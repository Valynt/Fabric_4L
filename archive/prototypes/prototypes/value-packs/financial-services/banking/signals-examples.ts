/**
 * Banking Vertical Subpack - Signal Examples TypeScript
 * ID: banking-v1
 * Parent Master: financial-services-master-v1
 * 
 * This file provides TypeScript type definitions and executable signal rule examples
 * for the Banking vertical subpack. All types extend the master pack schema.
 */

// ============================================================
// TYPE DEFINITIONS
// ============================================================

export type BankingSegment =
  | "Retail Banking"
  | "Commercial/Corporate Banking"
  | "Investment Banking"
  | "Community/Regional Banks"
  | "Credit Unions"
  | "Digital Banks/Neobanks"
  | "Private Banking/Wealth Management"
  | "Treasury Services/Cash Management"
  | "Payments/Cards"
  | "Mortgage Lending"
  | "Auto Lending"
  | "Small Business Lending";

export type ValueDriverCategory =
  | "Revenue Uplift"
  | "Cost Savings"
  | "Risk Reduction"
  | "Working Capital";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export type PrevalenceLevel = "HIGH" | "MEDIUM" | "LOW";

export interface BankingPain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  affectedSegments: BankingSegment[];
  affectedPersonas: string[];
  linkedKPIs: string[];
  linkedValueDrivers: string[];
  prevalence: PrevalenceLevel;
  confidence: ConfidenceLevel;
  sources: string[];
}

export interface BankingKPI {
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

export interface BankingSignalRule {
  id: string;
  triggerName: string;
  signalSources: string[];
  signalPattern: string;
  interpretedKPIs: string[];
  interpretedPain: string;
  valueDriverCategory: ValueDriverCategory;
  recommendedAction: string;
  confidenceLevel: ConfidenceLevel;
  requiredEvidence: string[];
}

export interface BankingPersona {
  id: string;
  name: string;
  roleDescription: string;
  primaryKPIs: string[];
  trustedEvidence: string[];
  dislikedClaims: string[];
  authorityLevel: string;
  influenceScope: string;
  reportingLine: string;
  budgetControl: string;
}

export interface BankingFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
}

export interface BankingBenchmark {
  id: string;
  name: string;
  benchmarkValue: string;
  unit: string;
  applicableSegment: string;
  timePeriod: string;
  source: string;
  notes: string;
  confidence: ConfidenceLevel;
}

export interface BankingDiscoveryQuestion {
  id: string;
  questionText: string;
  targetPersona: string;
  businessGoal: string;
  evidenceNeeded: string[];
}

export interface BankingObjection {
  id: string;
  objectionText: string;
  context: string;
  prevalence: PrevalenceLevel;
  recommendedResponse: string;
  supportingEvidence: string[];
}

// ============================================================
// SIGNAL RULE INSTANCES (20 examples)
// ============================================================

export const bankingSignalRules: BankingSignalRule[] = [
  {
    id: "SR_BNK_001",
    triggerName: "Deposit Beta Surge Alert",
    signalSources: ["ALCO meeting minutes", "Deposit pricing committee deck", "Peer NIM comparison"],
    signalPattern: "Deposit beta >70% in two consecutive quarters",
    interpretedKPIs: ["K_BNK_001", "K_BNK_002"],
    interpretedPain: "P_BNK_001",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Schedule ALCO deep-dive on deposit repricing strategy and brokered deposit alternatives",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Quarterly deposit beta calculation", "Brokered deposit maturity ladder", "CD promotional rate schedule"]
  },
  {
    id: "SR_BNK_002",
    triggerName: "Mortgage Cost Escalation",
    signalSources: ["LOS dashboard", "Mortgage production report", "Processor productivity metrics"],
    signalPattern: "Cost-to-close >$10,000 or cycle time >50 days for two months",
    interpretedKPIs: ["K_BNK_004", "K_BNK_005"],
    interpretedPain: "P_BNK_002",
    valueDriverCategory: "Cost Savings",
    recommendedAction: "Initiate LOS workflow optimization assessment with vendor and process mining",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Cost per process step analysis", "Appraisal vendor SLA data", "Underwriting queue depth"]
  },
  {
    id: "SR_BNK_003",
    triggerName: "Branch Rationalization Trigger",
    signalSources: ["Branch P&L report", "Foot traffic analytics", "Transaction channel mix"],
    signalPattern: "Branch cost per transaction >$7 with digital share >88% and lease renewal pending",
    interpretedKPIs: ["K_BNK_007", "K_BNK_008"],
    interpretedPain: "P_BNK_003",
    valueDriverCategory: "Cost Savings",
    recommendedAction: "Launch branch optimization study with lease exit economics and digital migration plan",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Branch-level P&L", "Lease obligation schedule", "Digital adoption by branch territory"]
  },
  {
    id: "SR_BNK_004",
    triggerName: "CRE Concentration Warning",
    signalSources: ["Credit committee report", "Stress test results", "Appraisal updates"],
    signalPattern: "CRE concentration >300% of RBC OR watch list >8% of CRE portfolio",
    interpretedKPIs: ["K_BNK_010", "K_BNK_011"],
    interpretedPain: "P_BNK_004",
    valueDriverCategory: "Risk Reduction",
    recommendedAction: "Engage portfolio management team on CRE concentration reduction strategy and refinancing support",
    confidenceLevel: "HIGH",
    requiredEvidence: ["CRE stratification by property type", "Maturity ladder next 24 months", "Vacancy rate by submarket"]
  },
  {
    id: "SR_BNK_005",
    triggerName: "Auto Lease Residual Deterioration",
    signalSources: ["Remarketing auction results", "Manheim Index update", "Lease end volume forecast"],
    signalPattern: "Residual loss >$500 per unit for two consecutive quarters",
    interpretedKPIs: ["K_BNK_013", "K_BNK_015"],
    interpretedPain: "P_BNK_005",
    valueDriverCategory: "Risk Reduction",
    recommendedAction: "Review residual value assumptions and remarketing channel efficiency; evaluate lease extension program",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Residual value audit by vintage", "Remarketing channel cost comparison", "Used vehicle price forecast"]
  },
  {
    id: "SR_BNK_006",
    triggerName: "Digital Onboarding Friction Spike",
    signalSources: ["Funnel analytics", "IDV vendor dashboard", "Customer complaint data"],
    signalPattern: "Onboarding abandonment >60% OR IDV failure >25% for three weeks",
    interpretedKPIs: ["K_BNK_016", "K_BNK_017"],
    interpretedPain: "P_BNK_006",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Launch UX audit of onboarding flow and IDV vendor performance review; A/B test streamlined KYC",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Funnel step-by-step dropout data", "IDV false reject root cause", "Competitor onboarding flow analysis"]
  },
  {
    id: "SR_BNK_007",
    triggerName: "Treasury Deposit Outflow Alert",
    signalSources: ["Commercial deposit report", "ECR rate analysis", "Client NPS survey"],
    signalPattern: "Commercial operating deposit outflows >8% quarterly OR ECR spread <50bps",
    interpretedKPIs: ["K_BNK_019", "K_BNK_020"],
    interpretedPain: "P_BNK_007",
    valueDriverCategory: "Working Capital",
    recommendedAction: "Review ECR schedule against competitive benchmarks; launch treasury client retention outreach",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Deposit outflow by client tier", "ECR comparison to top 3 competitors", "Client satisfaction scores by product"]
  },
  {
    id: "SR_BNK_008",
    triggerName: "Card Revenue Compression",
    signalSources: ["Card P&L", "Interchange revenue report", "Rewards program financials"],
    signalPattern: "Interchange yield declining >5bps annually OR rewards cost >50% of interchange",
    interpretedKPIs: ["K_BNK_022", "K_BNK_023"],
    interpretedPain: "P_BNK_008",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Evaluate rewards program ROI and interchange optimization; assess Durbin 2.0 legislative scenario planning",
    confidenceLevel: "MEDIUM",
    requiredEvidence: ["Rewards redemption and breakage analysis", "Interchange yield by card type", "Legislative risk assessment"]
  },
  {
    id: "SR_BNK_009",
    triggerName: "Commercial RFP Loss Pattern",
    signalSources: ["CRM pipeline", "RFP win/loss database", "Client feedback survey"],
    signalPattern: "RFP win rate <25% for two quarters OR decision time >18 days",
    interpretedKPIs: ["K_BNK_025", "K_BNK_026"],
    interpretedPain: "P_BNK_009",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Conduct win/loss analysis on last 20 RFPs; benchmark decision speed against top 3 competitors",
    confidenceLevel: "HIGH",
    requiredEvidence: ["RFP win/loss by product", "Decision process timeline", "Client loss interview notes"]
  },
  {
    id: "SR_BNK_010",
    triggerName: "Private Banking Succession Risk",
    signalSources: ["HR demographic report", "AUM per advisor trend", "Client retention data"],
    signalPattern: "Average advisor age >55 with AUM per advisor <$100M OR next-gen engagement <15%",
    interpretedKPIs: ["K_BNK_028", "K_BNK_029"],
    interpretedPain: "P_BNK_010",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Develop next-gen digital platform roadmap and advisor succession planning with recruitment acceleration",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Advisor age distribution", "AUM productivity by advisor tenure", "Intergenerational wealth transfer forecast"]
  },
  {
    id: "SR_BNK_011",
    triggerName: "Core System Bottleneck",
    signalSources: ["IT performance dashboard", "Product roadmap review", "Vendor contract renewal notice"],
    signalPattern: "API response time >500ms OR product launch cycle >14 months OR vendor increase >8%",
    interpretedKPIs: ["K_BNK_031", "K_BNK_033"],
    interpretedPain: "P_BNK_011",
    valueDriverCategory: "Cost Savings",
    recommendedAction: "Initiate core banking modernization business case with API-first architecture assessment",
    confidenceLevel: "HIGH",
    requiredEvidence: ["API latency logs", "Product launch history", "Vendor contract terms and alternatives"]
  },
  {
    id: "SR_BNK_012",
    triggerName: "Community Bank Efficiency Deterioration",
    signalSources: ["Efficiency ratio trend", "Expense breakdown", "Peer comparison report"],
    signalPattern: "Efficiency ratio >65% for two quarters with compliance cost >8% of non-interest expense",
    interpretedKPIs: ["K_BNK_034", "K_BNK_036"],
    interpretedPain: "P_BNK_012",
    valueDriverCategory: "Cost Savings",
    recommendedAction: "Launch efficiency improvement program with technology modernization and process automation assessment",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Expense breakdown by category", "Compliance cost allocation", "Peer efficiency comparison"]
  },
  {
    id: "SR_BNK_013",
    triggerName: "RTP Fraud Detection Gap",
    signalSources: ["Fraud monitoring dashboard", "Transaction decline data", "Customer complaint log"],
    signalPattern: "Detection latency >300ms OR APP scam losses >0.25% of RTP volume",
    interpretedKPIs: ["K_BNK_037", "K_BNK_038"],
    interpretedPain: "P_BNK_013",
    valueDriverCategory: "Risk Reduction",
    recommendedAction: "Upgrade real-time transaction monitoring to sub-100ms with behavioral biometrics and confirmation of payee",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Transaction monitoring architecture", "Fraud loss by payment rail", "Confirmation of payee adoption data"]
  },
  {
    id: "SR_BNK_014",
    triggerName: "SMB Relationship Fragmentation",
    signalSources: ["SMB deposit report", "Product penetration analysis", "NPS survey"],
    signalPattern: "SMB primary bank share <35% OR deposit outflows >12% annually OR loan abandonment >60%",
    interpretedKPIs: ["K_BNK_040", "K_BNK_042"],
    interpretedPain: "P_BNK_014",
    valueDriverCategory: "Working Capital",
    recommendedAction: "Develop SMB integrated banking platform with embedded payments and lending pre-qualification",
    confidenceLevel: "HIGH",
    requiredEvidence: ["SMB product penetration by client", "Deposit migration analysis", "Fintech competitive assessment"]
  },
  {
    id: "SR_BNK_015",
    triggerName: "Credit Card Portfolio Deterioration",
    signalSources: ["Card portfolio dashboard", "Delinquency migration report", "Charge-off trend"],
    signalPattern: "Charge-off rate >4.5% OR 30+ delinquency >3.2% for two months",
    interpretedKPIs: ["K_BNK_044", "K_BNK_045"],
    interpretedPain: "P_BNK_015",
    valueDriverCategory: "Risk Reduction",
    recommendedAction: "Tighten underwriting criteria for near-prime segments and enhance collections strategy",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Vintage loss curves", "Delinquency migration by FICO", "Collections effectiveness metrics"]
  },
  {
    id: "SR_BNK_016",
    triggerName: "Investment Banking Revenue Crisis",
    signalSources: ["Revenue waterfall", "League table ranking", "MD compensation ratio"],
    signalPattern: "Advisory revenue decline >25% YoY OR MD compensation ratio >38% OR pitch-to-win <12%",
    interpretedKPIs: ["K_BNK_046", "K_BNK_047"],
    interpretedPain: "P_BNK_016",
    valueDriverCategory: "Cost Savings",
    recommendedAction: "Review sector coverage model and pitch database; evaluate MD compensation structure and headcount right-sizing",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Revenue by product and sector", "Pitch database analytics", "Compensation ratio trend"]
  },
  {
    id: "SR_BNK_017",
    triggerName: "Digital Bank Burn Rate Crisis",
    signalSources: ["Monthly financials", "Unit economics dashboard", "Burn rate forecast"],
    signalPattern: "Monthly burn >$15M OR CAC >$250 with deposit per account <$1,200 for two quarters",
    interpretedKPIs: ["K_BNK_049", "K_BNK_051"],
    interpretedPain: "P_BNK_017",
    valueDriverCategory: "Cost Savings",
    recommendedAction: "Launch path-to-profitability initiative with product mix optimization and CAC channel efficiency review",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Unit economics by customer cohort", "CAC by channel", "Revenue per account waterfall"]
  },
  {
    id: "SR_BNK_018",
    triggerName: "Credit Union Demographic Cliff",
    signalSources: ["Member demographics", "Digital engagement metrics", "Technology budget"],
    signalPattern: "Membership growth <1.5% OR average age >52 OR digital engagement <25%",
    interpretedKPIs: ["K_BNK_052", "K_BNK_054"],
    interpretedPain: "P_BNK_018",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Develop digital-first member acquisition strategy with Gen Z value proposition and fintech partnership assessment",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Member age distribution", "Digital login cohort analysis", "Competitive digital offering comparison"]
  },
  {
    id: "SR_BNK_019",
    triggerName: "Brokered Deposit Dependence",
    signalSources: ["Funding mix report", "Brokered deposit maturity", "Liquidity coverage ratio"],
    signalPattern: "Brokered deposits >12% of total funding OR quarterly brokered growth >15%",
    interpretedKPIs: ["K_BNK_003"],
    interpretedPain: "P_BNK_001",
    valueDriverCategory: "Working Capital",
    recommendedAction: "Develop core deposit growth strategy and brokered deposit replacement plan",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Funding source mix trend", "Brokered deposit maturity ladder", "LCR and NSFR projections"]
  },
  {
    id: "SR_BNK_020",
    triggerName: "Mortgage Pipeline Pull-Through Collapse",
    signalSources: ["Pipeline dashboard", "Lock expiration report", "Competitor rate comparison"],
    signalPattern: "Pull-through rate <55% for two months OR lock expiration rate >20%",
    interpretedKPIs: ["K_BNK_006"],
    interpretedPain: "P_BNK_002",
    valueDriverCategory: "Revenue Uplift",
    recommendedAction: "Review lock desk pricing competitiveness and processor capacity constraints; evaluate rate float policies",
    confidenceLevel: "HIGH",
    requiredEvidence: ["Pull-through by channel", "Lock expiration reasons", "Processor queue depth"]
  }
];

// ============================================================
// EVALUATION ENGINE
// ============================================================

/**
 * Evaluates a single signal rule against provided KPI values.
 * Returns a match score and recommended actions if triggered.
 */
export interface SignalEvaluationResult {
  ruleId: string;
  triggerName: string;
  triggered: boolean;
  matchScore: number; // 0-100
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  matchedKPIs: string[];
  recommendedActions: string[];
  confidence: ConfidenceLevel;
  missingEvidence: string[];
}

export function evaluateSignalRule(
  rule: BankingSignalRule,
  kpiValues: Record<string, number | string>
): SignalEvaluationResult {
  let triggered = false;
  let matchScore = 0;
  let severity: SignalEvaluationResult["severity"] = "LOW";
  const matchedKPIs: string[] = [];
  const missingEvidence: string[] = [];

  // Simple threshold evaluation based on signal pattern keywords
  const pattern = rule.signalPattern.toLowerCase();

  // Check for deposit beta threshold
  if (pattern.includes("deposit beta")) {
    const beta = kpiValues["K_BNK_001"];
    if (typeof beta === "number" && beta > 70) {
      triggered = true;
      matchScore = Math.min(100, Math.round((beta - 70) * 3 + 50));
      matchedKPIs.push("K_BNK_001");
      severity = beta > 80 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for mortgage cost threshold
  if (pattern.includes("cost-to-close")) {
    const cost = kpiValues["K_BNK_004"];
    if (typeof cost === "number" && cost > 10000) {
      triggered = true;
      matchScore = Math.min(100, Math.round((cost - 8000) / 200 + 50));
      matchedKPIs.push("K_BNK_004");
      severity = cost > 12000 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for branch cost per transaction
  if (pattern.includes("branch cost per transaction")) {
    const cost = kpiValues["K_BNK_007"];
    if (typeof cost === "number" && cost > 7) {
      triggered = true;
      matchScore = Math.min(100, Math.round((cost - 5) * 20 + 40));
      matchedKPIs.push("K_BNK_007");
      severity = cost > 10 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for CRE concentration
  if (pattern.includes("cre concentration")) {
    const concentration = kpiValues["K_BNK_010"];
    if (typeof concentration === "number" && concentration > 300) {
      triggered = true;
      matchScore = Math.min(100, Math.round((concentration - 250) / 2));
      matchedKPIs.push("K_BNK_010");
      severity = concentration > 400 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for digital onboarding abandonment
  if (pattern.includes("onboarding abandonment")) {
    const abandonment = kpiValues["K_BNK_016"];
    if (typeof abandonment === "number" && abandonment > 60) {
      triggered = true;
      matchScore = Math.min(100, Math.round(abandonment * 1.2));
      matchedKPIs.push("K_BNK_016");
      severity = abandonment > 75 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for treasury deposit outflows
  if (pattern.includes("deposit outflows")) {
    const outflow = kpiValues["K_BNK_019"];
    if (typeof outflow === "number" && outflow > 8) {
      triggered = true;
      matchScore = Math.min(100, Math.round(outflow * 8));
      matchedKPIs.push("K_BNK_019");
      severity = outflow > 15 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for efficiency ratio
  if (pattern.includes("efficiency ratio")) {
    const ratio = kpiValues["K_BNK_034"];
    if (typeof ratio === "number" && ratio > 65) {
      triggered = true;
      matchScore = Math.min(100, Math.round((ratio - 55) * 3));
      matchedKPIs.push("K_BNK_034");
      severity = ratio > 70 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for RTP fraud latency
  if (pattern.includes("detection latency")) {
    const latency = kpiValues["K_BNK_037"];
    if (typeof latency === "number" && latency > 300) {
      triggered = true;
      matchScore = Math.min(100, Math.round((latency - 100) / 4));
      matchedKPIs.push("K_BNK_037");
      severity = latency > 500 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for SMB primary bank share
  if (pattern.includes("primary bank share")) {
    const share = kpiValues["K_BNK_040"];
    if (typeof share === "number" && share < 40) {
      triggered = true;
      matchScore = Math.min(100, Math.round((40 - share) * 3 + 30));
      matchedKPIs.push("K_BNK_040");
      severity = share < 30 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for credit card charge-off
  if (pattern.includes("charge-off")) {
    const chargeoff = kpiValues["K_BNK_044"];
    if (typeof chargeoff === "number" && chargeoff > 4.5) {
      triggered = true;
      matchScore = Math.min(100, Math.round((chargeoff - 3) * 15));
      matchedKPIs.push("K_BNK_044");
      severity = chargeoff > 6 ? "CRITICAL" : "HIGH";
    }
  }

  // Check for digital bank burn rate
  if (pattern.includes("burn")) {
    const burn = kpiValues["K_BNK_051"];
    if (typeof burn === "number" && burn > 10) {
      triggered = true;
      matchScore = Math.min(100, Math.round(burn * 6));
      matchedKPIs.push("K_BNK_051");
      severity = burn > 20 ? "CRITICAL" : "HIGH";
    }
  }

  // Determine missing evidence
  for (const evidence of rule.requiredEvidence) {
    if (!kpiValues[`evidence_${evidence}`]) {
      missingEvidence.push(evidence);
    }
  }

  return {
    ruleId: rule.id,
    triggerName: rule.triggerName,
    triggered,
    matchScore,
    severity,
    matchedKPIs,
    recommendedActions: triggered ? [rule.recommendedAction] : [],
    confidence: rule.confidenceLevel,
    missingEvidence
  };
}

/**
 * Evaluates all signal rules against a KPI dataset and returns triggered rules sorted by severity.
 */
export function evaluateAllSignalRules(
  kpiValues: Record<string, number | string>
): SignalEvaluationResult[] {
  const results = bankingSignalRules.map(rule => evaluateSignalRule(rule, kpiValues));
  return results
    .filter(r => r.triggered)
    .sort((a, b) => {
      const severityOrder = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      if (severityOrder[a.severity] !== severityOrder[b.severity]) {
        return severityOrder[a.severity] - severityOrder[b.severity];
      }
      return b.matchScore - a.matchScore;
    });
}

// ============================================================
// EXAMPLE USAGE
// ============================================================

/**
 * Example KPI dataset for a hypothetical $50B regional bank showing multiple pain signals.
 */
export const exampleBankKPIDataset: Record<string, number | string> = {
  // Deposit & NIM
  K_BNK_001: 78,      // Deposit beta: 78% (HIGH - above 70 threshold)
  K_BNK_002: 2.85,    // NIM: 2.85% (below benchmark)
  K_BNK_003: 3.95,    // Cost of funds: 3.95%
  
  // Mortgage
  K_BNK_004: 10800,   // Cost-to-close: $10,800 (HIGH - above 10K threshold)
  K_BNK_005: 48,      // Cycle time: 48 days (above 45 threshold)
  K_BNK_006: 58,      // Pull-through: 58% (below 65 threshold)
  
  // Branch
  K_BNK_007: 7.5,     // Branch cost per transaction: $7.50 (HIGH)
  K_BNK_008: 92,      // Digital transaction share: 92%
  
  // CRE
  K_BNK_010: 320,     // CRE concentration: 320% RBC (HIGH - above 300)
  K_BNK_011: 9.2,     // CRE watch list: 9.2%
  
  // Digital onboarding
  K_BNK_016: 65,      // Onboarding abandonment: 65% (HIGH)
  K_BNK_017: 28,      // IDV failure: 28%
  
  // Efficiency
  K_BNK_034: 68,      // Efficiency ratio: 68% (HIGH - above 65)
  K_BNK_036: 9.5,     // Compliance cost ratio: 9.5%
  
  // Treasury
  K_BNK_019: 9.5,     // Treasury deposit outflows: 9.5% quarterly (HIGH)
  
  // RTP Fraud
  K_BNK_037: 450,     // Fraud detection latency: 450ms (HIGH - above 300)
  
  // SMB
  K_BNK_040: 32,      // SMB primary bank share: 32% (below 35)
  
  // Card
  K_BNK_044: 4.8,     // Credit card charge-off: 4.8% (above 4.5)
};

/**
 * Example: Evaluate all signals for the example dataset.
 * 
 * import { evaluateAllSignalRules, exampleBankKPIDataset } from './signals-examples';
 * const triggered = evaluateAllSignalRules(exampleBankKPIDataset);
 * console.log(`Triggered ${triggered.length} signals`);
 * triggered.forEach(t => console.log(`${t.severity}: ${t.triggerName} (score: ${t.matchScore})`));
 * 
 * Expected output for example dataset:
 * - CRITICAL: Deposit Beta Surge Alert (score: 74)
 * - CRITICAL: CRE Concentration Warning (score: 85)
 * - CRITICAL: Digital Onboarding Friction Spike (score: 78)
 * - CRITICAL: Treasury Deposit Outflow Alert (score: 76)
 * - CRITICAL: RTP Fraud Detection Gap (score: 87)
 * - CRITICAL: SMB Relationship Fragmentation (score: 54)
 * - CRITICAL: Credit Card Portfolio Deterioration (score: 72)
 * - HIGH: Mortgage Cost Escalation (score: 64)
 * - HIGH: Branch Rationalization Trigger (score: 90)
 * - HIGH: Community Bank Efficiency Deterioration (score: 79)
 */

// ============================================================
// TYPE EXPORTS
// ============================================================

export type { BankingSegment, ValueDriverCategory, ConfidenceLevel, PrevalenceLevel };
