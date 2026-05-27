/**
 * Public Health and Human Services Subpack — Signal Interpretation Examples (TypeScript)
 * Subpack ID: public-health-v1
 * Parent Master: public-sector-master-v1
 * Version: 1.0.0
 * 
 * These examples demonstrate how raw external signals are mapped to
 * interpreted pains, value drivers, and financial outcomes for the
 * Public Health and Human Services vertical.
 */

// ============================================================
// TYPES (inherited from master schema, extended with vertical fields)
// ============================================================

interface SignalSource {
  sourceId: string;
  sourceType: "federal_agency_data" | "state_agency_data" | "audit_report" | "grant_document" | "news" | "procurement_notice" | "workforce_data" | "court_document";
  sourceUrl?: string;
  captureDate: string;
  rawMetricValue: number | string;
  rawMetricUnit: string;
  geographicScope: string; // e.g., "CA", "US", "County_X"
}

interface InterpretedSignal {
  signalRuleId: string;
  signalName: string;
  rawSignalPattern: string;
  source: SignalSource;
  confidenceScore: number; // 0.0 - 1.0
  interpretedMeaning: string;
  linkedPainIds: string[];
  linkedKpiIds: string[];
  linkedValueDriverIds: string[];
  affectedPersonaIds: string[];
  financialImplication: FinancialImplication;
  recommendedAction: string;
  requiredConfirmationSignals: string[];
}

interface FinancialImplication {
  valueCategory: "Cost Savings" | "Risk Reduction" | "Mission Effectiveness" | "Revenue Uplift" | "Working Capital";
  annualValueEstimateUsd: number | null;
  valueRangeLow: number | null;
  valueRangeHigh: number | null;
  confidence: "HIGH" | "MEDIUM" | "LOW";
  confidenceRationale: string;
  formulaId: string;
}

// ============================================================
// EXAMPLE 1: MEDICAID ELIGIBILITY BACKLOG SURGE
// Signal Rule: PH-SIG-001
// ============================================================

const medicaidBacklogSignal: InterpretedSignal = {
  signalRuleId: "PH-SIG-001",
  signalName: "Medicaid Eligibility Backlog Surge",
  rawSignalPattern:
    "Eligibility determination time >45 days growing 10%+ MoM; " +
    "ex parte renewal rate <40%; CMS corrective action plan issued",
  source: {
    sourceId: "KFF-MEDICAID-UNWINDING-2024Q3",
    sourceType: "federal_agency_data",
    sourceUrl: "https://www.kff.org/medicaid/issue-brief/…",
    captureDate: "2024-09-15",
    rawMetricValue: 67,
    rawMetricUnit: "days (avg eligibility determination)",
    geographicScope: "US-State-Aggregate",
  },
  confidenceScore: 0.92,
  interpretedMeaning:
    "State eligibility systems and staffing cannot handle redetermination volume. " +
    "CMS compliance risk is elevated. Coverage gaps for vulnerable populations are occurring. " +
    "This signal predicts imminent CMS enforcement action and potential FMAP penalties.",
  linkedPainIds: ["PH-PAIN-001"],
  linkedKpiIds: ["PH-KPI-001", "PH-KPI-002", "PH-KPI-003"],
  linkedValueDriverIds: ["PH-VD-001"],
  affectedPersonaIds: ["PH-PERS-001", "PH-PERS-005"],
  financialImplication: {
    valueCategory: "Cost Savings",
    annualValueEstimateUsd: 24000000, // $24M per PH-VF-001 example
    valueRangeLow: 15000000,
    valueRangeHigh: 35000000,
    confidence: "MEDIUM",
    confidenceRationale:
      "HIGH confidence on eligibility determination time data (state-reported to CMS). " +
      "MEDIUM on financial estimate because churn cost varies significantly by state " +
      "administrative structure and gap-in-care cost assumptions.",
    formulaId: "PH-VF-001",
  },
  recommendedAction:
    "Engage Medicaid Director and HHS CIO with ex parte automation proposal. " +
    "Reference CMS streamlined verification authority. Offer rapid assessment of " +
    "eligibility system modernization pathway with modular APD approach.",
  requiredConfirmationSignals: [
    "CMS-64 reports showing state Medicaid spending",
    "State eligibility system backlog report (internal)",
    "CMS T-MSIS data on enrollment and disenrollment trends",
    "Worker caseload analysis from state HR/operations",
  ],
};

// ============================================================
// EXAMPLE 2: SNAP QC ERROR RATE ABOVE THRESHOLD
// Signal Rule: PH-SIG-002
// ============================================================

const snapQcSignal: InterpretedSignal = {
  signalRuleId: "PH-SIG-002",
  signalName: "SNAP QC Error Rate Above Threshold",
  rawSignalPattern:
    "SNAP QC error rate >6% for 2+ quarters; " +
    "USDA corrective action notice; worker training completion <70%",
  source: {
    sourceId: "USDA-SNAP-QC-FY2023",
    sourceType: "federal_agency_data",
    sourceUrl: "https://www.fns.usda.gov/resource/…",
    captureDate: "2024-08-01",
    rawMetricValue: 8.3,
    rawMetricUnit: "percent (SNAP QC error rate)",
    geographicScope: "US-State-Aggregate",
  },
  confidenceScore: 0.88,
  interpretedMeaning:
    "Eligibility determination accuracy is declining. Federal funding is at risk — " +
    "USDA can reduce federal funding share from 50% to 25%. Worker competency and " +
    "system verification gaps are root causes. This signal predicts corrective action " +
    "requirements and potential multi-million-dollar federal funding loss.",
  linkedPainIds: ["PH-PAIN-002"],
  linkedKpiIds: ["PH-KPI-004", "PH-KPI-005"],
  linkedValueDriverIds: ["PH-VD-002"],
  affectedPersonaIds: ["PH-PERS-001", "PH-PERS-005"],
  financialImplication: {
    valueCategory: "Risk Reduction",
    annualValueEstimateUsd: 11000000, // $11M per PH-VF-003 example
    valueRangeLow: 6000000,
    valueRangeHigh: 18000000,
    confidence: "HIGH",
    confidenceRationale:
      "USDA SNAP QC data is standardized and audited. Federal funding share formula " +
      "is statutory (50% standard). Error rate and outlay data are publicly reported. " +
      "Calculation is deterministic once state-specific outlay is confirmed.",
    formulaId: "PH-VF-003",
  },
  recommendedAction:
    "Engage state SNAP director and HHS procurement with eligibility verification " +
    "automation proposal. Reference PH-VF-003 to quantify federal funding protection. " +
    "Propose phased approach: (1) income verification automation, (2) worker decision " +
    "support, (3) QC monitoring dashboard.",
  requiredConfirmationSignals: [
    "USDA SNAP QC annual report for target state",
    "State QC self-assessment and corrective action plan",
    "Worker training records and completion rates",
    "Eligibility system verification module inventory",
  ],
};

// ============================================================
// EXAMPLE 3: UI CLAIMS AND FRAUD BACKLOG
// Signal Rule: PH-SIG-004
// ============================================================

const uiBacklogSignal: InterpretedSignal = {
  signalRuleId: "PH-SIG-004",
  signalName: "UI Claims and Fraud Backlog",
  rawSignalPattern:
    "Claims pending >21 days >10% of volume; " +
    "identity verification queue >30 days; " +
    "overpayment balance growing >$500M",
  source: {
    sourceId: "GAO-23-105474",
    sourceType: "audit_report",
    sourceUrl: "https://www.gao.gov/products/gao-23-105474",
    captureDate: "2024-07-20",
    rawMetricValue: 15,
    rawMetricUnit: "percent (UI improper payment rate, national)",
    geographicScope: "US",
  },
  confidenceScore: 0.89,
  interpretedMeaning:
    "UI system is overwhelmed by volume and fraud prevention requirements. Trust fund " +
    "solvency is at risk. Claimant experience is severely degraded. DOL ETA performance " +
    "targets are likely not being met. State faces federal sanctions and potential " +
    "administrative grant reduction.",
  linkedPainIds: ["PH-PAIN-004"],
  linkedKpiIds: ["PH-KPI-009", "PH-KPI-010", "PH-KPI-011"],
  linkedValueDriverIds: ["PH-VD-004"],
  affectedPersonaIds: ["PH-PERS-004", "PH-PERS-005"],
  financialImplication: {
    valueCategory: "Cost Savings",
    annualValueEstimateUsd: 36500000, // $36.5M per PH-VF-005 example
    valueRangeLow: 15000000,
    valueRangeHigh: 60000000,
    confidence: "MEDIUM",
    confidenceRationale:
      "DOL ETA 901/902 data is standardized. However, recovery rate and trust fund " +
      "solvency improvement vary significantly by state UI tax structure and fraud " +
      "detection maturity. National GAO data must be calibrated to state-specific payment " +
      "volume.",
    formulaId: "PH-VF-005",
  },
  recommendedAction:
    "Engage UI Claims Director and state labor agency CIO with fraud detection and " +
    "identity verification modernization proposal. Reference GAO findings and DOL ETA " +
    "performance targets. Propose cloud-based identity verification platform with " +
    "real-time cross-state data matching.",
  requiredConfirmationSignals: [
    "DOL ETA 901/902 reports for target state",
    "State UI trust fund actuarial statement",
    "Fraud detection and overpayment recovery metrics",
    "Identity verification queue and resolution times",
  ],
};

// ============================================================
// EXAMPLE 4: PUBLIC HEALTH SURVEILLANCE DATA LATENCY
// Signal Rule: PH-SIG-005
// ============================================================

const surveillanceLatencySignal: InterpretedSignal = {
  signalRuleId: "PH-SIG-005",
  signalName: "Public Health Surveillance Data Latency",
  rawSignalPattern:
    "Notifiable disease reporting >7 days; " +
    "manual fax/phone lab reporting observed; " +
    "syndromic surveillance coverage <80% of EDs",
  source: {
    sourceId: "CDC-DMI-STATE-ASSESSMENT-2024",
    sourceType: "federal_agency_data",
    sourceUrl: "https://www.cdc.gov/surveillance/…",
    captureDate: "2024-06-10",
    rawMetricValue: 62,
    rawMetricUnit: "percent (EDs connected to syndromic surveillance)",
    geographicScope: "US-State-Aggregate",
  },
  confidenceScore: 0.87,
  interpretedMeaning:
    "Outbreak detection is delayed by days to weeks due to manual reporting pathways. " +
    "CDC Data Modernization Initiative mandate is unfulfilled. EHR interoperability gaps " +
    "prevent automated case reporting. Next outbreak or pandemic response will be " +
    "significantly impaired.",
  linkedPainIds: ["PH-PAIN-005"],
  linkedKpiIds: ["PH-KPI-012", "PH-KPI-013"],
  linkedValueDriverIds: ["PH-VD-005"],
  affectedPersonaIds: ["PH-PERS-002"],
  financialImplication: {
    valueCategory: "Risk Reduction",
    annualValueEstimateUsd: 4800000, // $4.8M per PH-VF-006 example
    valueRangeLow: 2000000,
    valueRangeHigh: 8000000,
    confidence: "MEDIUM",
    confidenceRationale:
      "CDC surveillance metrics are standardized. However, outbreak detection acceleration " +
      "value is difficult to quantify prospectively. Manual labor hours are more certain. " +
      "ELR rebates and CMS penalties depend on specific state EHR landscape.",
    formulaId: "PH-VF-006",
  },
  recommendedAction:
    "Engage State Epidemiologist and Public Health CIO with CDC DMI-aligned surveillance " +
    "modernization proposal. Reference PH-VF-006 to quantify labor efficiency and outbreak " +
    "readiness. Propose FHIR-based ELR expansion and syndromic surveillance dashboard.",
  requiredConfirmationSignals: [
    "CDC surveillance reports for target state",
    "Lab reporting audit (electronic vs. fax/phone)",
    "EHR interoperability test results",
    "Syndromic surveillance coverage map by ED",
  ],
};

// ============================================================
// EXAMPLE 5: MMIS END-OF-LIFE RISK
// Signal Rule: PH-SIG-011
// ============================================================

const mmisEolSignal: InterpretedSignal = {
  signalRuleId: "PH-SIG-011",
  signalName: "MMIS End-of-Life Risk",
  rawSignalPattern:
    "MMIS vendor contract ending <24 months; " +
    "claim adjudication >30 days; " +
    "no API or interoperability layer; " +
    "CMS MITA <Level 3",
  source: {
    sourceId: "STATE-MMIS-PROCUREMENT-PORTAL-2024",
    sourceType: "procurement_notice",
    captureDate: "2024-10-01",
    rawMetricValue: 14,
    rawMetricUnit: "months (remaining on MMIS contract)",
    geographicScope: "US-State-Example",
  },
  confidenceScore: 0.91,
  interpretedMeaning:
    "Medicaid payment system is at end of life. Vendor lock-in risk is high. CMS requires " +
    "modularity and MITA alignment. Replacement will cost $200M-$500M and take 3-5 years. " +
    "State must begin procurement within 6-12 months to avoid service disruption. This is a " +
    "critical infrastructure risk with federal compliance implications.",
  linkedPainIds: ["PH-PAIN-013"],
  linkedKpiIds: ["PH-KPI-029", "PH-KPI-030"],
  linkedValueDriverIds: ["PH-VD-011"],
  affectedPersonaIds: ["PH-PERS-001", "PH-PERS-002"],
  financialImplication: {
    valueCategory: "Cost Savings",
    annualValueEstimateUsd: null, // Multi-year capital investment, not annual savings
    valueRangeLow: null,
    valueRangeHigh: null,
    confidence: "HIGH",
    confidenceRationale:
      "MMIS contract end dates and MITA assessments are verifiable. Procurement timelines " +
      "are well-documented. Value is strategic (avoiding disruption, achieving modularity) " +
      "rather than purely financial. TCO comparison vs. incumbent is the primary value metric.",
    formulaId: "N/A — Strategic procurement value",
  },
  recommendedAction:
    "Engage Medicaid Director and state procurement with modular MMIS replacement strategy. " +
    "Reference CMS MITA 3.0 modular pathways and successful state examples (Illinois, Vermont). " +
    "Propose discovery/assessment engagement to define modular scope and APD pathway.",
  requiredConfirmationSignals: [
    "Current MMIS contract and all amendments",
    "Claim processing logs (adjudication time distribution)",
    "CMS MITA assessment (most recent)",
    "Vendor end-of-support notice or roadmap",
  ],
};

// ============================================================
// EXAMPLE 6: CROSS-PROGRAM ELIGIBILITY SILOS
// Signal Rule: PH-SIG-012
// ============================================================

const crossProgramSilosSignal: InterpretedSignal = {
  signalRuleId: "PH-SIG-012",
  signalName: "Cross-Program Eligibility Silos",
  rawSignalPattern:
    "Families submitting same documents to >3 programs; " +
    "no cross-program income verification; " +
    "duplicate benefits detected",
  source: {
    sourceId: "CODE-FOR-AMERICA-INTEGRATED-BENEFITS-2023",
    sourceType: "audit_report",
    sourceUrl: "https://www.codeforamerica.org/…",
    captureDate: "2024-05-15",
    rawMetricValue: 4.2,
    rawMetricUnit: "programs (avg duplicate verification count per family)",
    geographicScope: "US-State-Sample",
  },
  confidenceScore: 0.87,
  interpretedMeaning:
    "Program-centric systems are creating massive administrative waste and beneficiary burden. " +
    "Integrated eligibility is not implemented. Federal streamlined verification mandate is " +
    "unfulfilled. Each duplicate verification costs $15-$50 in staff time. Churn is elevated " +
    "because families drop out from burden.",
  linkedPainIds: ["PH-PAIN-015"],
  linkedKpiIds: ["PH-KPI-033", "PH-KPI-034"],
  linkedValueDriverIds: ["PH-VD-012"],
  affectedPersonaIds: ["PH-PERS-001", "PH-PERS-005"],
  financialImplication: {
    valueCategory: "Cost Savings",
    annualValueEstimateUsd: 11000000, // $11M per PH-VF-012 example
    valueRangeLow: 5000000,
    valueRangeHigh: 20000000,
    confidence: "MEDIUM",
    confidenceRationale:
      "Duplicate verification burden is measurable through time-motion studies. However, " +
      "citizen satisfaction and ex parte expansion values are less certain. Requires state-specific " +
      "program inventory and cross-system mapping.",
    formulaId: "PH-VF-012",
  },
  recommendedAction:
    "Engage HHS Secretary or integrated services director with cross-program eligibility " +
    "platform proposal. Reference Code for America research and successful state examples " +
    "(Minnesota, Kentucky). Propose pilot on 2-3 programs with unified verification engine.",
  requiredConfirmationSignals: [
    "Program eligibility system inventory (all programs)",
    "Citizen journey map showing verification touchpoints",
    "Duplicate benefit audit or improper payment analysis",
    "Federal streamlined verification assessment status",
  ],
};

// ============================================================
// SIGNAL RULE ENGINE — RUNTIME INTERPRETATION
// ============================================================

interface SignalRuleEngine {
  rules: InterpretedSignal[];
  match(signal: SignalSource): InterpretedSignal[];
  scoreConfidence(signal: InterpretedSignal): number;
}

class PublicHealthSignalEngine implements SignalRuleEngine {
  rules: InterpretedSignal[] = [
    medicaidBacklogSignal,
    snapQcSignal,
    uiBacklogSignal,
    surveillanceLatencySignal,
    mmisEolSignal,
    crossProgramSilosSignal,
  ];

  match(source: SignalSource): InterpretedSignal[] {
    return this.rules.filter((rule) => {
      // Simple matching: source type and geographic scope alignment
      // In production, this would use NLP/ML for pattern matching
      const typeMatch = rule.source.sourceType === source.sourceType;
      const scopeMatch =
        rule.source.geographicScope === source.geographicScope ||
        rule.source.geographicScope.startsWith("US-State") &&
          source.geographicScope.startsWith("US-State");
      return typeMatch && scopeMatch;
    });
  }

  scoreConfidence(signal: InterpretedSignal): number {
    const baseConfidence = signal.confidenceScore;
    const financialConfidence =
      signal.financialImplication.confidence === "HIGH"
        ? 1.0
        : signal.financialImplication.confidence === "MEDIUM"
        ? 0.7
        : 0.4;
    return (baseConfidence + financialConfidence) / 2;
  }
}

// Export for downstream consumers
export {
  PublicHealthSignalEngine,
  medicaidBacklogSignal,
  snapQcSignal,
  uiBacklogSignal,
  surveillanceLatencySignal,
  mmisEolSignal,
  crossProgramSilosSignal,
};

export type {
  SignalSource,
  InterpretedSignal,
  FinancialImplication,
  SignalRuleEngine,
};

// ============================================================
// USAGE EXAMPLE
// ============================================================

/*
import { PublicHealthSignalEngine } from './signals-examples';

const engine = new PublicHealthSignalEngine();

const incomingSignal: SignalSource = {
  sourceId: "STATE-MEDICAID-BACKLOG-REPORT-2024Q3",
  sourceType: "state_agency_data",
  captureDate: "2024-09-15",
  rawMetricValue: 67,
  rawMetricUnit: "days",
  geographicScope: "US-State-Example",
};

const matches = engine.match(incomingSignal);
for (const match of matches) {
  console.log(`Matched: ${match.signalName}`);
  console.log(`Confidence: ${engine.scoreConfidence(match)}`);
  console.log(`Financial Impact: $${match.financialImplication.annualValueEstimateUsd?.toLocaleString()}`);
  console.log(`Recommended Action: ${match.recommendedAction}`);
}
*/
