/**
 * Risk, Compliance, and Financial Crime Subpack
 * Signal Interpretation Examples and TypeScript Interface Definitions
 * 
 * Pack ID: risk-compliance-v1
 * Parent: financial-services-master-v1
 * Version: 1.0.0
 * 
 * These examples demonstrate how raw market/regulatory/technology signals
 * are interpreted into actionable business pains with financial outcomes.
 */

// ============================================================
// TYPE DEFINITIONS (Vertical-Specialized Extensions)
// ============================================================

interface RiskCompliancePain {
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

interface RiskComplianceKPI {
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

interface RiskComplianceSignalRule {
  id: string;
  name: string;
  signalPattern: string;
  interpretedPainId: string;
  confidenceLevel: "HIGH" | "MEDIUM" | "LOW";
  confidenceRationale: string;
  linkedPersonas: string[];
  requiredEvidence: string[];
  linkedKPIs: string[];
  financialImpactCategory: "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
  impactEstimateRange: string;
}

interface RiskComplianceFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
}

interface RiskComplianceWorkedExample {
  id: string;
  title: string;
  inputs: Record<string, number>;
  results: {
    annualBenefit: string;
    implementationCost: string;
    paybackPeriodMonths: number;
    threeYearNPV: string;
    roi: string;
  };
  confidence: "HIGH" | "MEDIUM" | "LOW";
  keyTakeaway: string;
}

// ============================================================
// SIGNAL INTERPRETATION EXAMPLES
// ============================================================

/**
 * Example 1: OFAC Enforcement Action Signal
 * 
 * RAW SIGNAL: OFAC announces $140M civil penalty against a major US bank
 * for sanctions compliance failures including defective interdiction software
 * and inadequate look-back procedures.
 * 
 * INTERPRETATION CHAIN:
 */
const ofacEnforcementSignal: RiskComplianceSignalRule = {
  id: "RC-SR002",
  name: "OFAC Consent Order Detection",
  signalPattern: "Active or settled OFAC consent order within last 36 months",
  interpretedPainId: "RC-P001",
  confidenceLevel: "HIGH",
  confidenceRationale: "Regulatory enforcement is direct evidence of sanctions program weakness with quantifiable penalty history",
  linkedPersonas: ["RC-PER001", "PER004"],
  requiredEvidence: ["OFAC enforcement action public record", "Consent order terms", "Remediation spend"],
  linkedKPIs: ["RC-K001", "RC-K003"],
  financialImpactCategory: "Risk Reduction",
  impactEstimateRange: "$1M-$500M (penalty scale)"
};

// Financial outcome mapping:
// - Direct penalty: $140M (observed)
// - Remediation cost: $50M-$100M (typical for consent orders with independent monitor)
// - Business restriction: Revenue loss from de-risking correspondent relationships
// - Technology upgrade: $5M-$15M for screening engine replacement/tuning
// - Reputational: Unquantified but material in correspondent banking relationships

/**
 * Example 2: CFPB Complaint Velocity Spike
 * 
 * RAW SIGNAL: CFPB Consumer Complaint Database shows 180% YoY increase
 * in complaints against a national bank, with 35% categorized as
 * "unexpected fees" and "account closure without notice."
 * 
 * INTERPRETATION CHAIN:
 */
const cfpbComplaintSignal: RiskComplianceSignalRule = {
  id: "RC-SR010",
  name: "CFPB Supervision Signal",
  signalPattern: "Active CFPB supervision or public enforcement action within 18 months",
  interpretedPainId: "RC-P008",
  confidenceLevel: "HIGH",
  confidenceRationale: "Active supervision indicates validated consumer harm pattern with consent order precedent",
  linkedPersonas: ["PER004"],
  requiredEvidence: ["CFPB enforcement action database", "Consent order terms", "Supervisory letter"],
  linkedKPIs: ["RC-K022", "RC-K023"],
  financialImpactCategory: "Risk Reduction",
  impactEstimateRange: "$5M-$50M in compliance cost and penalty"
};

// Financial outcome mapping:
// - Complaint handling cost: 10,000 additional complaints * $1,200 = $12M/year
// - UDAAP remediation: Product redesign, fee reversal, customer remediation = $5M-$15M
// - Consent order: $2M-$50M penalty (CFPB scale based on asset size)
// - Civil money penalty fund: $1M-$10M
// - Reputational: Customer acquisition cost increase, deposit attrition

/**
 * Example 3: VaR Backtesting Exception Cluster
 * 
 * RAW SIGNAL: A global trading bank reports 4 VaR backtesting exceptions
 * in the last 90 days, with no model update scheduled for 6 months.
 * FRTB parallel run shows 22% capital inflation.
 * 
 * INTERPRETATION CHAIN:
 */
const varBacktestSignal: RiskComplianceSignalRule = {
  id: "RC-SR005",
  name: "VaR Backtesting Exception Cluster",
  signalPattern: "3+ backtesting exceptions in trailing 90 days with no model update in progress",
  interpretedPainId: "RC-P004",
  confidenceLevel: "HIGH",
  confidenceRationale: "Basel framework explicitly ties backtesting exceptions to capital multiplier increases",
  linkedPersonas: ["RC-PER002"],
  requiredEvidence: ["Backtesting exception register", "Model validation report", "Capital plan impact analysis"],
  linkedKPIs: ["RC-K010", "RC-K012"],
  financialImpactCategory: "Working Capital",
  impactEstimateRange: "$10M-$150M in capital impact"
};

// Financial outcome mapping:
// - Capital multiplier increase: 4 exceptions in 250 days = 3.0x multiplier vs 1.5x baseline
// - Capital inflation: $300M additional market risk RWA * 10% cost of capital = $30M/year
// - Model remediation: $2M-$5M for model recalibration and documentation
// - FRTB IMA accreditation risk: Loss of IMA approval forces standardized approach = $50M-$100M additional capital
// - Trading desk impact: Position limit reductions, business line restrictions

/**
 * Example 4: FedNow Fraud Loss Spike
 * 
 * RAW SIGNAL: A mid-size bank launches FedNow instant payments and
 * experiences fraud losses of 28 bps on instant rails vs 3 bps on ACH.
 * APP scams account for 65% of fraud losses. Customer complaints on
 * held transactions spike 40%.
 * 
 * INTERPRETATION CHAIN:
 */
const fednowFraudSignal: RiskComplianceSignalRule = {
  id: "RC-SR007",
  name: "FedNow/RTP Fraud Spike",
  signalPattern: "Instant payment fraud losses >2x non-instant payment fraud rate with transaction growth >30%",
  interpretedPainId: "RC-P006",
  confidenceLevel: "HIGH",
  confidenceRationale: "Real-time rails inherently bypass batch detection; fraud rate differential is direct evidence",
  linkedPersonas: ["RC-PER004"],
  requiredEvidence: ["Instant payment fraud ledger", "Non-instant payment fraud comparison", "Transaction volume growth curve"],
  linkedKPIs: ["RC-K016", "RC-K018"],
  financialImpactCategory: "Cost Savings",
  impactEstimateRange: "$15M-$80M in fraud loss reduction"
};

// Financial outcome mapping:
// - Fraud loss reduction: $800M volume * (0.0028 - 0.0006) = $1.76M/year
// - APP scam reimbursement: $1.76M * 0.65 * 0.55 = $629K current liability
// - Reimbursement mandate: If enacted, liability = $1.76M * 0.65 * 0.90 = $1.03M
// - Customer complaint reduction: 600 fewer complaints * $850 = $510K
// - Transaction hold reduction: 20,000 fewer holds * $12 = $240K
// - Regulatory penalty avoidance: $500K-$2M
// - Total: $1.76M + $629K + $510K + $240K + $500K = $3.64M/year

/**
 * Example 5: SOX Material Weakness Disclosure
 * 
 * RAW SIGNAL: A fintech files an 8-K/A disclosing a material weakness
 * in ICFR related to revenue recognition controls. PCAOB inspection
 * identifies ITGC deficiencies in user access management.
 * 
 * INTERPRETATION CHAIN:
 */
const soxWeaknessSignal: RiskComplianceSignalRule = {
  id: "RC-SR009",
  name: "SOX Material Weakness Flag",
  signalPattern: "Material weakness or significant deficiency in ICFR disclosed in 10-K/A",
  interpretedPainId: "RC-P007",
  confidenceLevel: "HIGH",
  confidenceRationale: "Public disclosure is definitive evidence of control failure with reputational and remediation cost",
  linkedPersonas: ["PER005"],
  requiredEvidence: ["10-K/A filing", "PCAOB inspection report", "Remediation plan and costs"],
  linkedKPIs: ["RC-K019", "RC-K020"],
  financialImpactCategory: "Cost Savings",
  impactEstimateRange: "$5M-$25M in remediation and audit fees"
};

// Financial outcome mapping:
// - Remediation cost: $2M-$5M for control redesign and testing
// - External audit fee increase: $500K-$2M for expanded scope
// - Management time: 2,000 hours * $350/hr = $700K
// - Restatement cost: If required, $5M-$20M for restatement and legal
// - Reputational: Stock price impact, debt rating consideration
// - Technology investment: $1M-$3M for control automation

/**
 * Example 6: Climate Risk Regulatory Deadline
 * 
 * RAW SIGNAL: ECB announces climate risk stress test results showing
 * 25% of euro-area banks have inadequate climate risk data. The bank
 * has 18 months until mandatory ISSB S2 disclosures.
 * 
 * INTERPRETATION CHAIN:
 */
const climateRiskSignal: RiskComplianceSignalRule = {
  id: "RC-SR016",
  name: "Climate Risk Regulatory Mandate",
  signalPattern: "Regulator or exchange requiring climate risk disclosure with <24 months to compliance",
  interpretedPainId: "RC-P017",
  confidenceLevel: "MEDIUM",
  confidenceRationale: "Regulatory direction is clear but specific requirements continue evolving",
  linkedPersonas: ["RC-PER002"],
  requiredEvidence: ["Regulatory consultation paper", "Climate risk assessment status", "ISSB/TCFD gap analysis"],
  linkedKPIs: ["RC-K049", "RC-K051"],
  financialImpactCategory: "Risk Reduction",
  impactEstimateRange: "$5M-$25M in compliance and reporting"
};

// Financial outcome mapping:
// - Data acquisition: $2M-$5M for climate data vendors and integration
// - Scenario analysis: $1M-$3M for NGFS scenario implementation
// - Model development: $2M-$4M for transition risk and physical risk models
// - Disclosure infrastructure: $1M-$2M for TCFD/ISSB reporting platform
// - Portfolio steering: $10M-$50M in loan reallocation based on climate risk
// - Capital impact: Potential Pillar 2 add-on for climate risk concentration

// ============================================================
// COMPOSITE SIGNAL SCENARIOS
// ============================================================

/**
 * Composite Scenario: Post-Examination Remediation Acceleration
 * 
 * A regional bank receives an OCC MRA on BSA/AML program effectiveness.
 * Concurrent signals: sanctions FP rate 97%, KYC onboarding 14 days,
    * EDD backlog 110 days, no AI monitoring on AML.
 * 
 * This composite triggers multiple pains and creates a buying window
 * of 12-18 months with board-level accountability.
 */
const compositeExaminationScenario = {
  trigger: "RC-BT001: Regulatory examination findings (MRA/MRIA)",
  activatedPains: ["RC-P001", "RC-P002"],
  activatedPersonas: ["RC-PER001", "PER004", "PER003"],
  activatedValueDrivers: ["RC-VD001", "RC-VD002", "RC-VD003", "RC-VD004"],
  formulas: ["RC-VF001", "RC-VF002"],
  combinedAnnualBenefit: "$85M-$120M",
  implementationCostRange: "$5M-$8M",
  paybackPeriod: "3-6 months",
  boardPressure: "HIGH",
  competitiveContext: "Peer institutions completed similar remediation 12-24 months ago"
};

/**
 * Composite Scenario: Real-Time Payment Launch Risk
 * 
 * A credit union is preparing FedNow launch. Signals show:
 * - Current fraud detection latency: 450ms (batch-based)
 * - No APP scam detection capability
 * - APP scam reimbursement mandate expected in 12 months
 * - FedNow volume projected at $1.2B annually
 * 
 * The composite creates a time-bound decision: launch with friction/losses
 * or invest in real-time detection before go-live.
 */
const compositeFedNowScenario = {
  trigger: "RC-BT006: FedNow/RTP volume crosses detection threshold",
  activatedPains: ["RC-P006"],
  activatedPersonas: ["RC-PER004", "PER002"],
  activatedValueDrivers: ["RC-VD011", "RC-VD012"],
  formulas: ["RC-VF006"],
  combinedAnnualBenefit: "$5M-$15M",
  implementationCostRange: "$1M-$3M",
  paybackPeriod: "2-5 months",
  boardPressure: "MEDIUM",
  competitiveContext: "Digital banks achieving <3% APP scam rate vs industry 35-50%"
};

/**
 * Composite Scenario: Model Risk Governance Crisis
 * 
 * A capital markets firm has:
 * - Model inventory: 1,200 models, 400 AI/ML (no validation coverage)
 * - Credit model Gini decline: 8 points over 18 months
 * - VaR backtesting: 5 exceptions in last 250 days
 * - AI deployment velocity: 3x validation capacity
 * - SR 11-7 examination scheduled in 6 months
 * 
 * The composite creates urgent need for MRM platform investment
 * to avoid enforcement action and deployment moratorium.
 */
const compositeModelRiskScenario = {
  trigger: "RC-BT009: AI/ML deployment velocity exceeds validation capacity by >2x",
  activatedPains: ["RC-P003", "RC-P004", "RC-P012"],
  activatedPersonas: ["RC-PER002", "PER003"],
  activatedValueDrivers: ["RC-VD005", "RC-VD006", "RC-VD007", "RC-VD008", "RC-VD023", "RC-VD024"],
  formulas: ["RC-VF003", "RC-VF004", "RC-VF012"],
  combinedAnnualBenefit: "$60M-$150M",
  implementationCostRange: "$8M-$15M",
  paybackPeriod: "4-8 months",
  boardPressure: "HIGH",
  competitiveContext: "Peer firms with IMA approval and automated MRM have 15-20% lower market risk capital"
};

// ============================================================
// PERSONA-SPECIFIC DISCOVERY SIGNALS
// ============================================================

/**
 * RC-PER001 (AML Officer) Discovery Signal Map:
 * - High sanctions FP rate + OFAC finding = RC-P001 (HIGH confidence)
 * - KYC onboarding >10 days + periodic review backlog = RC-P002 (HIGH confidence)
 * - Correspondent banking concentration + Wolfsberg delays = RC-P016 (MEDIUM confidence)
 */
const amlOfficerSignalMap = {
  persona: "RC-PER001",
  primarySignals: ["RC-SR001", "RC-SR002", "RC-SR003", "RC-SR016"],
  discoveryQuestions: ["RC-DQ001", "RC-DQ002", "RC-DQ016"],
  keyFormulas: ["RC-VF001", "RC-VF002"],
  workedExample: "RC-WE001"
};

/**
 * RC-PER002 (Model Risk Manager) Discovery Signal Map:
 * - Gini decline + override spike = RC-P003 (HIGH confidence)
 * - VaR exceptions + FRTB inflation = RC-P004 (HIGH confidence)
 * - AI inventory growth + validation backlog = RC-P012 (HIGH confidence)
 */
const modelRiskManagerSignalMap = {
  persona: "RC-PER002",
  primarySignals: ["RC-SR004", "RC-SR005", "RC-SR014"],
  discoveryQuestions: ["RC-DQ003", "RC-DQ004", "RC-DQ012", "RC-DQ017"],
  keyFormulas: ["RC-VF003", "RC-VF004", "RC-VF012"],
  workedExample: null // Multiple applicable
};

/**
 * RC-PER004 (Fraud Prevention Director) Discovery Signal Map:
 * - Instant payment fraud spike + APP scam liability = RC-P006 (HIGH confidence)
 * - Trade surveillance FP + cross-market gap = RC-P013 (MEDIUM confidence)
 * - Insider threat coverage gap + whistleblower spike = RC-P018 (MEDIUM confidence)
 */
const fraudDirectorSignalMap = {
  persona: "RC-PER004",
  primarySignals: ["RC-SR007", "RC-SR008", "RC-SR017", "RC-SR018"],
  discoveryQuestions: ["RC-DQ006", "RC-DQ013", "RC-DQ018"],
  keyFormulas: ["RC-VF006"],
  workedExample: "RC-WE002"
};

// ============================================================
// EXPORTS
// ============================================================

export {
  // Types
  RiskCompliancePain,
  RiskComplianceKPI,
  RiskComplianceSignalRule,
  RiskComplianceFormula,
  RiskComplianceWorkedExample,
  
  // Signal Examples
  ofacEnforcementSignal,
  cfpbComplaintSignal,
  varBacktestSignal,
  fednowFraudSignal,
  soxWeaknessSignal,
  climateRiskSignal,
  
  // Composite Scenarios
  compositeExaminationScenario,
  compositeFedNowScenario,
  compositeModelRiskScenario,
  
  // Persona Maps
  amlOfficerSignalMap,
  modelRiskManagerSignalMap,
  fraudDirectorSignalMap
};
