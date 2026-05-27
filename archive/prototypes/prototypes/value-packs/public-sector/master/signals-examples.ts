/**
 * Public Sector Master Value Pack - Signal-to-Hypothesis Worked Examples
 * 
 * This file demonstrates the end-to-end reasoning chain from raw market/prospect
 * signals through to quantified value hypotheses, with confidence scoring and
 * evidence requirements at each step.
 * 
 * Pack: public-sector-master-v1
 * Version: 1.0.0
 */

// ============================================================================
// TYPE DEFINITIONS (mirrors MasterValuePack schema interfaces)
// ============================================================================

type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
type ValueDriverCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";

interface RawSignal {
  id: string;
  source: string;
  timestamp: string;
  signalType: string;
  rawData: string;
  credibility: ConfidenceLevel;
}

interface InterpretedSignal {
  id: string;
  rawSignalId: string;
  ruleId: string;
  interpretedMeaning: string;
  confidenceScore: number; // 0.0 - 1.0
  linkedPains: string[];
  linkedKPIs: string[];
  requiredConfirmationSignals: string[];
}

interface ValueHypothesis {
  id: string;
  interpretedSignalId: string;
  painId: string;
  valueDriverCategory: ValueDriverCategory;
  hypothesisStatement: string;
  affectedPersonas: string[];
  impactedKPIs: string[];
  applicableFormulaId: string;
  estimatedAnnualValue: {
    low: number;
    mid: number;
    high: number;
    unit: string;
  };
  confidence: ConfidenceLevel;
  evidenceNeeded: string[];
  discoveryQuestions: string[];
}

// ============================================================================
// EXAMPLE 1: Medicaid State Agency - Eligibility Churn Signal
// ============================================================================

/**
 * SCENARIO: A state Medicaid agency (SMA) is approaching the end of the
 * post-COVID unwinding period. A prospecting team observes signals from
 * CMS public reports, state budget documents, and KFF tracking data.
 */

const ex1_rawSignal: RawSignal = {
  id: "SIG-EX1-001",
  source: "CMS Medicaid Unwinding Data + KFF State Tracker + State Budget Justification",
  timestamp: "2026-04-25",
  signalType: "Program Churn / Ex Parte Renewal Rate",
  rawData: "State X disenrolled 850,000 Medicaid beneficiaries during unwinding; ex parte renewal rate at 18% vs. CMS target 75%; churn rate 28% for children; 45-day eligibility determination time exceeds statutory 90-day for 23% of applications; state share growing at 8.2% vs. 3.1% revenue growth",
  credibility: "HIGH"
};

const ex1_interpretedSignal: InterpretedSignal = {
  id: "INT-EX1-001",
  rawSignalId: "SIG-EX1-001",
  ruleId: "PS-SIG-021", // High Program Churn / Ex Parte Low
  interpretedMeaning:
    "The state Medicaid agency has a severely broken eligibility determination " +
    "and renewal process. Ex parte renewal at 18% means 82% of renewals require " +
    "manual processing, creating massive administrative burden. The 28% child " +
    "churn rate suggests many children losing coverage despite likely ongoing " +
    "eligibility. State share growing faster than revenue indicates the program " +
    "is crowding out other priorities. This is a compound pain: administrative " +
    "inefficiency + coverage gaps + fiscal pressure + CMS compliance risk.",
  confidenceScore: 0.92,
  linkedPains: ["PS-PAIN-016", "PS-PAIN-021", "PS-PAIN-003", "PS-PAIN-011"],
  linkedKPIs: ["PS-KPI-033", "PS-KPI-040", "PS-KPI-007", "PS-KPI-025"],
  requiredConfirmationSignals: [
    "State unwinding data (T-MSIS)",
    "Eligibility system vendor and version",
    "State Medicaid administrative cost per enrollee",
    "CMS 1115 waiver or SPA modification status",
    "Staffing levels for eligibility workers"
  ]
};

const ex1_valueHypothesis: ValueHypothesis = {
  id: "VH-EX1-001",
  interpretedSignalId: "INT-EX1-001",
  painId: "PS-PAIN-021", // Program Eligibility Determination Errors & Delays
  valueDriverCategory: "Cost Savings",
  hypothesisStatement:
    "By implementing automated ex parte renewal, integrated data verification, " +
    "and modernized eligibility determination workflows, the state can reduce " +
    "churn from 28% to 12%, cut eligibility determination time from 45 days to " +
    "15 days, and lower administrative cost per enrollee by $200/year. This " +
    "improves CMS compliance posture, reduces manual processing FTE needs, and " +
    "minimizes coverage gaps that drive downstream health cost increases.",
  affectedPersonas: [
    "PS-PERS-003 (Medicaid Director - mission + budget accountability)",
    "PS-PERS-008 (Eligibility Specialist - frontline burden)",
    "PS-PERS-002 (CFO - state share pressure + audit risk)",
    "PS-PERS-005 (Inspector General - program integrity)"
  ],
  impactedKPIs: [
    "PS-KPI-033 (Program Churn Rate): 28% -> 12%",
    "PS-KPI-040 (Ex Parte Renewal Rate): 18% -> 80%",
    "PS-KPI-007 (Case Processing Time): 45 days -> 15 days",
    "PS-KPI-025 (Cost Per Transaction): reduction via automation"
  ],
  applicableFormulaId: "PS-VF-022", // Ex Parte Renewal Efficiency Value
  estimatedAnnualValue: {
    low: 18_500_000,
    mid: 32_000_000,
    high: 55_000_000,
    unit: "USD (annual state savings + retained federal match)"
  },
  confidence: "HIGH",
  evidenceNeeded: [
    "State Medicaid budget document showing administrative spend and enrollment",
    "CMS T-MSIS unwinding report with state-specific churn data",
    "Eligibility system technical architecture assessment",
    "Staffing model and FTE cost data",
    "Peer state case study (e.g., states achieving >70% ex parte)",
    "Current manual processing cost per renewal/transaction"
  ],
  discoveryQuestions: [
    "What is your current ex parte renewal rate, and what are the top 3 barriers?",
    "How many FTEs are dedicated to manual eligibility renewal processing?",
    "What was your CMS unwinding corrective action plan response?",
    "Have you assessed the cost of churn in terms of downstream health expenditures?",
    "What is your eligibility system's upgrade/ replacement timeline?"
  ]
};

// ============================================================================
// EXAMPLE 2: Federal Civilian Agency - Legacy + Cybersecurity Compound Signal
// ============================================================================

/**
 * SCENARIO: A mid-sized federal civilian agency (e.g., DOL, EPA, or SBA) has
 * been flagged in the latest FISMA report with persistent deficiencies. The
 * agency's CIO testifies before Congress about modernization needs. Meanwhile,
 * GAO reports show 78% of IT spend goes to O&M on systems averaging 22 years
 * of age. A TMF proposal is pending.
 */

const ex2_rawSignal: RawSignal = {
  id: "SIG-EX2-001",
  source: "FISMA Report to Congress + GAO-24-xxxxx + Agency CIO Congressional Testimony + TMF Proposal Pipeline",
  timestamp: "2026-04-25",
  signalType: "Legacy O&M + Cybersecurity + Modernization Mandate",
  rawData: "Agency Y: O&M at 78% of $180M IT budget; 14 of 23 major systems >20 years old; 3 systems have vendor EOL within 18 months; FISMA rating 'At Risk'; 43 unpatched critical CVEs >45 days; no Zero Trust architecture plan; 35% of cybersecurity positions vacant; TMF proposal submitted for $45M modernization initiative; FITARA score dropped from B- to C+",
  credibility: "HIGH"
};

const ex2_interpretedSignal: InterpretedSignal = {
  id: "INT-EX2-001",
  rawSignalId: "SIG-EX2-001",
  ruleId: "PS-SIG-001", // Legacy System Maintenance
  interpretedMeaning:
    "The agency is trapped in a legacy maintenance cycle that consumes nearly " +
    "4/5 of its IT budget, leaving minimal resources for modernization. The " +
    "compound effect is severe: aging systems create cybersecurity gaps (43 " +
    "unpatched CVEs), the cybersecurity workforce is understaffed (35% vacant), " +
    "and there is no Zero Trust roadmap. Three impending vendor EOL events will " +
    "force replacement decisions within 18 months. The TMF proposal and FITARA " +
    "score decline indicate leadership awareness and external pressure. This is a " +
    "compound transformation opportunity: modernization + security + workforce.",
  confidenceScore: 0.95,
  linkedPains: ["PS-PAIN-001", "PS-PAIN-002", "PS-PAIN-006", "PS-PAIN-023", "PS-PAIN-011"],
  linkedKPIs: ["PS-KPI-001", "PS-KPI-003", "PS-KPI-004", "PS-KPI-028", "PS-KPI-012", "PS-KPI-029"],
  requiredConfirmationSignals: [
    "System inventory with age, vendor, and EOL dates",
    "FISMA POA&M (Plan of Action and Milestones)",
    "TMF proposal details and status",
    "Cybersecurity workforce analysis (OPM FedScope or agency data)",
    "Vulnerability scan reports (CISA KEV overlap)"
  ]
};

const ex2_valueHypothesis: ValueHypothesis = {
  id: "VH-EX2-001",
  interpretedSignalId: "INT-EX2-001",
  painId: "PS-PAIN-001", // Legacy System Maintenance Burden
  valueDriverCategory: "Cost Savings",
  hypothesisStatement:
    "By modernizing 8 of the 14 legacy systems to cloud-native architectures, " +
    "implementing Zero Trust identity and access management, and deploying " +
    "automated vulnerability management, the agency can reduce O&M from 78% to " +
    "52% of IT spend over 3 years, achieve FedRAMP ATO for 6 new systems, and " +
    "reduce mean-time-to-patch from 45 days to 7 days. The TMF-funded portion " +
    "($45M) catalyzes agency match ($45M) and unlocks recurring O&M savings " +
    "of $35M annually by year 3.",
  affectedPersonas: [
    "PS-PERS-001 (CIO - FITARA score, modernization mandate)",
    "PS-PERS-004 (CISO - FISMA rating, breach risk)",
    "PS-PERS-002 (CFO - budget execution, OMB scorecard)",
    "PS-PERS-005 (IG - repeat findings, POA&M closure)"
  ],
  impactedKPIs: [
    "PS-KPI-001 (Legacy O&M Ratio): 78% -> 52%",
    "PS-KPI-003 (Mean Time to Patch): 45 days -> 7 days",
    "PS-KPI-004 (Critical Vulnerability Count): 43 -> trending to 0",
    "PS-KPI-028 (Zero Trust Maturity Score): 1.2 -> 3.5+",
    "PS-KPI-029 (Cloud Cost Per Workload): optimized via FinOps",
    "PS-KPI-012 (Vacancy Rate): 35% -> 15% via automation + contractor-to-FTE"
  ],
  applicableFormulaId: "PS-VF-001", // Legacy O&M Cost Avoidance
  estimatedAnnualValue: {
    low: 25_000_000,
    mid: 42_000_000,
    high: 68_000_000,
    unit: "USD (3-year NPV of O&M reduction + risk avoidance)"
  },
  confidence: "HIGH",
  evidenceNeeded: [
    "Agency IT budget with O&M vs. DME breakout (CBJ or PAR)",
    "System inventory from EA repository or IRM office",
    "Vendor EOL notices and support contract terms",
    "FISMA POA&M showing open deficiencies and remediation plans",
    "TMF proposal with technical approach and cost model",
    "Cybersecurity workforce plan (CDM, cyber hiring surge data)",
    "GAO or OIG report with specific findings and recommendations"
  ],
  discoveryQuestions: [
    "What are your top 3 systems at highest risk of failure or EOL?",
    "How much of your O&M budget is spent on systems that could be retired?",
    "What is your agency's Zero Trust implementation timeline per OMB M-22-09?",
    "How many POA&M items are >180 days past due?",
    "If TMF funding is approved, what is your agency match strategy?",
    "What is your current cloud migration status and what has blocked progress?"
  ]
};

// ============================================================================
// EXAMPLE 3: Municipal Water Utility - Infrastructure + Compliance Signal
// ============================================================================

/**
 * SCENARIO: A municipal water utility serving 450,000 residents is under
 * EPA consent decree for lead service line replacement and PFAS contamination.
 * Rate cases are contentious. The utility has a $2.1B CIP but faces
 * affordability constraints. Smart water meter deployment is at 12%.
 */

const ex3_rawSignal: RawSignal = {
  id: "SIG-EX3-001",
  source: "EPA SDWIS + Consent Decree Filing + Rate Case Docket + CIP Document + AWWA M36 Assessment",
  timestamp: "2026-04-25",
  signalType: "Infrastructure Degradation + Regulatory Compliance + Affordability Crisis",
  rawData: "Municipal Water Utility Z: EPA consent decree for lead service lines (45,000 remaining, 20-year deadline); PFAS detected above EPA MCL in 3 of 8 treatment plants; unaccounted-for water at 24%; water main breaks averaging 18/month; smart meter deployment at 12%; CIP of $2.1B over 10 years; rate increase of 6.8% denied by city council due to affordability concerns; 22% of customers in arrears; SCADA system is 19 years old with vendor EOL announced; deferred maintenance backlog $380M; workforce vacancy rate 18% for licensed operators",
  credibility: "HIGH"
};

const ex3_interpretedSignal: InterpretedSignal = {
  id: "INT-EX3-001",
  rawSignalId: "SIG-EX3-001",
  ruleId: "PS-SIG-018", // Water System Violations and Breaks
  interpretedMeaning:
    "The utility faces a multi-front crisis: regulatory (EPA consent decree with " +
    "enforceable timeline), infrastructure (high UFW, frequent main breaks, aging " +
    "SCADA), financial (affordability constraints blocking rate increases, high " +
    "customer arrears), and workforce (operator vacancies threatening compliance). " +
    "The low smart meter penetration prevents real-time leak detection and demand " +
    "management. Without intervention, the utility risks: EPA enforcement escalation, " +
    "service interruptions, credit rating downgrade, and potential state takeover. " +
    "The compound opportunity is infrastructure + technology + compliance.",
  confidenceScore: 0.94,
  linkedPains: ["PS-PAIN-018", "PS-PAIN-010", "PS-PAIN-006", "PS-PAIN-011", "PS-PAIN-001"],
  linkedKPIs: ["PS-KPI-035", "PS-KPI-018", "PS-KPI-019", "PS-KPI-034", "PS-KPI-012", "PS-KPI-030"],
  requiredConfirmationSignals: [
    "EPA consent decree text and compliance milestones",
    "Asset condition assessment (latest AWWA M36 or equivalent)",
    "Rate case docket and affordability study",
    "SCADA system vendor EOL notice and replacement cost estimate",
    "Customer billing/arrears data by income segment",
    "Operator license status and vacancy detail"
  ]
};

const ex3_valueHypothesis: ValueHypothesis = {
  id: "VH-EX3-001",
  interpretedSignalId: "INT-EX3-001",
  painId: "PS-PAIN-018", // Water/Wastewater System Affordability & Infrastructure Gap
  valueDriverCategory: "Risk Reduction",
  hypothesisStatement:
    "By deploying smart water meters (AMI) with real-time leak detection, " +
    "modernizing the SCADA system, implementing predictive analytics for main break " +
    "prevention, and deploying a customer assistance portal with income-based " +
    "rate programs, the utility can reduce unaccounted-for water from 24% to 12%, " +
    "cut main breaks by 40%, improve customer payment timeliness by 25%, and achieve " +
    "EPA consent decree milestones on schedule. This avoids EPA penalty escalation " +
    "(up to $50K/day), deferred replacement cost inflation, and service interruption " +
    "liability. Smart infrastructure also enables operational optimization reducing " +
    "energy and chemical costs by 8-12%.",
  affectedPersonas: [
    "PS-PERS-009 (Utility Director - regulatory + infrastructure + rate accountability)",
    "PS-PERS-002 (CFO/City Finance - affordability constraints + bond rating)",
    "PS-PERS-014 (City Council / Mayor - political pressure + public health)",
    "PS-PERS-011 (Emergency Manager - service continuity + disaster resilience)"
  ],
  impactedKPIs: [
    "PS-KPI-035 (Unaccounted-for Water): 24% -> 12%",
    "PS-KPI-018 (Asset Condition Index): trending improvement via preventive maintenance",
    "PS-KPI-019 (Deferred Maintenance Ratio): $380M backlog reduction through targeted CIP",
    "PS-KPI-034 (Infrastructure Replacement Rate): accelerated to >2.5% annually",
    "PS-KPI-027 (Revenue Collection Rate): improved via AMI accuracy + customer assistance",
    "PS-KPI-030 (System Availability): SCADA modernization improves reliability to 99.9%+"
  ],
  applicableFormulaId: "PS-VF-014", // Water Loss Reduction Value
  estimatedAnnualValue: {
    low: 8_500_000,
    mid: 18_000_000,
    high: 35_000_000,
    unit: "USD (annual: water revenue recovery + penalty avoidance + O&M efficiency + deferred cost avoidance)"
  },
  confidence: "HIGH",
  evidenceNeeded: [
    "EPA consent decree with specific milestones and penalties",
    "Water audit (AWWA M36) with component analysis of NRW",
    "Rate case docket with affordability study and customer impact analysis",
    "SCADA system assessment and vendor EOL documentation",
    "CIP plan with project priorities and funding sources",
    "Peer utility case study (similar size, AMI deployment outcomes)",
    "Customer arrears data and current assistance program uptake",
    "Bond rating report and credit agency commentary"
  ],
  discoveryQuestions: [
    "What is the current status of your EPA consent decree milestones, and what's the penalty exposure?",
    "Have you conducted a water audit to break down non-revenue water by component (leaks, metering, unauthorized use)?",
    "What is your smart meter deployment plan, and what has blocked accelerated rollout?",
    "How do you balance rate affordability with infrastructure investment needs?",
    "What is your SCADA end-of-life plan, and have you assessed cybersecurity risks?",
    "What percentage of your operator workforce is eligible for retirement in the next 5 years?"
  ]
};

// ============================================================================
// EXPORTS - All worked examples for orchestrator integration
// ============================================================================

export const workedExamples = {
  ex1: {
    name: "Medicaid State Agency - Eligibility Churn",
    rawSignal: ex1_rawSignal,
    interpretedSignal: ex1_interpretedSignal,
    valueHypothesis: ex1_valueHypothesis,
    segment: "D. Public Health and Human Services",
    subSegment: "Medicaid State Agencies (SMAs)"
  },
  ex2: {
    name: "Federal Civilian Agency - Legacy + Cybersecurity Compound",
    rawSignal: ex2_rawSignal,
    interpretedSignal: ex2_interpretedSignal,
    valueHypothesis: ex2_valueHypothesis,
    segment: "A. Federal Government",
    subSegment: "Civilian Agencies (GSA, SBA, State, Interior)"
  },
  ex3: {
    name: "Municipal Water Utility - Infrastructure + Compliance Crisis",
    rawSignal: ex3_rawSignal,
    interpretedSignal: ex3_interpretedSignal,
    valueHypothesis: ex3_valueHypothesis,
    segment: "E. Public Infrastructure and Utilities",
    subSegment: "Water Utilities (Drinking Water, Treatment)"
  }
};

export type { RawSignal, InterpretedSignal, ValueHypothesis, ConfidenceLevel, ValueDriverCategory };
