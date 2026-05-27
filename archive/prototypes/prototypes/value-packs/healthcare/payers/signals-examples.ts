/**
 * Payers and Health Insurance Subpack — Signal Examples (TypeScript)
 * ID: payers-v1
 * Parent Master: healthcare-master-v1
 * Agent Swarm: kimi-k2.6-swarm-payers-s3.2
 * 
 * This file provides typed, machine-parseable signal interpretation rules
 * and example inference chains for the Payers vertical. It is designed
 * to be imported by orchestration systems that perform signal-to-pain
 * mapping and automated discovery prioritization.
 */

// ─────────────────────────────────────────────────────────────────────────────
// Core Enums & Types
// ─────────────────────────────────────────────────────────────────────────────

export type PayerSegment =
  | "Commercial Health Plans"
  | "Medicare Advantage"
  | "Part D"
  | "Medicaid MCO"
  | "TPA"
  | "PBM"
  | "Stop-Loss"
  | "ACO / VBC";

export type ValueDriverCategory =
  | "Revenue Uplift"
  | "Cost Savings"
  | "Risk Reduction"
  | "Working Capital";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
export type UrgencyLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface PayerSignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];     // PPxxx IDs
  linkedKPIs: string[];      // PKxxx IDs
  linkedPersonas: string[];  // PER-Pxxx IDs
  confidenceScore: number;   // 0.0 – 1.0
  valueDriverCategory: ValueDriverCategory;
  requiredConfirmationSignals: string[];
  estimatedAnnualValueRange?: { min: number; max: number; unit: string };
  exampleEvidence: string[];
}

export interface SignalInferenceChain {
  chainId: string;
  chainName: string;
  triggerSignal: string;     // PSxxx ID
  followUpSignals: string[];
  inferredPain: string;      // PPxxx ID
  recommendedDiscoveryQuestions: string[]; // PDQxxx IDs
  recommendedPersonaOutreach: string[];    // PER-Pxxx IDs
  timeToDecisionEstimate: string;
  competitiveThreatLevel: UrgencyLevel;
}

// ─────────────────────────────────────────────────────────────────────────────
// Signal Rules (18 payer-specific rules)
// ─────────────────────────────────────────────────────────────────────────────

export const PAYER_SIGNAL_RULES: PayerSignalRule[] = [
  {
    id: "PS001",
    signalName: "CMS Star Rating Decline",
    rawSignalPattern: "MA plan declines 0.5+ stars or below 4.0",
    interpretedMeaning: "Quality underperformance threatening QBP bonus ($50-150 PMPM), marketing restriction, and competitive positioning.",
    linkedPains: ["PP001", "PP005"],
    linkedKPIs: ["PK001", "PK002", "PK003", "PK004"],
    linkedPersonas: ["PER-P001", "PER-P002", "PER-P005"],
    confidenceScore: 0.91,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "HEDIS measure detail — which domains declined",
      "CAHPS breakdown — member experience vs. clinical measures",
      "QBP projection — dollar impact at current vs. target stars"
    ],
    estimatedAnnualValueRange: { min: 20000000, max: 200000000, unit: "USD" },
    exampleEvidence: [
      "CMS 2025 Star Ratings public release (Oct 2024)",
      "Plan-specific HEDIS measure scorecard",
      "Internal QBP accrual model"
    ]
  },
  {
    id: "PS002",
    signalName: "MLR Filing – Admin Cost Spike",
    rawSignalPattern: "NAIC filing shows admin cost PMPM increase > 15% YoY or MLR > 87%",
    interpretedMeaning: "Administrative bloat or operational crisis pressuring MLR compliance and competitive pricing ability.",
    linkedPains: ["PP002", "PP003"],
    linkedKPIs: ["PK005", "PK006", "PK007"],
    linkedPersonas: ["PER-P002", "CFO", "COO"],
    confidenceScore: 0.87,
    valueDriverCategory: "Cost Savings",
    requiredConfirmationSignals: [
      "Premium trend vs. admin cost trend comparison",
      "SG&A line item detail — which functions grew",
      "Competitor MLR benchmarking"
    ],
    estimatedAnnualValueRange: { min: 10000000, max: 100000000, unit: "USD" },
    exampleEvidence: [
      "NAIC MLR annual filing (public for publicly traded plans)",
      "10-K / 10-Q SG&A disclosure",
      "CAQH Index admin cost benchmarks"
    ]
  },
  {
    id: "PS003",
    signalName: "CMS Sanctions / CMP Notice",
    rawSignalPattern: "CMS issues sanctions, CMP, or marketing suspension to MA/PDP plan",
    interpretedMeaning: "Compliance failure with direct financial penalties, operational restrictions, and reputational damage. Indicates systemic grievance/appeals or Stars issues.",
    linkedPains: ["PP013", "PP018"],
    linkedKPIs: ["PK037", "PK038", "PK039", "PK052", "PK053"],
    linkedPersonas: ["PER-P004", "CCO", "General Counsel", "PER-P006"],
    confidenceScore: 0.93,
    valueDriverCategory: "Risk Reduction",
    requiredConfirmationSignals: [
      "Sanction type — marketing suspension vs. CMP vs. enrollment freeze",
      "Historical sanction pattern — repeat offender?",
      "Remediation timeline and CMS acceptance"
    ],
    estimatedAnnualValueRange: { min: 5000000, max: 50000000, unit: "USD" },
    exampleEvidence: [
      "CMS Medicare Advantage Compliance Activity report",
      "Plan press release acknowledging sanction",
      "CMS HPMS (Health Plan Management System) notices"
    ]
  },
  {
    id: "PS004",
    signalName: "MA Member Growth Plateau",
    rawSignalPattern: "Quarterly enrollment flat or declining vs. county/state market growth > 2%",
    interpretedMeaning: "Product-market fit deterioration, broker relationship weakness, or member experience deficits threatening plan viability.",
    linkedPains: ["PP007", "PP001"],
    linkedKPIs: ["PK020", "PK021", "PK022"],
    linkedPersonas: ["PER-P002", "Chief Strategy Officer", "VP Member Experience"],
    confidenceScore: 0.85,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "County-level market share trend",
      "Broker commission and production data",
      "Member satisfaction (CAHPS / NPS) correlation"
    ],
    estimatedAnnualValueRange: { min: 15000000, max: 150000000, unit: "USD" },
    exampleEvidence: [
      "CMS Monthly Enrollment by Plan (public)",
      "County health plan competitive filings",
      "Internal broker production reports"
    ]
  },
  {
    id: "PS005",
    signalName: "State DOI Complaint Surge",
    rawSignalPattern: "NAIC complaint index > 1.5x state median for 2+ consecutive quarters",
    interpretedMeaning: "Service quality or claims handling issues escalating to state regulators, creating license risk and CMP exposure.",
    linkedPains: ["PP013"],
    linkedKPIs: ["PK038", "PK039"],
    linkedPersonas: ["PER-P004", "CCO", "General Counsel"],
    confidenceScore: 0.89,
    valueDriverCategory: "Risk Reduction",
    requiredConfirmationSignals: [
      "Complaint category breakdown — claims vs. marketing vs. service",
      "Quarter-over-quarter trend trajectory",
      "Peer plan complaint index comparison"
    ],
    estimatedAnnualValueRange: { min: 2000000, max: 25000000, unit: "USD" },
    exampleEvidence: [
      "NAIC Consumer Complaint Database (public)",
      "State DOI annual complaint report",
      "Internal grievance root cause analysis"
    ]
  },
  {
    id: "PS006",
    signalName: "Medicaid MCO Contract Loss",
    rawSignalPattern: "State awards contract to competitor, reduces service area, or announces rebid",
    interpretedMeaning: "Revenue and margin pressure from core government book. Indicates pricing, quality, or administrative performance gaps.",
    linkedPains: ["PP008", "PP002"],
    linkedKPIs: ["PK005", "PK023", "PK024"],
    linkedPersonas: ["CFO", "PER-P002", "VP Government Programs"],
    confidenceScore: 0.86,
    valueDriverCategory: "Cost Savings",
    requiredConfirmationSignals: [
      "Protest status — did incumbent file?",
      "Remaining contract duration and transition timeline",
      "Winning bidder pricing and quality scores"
    ],
    estimatedAnnualValueRange: { min: 5000000, max: 100000000, unit: "USD" },
    exampleEvidence: [
      "State procurement announcement (public)",
      "Medicaid MCO contract award notice",
      "Incumbent 10-K/10-Q revenue disclosure by state"
    ]
  },
  {
    id: "PS007",
    signalName: "PBM Contract RFP / Termination",
    rawSignalPattern: "PBM client issues RFP or announces non-renewal; health plan insources PBM",
    interpretedMeaning: "Rebate transparency pressure, service quality failure, or cost optimization initiative. Creates technology and analytics opportunity.",
    linkedPains: ["PP010", "PP017"],
    linkedKPIs: ["PK028", "PK029", "PK049", "PK050"],
    linkedPersonas: ["Chief Pharmacy Officer", "CFO", "PER-P002"],
    confidenceScore: 0.84,
    valueDriverCategory: "Cost Savings",
    requiredConfirmationSignals: [
      "Contract value and duration",
      "Competing PBMs in RFP",
      "Client stated reason — cost vs. service vs. transparency"
    ],
    estimatedAnnualValueRange: { min: 10000000, max: 100000000, unit: "USD" },
    exampleEvidence: [
      "Client press release or 10-K disclosure",
      "PBM industry trade publication (Drug Channels, PBMI)",
      "RFP notice on procurement portal"
    ]
  },
  {
    id: "PS008",
    signalName: "High-Cost Claimant / LASER Event",
    rawSignalPattern: "Stop-loss carrier reports claimant exceeding specific deductible; LASER rate > 15%",
    interpretedMeaning: "Underwriting precision declining; high-cost claimant identification and management suboptimal. Clinical management vendor opportunity.",
    linkedPains: ["PP012"],
    linkedKPIs: ["PK034", "PK035", "PK036"],
    linkedPersonas: ["PER-P002", "VP Underwriting", "CFO"],
    confidenceScore: 0.82,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "Claimant diagnosis and prognosis",
      "LASER history by group",
      "Aggregate attachment point trend"
    ],
    estimatedAnnualValueRange: { min: 1000000, max: 15000000, unit: "USD" },
    exampleEvidence: [
      "Stop-loss carrier quarterly report",
      "Self-insured employer benefits committee minutes",
      "High-cost claimant trend analysis"
    ]
  },
  {
    id: "PS009",
    signalName: "RADV Audit Letter Received",
    rawSignalPattern: "CMS issues RADV audit notification or conditional payment demand to MA plan",
    interpretedMeaning: "Documentation quality failure with extrapolation penalty risk. Risk adjustment and coding education vendor critical need.",
    linkedPains: ["PP018", "PP006"],
    linkedKPIs: ["PK052", "PK053", "PK054", "PK017", "PK018"],
    linkedPersonas: ["PER-P006", "CCO", "CFO"],
    confidenceScore: 0.94,
    valueDriverCategory: "Risk Reduction",
    requiredConfirmationSignals: [
      "Audit scope — targeted vs. national",
      "Sample size and HCC categories targeted",
      "Historical RADV error rate and extrapolation"
    ],
    estimatedAnnualValueRange: { min: 5000000, max: 100000000, unit: "USD" },
    exampleEvidence: [
      "CMS RADV audit letter (client confidential)",
      "OIG MA risk adjustment audit public reports",
      "CMS conditional payment demand notice"
    ]
  },
  {
    id: "PS010",
    signalName: "Employer Group Defection Announcement",
    rawSignalPattern: "Employer announces plan switch, self-insured migration, or broker-driven move",
    interpretedMeaning: "Commercial risk erosion indicating pricing, service, or network competitiveness gap. Retention and sales platform opportunity.",
    linkedPains: ["PP009", "PP002"],
    linkedKPIs: ["PK025", "PK026", "PK027"],
    linkedPersonas: ["Chief Strategy Officer", "VP Sales", "PER-P002"],
    confidenceScore: 0.88,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "Group size and premium value",
      "Reason cited — price vs. network vs. service",
      "Broker involvement and commission structure"
    ],
    estimatedAnnualValueRange: { min: 5000000, max: 50000000, unit: "USD" },
    exampleEvidence: [
      "Employer benefits committee public minutes",
      "Broker newsletter or industry publication",
      "Plan 10-K employer group revenue disclosure"
    ]
  },
  {
    id: "PS011",
    signalName: "FWA Whistleblower / Qui Tam Filing",
    rawSignalPattern: "DOJ unseals qui tam relator complaint or announces settlement involving health plan",
    interpretedMeaning: "Systematic fraud detection, coding, or billing practice failure. SIU technology and compliance program overhaul needed.",
    linkedPains: ["PP004"],
    linkedKPIs: ["PK011", "PK012", "PK013"],
    linkedPersonas: ["CCO", "SIU Director", "General Counsel"],
    confidenceScore: 0.92,
    valueDriverCategory: "Risk Reduction",
    requiredConfirmationSignals: [
      "Allegation scope — upcoding, phantom billing, kickbacks",
      "Plan public response or settlement reserve",
      "DOJ settlement range and CIA requirements"
    ],
    estimatedAnnualValueRange: { min: 10000000, max: 200000000, unit: "USD" },
    exampleEvidence: [
      "DOJ press release (public)",
      "Qui tam complaint (public upon unsealing)",
      "Plan 10-K litigation reserve disclosure"
    ]
  },
  {
    id: "PS012",
    signalName: "Network Provider Termination Spree",
    rawSignalPattern: "> 5% of network providers terminated or not renewed in 12-month period",
    interpretedMeaning: "Network adequacy risk and member disruption. May indicate contract rate disputes, network optimization without member protection, or provider system consolidation.",
    linkedPains: ["PP011"],
    linkedKPIs: ["PK031", "PK032", "PK033"],
    linkedPersonas: ["PER-P003", "General Counsel", "Chief Strategy Officer"],
    confidenceScore: 0.81,
    valueDriverCategory: "Risk Reduction",
    requiredConfirmationSignals: [
      "Provider type — primary care vs. specialty vs. hospital",
      "Replacement rate and timeline",
      "Member notification and transition plan"
    ],
    estimatedAnnualValueRange: { min: 2000000, max: 20000000, unit: "USD" },
    exampleEvidence: [
      "Provider termination notices (public filings in some states)",
      "Member newsletter or EOC changes",
      "State DOI network adequacy complaint data"
    ]
  },
  {
    id: "PS013",
    signalName: "HEDIS Audit Finding / NCQA Accreditation Risk",
    rawSignalPattern: "NCQA issues accreditation deferral, HEDIS audit finding, or provisional status",
    interpretedMeaning: "Quality reporting integrity at risk. HEDIS measure jeopardy threatens Stars, employer RFP eligibility, and Medicaid contract renewal.",
    linkedPains: ["PP005", "PP001"],
    linkedKPIs: ["PK016", "PK002"],
    linkedPersonas: ["PER-P001", "PER-P005", "VP Quality"],
    confidenceScore: 0.90,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "Finding type — data integrity vs. measure calculation vs. sampling",
      "Measures affected and Stars weight impact",
      "Remediation timeline and NCQA acceptance criteria"
    ],
    estimatedAnnualValueRange: { min: 5000000, max: 50000000, unit: "USD" },
    exampleEvidence: [
      "NCQA accreditation status report",
      "HEDIS audit findings (client confidential)",
      "CMS Stars technical notes measure exclusions"
    ]
  },
  {
    id: "PS014",
    signalName: "DIR Fee Regulation Comment Letter",
    rawSignalPattern: "Plan or PBM submits CMS comment letter on DIR, True OOP, or counting rules",
    interpretedMeaning: "Pharmacy reimbursement timing and fee structure uncertainty. Indicates significant financial exposure to proposed rule changes.",
    linkedPains: ["PP017"],
    linkedKPIs: ["PK049", "PK050", "PK051"],
    linkedPersonas: ["Chief Pharmacy Officer", "CFO", "PER-P002"],
    confidenceScore: 0.78,
    valueDriverCategory: "Cost Savings",
    requiredConfirmationSignals: [
      "Comment position — supportive vs. opposed vs. alternative proposal",
      "CMS response trajectory and rulemaking timeline",
      "Financial impact model under proposed rule"
    ],
    estimatedAnnualValueRange: { min: 2000000, max: 30000000, unit: "USD" },
    exampleEvidence: [
      "Federal Register comment docket (public)",
      "Plan investor day pharmacy commentary",
      "CMS Part D bidding guidance"
    ]
  },
  {
    id: "PS015",
    signalName: "Digital Member Engagement Vendor RFP",
    rawSignalPattern: "RFP issued for member portal, mobile app, CRM, or digital engagement platform",
    interpretedMeaning: "Digital maturity gap driving service cost and member dissatisfaction. Retention and experience platform opportunity.",
    linkedPains: ["PP015", "PP007"],
    linkedKPIs: ["PK022", "PK043", "PK044", "PK045"],
    linkedPersonas: ["VP Member Experience", "CIO", "Chief Strategy Officer"],
    confidenceScore: 0.76,
    valueDriverCategory: "Cost Savings",
    requiredConfirmationSignals: [
      "Incumbent vendor and contract status",
      "RFP scope — portal only vs. omnichannel vs. care gap closure",
      "Timeline and budget indication"
    ],
    estimatedAnnualValueRange: { min: 3000000, max: 25000000, unit: "USD" },
    exampleEvidence: [
      "Public procurement portal RFP notice",
      "Job postings for digital product managers",
      "Industry analyst briefings"
    ]
  },
  {
    id: "PS016",
    signalName: "ACO Shared Savings Miss",
    rawSignalPattern: "MSSP or commercial ACO misses savings target; provider exit or non-renewal",
    interpretedMeaning: "Value-based contract underperformance eroding provider trust and threatening shared savings revenue.",
    linkedPains: ["PP014", "PP011"],
    linkedKPIs: ["PK040", "PK041", "PK042"],
    linkedPersonas: ["PER-P005", "CFO", "PER-P003"],
    confidenceScore: 0.83,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "ACO track record — 1-year miss vs. multi-year pattern",
      "Measure performance detail",
      "Provider sentiment survey or exit interview"
    ],
    estimatedAnnualValueRange: { min: 5000000, max: 50000000, unit: "USD" },
    exampleEvidence: [
      "CMS MSSP financial results (public)",
      "ACO press release or provider newsletter",
      "CMS ACO REACH performance data"
    ]
  },
  {
    id: "PS017",
    signalName: "COB / Subrogation Vendor Search",
    rawSignalPattern: "Job postings or RFP for COB, subrogation, MSP compliance, or recovery services",
    interpretedMeaning: "Recovery gap or Medicare Secondary Payer compliance concern. Indicates underperforming current vendor or insourcing initiative.",
    linkedPains: ["PP016"],
    linkedKPIs: ["PK046", "PK047", "PK048"],
    linkedPersonas: ["VP Claims", "CFO", "PER-P002"],
    confidenceScore: 0.79,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "Current vendor and contract expiration",
      "Recovery rate vs. industry benchmark",
      "MSP error rate and conditional payment backlog"
    ],
    estimatedAnnualValueRange: { min: 1000000, max: 15000000, unit: "USD" },
    exampleEvidence: [
      "Job postings for COB/subrogation analysts",
      "RFP on procurement portal",
      "CMS MSP compliance report (client confidential)"
    ]
  },
  {
    id: "PS018",
    signalName: "Risk Adjustment Vendor Consolidation",
    rawSignalPattern: "Job postings for in-house risk adjustment, retrospective chart review, or vendor RFP for RAF optimization",
    interpretedMeaning: "RAF optimization pressure or RADV response need. May indicate current vendor underperformance or cost reduction initiative.",
    linkedPains: ["PP006", "PP018"],
    linkedKPIs: ["PK017", "PK018", "PK019"],
    linkedPersonas: ["PER-P006", "CFO", "CCO"],
    confidenceScore: 0.86,
    valueDriverCategory: "Revenue Uplift",
    requiredConfirmationSignals: [
      "Current vendor performance and contract status",
      "RAF trend vs. market benchmark",
      "RADV audit status and extrapolation exposure"
    ],
    estimatedAnnualValueRange: { min: 3000000, max: 50000000, unit: "USD" },
    exampleEvidence: [
      "Job postings for risk adjustment analysts/coders",
      "Vendor RFP on procurement portal",
      "Internal RAF dashboard trend"
    ]
  }
];

// ─────────────────────────────────────────────────────────────────────────────
// Inference Chains (example multi-signal sequences)
// ─────────────────────────────────────────────────────────────────────────────

export const PAYER_INFERENCE_CHAINS: SignalInferenceChain[] = [
  {
    chainId: "PIC001",
    chainName: "MA Stars Death Spiral",
    triggerSignal: "PS001",
    followUpSignals: ["PS004", "PS005", "PS013"],
    inferredPain: "PP001",
    recommendedDiscoveryQuestions: ["PDQ001", "PDQ004", "PDQ017", "PDQ005"],
    recommendedPersonaOutreach: ["PER-P001", "PER-P002", "PER-P005", "PER-P006"],
    timeToDecisionEstimate: "6-9 months (board-level priority)",
    competitiveThreatLevel: "HIGH"
  },
  {
    chainId: "PIC002",
    chainName: "Medicaid MCO Margin Crisis",
    triggerSignal: "PS006",
    followUpSignals: ["PS002", "PS017"],
    inferredPain: "PP008",
    recommendedDiscoveryQuestions: ["PDQ006", "PDQ003", "PDQ014"],
    recommendedPersonaOutreach: ["CFO", "PER-P002", "VP Government Programs"],
    timeToDecisionEstimate: "9-18 months (strategic rebid cycle)",
    competitiveThreatLevel: "HIGH"
  },
  {
    chainId: "PIC003",
    chainName: "RADV Compliance Emergency",
    triggerSignal: "PS009",
    followUpSignals: ["PS003", "PS018"],
    inferredPain: "PP018",
    recommendedDiscoveryQuestions: ["PDQ004", "PDQ016", "PDQ011"],
    recommendedPersonaOutreach: ["PER-P006", "CCO", "CFO"],
    timeToDecisionEstimate: "1-3 months (accelerated compliance)",
    competitiveThreatLevel: "CRITICAL"
  },
  {
    chainId: "PIC004",
    chainName: "Commercial Risk Erosion",
    triggerSignal: "PS010",
    followUpSignals: ["PS007", "PS012"],
    inferredPain: "PP009",
    recommendedDiscoveryQuestions: ["PDQ007", "PDQ008", "PDQ009"],
    recommendedPersonaOutreach: ["Chief Strategy Officer", "VP Sales", "PER-P002"],
    timeToDecisionEstimate: "6-12 months (sales cycle)",
    competitiveThreatLevel: "HIGH"
  },
  {
    chainId: "PIC005",
    chainName: "Digital Maturity Gap",
    triggerSignal: "PS015",
    followUpSignals: ["PS004", "PS005"],
    inferredPain: "PP015",
    recommendedDiscoveryQuestions: ["PDQ013", "PDQ005", "PDQ018"],
    recommendedPersonaOutreach: ["VP Member Experience", "CIO", "Chief Strategy Officer"],
    timeToDecisionEstimate: "6-9 months (platform selection)",
    competitiveThreatLevel: "MEDIUM"
  }
];

// ─────────────────────────────────────────────────────────────────────────────
// Utility Functions
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Find all signal rules linked to a specific pain.
 */
export function getSignalsByPain(painId: string): PayerSignalRule[] {
  return PAYER_SIGNAL_RULES.filter(rule => rule.linkedPains.includes(painId));
}

/**
 * Find all signal rules linked to a specific KPI.
 */
export function getSignalsByKPI(kpiId: string): PayerSignalRule[] {
  return PAYER_SIGNAL_RULES.filter(rule => rule.linkedKPIs.includes(kpiId));
}

/**
 * Find all signal rules by confidence threshold.
 */
export function getSignalsByConfidence(minScore: number): PayerSignalRule[] {
  return PAYER_SIGNAL_RULES.filter(rule => rule.confidenceScore >= minScore);
}

/**
 * Get inference chains that include a specific trigger signal.
 */
export function getChainsByTrigger(signalId: string): SignalInferenceChain[] {
  return PAYER_INFERENCE_CHAINS.filter(chain =>
    chain.triggerSignal === signalId || chain.followUpSignals.includes(signalId)
  );
}

/**
 * Calculate total estimated value exposure for a set of pains.
 */
export function calculateValueExposure(painIds: string[]): { min: number; max: number; unit: string } {
  let minTotal = 0;
  let maxTotal = 0;
  
  for (const painId of painIds) {
    const rules = getSignalsByPain(painId);
    for (const rule of rules) {
      if (rule.estimatedAnnualValueRange) {
        minTotal += rule.estimatedAnnualValueRange.min;
        maxTotal += rule.estimatedAnnualValueRange.max;
      }
    }
  }
  
  return { min: minTotal, max: maxTotal, unit: "USD" };
}

// ─────────────────────────────────────────────────────────────────────────────
// Export all for orchestration
// ─────────────────────────────────────────────────────────────────────────────

export const PAYER_SIGNALS_MODULE = {
  rules: PAYER_SIGNAL_RULES,
  chains: PAYER_INFERENCE_CHAINS,
  metadata: {
    subpackId: "payers-v1",
    parentMasterId: "healthcare-master-v1",
    version: "1.0.0",
    totalRules: PAYER_SIGNAL_RULES.length,
    totalChains: PAYER_INFERENCE_CHAINS.length,
    lastUpdated: "2026-04-25"
  }
};
