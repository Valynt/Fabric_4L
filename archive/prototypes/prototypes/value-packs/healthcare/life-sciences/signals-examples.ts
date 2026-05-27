// Life Sciences Subpack – Signal Interpretation Examples
// ID: life-sciences-v1 | Parent: healthcare-master-v1
// Generated: 2026-04-25 | Agent Swarm: kimi-k2.6-swarm-healthcare-s3.3

// ---------------------------------------------------------------------------
// SignalRule – TypeScript interface (aligned with Master schema)
// ---------------------------------------------------------------------------
export interface SignalInterpretationRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number; // 0.0 – 1.0
  requiredConfirmationSignals: string[];
}

// ---------------------------------------------------------------------------
// Life Sciences Vertical Signal Rules (18)
// ---------------------------------------------------------------------------
export const lifeSciencesSignalRules: SignalInterpretationRule[] = [
  {
    id: "LS-S001",
    signalName: "ClinicalTrials.gov Status Suspended/Terminated/Withdrawn",
    rawSignalPattern: "ClinicalTrials.gov entry changes status to 'suspended', 'terminated', or 'withdrawn' for a sponsor's Phase 2/3 trial",
    interpretedMeaning: "Enrollment or safety issues have caused study halt, indicating pipeline risk, remediation cost, and potential timeline impact of 6-18 months",
    linkedPains: ["LS-P001"],
    linkedKPIs: ["LS-K001", "LS-K003"],
    confidenceScore: 0.92,
    requiredConfirmationSignals: ["LS-S005", "LS-S010"]
  },
  {
    id: "LS-S002",
    signalName: "FDA Complete Response Letter (CRL) Issued",
    rawSignalPattern: "FDA issues CRL for NDA/BLA; press release or SEC filing within 30 days",
    interpretedMeaning: "Regulatory rejection requiring 12-24 month delay. CMC deficiency implies manufacturing quality and process validation gaps.",
    linkedPains: ["LS-P002", "LS-P004"],
    linkedKPIs: ["LS-K005", "LS-K008", "LS-K012"],
    confidenceScore: 0.95,
    requiredConfirmationSignals: ["LS-S003"]
  },
  {
    id: "LS-S003",
    signalName: "FDA Warning Letter with GMP/QSR Data Integrity Citation",
    rawSignalPattern: "Warning Letter posted on FDA.gov with citations under 21 CFR 211 (GMP) or 820 (QSR), especially data integrity or records deficiencies",
    interpretedMeaning: "GxP compliance failure requiring immediate remediation; high risk of CRL, import alert, or consent decree if unresolved within 15 working days",
    linkedPains: ["LS-P002", "LS-P005", "LS-P009", "LS-P015"],
    linkedKPIs: ["LS-K009", "LS-K012"],
    confidenceScore: 0.94,
    requiredConfirmationSignals: ["LS-S009"]
  },
  {
    id: "LS-S004",
    signalName: "Patent Cliff / Loss of Exclusivity within 36 Months for >$500M Product",
    rawSignalPattern: "Orange Book patent expiry or biosimilar FDA approval within 36 months for product generating >$500M annual revenue",
    interpretedMeaning: "Revenue erosion event of 30-80% within 12-24 months; drives lifecycle management, authorized generic, or M&A urgency",
    linkedPains: ["LS-P008"],
    linkedKPIs: ["LS-K015", "LS-K016", "LS-K021"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: ["LS-S007"]
  },
  {
    id: "LS-S005",
    signalName: "Pipeline Asset Phase 2/3 Failure Announcement",
    rawSignalPattern: "Press release or 8-K disclosing discontinuation of Phase 2/3 asset due to futility, safety, or efficacy failure",
    interpretedMeaning: "Portfolio NPV write-down; triggers restructuring, R&D prioritization shift, and potential partnership/acquisition search",
    linkedPains: ["LS-P001", "LS-P012"],
    linkedKPIs: ["LS-K016", "LS-K015"],
    confidenceScore: 0.91,
    requiredConfirmationSignals: ["LS-S010"]
  },
  {
    id: "LS-S006",
    signalName: "10-K Disclosure of R&D Restructuring or Site Closure",
    rawSignalPattern: "Annual report discloses restructuring of R&D organization, site closure, or workforce reduction in clinical or discovery functions",
    interpretedMeaning: "Portfolio rationalization or cost pressure; may indicate pipeline prioritization failure or investor pressure to reduce R&D intensity",
    linkedPains: ["LS-P004", "LS-P013"],
    linkedKPIs: ["LS-K015", "LS-K016"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: ["LS-S005", "LS-S010"]
  },
  {
    id: "LS-S007",
    signalName: "Biosimilar FDA Approval for Reference Product",
    rawSignalPattern: "FDA approves biosimilar or interchangeable biosimilar referencing sponsor's product in Orange Book or Purple Book",
    interpretedMeaning: "Price erosion and market share loss event; triggers defensive contracting, authorized generic launch, or lifecycle management investment",
    linkedPains: ["LS-P008"],
    linkedKPIs: ["LS-K016"],
    confidenceScore: 0.92,
    requiredConfirmationSignals: ["LS-S004"]
  },
  {
    id: "LS-S008",
    signalName: "EMA PRAC Signal Referral or Safety Review Initiation",
    rawSignalPattern: "European Medicines Agency PRAC publishes signal assessment or starts referral procedure for sponsor's product",
    interpretedMeaning: "Pharmacovigilance signal has reached regulatory review level; may trigger label change, risk minimization measures, or product withdrawal in EU",
    linkedPains: ["LS-P003"],
    linkedKPIs: ["LS-K006", "LS-K007"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["LS-S013"]
  },
  {
    id: "LS-S009",
    signalName: "Manufacturing Site Import Alert",
    rawSignalPattern: "FDA issues Import Alert (IA) or places manufacturing site on OAI (Official Action Indicated) status",
    interpretedMeaning: "Supply chain disruption; product cannot enter US; requires remediation and re-inspection; revenue risk if sole source",
    linkedPains: ["LS-P005", "LS-P007", "LS-P016"],
    linkedKPIs: ["LS-K009", "LS-K022"],
    confidenceScore: 0.94,
    requiredConfirmationSignals: ["LS-S003"]
  },
  {
    id: "LS-S010",
    signalName: "C-Suite Departure in Clinical or R&D Functions",
    rawSignalPattern: "Announcement of CMO, Head of R&D, or Chief Scientific Officer departure within 90 days",
    interpretedMeaning: "Leadership instability at critical juncture; may indicate pipeline disappointment, board pressure, or strategic pivot; creates 6-12 month decision paralysis",
    linkedPains: ["LS-P004", "LS-P001", "LS-P013"],
    linkedKPIs: ["LS-K001", "LS-K005", "LS-K016"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["LS-S005", "LS-S006"]
  },
  {
    id: "LS-S011",
    signalName: "CDMO Contract Termination or Public Quality Dispute",
    rawSignalPattern: "SEC filing, press release, or industry reporting discloses termination of CDMO agreement or quality dispute at contract manufacturer",
    interpretedMeaning: "Manufacturing quality transfer failure; supply risk; triggers search for new CDMO or internal capacity expansion; 12-24 month delay risk",
    linkedPains: ["LS-P016", "LS-P005"],
    linkedKPIs: ["LS-K022", "LS-K009"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: ["LS-S009"]
  },
  {
    id: "LS-S012",
    signalName: "Orphan Drug Exclusivity Expiration without Indication Expansion",
    rawSignalPattern: "Orphan drug exclusivity expires within 24 months with no sNDA or line extension in active development",
    interpretedMeaning: "Revenue protection gap; competitor can enter rare disease market; signals underinvestment in lifecycle management",
    linkedPains: ["LS-P013"],
    linkedKPIs: ["LS-K021"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["LS-S004"]
  },
  {
    id: "LS-S013",
    signalName: "Pharmacovigilance Inspection Finding (FDA/MHRA/EMA)",
    rawSignalPattern: "Inspection close-out letter or public record indicates PV-specific finding related to case processing, signal detection, or PSUR/PBRER quality",
    interpretedMeaning: "PV compliance risk; may require CAPA, process overhaul, or vendor replacement; escalates to PRAC referral if signal detection inadequate",
    linkedPains: ["LS-P003"],
    linkedKPIs: ["LS-K006", "LS-K020", "LS-K007"],
    confidenceScore: 0.90,
    requiredConfirmationSignals: ["LS-S008"]
  },
  {
    id: "LS-S014",
    signalName: "RWE Partnership or Acquisition Announcement",
    rawSignalPattern: "Company announces RWE data partnership, registry collaboration, or HEOR consultancy engagement within 90 days",
    interpretedMeaning: "Reactive evidence generation strategy suggests prior underinvestment; may indicate HTA/reimbursement negotiation pressure or label expansion need",
    linkedPains: ["LS-P012", "LS-P014"],
    linkedKPIs: ["LS-K019"],
    confidenceScore: 0.72,
    requiredConfirmationSignals: ["LS-S012", "LS-S006"]
  },
  {
    id: "LS-S015",
    signalName: "eTMF Vendor Replacement RFP or Migration Announcement",
    rawSignalPattern: "Job postings for eTMF migration lead, RFP notice, or press release about new clinical operations platform",
    interpretedMeaning: "Legacy eTMF system inadequate for inspection readiness or multi-trial scale; implies prior TMF-related inspection observation or operational bottleneck",
    linkedPains: ["LS-P006"],
    linkedKPIs: ["LS-K011", "LS-K012"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["LS-S003"]
  },
  {
    id: "LS-S016",
    signalName: "CGT Manufacturing Capacity Expansion Announcement",
    rawSignalPattern: "Press release or investor disclosure announcing new CGT manufacturing facility, capacity expansion, or technology acquisition",
    interpretedMeaning: "Current capacity constraints blocking commercial demand; high COGS or batch failure rate driving vertical integration decision",
    linkedPains: ["LS-P011"],
    linkedKPIs: ["LS-K018"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: ["LS-S011"]
  },
  {
    id: "LS-S017",
    signalName: "ICH E6(R3) Readiness Gap Disclosure",
    rawSignalPattern: "Industry conference presentation, investor call, or consultant engagement signals unpreparedness for ICH E6(R3) GCP update",
    interpretedMeaning: "GCP framework update requiring process, training, and technology changes; non-readiness risks inspection findings and trial delay in 2026-2028",
    linkedPains: ["LS-P001", "LS-P006"],
    linkedKPIs: ["LS-K001", "LS-K011"],
    confidenceScore: 0.70,
    requiredConfirmationSignals: ["LS-S015"]
  },
  {
    id: "LS-S018",
    signalName: "DTx FDA De Novo / 510(k) Clearance Delay or Denial",
    rawSignalPattern: "Digital therapeutic product remains in FDA review beyond typical 150-day de novo or 90-day 510(k) timeline, or receives non-substantial equivalence letter",
    interpretedMeaning: "Software validation, clinical evidence, or SaMD classification issues; delays market entry and reimbursement negotiation; may require additional trial investment",
    linkedPains: ["LS-P017"],
    linkedKPIs: ["LS-K016"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: ["LS-S002"]
  }
];

// ---------------------------------------------------------------------------
// Helper: Filter signals by confidence threshold
// ---------------------------------------------------------------------------
export function getHighConfidenceSignals(
  threshold: number = 0.85
): SignalInterpretationRule[] {
  return lifeSciencesSignalRules.filter((s) => s.confidenceScore >= threshold);
}

// ---------------------------------------------------------------------------
// Helper: Get signals linked to a specific pain
// ---------------------------------------------------------------------------
export function getSignalsForPain(painId: string): SignalInterpretationRule[] {
  return lifeSciencesSignalRules.filter((s) => s.linkedPains.includes(painId));
}

// ---------------------------------------------------------------------------
// Example usage (for agent swarm orchestration):
//
//   const criticalSignals = getHighConfidenceSignals(0.90);
//   const enrollmentSignals = getSignalsForPain("LS-P001");
//
// ---------------------------------------------------------------------------
