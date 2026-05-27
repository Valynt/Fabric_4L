/**
 * Federal Government Subpack (S5.1) — Signal Rules & Buying Triggers
 * 
 * TypeScript-style definitions for machine-parseable signal interpretation,
 * buying trigger detection, and persona-based routing.
 * 
 * Parent Master: public-sector-master-v1
 * Subpack ID: federal-v1
 * Version: 1.0.0
 * Last Updated: 2026-04-25
 */

// ============================================================================
// CORE TYPES
// ============================================================================

export type Confidence = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Urgency = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
export type Prevalence = "LOW" | "MEDIUM" | "HIGH";
export type ValueDriverCategory =
  | "Cost Savings"
  | "Revenue Uplift"
  | "Risk Reduction"
  | "Working Capital"
  | "Mission Effectiveness"
  | "Compliance"
  | "Time-to-Value";

export interface SignalRule {
  id: string;
  name: string;
  rawSignalPatterns: string[];
  interpretedMeaning: string;
  linkedPainIds: string[];
  linkedKpiIds: string[];
  confidence: number; // 0.0 - 1.0
  requiredConfirmationSignals: string[];
  triggerThreshold?: string;
}

export interface BuyingTrigger {
  id: string;
  name: string;
  triggerEvent: string;
  urgencyLevel: Urgency;
  typicalTimingDays: [number, number];
  affectedSegmentIds: string[];
  linkedPainIds: string[];
  procurementImplications: string;
  cta: string; // Recommended call-to-action for sellers
}

export interface PersonaRoutingRule {
  personaId: string;
  personaName: string;
  triggerKeywords: string[];
  discoveryQuestionIds: string[];
  objectionIds: string[];
  valueFormulaIds: string[];
  preferredEvidenceTypes: string[];
}

export interface ValueFormulaCalc {
  formulaId: string;
  formulaName: string;
  inputs: Record<string, string>;
  outputUnit: string;
  confidence: Confidence;
}

// ============================================================================
// SIGNAL RULES (18 rules)
// ============================================================================

export const FED_SIGNAL_RULES: SignalRule[] = [
  {
    id: "FED-SIG-001",
    name: "RMF ATO Delay Signal",
    rawSignalPatterns: [
      "eMASS package status unchanged >90 days",
      "POA&M items aging >120 days",
      "ISSO turnover detected during ATO process",
      "Interim ATO duration >12 months"
    ],
    interpretedMeaning:
      "RMF process bottlenecked by control implementation gaps, SCA review delays, or resource constraints. System deployment and program schedule at risk.",
    linkedPainIds: ["FED-PAIN-001"],
    linkedKpiIds: ["FED-KPI-001", "FED-KPI-013"],
    confidence: 0.88,
    requiredConfirmationSignals: [
      "eMASS status report",
      "ISSO staffing plan",
      "SCA availability schedule",
      "POA&M age analysis"
    ]
  },
  {
    id: "FED-SIG-002",
    name: "FITARA Score Decline Signal",
    rawSignalPatterns: [
      "OMB scorecard score declined QoQ",
      "Data center consolidation behind plan",
      "Working capital fund underutilized",
      "CIO authority gaps in budget formulation"
    ],
    interpretedMeaning:
      "Agency IT governance underperforming. Modernization funding, consolidation, and workforce management face structural barriers. Congressional scrutiny likely.",
    linkedPainIds: ["FED-PAIN-002", "FED-PAIN-003"],
    linkedKpiIds: ["FED-KPI-003", "PS-KPI-001"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "OMB scorecard",
      "Budget justification IT section",
      "Data center closure schedule",
      "CIO org chart"
    ]
  },
  {
    id: "FED-SIG-003",
    name: "Continuing Resolution Planning Freeze Signal",
    rawSignalPatterns: [
      "CR in effect >3 months",
      "New start freeze invoked by OMB",
      "Q1 obligation rate <15% of annual",
      "Q4 obligation rate >45%"
    ],
    interpretedMeaning:
      "Agency cannot execute multi-year planning. Procurement timelines compressed. Q4 spend surge creates waste and suboptimal awards.",
    linkedPainIds: ["FED-PAIN-003"],
    linkedKpiIds: ["FED-KPI-007", "FED-KPI-014"],
    confidence: 0.92,
    requiredConfirmationSignals: [
      "OMB CR guidance",
      "Agency contingency plan",
      "FPDS obligation timing data",
      "Contract stop-work history"
    ]
  },
  {
    id: "FED-SIG-004",
    name: "FedRAMP Marketplace Gap Signal",
    rawSignalPatterns: [
      "Agency ATO queue >20 pending",
      "CSP withdrawn from FedRAMP in last 12 months",
      "Shadow IT cloud detected via CASB",
      "SaaS procurement blocked pending ATO"
    ],
    interpretedMeaning:
      "FedRAMP authorization capacity insufficient for agency cloud demand. Shadow IT risk rising. Innovation adoption constrained.",
    linkedPainIds: ["FED-PAIN-004"],
    linkedKpiIds: ["FED-KPI-009", "PS-KPI-029"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "FedRAMP ATO tracker",
      "CASB shadow IT report",
      "Cloud procurement pipeline",
      "CSP engagement status"
    ]
  },
  {
    id: "FED-SIG-005",
    name: "CMMC Compliance Gap Signal",
    rawSignalPatterns: [
      "SPRSSP score <100",
      "POA&M items >50",
      "C3PAO assessment not scheduled",
      "Subcontractor compliance unverified",
      "Contract award eligibility at risk"
    ],
    interpretedMeaning:
      "DOD contractor not ready for CMMC Level 2/3. Supply chain accreditation risk. Potential contract loss or stop-work.",
    linkedPainIds: ["FED-PAIN-005"],
    linkedKpiIds: ["FED-KPI-004", "FED-KPI-011"],
    confidence: 0.90,
    requiredConfirmationSignals: [
      "SPRSSP report",
      "C3PAO engagement letter",
      "Subcontractor compliance attestations",
      "DoD contract eligibility review"
    ]
  },
  {
    id: "FED-SIG-006",
    name: "1102 Workforce Crisis Signal",
    rawSignalPatterns: [
      "1102 vacancy rate >18%",
      "Procurement action lead time >250 days",
      "Protest rate >5% on IT acquisitions",
      "Requirements packages >3 revisions"
    ],
    interpretedMeaning:
      "Acquisition workforce cannot meet demand. Complex IT procurements failing. Schedule and capability delivery at risk.",
    linkedPainIds: ["FED-PAIN-006"],
    linkedKpiIds: ["PS-KPI-011", "PS-KPI-012", "FED-KPI-015"],
    confidence: 0.88,
    requiredConfirmationSignals: [
      "FPDS procurement timeline data",
      "DAU workforce reports",
      "GAO protest docket",
      "Requirements revision log"
    ]
  },
  {
    id: "FED-SIG-007",
    name: "ITAR License Delay Signal",
    rawSignalPatterns: [
      "DDTC license application processing time >90 days",
      "ITAR staffing turnover >20%",
      "Violations in last 3 years",
      "Commingled ITAR/unclassified environments"
    ],
    interpretedMeaning:
      "Export control compliance operations understaffed or under-resourced. Program delays and legal/debarment risk rising.",
    linkedPainIds: ["FED-PAIN-007"],
    linkedKpiIds: ["FED-KPI-011", "PS-KPI-021"],
    confidence: 0.82,
    requiredConfirmationSignals: [
      "DDTC license queue",
      "ITAR compliance audit",
      "Export transaction logs",
      "Commingled environment assessment"
    ]
  },
  {
    id: "FED-SIG-008",
    name: "Grant Deobligation Surge Signal",
    rawSignalPatterns: [
      "Deobligation rate >8%",
      "Physically incomplete grants >180 days past end",
      "Closeout staffing <2 FTE per $1B",
      "Recipient audit findings recurring"
    ],
    interpretedMeaning:
      "Grant management lifecycle broken at closeout stage. Appropriated funds returning to Treasury. Program impact reduced.",
    linkedPainIds: ["FED-PAIN-008"],
    linkedKpiIds: ["FED-KPI-006", "PS-KPI-009", "PS-KPI-031"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "Grant system deobligation report",
      "Closeout staffing analysis",
      "Recipient audit history",
      "Physical completion backlog"
    ]
  },
  {
    id: "FED-SIG-009",
    name: "Cross-Domain Friction Signal",
    rawSignalPatterns: [
      "Cross-domain transfer approval time >30 days",
      "Manual data transfer (sneakernet) observed",
      "ICD 503 compliance gaps",
      "CUI mishandling incidents"
    ],
    interpretedMeaning:
      "Information sharing across classification boundaries impeded by inadequate cross-domain solutions or data tagging. Mission effectiveness and security both compromised.",
    linkedPainIds: ["FED-PAIN-009"],
    linkedKpiIds: ["PS-KPI-032", "FED-KPI-011"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "Cross-domain transfer logs",
      "ICD 503 assessment",
      "CUI incident reports",
      "Data tagging audit"
    ]
  },
  {
    id: "FED-SIG-010",
    name: "VA Claims Backlog Signal",
    rawSignalPatterns: [
      "Pending disability claims >200K",
      "Average processing time >125 days",
      "Error rate >10%",
      "Appeals backlog >100K at BVA"
    ],
    interpretedMeaning:
      "VBA processing capacity insufficient for demand. Veteran satisfaction and congressional scrutiny rising. Overtime and temp staffing costs increasing.",
    linkedPainIds: ["FED-PAIN-010"],
    linkedKpiIds: ["FED-KPI-019", "PS-KPI-006", "PS-KPI-007"],
    confidence: 0.90,
    requiredConfirmationSignals: [
      "VBA performance dashboard",
      "Congressional inquiry log",
      "Staffing analysis",
      "Error rate report"
    ]
  },
  {
    id: "FED-SIG-011",
    name: "IRS Service Delivery Strain Signal",
    rawSignalPatterns: [
      "Paper return backlog >1M",
      "Customer service LOS <70%",
      "Telephone wait time >20 min",
      "CADE 2 transition behind schedule"
    ],
    interpretedMeaning:
      "IRS operational infrastructure overwhelmed during filing season. Taxpayer service degraded. Tax gap enforcement capacity constrained.",
    linkedPainIds: ["FED-PAIN-011"],
    linkedKpiIds: ["FED-KPI-020", "PS-KPI-015", "PS-KPI-016"],
    confidence: 0.88,
    requiredConfirmationSignals: [
      "IRS operational reports",
      "Customer service metrics",
      "CADE 2 project status",
      "Tax gap estimates"
    ]
  },
  {
    id: "FED-SIG-012",
    name: "Section 508 Settlement Risk Signal",
    rawSignalPatterns: [
      "Section 508 complaints >10 per year",
      "DOJ settlement active",
      "Procurement lacking VPAT",
      "Video without captions"
    ],
    interpretedMeaning:
      "Agency at risk of DOJ enforcement action, complaint-driven litigation, or OIG finding. Digital accessibility compliance immature.",
    linkedPainIds: ["FED-PAIN-012"],
    linkedKpiIds: ["FED-KPI-012", "PS-KPI-020", "PS-KPI-021"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "DOJ complaint log",
      "508 conformance testing results",
      "Procurement VPAT inventory",
      "Video caption audit"
    ]
  },
  {
    id: "FED-SIG-013",
    name: "Contract Closeout Backlog Signal",
    rawSignalPatterns: [
      "Physically complete contracts >180 days not closed",
      "DCAA incurred cost backlog >2 years",
      "Closeout staffing vacancy >20%"
    ],
    interpretedMeaning:
      "Contract closeout process broken due to staffing, DCAA audit delays, or documentation gaps. Working capital tied up. Final indirect cost rates unresolved.",
    linkedPainIds: ["FED-PAIN-013"],
    linkedKpiIds: ["FED-KPI-021", "PS-KPI-013"],
    confidence: 0.80,
    requiredConfirmationSignals: [
      "Contract writing system report",
      "DCAA workload metrics",
      "Closeout staffing plan",
      "Final indirect cost rate status"
    ]
  },
  {
    id: "FED-SIG-014",
    name: "EIS Transition Stalled Signal",
    rawSignalPatterns: [
      "EIS transition <80% complete",
      "Legacy contract extension fees >10%",
      "Telecom inventory data quality issues",
      "Circuit cutover failures"
    ],
    interpretedMeaning:
      "GSA EIS transition behind schedule. Legacy FTS/Networx contracts extended at premium. Network modernization and cost savings delayed.",
    linkedPainIds: ["FED-PAIN-014"],
    linkedKpiIds: ["FED-KPI-022", "PS-KPI-030"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "GSA EIS dashboard",
      "Legacy contract billing analysis",
      "Telecom inventory audit",
      "Cutover failure log"
    ]
  },
  {
    id: "FED-SIG-015",
    name: "Congressional Mandate Overload Signal",
    rawSignalPatterns: [
      "Open mandates >50",
      "GAO reporting requirements >10 per year",
      "Mandate compliance rate <80%",
      "IG findings on noncompliance"
    ],
    interpretedMeaning:
      "Policy office overwhelmed by statutory mandates. Implementation tracking inadequate. Risk of missed deadlines and GAO/IG escalation.",
    linkedPainIds: ["FED-PAIN-015"],
    linkedKpiIds: ["FED-KPI-018", "PS-KPI-020"],
    confidence: 0.82,
    requiredConfirmationSignals: [
      "Mandate tracking system",
      "GAO recommendation database",
      "OMB passback comments",
      "IG correspondence"
    ]
  },
  {
    id: "FED-SIG-016",
    name: "Small Business Goal Miss Signal",
    rawSignalPatterns: [
      "SB prime achievement <90% of 23% goal",
      "Bundling determinations >5 per year",
      "Subcontracting plan defaults >3",
      "SBA protests increasing"
    ],
    interpretedMeaning:
      "Agency failing to meet statutory small business contracting goals. SBA and congressional scrutiny likely. Bundling reducing competition.",
    linkedPainIds: ["FED-PAIN-016"],
    linkedKpiIds: ["FED-KPI-005", "PS-KPI-014"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "SBA Goaling Report",
      "FPDS small business data",
      "Bundling justification files",
      "Subcontracting plan database"
    ]
  },
  {
    id: "FED-SIG-017",
    name: "NARA Electronic Records Noncompliance Signal",
    rawSignalPatterns: [
      "Paper records >20% of holdings",
      "Email archive not NARA-compliant",
      "Records schedule not approved",
      "e-discovery costs >$500K per case"
    ],
    interpretedMeaning:
      "Records management not transitioned to electronic per M-19-21/M-23-07. NARA compliance risk. Legal discovery costs excessive.",
    linkedPainIds: ["FED-PAIN-017"],
    linkedKpiIds: ["PS-KPI-024", "FED-KPI-012"],
    confidence: 0.80,
    requiredConfirmationSignals: [
      "NARA appraisal status",
      "Records retention schedule",
      "e-discovery cost history",
      "Email archive assessment"
    ]
  },
  {
    id: "FED-SIG-018",
    name: "Counterfeit Parts / Supply Chain Risk Signal",
    rawSignalPatterns: [
      "Counterfeit parts detected in last 3 years",
      "Single-source critical suppliers >10",
      "GIDEP alerts >5 per year",
      "Foreign microelectronics dependency"
    ],
    interpretedMeaning:
      "Supply chain integrity at risk for space, defense, or nuclear programs. DFARS compliance gaps. Program failure or safety risk possible.",
    linkedPainIds: ["FED-PAIN-018"],
    linkedKpiIds: ["FED-KPI-011", "FED-KPI-004"],
    confidence: 0.85,
    requiredConfirmationSignals: [
      "GIDEP alert log",
      "Supplier audit results",
      "DFARS 252.246-7007 compliance report",
      "Foreign dependency assessment"
    ]
  }
];

// ============================================================================
// BUYING TRIGGERS (15 triggers)
// ============================================================================

export const FED_BUYING_TRIGGERS: BuyingTrigger[] = [
  {
    id: "FED-TRIG-001",
    name: "GAO High Risk List Update",
    triggerEvent: "GAO releases biennial High Risk List update with agency-specific recommendations",
    urgencyLevel: "HIGH",
    typicalTimingDays: [30, 90],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-002", "FED-PAIN-010", "FED-PAIN-011", "PS-PAIN-001"],
    procurementImplications:
      "Directed procurements for remediation; IG monitoring; congressional hearing preparation; sole-source justification possible for urgent fixes",
    cta:
      "Align solution to specific GAO recommendation language; offer rapid deployment with IG-ready reporting."
  },
  {
    id: "FED-TRIG-002",
    name: "OMB FITARA Scorecard Release",
    triggerEvent: "OMB releases quarterly FITARA scorecard showing agency score decline or persistent low performance",
    urgencyLevel: "HIGH",
    typicalTimingDays: [30, 60],
    affectedSegmentIds: ["ALL_CIVILIAN"],
    linkedPainIds: ["FED-PAIN-002", "FED-PAIN-003"],
    procurementImplications:
      "CIO-driven remediation procurements; data center consolidation contracts; working capital fund requests; modernization SOWs",
    cta:
      "Scorecard-responsive proposal mapping each solution capability to FITARA scoring categories."
  },
  {
    id: "FED-TRIG-003",
    name: "CISA Binding Operational Directive (BOD)",
    triggerEvent: "CISA issues BOD requiring specific action (e.g., BOD 22-01 KEV patching, BOD 23-02 asset management)",
    urgencyLevel: "CRITICAL",
    typicalTimingDays: [30, 180],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["PS-PAIN-002", "FED-PAIN-001", "FED-PAIN-012"],
    procurementImplications:
      "Emergency procurement authority; COTS security tools; vulnerability management platforms; EDR/XDR; asset discovery",
    cta:
      "Immediate outreach with BOD-specific compliance timeline and off-the-shelf deployment plan."
  },
  {
    id: "FED-TRIG-004",
    name: "FedRAMP Marketplace Gap / Agency ATO Need",
    triggerEvent: "Agency identifies mission-critical SaaS need with no FedRAMP-authorized equivalent; or CSP withdraws from marketplace",
    urgencyLevel: "HIGH",
    typicalTimingDays: [60, 120],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-004", "PS-PAIN-023"],
    procurementImplications:
      "FedRAMP Fast Track sponsorship; agency ATO support contract; hybrid deployment; sole-source if only viable vendor",
    cta:
      "Offer agency-sponsored FedRAMP Fast Track pathway; position hybrid deployment as interim solution."
  },
  {
    id: "FED-TRIG-005",
    name: "DoD CMMC Rule Effective Date / Contract Clause Insertion",
    triggerEvent: "DoD inserts CMMC clause into RFP or contract; CMMC assessment deadline approaches",
    urgencyLevel: "HIGH",
    typicalTimingDays: [180, 540],
    affectedSegmentIds: ["DOD", "DIB"],
    linkedPainIds: ["FED-PAIN-005"],
    procurementImplications:
      "C3PAO assessment contracts; cybersecurity consulting; SPRSSP remediation; GRC platform procurement",
    cta:
      "Engage DIB primes and subs with C3PAO-scheduled assessment path and SPRSSP remediation timeline."
  },
  {
    id: "FED-TRIG-006",
    name: "Continuing Resolution Resolution / Full Appropriation",
    triggerEvent: "CR ends with full-year appropriation; shutdown ends with retroactive funding",
    urgencyLevel: "HIGH",
    typicalTimingDays: [30, 90],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-003", "PS-PAIN-007", "FED-PAIN-006"],
    procurementImplications:
      "Compressed procurement timelines; use-it-or-lose-it spending surge; simplified acquisition threshold utilization; pre-positioned proposals execute",
    cta:
      "Pre-position procurement-ready packages with simplified acquisition pathways; activate Q4 capture teams."
  },
  {
    id: "FED-TRIG-007",
    name: "1102 Workforce Retirement Wave / Vacancy Surge",
    triggerEvent: ">20% of contracting workforce eligible for retirement within 3 years; vacancy rate spikes >15%",
    urgencyLevel: "HIGH",
    typicalTimingDays: [730, 1825],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-006", "PS-PAIN-006"],
    procurementImplications:
      "Acquisition support services (AAS); staff augmentation; knowledge management systems; automated procurement tools; DAU training technology",
    cta:
      "Position workforce augmentation and knowledge capture as retirement-risk mitigation."
  },
  {
    id: "FED-TRIG-008",
    name: "NARA Electronic Records Deadline Extension / Enforcement",
    triggerEvent: "NARA issues noncompliance notice; records management deadline extension expires; litigation requires e-discovery",
    urgencyLevel: "HIGH",
    typicalTimingDays: [90, 365],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-017", "PS-PAIN-014"],
    procurementImplications:
      "Records management platform; email archiving; e-discovery tools; NARA-compliant storage; digitization services",
    cta:
      "Reference NARA noncompliance language in proposal; offer 90-day remediation pilot."
  },
  {
    id: "FED-TRIG-009",
    name: "TMF Board Funding Round Approval",
    triggerEvent: "TMF Board approves agency project for repayable capital funding",
    urgencyLevel: "HIGH",
    typicalTimingDays: [90, 180],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-002", "PS-PAIN-001", "PS-PAIN-023"],
    procurementImplications:
      "Modernization services; cloud migration; legacy replacement; agile development; repayment-plan-aware pricing",
    cta:
      "Align pricing model to TMF repayment structure; emphasize agile delivery milestones."
  },
  {
    id: "FED-TRIG-010",
    name: "Recompete / Contract Option Decline",
    triggerEvent: "Major contract within 12-18 months of expiration; option years not exercised; CPARS rating below satisfactory",
    urgencyLevel: "MEDIUM",
    typicalTimingDays: [365, 730],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-006", "PS-PAIN-007", "FED-PAIN-013"],
    procurementImplications:
      "Full and open competition; incumbent displacement opportunity; past performance requirements; transition planning",
    cta:
      "Begin capture 18-24 months out; map incumbent weaknesses to specific federal pains."
  },
  {
    id: "FED-TRIG-011",
    name: "Congressional Hearing / Committee Inquiry",
    triggerEvent: "House or Senate committee schedules oversight hearing on agency program with documented failures",
    urgencyLevel: "HIGH",
    typicalTimingDays: [30, 90],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-010", "FED-PAIN-011", "FED-PAIN-015", "PS-PAIN-003"],
    procurementImplications:
      "Urgent remediation services; dashboard/analytics for hearing prep; consulting for response strategy; rapid deployment",
    cta:
      "Offer rapid-response team with congressional reporting experience and hearing-prep dashboards."
  },
  {
    id: "FED-TRIG-012",
    name: "OIG Report with Management Commitment",
    triggerEvent: "Agency OIG issues report with management decision to implement recommendations within 12 months",
    urgencyLevel: "HIGH",
    typicalTimingDays: [30, 90],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["PS-PAIN-011", "FED-PAIN-001", "FED-PAIN-012", "FED-PAIN-017"],
    procurementImplications:
      "Directed procurement for remediation; IG may monitor vendor selection; corrective action plan drives requirements",
    cta:
      "Map solution directly to OIG recommendation language; offer IG-monitored pilot with milestone reporting."
  },
  {
    id: "FED-TRIG-013",
    name: "New Administration Priority Alignment",
    triggerEvent: "New administration publishes technology or program priorities (e.g., AI, quantum, clean energy, cybersecurity)",
    urgencyLevel: "MEDIUM",
    typicalTimingDays: [90, 180],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-015", "FED-PAIN-002", "PS-PAIN-011"],
    procurementImplications:
      "Strategic alignment messaging; policy-aware solution positioning; OMB guidance-responsive proposals; early engagement with policy offices",
    cta:
      "Map solution to bipartisan priorities with cross-administration staying power (e.g., cybersecurity, modernization)."
  },
  {
    id: "FED-TRIG-014",
    name: "Zero Trust Implementation Milestone",
    triggerEvent: "OMB M-22-09 milestone deadline approaching; CISA Zero Trust maturity assessment scheduled; agency score <2.0",
    urgencyLevel: "HIGH",
    typicalTimingDays: [180, 365],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["PS-PAIN-002", "FED-PAIN-001", "FED-PAIN-012"],
    procurementImplications:
      "Identity platform (ICAM); EDR/XDR; network segmentation; PIV/CAC integration; privileged access management",
    cta:
      "Position as Zero Trust maturity accelerator with NIST 800-207 and CISA ZTMM alignment."
  },
  {
    id: "FED-TRIG-015",
    name: "GSA EIS Contract Extension Expiration",
    triggerEvent: "Agency legacy telecom contract extension expires; GSA imposes premium pricing or discontinues support",
    urgencyLevel: "HIGH",
    typicalTimingDays: [180, 365],
    affectedSegmentIds: ["ALL"],
    linkedPainIds: ["FED-PAIN-014", "PS-PAIN-001"],
    procurementImplications:
      "EIS transition services; network modernization; unified communications; SD-WAN; cloud connectivity",
    cta:
      "Offer EIS transition playbooks with circuit-by-circuit cutover plans and legacy premium quantification."
  }
];

// ============================================================================
// PERSONA ROUTING RULES (6 personas)
// ============================================================================

export const FED_PERSONA_ROUTING_RULES: PersonaRoutingRule[] = [
  {
    personaId: "FED-PERS-001",
    personaName: "Program Manager (Federal)",
    triggerKeywords: [
      "CDRL", "program schedule", "EVM", "milestone", "deliverable",
      "requirement traceability", "JIRA", "earned value", "contract performance"
    ],
    discoveryQuestionIds: [
      "FED-DQ-001", "FED-DQ-003", "FED-DQ-010", "FED-DQ-013", "FED-DQ-018"
    ],
    objectionIds: [
      "FED-OBJ-002", "FED-OBJ-004", "FED-OBJ-008"
    ],
    valueFormulaIds: [
      "FED-VF-001", "FED-VF-004", "FED-VF-008", "FED-VF-011"
    ],
    preferredEvidenceTypes: [
      "GAO program assessments",
      "EVM reports",
      "DCMA contract performance data",
      "CPARS excerpts"
    ]
  },
  {
    personaId: "FED-PERS-002",
    personaName: "CIO (Civilian Agency)",
    triggerKeywords: [
      "FITARA", "TMF", "Zero Trust", "cloud smart", "data center",
      "IT portfolio", "OMB scorecard", "enterprise architecture", "modernization"
    ],
    discoveryQuestionIds: [
      "FED-DQ-002", "FED-DQ-004", "FED-DQ-011", "FED-DQ-014", "FED-DQ-017"
    ],
    objectionIds: [
      "FED-OBJ-003", "FED-OBJ-007", "FED-OBJ-008"
    ],
    valueFormulaIds: [
      "FED-VF-002", "FED-VF-003", "FED-VF-012", "FED-VF-014"
    ],
    preferredEvidenceTypes: [
      "OMB FITARA scorecard",
      "CISA assessments",
      "TMF project outcomes",
      "NIST frameworks"
    ]
  },
  {
    personaId: "FED-PERS-003",
    personaName: "ISSO / ISSM",
    triggerKeywords: [
      "RMF", "eMASS", "NIST 800-53", "POA&M", "STIG", "SCAP",
      "continuous monitoring", "ATO", "control implementation", "CUI"
    ],
    discoveryQuestionIds: [
      "FED-DQ-001", "FED-DQ-004", "FED-DQ-005", "FED-DQ-007", "FED-DQ-009", "FED-DQ-012"
    ],
    objectionIds: [
      "FED-OBJ-003", "FED-OBJ-006", "FED-OBJ-010"
    ],
    valueFormulaIds: [
      "FED-VF-001", "FED-VF-004", "FED-VF-006", "FED-VF-010"
    ],
    preferredEvidenceTypes: [
      "NIST SP 800-53 controls",
      "CISA BODs",
      "eMASS metrics",
      "DISA STIGs",
      "ICD 503 assessments"
    ]
  },
  {
    personaId: "FED-PERS-004",
    personaName: "Contracting Officer (KO)",
    triggerKeywords: [
      "FAR", "DFARS", "procurement", "solicitation", "proposal",
      "competition", "CPARS", "past performance", "acquisition strategy", "CLIN"
    ],
    discoveryQuestionIds: [
      "FED-DQ-006", "FED-DQ-013", "FED-DQ-016", "FED-DQ-018"
    ],
    objectionIds: [
      "FED-OBJ-001", "FED-OBJ-005", "FED-OBJ-009"
    ],
    valueFormulaIds: [
      "FED-VF-005", "FED-VF-011", "FED-VF-012", "FED-VF-014"
    ],
    preferredEvidenceTypes: [
      "FPDS data",
      "GAO protest decisions",
      "FAR provisions",
      "CPSR results",
      "DCAA audit findings"
    ]
  },
  {
    personaId: "FED-PERS-005",
    personaName: "Grants Management Specialist",
    triggerKeywords: [
      "NOFO", "2 CFR 200", "uniform guidance", "recipient monitoring",
      "single audit", "closeout", "deobligation", "drawdown", "subaward"
    ],
    discoveryQuestionIds: [
      "FED-DQ-008"
    ],
    objectionIds: [
      "FED-OBJ-004"
    ],
    valueFormulaIds: [
      "FED-VF-007"
    ],
    preferredEvidenceTypes: [
      "Federal Audit Clearinghouse data",
      "2 CFR 200 compliance reviews",
      "Recipient monitoring reports",
      "OMB grant training data"
    ]
  },
  {
    personaId: "FED-PERS-006",
    personaName: "Policy Analyst (Federal)",
    triggerKeywords: [
      "GAO recommendation", "congressional mandate", "statutory deadline",
      "regulatory impact", "OMB circular", "legislative tracking",
      "rulemaking", "CBO scoring", "high risk list"
    ],
    discoveryQuestionIds: [
      "FED-DQ-015"
    ],
    objectionIds: [
      "FED-OBJ-007"
    ],
    valueFormulaIds: [
      "FED-VF-013", "FED-VF-014"
    ],
    preferredEvidenceTypes: [
      "GAO reports",
      "Congressional Research Service analyses",
      "OMB circulars and memos",
      "Federal Register rulemaking",
      "CBO scoring"
    ]
  }
];

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

/**
 * Find all signal rules linked to a given pain ID.
 */
export function getSignalsForPain(painId: string): SignalRule[] {
  return FED_SIGNAL_RULES.filter((s) => s.linkedPainIds.includes(painId));
}

/**
 * Find all buying triggers linked to a given pain ID.
 */
export function getTriggersForPain(painId: string): BuyingTrigger[] {
  return FED_BUYING_TRIGGERS.filter((t) => t.linkedPainIds.includes(painId));
}

/**
 * Route a discovery question to the correct persona based on keyword match.
 */
export function routeToPersona(text: string): PersonaRoutingRule | undefined {
  const lower = text.toLowerCase();
  return FED_PERSONA_ROUTING_RULES.find((p) =>
    p.triggerKeywords.some((k) => lower.includes(k.toLowerCase()))
  );
}

/**
 * Calculate composite buying readiness score based on signal count and trigger proximity.
 */
export function calculateBuyingReadiness(
  activeSignals: SignalRule[],
  activeTriggers: BuyingTrigger[]
): number {
  const signalWeight = activeSignals.reduce((sum, s) => sum + s.confidence, 0);
  const triggerWeight = activeTriggers.reduce(
    (sum, t) =>
      sum +
      (t.urgencyLevel === "CRITICAL" ? 1.0 : t.urgencyLevel === "HIGH" ? 0.7 : 0.3),
    0
  );
  const score = Math.min(1.0, (signalWeight + triggerWeight) / 10);
  return Math.round(score * 100) / 100;
}

// ============================================================================
// EXPORT ALL
// ============================================================================

export default {
  FED_SIGNAL_RULES,
  FED_BUYING_TRIGGERS,
  FED_PERSONA_ROUTING_RULES,
  getSignalsForPain,
  getTriggersForPain,
  routeToPersona,
  calculateBuyingReadiness,
};
