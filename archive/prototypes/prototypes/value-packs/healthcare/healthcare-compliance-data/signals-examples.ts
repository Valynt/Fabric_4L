/**
 * Healthcare Compliance and Data Subpack — Signal Examples & TypeScript Definitions
 * ID: healthcare-compliance-v1
 * Parent Master: healthcare-master-v1
 * Generated: 2026-04-25
 * Agent Swarm: kimi-k2.6-swarm-healthcare-s3.5
 *
 * This file provides concrete TypeScript types, signal interpretation examples,
 * and machine-parseable rules for the Healthcare Compliance and Data vertical.
 * It is designed to be imported by orchestrator agents for real-time signal
 * processing and value-selling automation.
 */

// ─────────────────────────────────────────────────────────────────────────────
// CORE TYPES (inherited from master, extended for vertical)
// ─────────────────────────────────────────────────────────────────────────────

export type FinancialOutcome = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
export type Confidence = "LOW" | "MEDIUM" | "HIGH";
export type Prevalence = "HIGH" | "MEDIUM" | "LOW";
export type Urgency = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface CompliancePain {
  id: string;
  name: string;
  description: string;
  symptoms: string[];
  affectedSegments: string[];
  affectedPersonas: string[];
  linkedKPIs: string[];
  linkedValueDrivers: string[];
  prevalence: Prevalence;
  confidence: Confidence;
  sources: string[];
}

export interface ComplianceKPI {
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

export interface ComplianceSignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
}

export interface ComplianceFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
}

export interface ComplianceBenchmark {
  id: string;
  name: string;
  value: number;
  range: string;
  unit: string;
  source: string;
  sourceType: "industry_survey" | "government" | "financial_ratings" | "academic" | "industry_standard";
  segmentApplicability: string[];
  geographicScope: string;
  companySizeScope: string;
  confidence: Confidence;
  dateSourced: string;
}

// ─────────────────────────────────────────────────────────────────────────────
// SIGNAL INTERPRETATION EXAMPLES
// Concrete, copy-pasteable signal handlers for orchestrator use
// ─────────────────────────────────────────────────────────────────────────────

export const COMPLIANCE_SIGNAL_EXAMPLES: ComplianceSignalRule[] = [
  {
    id: "CS001",
    signalName: "HHS OCR Breach Portal Listing",
    rawSignalPattern: "Organization appears on HHS OCR Breach Portal with > 500 records",
    interpretedMeaning: "Confirmed PHI breach with public disclosure. Indicates detection/control failure. Creates 60-day notification clock and potential OCR investigation.",
    linkedPains: ["CP001", "CP010", "CP016"],
    linkedKPIs: ["CK001", "CK003"],
    confidenceScore: 0.95,
    requiredConfirmationSignals: [
      "8-K or press release confirming",
      "cyber insurance claim filed",
      "law firm breach counsel retained"
    ]
  },
  {
    id: "CS002",
    signalName: "HITRUST Validated Assessment Expiration",
    rawSignalPattern: "HITRUST validated assessment expiration within 6 months with no re-assessment scheduled",
    interpretedMeaning: "Certification gap imminent. Contracts requiring HITRUST may be at risk. RFP eligibility may lapse.",
    linkedPains: ["CP003"],
    linkedKPIs: ["CK007", "CK009"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: [
      "Job postings for compliance/security roles",
      "RFP pipeline requiring HITRUST",
      "Third-party attestation requests pending"
    ]
  },
  {
    id: "CS003",
    signalName: "FHIR API Downtime Alert",
    rawSignalPattern: "Public FHIR endpoint monitoring shows > 30 min unplanned outage in 90 days",
    interpretedMeaning: "Information blocking compliance risk. Patient access API must be available per ONC Cures Act. CMP exposure up to $1M per violation for IT developers.",
    linkedPains: ["CP002", "CP011"],
    linkedKPIs: ["CK004", "CK006"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: [
      "Information blocking complaint count > 0",
      "ONC certification status",
      "Customer churn in patient portal usage"
    ]
  },
  {
    id: "CS004",
    signalName: "ONC Information Blocking Complaint Filed",
    rawSignalPattern: "Complaint filed with HHS/ONC information blocking portal naming the organization",
    interpretedMeaning: "Direct regulatory enforcement exposure. ONC may refer to OIG for CMP assessment. Reputational risk with referring providers and patients.",
    linkedPains: ["CP002", "CP011"],
    linkedKPIs: ["CK006"],
    confidenceScore: 0.92,
    requiredConfirmationSignals: [
      "API uptime < 99.5%",
      "Care summary exchange rate < 70%",
      "Public statement or response"
    ]
  },
  {
    id: "CS005",
    signalName: "MPI Duplicate Surge",
    rawSignalPattern: "Job postings for MPI/EMPI analysts or data quality engineers > 5 in 90 days",
    interpretedMeaning: "Identity data quality crisis. Duplicate records increasing, causing billing errors, care fragmentation, and patient safety risk.",
    linkedPains: ["CP004"],
    linkedKPIs: ["CK010", "CK012"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: [
      "Patient complaints about billing errors increasing",
      "Registration accuracy < 90%",
      "EMPI vendor support tickets escalating"
    ]
  },
  {
    id: "CS007",
    signalName: "Third-Party Breach Notification",
    rawSignalPattern: "Business associate or vendor discloses breach affecting the organization's PHI",
    interpretedMeaning: "BAA enforcement gap. Vendor risk management insufficient. OCR may investigate BAA adequacy and oversight.",
    linkedPains: ["CP010"],
    linkedKPIs: ["CK028", "CK029"],
    confidenceScore: 0.91,
    requiredConfirmationSignals: [
      "BAA audit finding in prior 12 months",
      "Vendor risk assessment backlog > 6 months",
      "No continuous monitoring of vendor security posture"
    ]
  },
  {
    id: "CS008",
    signalName: "FWA Whistleblower or Qui Tam Filing",
    rawSignalPattern: "DOJ qui tam complaint unsealed naming organization or related entity",
    interpretedMeaning: "Significant FWA exposure. FCA treble damages and DOJ intervention likely. SIU program effectiveness under scrutiny.",
    linkedPains: ["CP007", "CP008"],
    linkedKPIs: ["CK019", "CK020", "CK021"],
    confidenceScore: 0.94,
    requiredConfirmationSignals: [
      "DOJ press release or settlement announcement",
      "OIG exclusion risk assessment",
      "Legal counsel specializing in FCA retained"
    ]
  },
  {
    id: "CS009",
    signalName: "Ransomware Incident Disclosure",
    rawSignalPattern: "8-K, press release, or regulator notification discloses ransomware affecting healthcare operations",
    interpretedMeaning: "Critical security incident with PHI exposure, operational disruption, and OCR settlement exposure. Downtime cost $8,000+/minute for hospitals.",
    linkedPains: ["CP001", "CP016", "CP017"],
    linkedKPIs: ["CK003", "CK044", "CK046"],
    confidenceScore: 0.96,
    requiredConfirmationSignals: [
      "EHR downtime > 4 hours",
      "Patient diversion activated",
      "Cyber insurance claim > $1M"
    ]
  },
  {
    id: "CS010",
    signalName: "Coding Compliance Job Posting Surge",
    rawSignalPattern: "> 8 open positions for coding auditors, CDI specialists, or compliance auditors in 90 days",
    interpretedMeaning: "Coding accuracy crisis or external audit pressure. Likely RAC/MAC findings, OIG work plan alignment, or DOJ investigation.",
    linkedPains: ["CP008"],
    linkedKPIs: ["CK022", "CK023", "CK024"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: [
      "RAC takeback > $500K in prior year",
      "Coding accuracy < 95%",
      "External audit scheduled"
    ]
  },
  {
    id: "CS011",
    signalName: "SOC 2 Type II Audit Failure",
    rawSignalPattern: "SOC 2 Type II report with qualified opinion or material exceptions disclosed",
    interpretedMeaning: "Customer-mandated security certification compromised. Churn risk for SaaS contracts. Sales cycle elongation.",
    linkedPains: ["CP013"],
    linkedKPIs: ["CK035", "CK036"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: [
      "Customer security questionnaire backlog > 30",
      "Churn attributed to missing cert > 5%",
      "New customer sales cycle > 6 months"
    ]
  },
  {
    id: "CS012",
    signalName: "State Privacy Law Expansion",
    rawSignalPattern: "State legislature passes new health data privacy law (e.g., WA MHMDA, CT, NV) affecting organization's operating states",
    interpretedMeaning: "Compliance program must expand beyond HIPAA. Consent, opt-out, and deletion requirements diverge across states. Legal and technology investment required.",
    linkedPains: ["CP012", "CP005"],
    linkedKPIs: ["CK032", "CK033", "CK034"],
    confidenceScore: 0.87,
    requiredConfirmationSignals: [
      "No unified state privacy policy",
      "Patient rights request process not automated",
      "Legal team hiring for privacy"
    ]
  },
  {
    id: "CS013",
    signalName: "Cloud EHR Migration Announcement",
    rawSignalPattern: "Health system announces EHR cloud migration (Epic Azure, Oracle AWS, etc.) without security architecture disclosure",
    interpretedMeaning: "Shared responsibility model risk. BAA architecture, encryption key management, and egress control may be immature. Compliance exposure during transition.",
    linkedPains: ["CP020"],
    linkedKPIs: ["CK056", "CK057"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: [
      "No CISO named to migration governance",
      "Cloud security architect role open",
      "Penetration test of cloud environment not scheduled"
    ]
  },
  {
    id: "CS014",
    signalName: "HL7 Interface Engine End-of-Life",
    rawSignalPattern: "Interface engine vendor announces EOL for version in production (e.g., Rhapsody, Corepoint, Mirth)",
    interpretedMeaning: "Interoperability infrastructure at risk. Migration to modern integration platform (FHIR/API gateway) required. Downtime and data loss risk during transition.",
    linkedPains: ["CP015"],
    linkedKPIs: ["CK041", "CK042", "CK043"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: [
      "Interface engine version > 5 years behind current",
      "No API gateway in architecture",
      "Interface downtime > 2 hours/month"
    ]
  },
  {
    id: "CS015",
    signalName: "AI/ML Healthcare Model FDA Inquiry",
    rawSignalPattern: "FDA issues public inquiry, warning, or AI/ML pre-submission feedback to healthcare organization",
    interpretedMeaning: "Algorithmic governance gap. Model validation, bias audit, and explainability documentation may be insufficient. SaMD classification risk.",
    linkedPains: ["CP018"],
    linkedKPIs: ["CK050", "CK051"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: [
      "No AI governance board",
      "Bias audit not completed",
      "Model drift monitoring absent"
    ]
  },
  {
    id: "CS017",
    signalName: "Security Operations Job Posting Surge",
    rawSignalPattern: "> 10 open security operations, SOC analyst, or incident responder positions in 90 days",
    interpretedMeaning: "SOC understaffed or alert volume exceeding capacity. MTTD/MTTR likely degrading. Insider threat and PHI access monitoring at risk.",
    linkedPains: ["CP017"],
    linkedKPIs: ["CK047", "CK048", "CK049"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: [
      "SOC coverage 8x5 only",
      "MTTD > 15 minutes",
      "SIEM alert volume > 10K/day unreviewed"
    ]
  },
  {
    id: "CS019",
    signalName: "Healthcare Data Breach Class Action Filed",
    rawSignalPattern: "Class action complaint filed alleging negligence after breach disclosure",
    interpretedMeaning: "Breach cost escalating beyond OCR fines to civil litigation. Reputational damage and settlement exposure increasing. Cyber insurance may have coverage gaps.",
    linkedPains: ["CP001", "CP010"],
    linkedKPIs: ["CK001", "CK003"],
    confidenceScore: 0.92,
    requiredConfirmationSignals: [
      "Breach size > 500K records",
      "State AG investigation announced",
      "Cyber insurance retention > $5M"
    ]
  },
  {
    id: "CS020",
    signalName: "CMS Conditions of Participation Survey Failure",
    rawSignalPattern: "CMS survey finds Condition of Participation (CoP) deficiency in patient rights, medical records, or QA",
    interpretedMeaning: "Immediate jeopardy or standard deficiency requiring plan of correction. Medicare payment at risk. Often linked to documentation, privacy, or data quality failures.",
    linkedPains: ["CP006", "CP008", "CP019"],
    linkedKPIs: ["CK016", "CK022", "CK053"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: [
      "Plan of correction required",
      "IJ tag issued",
      "Prior survey within 12 months with repeat finding"
    ]
  }
];

// ─────────────────────────────────────────────────────────────────────────────
// SIGNAL SCORING UTILITIES
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Evaluate a raw signal against a rule and return an interpretation score.
 */
export function evaluateSignal(
  rule: ComplianceSignalRule,
  rawSignals: Record<string, boolean | number | string>
): { matched: boolean; confidence: number; reasons: string[] } {
  const reasons: string[] = [];
  let matchCount = 0;
  let totalChecks = 0;

  // Simple heuristic: check if required confirmation signals are present
  for (const signal of rule.requiredConfirmationSignals) {
    totalChecks++;
    const key = signal.split(" ")[0].toLowerCase().replace(/[^a-z0-9]/g, "");
    if (rawSignals[key] !== undefined && rawSignals[key] !== false) {
      matchCount++;
      reasons.push(`Confirmed: ${signal}`);
    }
  }

  const matched = matchCount >= Math.ceil(totalChecks * 0.5);
  const confidence = matched
    ? rule.confidenceScore * (0.6 + 0.4 * (matchCount / totalChecks))
    : rule.confidenceScore * 0.3 * (matchCount / Math.max(totalChecks, 1));

  return { matched, confidence: Math.round(confidence * 100) / 100, reasons };
}

/**
 * Map a detected signal to its financial outcome category and linked personas.
 */
export function mapSignalToValue(
  rule: ComplianceSignalRule,
  pains: CompliancePain[],
  valueDrivers: Array<{ id: string; valueDriverCategory: FinancialOutcome; affectedPersonas: string[] }>
): {
  outcomes: FinancialOutcome[];
  personas: string[];
  painNames: string[];
} {
  const painNames = pains
    .filter((p) => rule.linkedPains.includes(p.id))
    .map((p) => p.name);

  const driverIds = new Set<string>();
  pains
    .filter((p) => rule.linkedPains.includes(p.id))
    .forEach((p) => p.linkedValueDrivers.forEach((vd) => driverIds.add(vd)));

  const outcomes = Array.from(
    new Set(
      valueDrivers
        .filter((vd) => driverIds.has(vd.id))
        .map((vd) => vd.valueDriverCategory)
    )
  );

  const personas = Array.from(
    new Set(
      valueDrivers
        .filter((vd) => driverIds.has(vd.id))
        .flatMap((vd) => vd.affectedPersonas)
    )
  );

  return { outcomes, personas, painNames };
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI THRESHOLD ALERTS
// Machine-parseable thresholds for automated monitoring
// ─────────────────────────────────────────────────────────────────────────────

export const COMPLIANCE_KPI_THRESHOLDS: Record<string, { critical: number | string; warning: number | string; unit: string }> = {
  CK001: { critical: 60, warning: 45, unit: "days" },      // Breach discovery-to-notification
  CK004: { critical: 99.5, warning: 99.7, unit: "%" },     // FHIR API uptime (inverse: below = bad)
  CK007: { critical: 70, warning: 80, unit: "score" },      // HITRUST score
  CK008: { critical: 20, warning: 12, unit: "count" },      // Open critical control gaps
  CK010: { critical: 5, warning: 3, unit: "%" },            // MPI duplicate rate
  CK011: { critical: 0.3, warning: 0.1, unit: "%" },        // MPI overlay rate
  CK014: { critical: 4320, warning: 1440, unit: "minutes" },// Consent revoke propagation
  CK016: { critical: 90, warning: 95, unit: "%" },          // Audit log coverage
  CK019: { critical: 3, warning: 5, unit: "ratio" },        // FWA recovery ratio (below = bad)
  CK020: { critical: 95, warning: 90, unit: "%" },          // FWA false positive rate (above = bad)
  CK022: { critical: 94, warning: 96, unit: "%" },          // Coding accuracy (below = bad)
  CK023: { critical: 4, warning: 2, unit: "%" },            // DRG validation error
  CK025: { critical: 30, warning: 14, unit: "days" },        // De-identification cycle time
  CK044: { critical: 72, warning: 24, unit: "hours" },      // Ransomware RTO
  CK047: { critical: 30, warning: 15, unit: "minutes" },    // SOC MTTD
};

/**
 * Check if a KPI value crosses a threshold and return an alert level.
 */
export function checkKPIAlert(kpiId: string, value: number): { alert: "NONE" | "WARNING" | "CRITICAL"; message: string } {
  const threshold = COMPLIANCE_KPI_THRESHOLDS[kpiId];
  if (!threshold) return { alert: "NONE", message: "No threshold defined" };

  const isLowerWorse = ["CK004", "CK007", "CK019", "CK022", "CK016"].includes(kpiId);
  const isHigherWorse = !isLowerWorse;

  if (isHigherWorse && value >= threshold.critical) {
    return { alert: "CRITICAL", message: `${kpiId} = ${value}${threshold.unit} exceeds critical threshold ${threshold.critical}` };
  }
  if (isHigherWorse && value >= threshold.warning) {
    return { alert: "WARNING", message: `${kpiId} = ${value}${threshold.unit} exceeds warning threshold ${threshold.warning}` };
  }
  if (isLowerWorse && value <= threshold.critical) {
    return { alert: "CRITICAL", message: `${kpiId} = ${value}${threshold.unit} below critical threshold ${threshold.critical}` };
  }
  if (isLowerWorse && value <= threshold.warning) {
    return { alert: "WARNING", message: `${kpiId} = ${value}${threshold.unit} below warning threshold ${threshold.warning}` };
  }

  return { alert: "NONE", message: `${kpiId} = ${value}${threshold.unit} within normal range` };
}

// ─────────────────────────────────────────────────────────────────────────────
// WORKED EXAMPLE TEMPLATES
// Ready-to-use value calculations for sales conversations
// ─────────────────────────────────────────────────────────────────────────────

export const WORKED_EXAMPLE_TEMPLATES = [
  {
    id: "CWE001",
    name: "Regional Health System — HITRUST Acceleration",
    formulaId: "CF002",
    quickCalc: (contractsAtRiskM: number, retentionRiskPct: number, breachProbReduction: number, avgBreachCostM: number) => ({
      contractProtection: contractsAtRiskM * retentionRiskPct,
      breachAvoidance: breachProbReduction * avgBreachCostM,
      total: contractsAtRiskM * retentionRiskPct + breachProbReduction * avgBreachCostM
    })
  },
  {
    id: "CWE002",
    name: "MA Plan — FWA Detection Modernization",
    formulaId: "CF007",
    quickCalc: (prepaySavingsM: number, postpayRecoveryM: number, schemeAvoidanceM: number, siuCostM: number) => ({
      grossValue: prepaySavingsM + postpayRecoveryM + schemeAvoidanceM,
      netValue: prepaySavingsM + postpayRecoveryM + schemeAvoidanceM - siuCostM
    })
  },
  {
    id: "CWE003",
    name: "AMC — MPI Modernization + Cloud Security",
    formulaId: "CF004",
    quickCalc: (admissions: number, dupRateCurrent: number, dupRateTarget: number, costPerDup: number, reworkM: number) => ({
      duplicateSavings: (dupRateCurrent - dupRateTarget) * admissions * costPerDup,
      reworkSavings: reworkM * 0.7, // assume 70% rework reduction
      total: (dupRateCurrent - dupRateTarget) * admissions * costPerDup + reworkM * 0.7
    })
  }
];

// ─────────────────────────────────────────────────────────────────────────────
// DISCOVERY QUESTION SEQUENCES
// Pre-built conversation flows by persona
// ─────────────────────────────────────────────────────────────────────────────

export const DISCOVERY_SEQUENCES: Record<string, string[]> = {
  "Chief Privacy Officer": [
    "CDQ001", // Breach discovery-to-notification time
    "CDQ005", // Consent fragmentation
    "CDQ011", // State privacy law fragmentation
    "CDQ009", // De-identification cycle time
    "CDQ020"  // Strategic initiatives
  ],
  "CISO": [
    "CDQ001", // Breach response
    "CDQ003", // HITRUST status
    "CDQ010", // Third-party risk
    "CDQ015", // Ransomware recovery
    "CDQ016", // SOC coverage
    "CDQ019"  // Cloud security
  ],
  "FHIR Integration Engineer": [
    "CDQ002", // FHIR API performance
    "CDQ014", // HL7 modernization
    "CDQ018", // Data quality
    "CDQ019"  // Cloud migration
  ],
  "SIU Director": [
    "CDQ007", // FWA metrics
    "CDQ020"  // Strategic priorities
  ],
  "Compliance Auditor": [
    "CDQ008", // Coding compliance
    "CDQ018", // Data quality
    "CDQ020"  // Strategic priorities
  ],
  "Patient Identity Architect": [
    "CDQ004", // MPI duplicate rate
    "CDQ018", // Data quality
    "CDQ020"  // Strategic priorities
  ]
};

// ─────────────────────────────────────────────────────────────────────────────
// EXPORTS
// ─────────────────────────────────────────────────────────────────────────────

export default {
  signals: COMPLIANCE_SIGNAL_EXAMPLES,
  thresholds: COMPLIANCE_KPI_THRESHOLDS,
  workedExamples: WORKED_EXAMPLE_TEMPLATES,
  discoverySequences: DISCOVERY_SEQUENCES
};
