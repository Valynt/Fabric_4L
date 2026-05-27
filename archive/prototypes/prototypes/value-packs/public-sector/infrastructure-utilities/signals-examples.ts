/**
 * Infrastructure & Utilities Subpack — Signal Examples (TypeScript)
 * 
 * Pack ID: infrastructure-v1
 * Parent Master: public-sector-master-v1
 * 
 * This file provides:
 *   1. TypeScript interface definitions for the subpack schema
 *   2. Executable signal rule implementations (18 rules)
 *   3. Example usage and test cases
 *   4. KPI calculation helpers
 * 
 * All signal rules are backed by the evidence sources cited in the
 * subpack JSON and documented in the master pack's evidence taxonomy.
 */

// ============================================================================
// 1. CORE TYPE DEFINITIONS (Inherited from Master Schema)
// ============================================================================

export type ValueDriver =
  | "Revenue Uplift"
  | "Cost Savings"
  | "Risk Reduction"
  | "Mission Effectiveness"
  | "Working Capital / Cash Flow";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export type SegmentCode =
  | "Water Utilities"
  | "Wastewater Management"
  | "Public Transit"
  | "Roads / Bridges"
  | "Airports"
  | "Port Authorities"
  | "Public Energy Authorities"
  | "Grid Modernization"
  | "Broadband Authorities"
  | "Smart City"
  | "Emergency Communications"
  | "Waste Management";

export interface SignalInput {
  /** Raw metric values keyed by KPI or custom field */
  metrics: Record<string, number>;
  /** Qualitative flags (e.g., "consent_decree_present", "cama_primary") */
  flags: Record<string, boolean>;
  /** Text/narrative context for NLP or manual review */
  narrative?: string;
  /** Source system or dataset provenance */
  sourceSystem?: string;
  /** Timestamp of data capture */
  capturedAt: string; // ISO 8601
}

export interface SignalResult {
  ruleId: string;
  ruleName: string;
  triggered: boolean;
  confidence: number; // 0.0 - 1.0
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "INFO";
  linkedPains: string[];
  linkedKPIs: string[];
  interpretedMeaning: string;
  requiredConfirmationSignals: string[];
  /** Human-readable explanation */
  narrative: string;
  /** Financially meaningful outcome estimate (if calculable) */
  estimatedAnnualImpact?: {
    valueUSD: number;
    confidence: ConfidenceLevel;
    basis: string;
  };
}

export interface KPIDefinition {
  id: string;
  name: string;
  formula: string;
  unit: string;
  typicalRange: string;
  benchmarkRange: string;
  valueDriverLinks: ValueDriver[];
  segmentApplicability: SegmentCode[];
  calculationFrequency: string;
}

export interface BusinessPain {
  id: string;
  name: string;
  symptoms: string[];
  prevalence: "HIGH" | "MEDIUM" | "LOW";
  confidence: ConfidenceLevel;
  sources: string[];
}

// ============================================================================
// 2. VERTICAL KPI REGISTRY (25 KPIs)
// ============================================================================

export const INFRASTRUCTURE_KPIS: KPIDefinition[] = [
  {
    id: "INF-KPI-001", name: "Water Main Break Rate",
    formula: "COUNT(Breaks) / (Total_Miles / 100)", unit: "Breaks/100 mi/yr",
    typicalRange: "10-40", benchmarkRange: "Best <15; Median ~25; Fail >35",
    valueDriverLinks: ["Cost Savings", "Risk Reduction"],
    segmentApplicability: ["Water Utilities"], calculationFrequency: "Monthly/Annual"
  },
  {
    id: "INF-KPI-002", name: "Unaccounted-for Water",
    formula: "(Produced - Billed + Unbilled) / Produced * 100%", unit: "%",
    typicalRange: "10-30", benchmarkRange: "AWWA target <10%",
    valueDriverLinks: ["Cost Savings", "Revenue Uplift"],
    segmentApplicability: ["Water Utilities"], calculationFrequency: "Monthly/Annual"
  },
  {
    id: "INF-KPI-003", name: "Pipe Replacement Rate",
    formula: "Miles_Replaced / Total_Miles * 100%", unit: "%/yr",
    typicalRange: "0.5-2", benchmarkRange: "Sustainable >1.5%",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Water Utilities"], calculationFrequency: "Annual"
  },
  {
    id: "INF-KPI-004", name: "Transit On-Time Performance",
    formula: "On_Time_Trips / Total_Trips * 100%", unit: "%",
    typicalRange: "70-92", benchmarkRange: "Best >85%; Fail <75%",
    valueDriverLinks: ["Mission Effectiveness", "Revenue Uplift"],
    segmentApplicability: ["Public Transit"], calculationFrequency: "Daily/Monthly"
  },
  {
    id: "INF-KPI-005", name: "Operating Cost Per VRM",
    formula: "Total_Op_Cost / Vehicle_Revenue_Miles", unit: "USD/VRM",
    typicalRange: "8-25", benchmarkRange: "Bus $10-15; Rail $15-25",
    valueDriverLinks: ["Cost Savings"],
    segmentApplicability: ["Public Transit"], calculationFrequency: "Monthly"
  },
  {
    id: "INF-KPI-006", name: "Farebox Recovery Ratio",
    formula: "Fare_Revenue / Total_Op_Cost * 100%", unit: "%",
    typicalRange: "15-40", benchmarkRange: "Heavy rail >50%; Bus 20-35%",
    valueDriverLinks: ["Revenue Uplift", "Cost Savings"],
    segmentApplicability: ["Public Transit"], calculationFrequency: "Monthly"
  },
  {
    id: "INF-KPI-007", name: "OT Network Security Posture Score",
    formula: "AVG(Segmentation + Access + Monitoring + Patch + Backup) on 0-100", unit: "Score",
    typicalRange: "30-70", benchmarkRange: "CIP >80; Critical <50",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Water Utilities", "Public Energy Authorities", "Grid Modernization", "Public Transit"], calculationFrequency: "Quarterly"
  },
  {
    id: "INF-KPI-008", name: "SCADA System Availability",
    formula: "(Uptime - Downtime) / Uptime * 100%", unit: "%",
    typicalRange: "99.0-99.95", benchmarkRange: "Critical OT >99.95%",
    valueDriverLinks: ["Risk Reduction", "Mission Effectiveness"],
    segmentApplicability: ["Water Utilities", "Public Energy Authorities", "Grid Modernization", "Public Transit"], calculationFrequency: "Real-time/Monthly"
  },
  {
    id: "INF-KPI-009", name: "Mean Time to Restore OT Service",
    formula: "AVG(Restoration - Outage_Start)", unit: "Minutes",
    typicalRange: "15-240", benchmarkRange: "Best <60; Concerning >180",
    valueDriverLinks: ["Risk Reduction", "Mission Effectiveness"],
    segmentApplicability: ["Water Utilities", "Public Energy Authorities", "Grid Modernization", "Public Transit"], calculationFrequency: "Per incident/Monthly"
  },
  {
    id: "INF-KPI-010", name: "Structurally Deficient Bridge Percentage",
    formula: "SD_Bridges / Total * 100%", unit: "%",
    typicalRange: "3-12", benchmarkRange: "Target <5%; Concern >8%",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Roads / Bridges"], calculationFrequency: "Biennial"
  },
  {
    id: "INF-KPI-011", name: "Bridge Condition Index",
    formula: "AVG(Element_Rating weighted by quantity)", unit: "0-100",
    typicalRange: "60-85", benchmarkRange: "Good >75; Poor <60",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Roads / Bridges"], calculationFrequency: "Biennial"
  },
  {
    id: "INF-KPI-012", name: "Pavement Condition Index - Roads",
    formula: "AVG(PCI weighted by lane miles)", unit: "0-100",
    typicalRange: "55-80", benchmarkRange: "Good >70; Poor <55",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Roads / Bridges"], calculationFrequency: "Annual/Biennial"
  },
  {
    id: "INF-KPI-013", name: "ARFF Response Time to Midpoint",
    formula: "AVG(Response to midpoint)", unit: "Seconds",
    typicalRange: "120-300", benchmarkRange: "Part 139 <180s; Best <120s",
    valueDriverLinks: ["Risk Reduction", "Mission Effectiveness"],
    segmentApplicability: ["Airports"], calculationFrequency: "Quarterly/Annual drill"
  },
  {
    id: "INF-KPI-014", name: "Airfield Pavement Condition Index",
    formula: "AVG(PCI weighted by area)", unit: "0-100",
    typicalRange: "65-85", benchmarkRange: "Good >75; Poor <65",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Airports"], calculationFrequency: "Annual"
  },
  {
    id: "INF-KPI-015", name: "FOD Detection Event Rate",
    formula: "FOD_Incidents / 100,000 Operations", unit: "Per 100K ops",
    typicalRange: "0.5-5", benchmarkRange: "Best <1; Concern >3",
    valueDriverLinks: ["Risk Reduction"],
    segmentApplicability: ["Airports"], calculationFrequency: "Monthly/Annual"
  },
  {
    id: "INF-KPI-016", name: "Broadband Cost Per Location Passed",
    formula: "Total_Cost / Locations_Passed", unit: "USD",
    typicalRange: "2000-8000", benchmarkRange: "Urban <$2,500; Rural $4K-$8K",
    valueDriverLinks: ["Cost Savings", "Mission Effectiveness"],
    segmentApplicability: ["Broadband Authorities"], calculationFrequency: "Project/Annual"
  },
  {
    id: "INF-KPI-017", name: "BEAD Milestone Compliance Rate",
    formula: "Milestones_Met / Total * 100%", unit: "%",
    typicalRange: "60-95", benchmarkRange: "Target >90%; At risk <75%",
    valueDriverLinks: ["Risk Reduction", "Working Capital / Cash Flow"],
    segmentApplicability: ["Broadband Authorities"], calculationFrequency: "Quarterly"
  },
  {
    id: "INF-KPI-018", name: "Broadband Adoption Rate",
    formula: "Subscribers / Serviceable_Locations * 100%", unit: "%",
    typicalRange: "30-70", benchmarkRange: "Mature >50%; New 30-45%",
    valueDriverLinks: ["Revenue Uplift", "Mission Effectiveness"],
    segmentApplicability: ["Broadband Authorities"], calculationFrequency: "Monthly/Quarterly"
  },
  {
    id: "INF-KPI-019", name: "Sanitary Sewer Overflow Rate",
    formula: "SSO_Events / 100_Miles_Sewer", unit: "Events/100 mi/yr",
    typicalRange: "2-20", benchmarkRange: "Best <5; Enforcement >10",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Wastewater Management"], calculationFrequency: "Monthly/Annual"
  },
  {
    id: "INF-KPI-020", name: "I/I Volume Ratio",
    formula: "Wet_Weather_Increase / Dry_Flow * 100%", unit: "%",
    typicalRange: "20-80", benchmarkRange: "Target <30%; High >50%",
    valueDriverLinks: ["Cost Savings", "Risk Reduction"],
    segmentApplicability: ["Wastewater Management"], calculationFrequency: "Annual"
  },
  {
    id: "INF-KPI-021", name: "Collection System Rehabilitation Rate",
    formula: "Miles_Rehabbed / Total_Miles * 100%", unit: "%/yr",
    typicalRange: "0.3-1.5", benchmarkRange: "Sustainable >1%",
    valueDriverLinks: ["Risk Reduction", "Cost Savings"],
    segmentApplicability: ["Wastewater Management"], calculationFrequency: "Annual"
  },
  {
    id: "INF-KPI-022", name: "Fleet Electrification Percentage",
    formula: "EVs / Total_Fleet * 100%", unit: "%",
    typicalRange: "2-25", benchmarkRange: "Leading >20%; Fed target 100% LD",
    valueDriverLinks: ["Cost Savings", "Risk Reduction", "Mission Effectiveness"],
    segmentApplicability: ["Public Transit", "Public Energy Authorities", "Airports"], calculationFrequency: "Annual"
  },
  {
    id: "INF-KPI-023", name: "EV Charging Utilization Rate",
    formula: "Sessions / (Chargers * Days) * 100%", unit: "%",
    typicalRange: "15-60", benchmarkRange: "Viable >30%; Under <20%",
    valueDriverLinks: ["Cost Savings", "Mission Effectiveness"],
    segmentApplicability: ["Public Transit", "Public Energy Authorities"], calculationFrequency: "Monthly"
  },
  {
    id: "INF-KPI-024", name: "Fleet Vehicle Availability",
    formula: "Available / Total * 100%", unit: "%",
    typicalRange: "85-95", benchmarkRange: "Best >92%; Concern <85%",
    valueDriverLinks: ["Mission Effectiveness", "Cost Savings"],
    segmentApplicability: ["Public Transit", "Public Energy Authorities", "Airports"], calculationFrequency: "Daily/Monthly"
  },
  {
    id: "INF-KPI-025", name: "System Average Interruption Duration Index (SAIDI)",
    formula: "SUM(Duration) / Total_Customers", unit: "Minutes/yr",
    typicalRange: "60-300", benchmarkRange: "Best <100; Median ~200; Concern >300",
    valueDriverLinks: ["Risk Reduction", "Mission Effectiveness"],
    segmentApplicability: ["Public Energy Authorities", "Grid Modernization"], calculationFrequency: "Annual"
  }
];

// ============================================================================
// 3. SIGNAL RULE ENGINE (18 Rules)
// ============================================================================

/**
 * Base interface for all signal rule evaluators.
 */
export type SignalEvaluator = (input: SignalInput) => SignalResult;

/**
 * Helper: compute confidence from multiple boolean conditions.
 */
function computeConfidence(
  conditions: boolean[],
  weights: number[],
  base: number
): number {
  let score = base;
  for (let i = 0; i < conditions.length; i++) {
    if (conditions[i]) score += (weights[i] ?? 0.05);
  }
  return Math.min(0.99, Math.max(0.3, score));
}

// --- INF-SIG-001: Water Main Break Escalation ---
export const evaluateWaterMainBreakEscalation: SignalEvaluator = (input) => {
  const breakRate = input.metrics["water_main_break_rate_per_100mi"] ?? 0;
  const repeatBreaks = input.metrics["repeat_breaks_same_line_annual"] ?? 0;
  const castIronAge = input.metrics["cast_iron_pipe_age_years"] ?? 0;
  const triggered = breakRate > 25 || repeatBreaks > 2 || castIronAge > 50;
  const confidence = computeConfidence(
    [breakRate > 25, repeatBreaks > 2, castIronAge > 50],
    [0.25, 0.15, 0.10],
    0.40
  );
  return {
    ruleId: "INF-SIG-001",
    ruleName: "Water Main Break Escalation",
    triggered,
    confidence,
    severity: breakRate > 35 ? "CRITICAL" : breakRate > 25 ? "HIGH" : "MEDIUM",
    linkedPains: ["INF-PAIN-001", "INF-PAIN-016"],
    linkedKPIs: ["INF-KPI-001", "INF-KPI-003"],
    interpretedMeaning:
      "Pipe inventory at failure threshold; reactive maintenance dominating; replacement backlog growing; risk of large-diameter catastrophic failure.",
    requiredConfirmationSignals: [
      "Pipe material inventory",
      "Break log GIS",
      "Cathodic protection status",
      "Pressure zone data"
    ],
    narrative: `Break rate ${breakRate}/100mi with ${repeatBreaks} repeat breaks and ${castIronAge}yr cast iron. ` +
      (triggered ? "CRITICAL: Pipe replacement program urgently needed." : "Within acceptable range."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(breakRate * 500 * 15000),
          confidence: "HIGH",
          basis: "AWWA median cost per break $15K scaled by system size"
        }
      : undefined
  };
};

// --- INF-SIG-002: Transit Reliability Decline ---
export const evaluateTransitReliabilityDecline: SignalEvaluator = (input) => {
  const otp = input.metrics["transit_otp_pct"] ?? 100;
  const vacancy = input.metrics["operator_vacancy_pct"] ?? 0;
  const farebox = input.metrics["farebox_recovery_pct"] ?? 100;
  const triggered = otp < 75 || vacancy > 15 || farebox < 20;
  const confidence = computeConfidence(
    [otp < 75, vacancy > 15, farebox < 20],
    [0.25, 0.15, 0.10],
    0.38
  );
  return {
    ruleId: "INF-SIG-002",
    ruleName: "Transit Reliability Decline",
    triggered,
    confidence,
    severity: otp < 65 ? "CRITICAL" : otp < 75 ? "HIGH" : "MEDIUM",
    linkedPains: ["INF-PAIN-002", "INF-PAIN-015"],
    linkedKPIs: ["INF-KPI-004", "INF-KPI-006"],
    interpretedMeaning:
      "Service-quality spiral risk; ridership loss accelerating; revenue model broken; potential service cuts and political backlash.",
    requiredConfirmationSignals: [
      "NTD monthly data",
      "Operator attendance records",
      "Run-cut analysis",
      "Customer complaint log"
    ],
    narrative: `OTP ${otp}% with ${vacancy}% operator vacancy and ${farebox}% farebox recovery. ` +
      (triggered ? "Service reliability at risk; ridership recovery jeopardized." : "Performance within norms."),
    estimatedAnnualImpact: triggered && otp < 75
      ? {
          valueUSD: Math.round((75 - otp) * 50000),
          confidence: "MEDIUM",
          basis: "NTD peer data: each 1pp OTP decline correlates with $50K-$100K revenue loss per 1M ridership"
        }
      : undefined
  };
};

// --- INF-SIG-003: OT Cybersecurity Exposure ---
export const evaluateOTCyberExposure: SignalEvaluator = (input) => {
  const flatNetwork = input.flags["ot_network_flat"] ?? false;
  const defaultPwds = input.flags["default_plc_passwords"] ?? false;
  const unmanagedVpn = input.flags["unmanaged_remote_vpn"] ?? false;
  const noOtIds = input.flags["no_ot_ids"] ?? false;
  const win7Scada = input.flags["scada_on_windows7_xp"] ?? false;
  const triggered = flatNetwork || defaultPwds || unmanagedVpn || noOtIds || win7Scada;
  const confidence = computeConfidence(
    [flatNetwork, defaultPwds, unmanagedVpn, noOtIds, win7Scada],
    [0.18, 0.18, 0.15, 0.15, 0.15],
    0.11
  );
  return {
    ruleId: "INF-SIG-003",
    ruleName: "OT Cybersecurity Exposure",
    triggered,
    confidence,
    severity: (flatNetwork && defaultPwds) ? "CRITICAL" : triggered ? "HIGH" : "LOW",
    linkedPains: ["INF-PAIN-003"],
    linkedKPIs: ["INF-KPI-007", "INF-KPI-008"],
    interpretedMeaning:
      "Critical infrastructure exposed to ransomware and nation-state attack; potential for service disruption and safety incident; regulatory enforcement likely.",
    requiredConfirmationSignals: [
      "Network diagram",
      "OT asset inventory",
      "Vulnerability scan (OT-safe)",
      "Incident history",
      "Remote access audit"
    ],
    narrative: `OT security flags: flat=${flatNetwork}, defaultPwds=${defaultPwds}, vpn=${unmanagedVpn}, noIDS=${noOtIds}, win7=${win7Scada}. ` +
      (triggered ? "CRITICAL OT exposure per CISA/Dragos threat intelligence." : "OT posture acceptable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: 5000000,
          confidence: "MEDIUM",
          basis: "Dragos/ICS-CERT median incident cost estimate for critical infrastructure"
        }
      : undefined
  };
};

// --- INF-SIG-004: Bridge Condition Deterioration ---
export const evaluateBridgeDeterioration: SignalEvaluator = (input) => {
  const sdPct = input.metrics["structurally_deficient_pct"] ?? 0;
  const loadPostings = input.metrics["load_postings_increasing"] ?? 0;
  const inspectionBacklog = input.metrics["inspection_backlog_months"] ?? 0;
  const triggered = sdPct > 7 || loadPostings > 0 || inspectionBacklog > 12;
  const confidence = computeConfidence(
    [sdPct > 7, loadPostings > 0, inspectionBacklog > 12],
    [0.30, 0.15, 0.10],
    0.35
  );
  return {
    ruleId: "INF-SIG-004",
    ruleName: "Bridge Condition Deterioration",
    triggered,
    confidence,
    severity: sdPct > 10 ? "CRITICAL" : sdPct > 7 ? "HIGH" : "MEDIUM",
    linkedPains: ["INF-PAIN-004"],
    linkedKPIs: ["INF-KPI-010", "INF-KPI-011"],
    interpretedMeaning:
      "Federal funding insufficient for state of good repair; emergency closure risk; freight diversion costs; potential federal enforcement.",
    requiredConfirmationSignals: [
      "NBI data extract",
      "Inspection reports",
      "Load posting records",
      "STIP/TIP project list"
    ],
    narrative: `SD bridges ${sdPct}%, load postings ${loadPostings}, backlog ${inspectionBacklog}mo. ` +
      (triggered ? "Bridge inventory at risk; STIP competitiveness may be impaired." : "Bridge inventory stable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(sdPct * 2000000),
          confidence: "HIGH",
          basis: "FHWA average cost per SD bridge for detour and deferred maintenance"
        }
      : undefined
  };
};

// --- INF-SIG-005: Airport Part 139 Risk ---
export const evaluateAirportPart139Risk: SignalEvaluator = (input) => {
  const findings = input.metrics["part139_inspection_findings"] ?? 0;
  const arffTime = input.metrics["arff_response_seconds"] ?? 0;
  const pci = input.metrics["primary_runway_pci"] ?? 100;
  const triggered = findings > 2 || arffTime > 180 || pci < 70;
  const confidence = computeConfidence(
    [findings > 2, arffTime > 180, pci < 70],
    [0.20, 0.20, 0.20],
    0.28
  );
  return {
    ruleId: "INF-SIG-005",
    ruleName: "Airport Part 139 Risk",
    triggered,
    confidence,
    severity: findings > 4 || arffTime > 240 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-005", "INF-PAIN-017"],
    linkedKPIs: ["INF-KPI-013", "INF-KPI-014"],
    interpretedMeaning:
      "FAA enforcement risk; potential certificate action; airline operational concerns; capital needs urgent but AIP competitive.",
    requiredConfirmationSignals: [
      "FAA inspection report",
      "ARFF drill records",
      "Pavement condition survey",
      "Snow plan document"
    ],
    narrative: `Part 139 findings=${findings}, ARFF=${arffTime}s, runway PCI=${pci}. ` +
      (triggered ? "Airport compliance posture at risk; AIP planning urgent." : "Compliance posture acceptable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: findings * 150000 + (arffTime > 180 ? 500000 : 0),
          confidence: "MEDIUM",
          basis: "FAA civil penalty schedule and remediation cost estimates"
        }
      : undefined
  };
};

// --- INF-SIG-006: Broadband Deployment Blockers ---
export const evaluateBroadbandBlockers: SignalEvaluator = (input) => {
  const subgranteeDelay = input.metrics["bead_subgrantee_delay_months"] ?? 0;
  const permittingPct = input.metrics["permitting_schedule_pct"] ?? 0;
  const mrPct = input.metrics["make_ready_cost_pct"] ?? 0;
  const triggered = subgranteeDelay > 6 || permittingPct > 50 || mrPct > 30;
  const confidence = computeConfidence(
    [subgranteeDelay > 6, permittingPct > 50, mrPct > 30],
    [0.20, 0.15, 0.15],
    0.35
  );
  return {
    ruleId: "INF-SIG-006",
    ruleName: "Broadband Deployment Blockers",
    triggered,
    confidence,
    severity: subgranteeDelay > 12 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-006"],
    linkedKPIs: ["INF-KPI-016", "INF-KPI-017"],
    interpretedMeaning:
      "NTIA compliance deadline at risk; federal funding lapse possible; deployment cost unsustainable; digital equity gap persists.",
    requiredConfirmationSignals: [
      "BEAD application timeline",
      "Permit tracking data",
      "Make-ready estimate",
      "FCC BDC map"
    ],
    narrative: `BEAD delay ${subgranteeDelay}mo, permitting ${permittingPct}%, make-ready ${mrPct}%. ` +
      (triggered ? "BEAD program at compliance risk; funding drawdown may lapse." : "Deployment on track."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(subgranteeDelay * 100000),
          confidence: "MEDIUM",
          basis: "NTIA clawback risk and local match opportunity cost"
        }
      : undefined
  };
};

// --- INF-SIG-007: Wastewater SSO / I-I Crisis ---
export const evaluateWastewaterSSOCrisis: SignalEvaluator = (input) => {
  const sso = input.metrics["sso_events_annual"] ?? 0;
  const iiRatio = input.metrics["ii_volume_pct"] ?? 0;
  const consentDecree = input.flags["consent_decree_present"] ?? false;
  const triggered = sso > 10 || iiRatio > 50 || consentDecree;
  const confidence = computeConfidence(
    [sso > 10, iiRatio > 50, consentDecree],
    [0.25, 0.20, 0.25],
    0.22
  );
  return {
    ruleId: "INF-SIG-007",
    ruleName: "Wastewater SSO / I-I Crisis",
    triggered,
    confidence,
    severity: consentDecree || sso > 20 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-007"],
    linkedKPIs: ["INF-KPI-019", "INF-KPI-020"],
    interpretedMeaning:
      "Collection system at capacity; wet weather bypasses threatening CWA permit; capital program urgently needed but rate capacity limited.",
    requiredConfirmationSignals: [
      "SSO log (NPDES DMR)",
      "Flow monitoring data",
      "Consent decree status",
      "Sewer assessment backlog"
    ],
    narrative: `SSO=${sso}/yr, I/I=${iiRatio}%, consentDecree=${consentDecree}. ` +
      (triggered ? "CRITICAL: CWA permit violation risk; EPA enforcement probable." : "Collection system within capacity."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: sso * 100000 + (consentDecree ? 2000000 : 0),
          confidence: "HIGH",
          basis: "EPA penalty schedule and consent decree stipulated penalty rates"
        }
      : undefined
  };
};

// --- INF-SIG-008: Fleet Electrification Blocked ---
export const evaluateFleetElectrificationBlocked: SignalEvaluator = (input) => {
  const evDelay = input.metrics["ev_procurement_delay_months"] ?? 0;
  const depotCapacity = input.flags["depot_electrical_sufficient"] ?? true;
  const bayReady = input.flags["maintenance_bay_ev_ready"] ?? true;
  const triggered = evDelay > 12 || !depotCapacity || !bayReady;
  const confidence = computeConfidence(
    [evDelay > 12, !depotCapacity, !bayReady],
    [0.15, 0.20, 0.15],
    0.32
  );
  return {
    ruleId: "INF-SIG-008",
    ruleName: "Fleet Electrification Blocked",
    triggered,
    confidence,
    severity: !depotCapacity ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-008"],
    linkedKPIs: ["INF-KPI-022", "INF-KPI-023"],
    interpretedMeaning:
      "Federal/state ZEV mandates at risk; total cost of ownership analysis incomplete; infrastructure upgrade needed before fleet procurement.",
    requiredConfirmationSignals: [
      "Fleet replacement plan",
      "Depot electrical assessment",
      "EV TCO analysis",
      "Training completion records"
    ],
    narrative: `EV delay ${evDelay}mo, depotOK=${depotCapacity}, bayReady=${bayReady}. ` +
      (triggered ? "Fleet transition blocked by infrastructure gaps; mandate deadline at risk." : "Electrification program on track."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: 1500000,
          confidence: "MEDIUM",
          basis: "DOE estimate for depot electrical upgrade and delayed fleet procurement cost"
        }
      : undefined
  };
};

// --- INF-SIG-009: Distribution Reliability Erosion ---
export const evaluateDistributionReliability: SignalEvaluator = (input) => {
  const saidi = input.metrics["saidi_minutes"] ?? 0;
  const saifi = input.metrics["saifi_interruptions"] ?? 0;
  const majorEvents = input.metrics["major_event_days"] ?? 0;
  const vegOutages = input.metrics["vegetation_outage_pct"] ?? 0;
  const triggered = saidi > 240 || saifi > 2.0 || majorEvents > 5 || vegOutages > 30;
  const confidence = computeConfidence(
    [saidi > 240, saifi > 2.0, majorEvents > 5, vegOutages > 30],
    [0.20, 0.15, 0.15, 0.15],
    0.25
  );
  return {
    ruleId: "INF-SIG-009",
    ruleName: "Distribution Reliability Erosion",
    triggered,
    confidence,
    severity: saidi > 360 ? "CRITICAL" : saidi > 240 ? "HIGH" : "MEDIUM",
    linkedPains: ["INF-PAIN-009"],
    linkedKPIs: ["INF-KPI-025", "INF-KPI-026"],
    interpretedMeaning:
      "Distribution infrastructure aging; storm intensity exceeding design; vegetation program underfunded; customer satisfaction and regulatory risk rising.",
    requiredConfirmationSignals: [
      "SAIDI/SAIFI annual report",
      "Outage cause analysis",
      "Vegetation management spend",
      "Circuit condition data"
    ],
    narrative: `SAIDI=${saidi}min, SAIFI=${saifi}, majorEvents=${majorEvents}, veg=${vegOutages}%. ` +
      (triggered ? "Reliability declining; storm hardening investment needed." : "Reliability within norms."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round((saidi - 200) * 5000),
          confidence: "HIGH",
          basis: "DOE VOLL estimate $5-15/kWh applied to incremental outage duration"
        }
      : undefined
  };
};

// --- INF-SIG-010: Smart City Integration Failure ---
export const evaluateSmartCityFailure: SignalEvaluator = (input) => {
  const platforms = input.metrics["iot_platform_count"] ?? 1;
  const centralLayer = input.flags["central_data_layer_exists"] ?? false;
  const twinStaleDays = input.metrics["digital_twin_stale_days"] ?? 0;
  const sensorUptime = input.metrics["sensor_uptime_pct"] ?? 100;
  const triggered = platforms > 5 && !centralLayer || twinStaleDays > 30 || sensorUptime < 90;
  const confidence = computeConfidence(
    [platforms > 5 && !centralLayer, twinStaleDays > 30, sensorUptime < 90],
    [0.15, 0.10, 0.15],
    0.38
  );
  return {
    ruleId: "INF-SIG-010",
    ruleName: "Smart City Integration Failure",
    triggered,
    confidence,
    severity: platforms > 10 && !centralLayer ? "HIGH" : "MEDIUM",
    linkedPains: ["INF-PAIN-010"],
    linkedKPIs: ["INF-KPI-028", "INF-KPI-029"],
    interpretedMeaning:
      "Vendor silos preventing city-wide optimization; digital twin not decision-ready; sensor network ROI unproven; data governance immature.",
    requiredConfirmationSignals: [
      "IoT platform inventory",
      "API catalog",
      "Digital twin documentation",
      "Sensor uptime logs"
    ],
    narrative: `${platforms} platforms, centralLayer=${centralLayer}, twinStale=${twinStaleDays}d, uptime=${sensorUptime}%. ` +
      (triggered ? "Smart city data fragmented; interoperability investment needed." : "Integration posture acceptable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: platforms * 100000,
          confidence: "LOW",
          basis: "Speculative based on redundant platform maintenance cost"
        }
      : undefined
  };
};

// --- INF-SIG-011: NextGen 911 Transition Lag ---
export const evaluateNG911Lag: SignalEvaluator = (input) => {
  const text911 = input.flags["text_to_911_deployed"] ?? false;
  const camaPrimary = input.flags["cama_still_primary"] ?? false;
  const gisAccuracy = input.metrics["gis_z_axis_accuracy_pct"] ?? 100;
  const psapTurnover = input.metrics["psap_turnover_pct"] ?? 0;
  const triggered = !text911 || camaPrimary || gisAccuracy < 95 || psapTurnover > 15;
  const confidence = computeConfidence(
    [!text911, camaPrimary, gisAccuracy < 95, psapTurnover > 15],
    [0.20, 0.20, 0.15, 0.15],
    0.18
  );
  return {
    ruleId: "INF-SIG-011",
    ruleName: "NextGen 911 Transition Lag",
    triggered,
    confidence,
    severity: camaPrimary || psapTurnover > 25 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-011"],
    linkedKPIs: ["INF-KPI-031", "INF-KPI-033"],
    interpretedMeaning:
      "Legacy 911 at end of life; NG911 vendor lock-in risk; staffing crisis compounding technology transition; FCC and state deadline pressure.",
    requiredConfirmationSignals: [
      "State 911 plan",
      "Vendor contract review",
      "GIS accuracy audit",
      "PSAP staffing data"
    ],
    narrative: `text911=${text911}, cama=${camaPrimary}, GIS=${gisAccuracy}%, turnover=${psapTurnover}%. ` +
      (triggered ? "911 system modernization lagging; public safety risk." : "NG911 transition on track."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: 800000,
          confidence: "MEDIUM",
          basis: "NENA estimate for legacy trunk cost and dispatch inefficiency"
        }
      : undefined
  };
};

// --- INF-SIG-012: Recycling Economics Collapse ---
export const evaluateRecyclingCollapse: SignalEvaluator = (input) => {
  const contamination = input.metrics["recycling_contamination_pct"] ?? 0;
  const revenueDown = input.metrics["commodity_revenue_change_pct"] ?? 0;
  const processingCost = input.metrics["mrf_processing_cost_per_ton"] ?? 0;
  const landfillTip = input.metrics["landfill_tip_fee_per_ton"] ?? 999;
  const triggered = contamination > 25 || revenueDown < -30 || processingCost > landfillTip;
  const confidence = computeConfidence(
    [contamination > 25, revenueDown < -30, processingCost > landfillTip],
    [0.20, 0.15, 0.20],
    0.30
  );
  return {
    ruleId: "INF-SIG-012",
    ruleName: "Recycling Economics Collapse",
    triggered,
    confidence,
    severity: contamination > 35 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-012"],
    linkedKPIs: ["INF-KPI-034", "INF-KPI-036"],
    interpretedMeaning:
      "Recycling program financially unsustainable; public support eroding; MRF viability at risk; potential service cutback or program termination.",
    requiredConfirmationSignals: [
      "MRF financial statements",
      "Commodity price history",
      "Contamination audit",
      "Public complaint data"
    ],
    narrative: `Contamination=${contamination}%, revenueDown=${revenueDown}%, processing=$${processingCost}/ton vs landfill=$${landfillTip}. ` +
      (triggered ? "Recycling program financially stressed; intervention required." : "Program economics stable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(contamination * 50000),
          confidence: "HIGH",
          basis: "SWANA cost model: each 1pp contamination increase = $50K/yr per 50K ton MRF"
        }
      : undefined
  };
};

// --- INF-SIG-013: Port Throughput Bottleneck ---
export const evaluatePortBottleneck: SignalEvaluator = (input) => {
  const turnTime = input.metrics["truck_turn_time_minutes"] ?? 0;
  const dwell = input.metrics["container_dwell_days"] ?? 0;
  const chassisAvail = input.metrics["chassis_availability_pct"] ?? 100;
  const disputes = input.metrics["demurrage_dispute_volume"] ?? 0;
  const triggered = turnTime > 75 || dwell > 6 || chassisAvail < 85 || disputes > 100;
  const confidence = computeConfidence(
    [turnTime > 75, dwell > 6, chassisAvail < 85, disputes > 100],
    [0.15, 0.15, 0.15, 0.15],
    0.36
  );
  return {
    ruleId: "INF-SIG-013",
    ruleName: "Port Throughput Bottleneck",
    triggered,
    confidence,
    severity: dwell > 8 || turnTime > 90 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-013"],
    linkedKPIs: ["INF-KPI-037", "INF-KPI-038"],
    interpretedMeaning:
      "Drayage capacity constrained; yard congestion creating vessel delay; shipper dissatisfaction; regulatory attention on demurrage; emissions exceedance risk.",
    requiredConfirmationSignals: [
      "TOS data export",
      "Truck gate logs",
      "Chassis pool reports",
      "FMC complaint data"
    ],
    narrative: `Turn=${turnTime}min, dwell=${dwell}d, chassis=${chassisAvail}%, disputes=${disputes}. ` +
      (triggered ? "Port throughput constrained; FMC and shipper pressure rising." : "Port operations within norms."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(turnTime * 10000 + dwell * 500000),
          confidence: "MEDIUM",
          basis: "PIERS/FMC estimate: each minute of turn time = $10K annual drayage cost; each day dwell = $500K carrier cost"
        }
      : undefined
  };
};

// --- INF-SIG-014: Utility Affordability Crisis ---
export const evaluateAffordabilityCrisis: SignalEvaluator = (input) => {
  const shutoff = input.metrics["shutoff_rate_pct"] ?? 0;
  const rateIncrease = input.metrics["rate_increase_trajectory_pct"] ?? 0;
  const delinquency = input.metrics["delinquency_rate_pct"] ?? 0;
  const liEnrollment = input.metrics["low_income_enrollment_pct"] ?? 100;
  const triggered = shutoff > 5 || rateIncrease > 5 || delinquency > 8 || liEnrollment < 20;
  const confidence = computeConfidence(
    [shutoff > 5, rateIncrease > 5, delinquency > 8, liEnrollment < 20],
    [0.20, 0.15, 0.20, 0.15],
    0.18
  );
  return {
    ruleId: "INF-SIG-014",
    ruleName: "Utility Affordability Crisis",
    triggered,
    confidence,
    severity: shutoff > 8 || delinquency > 12 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-014"],
    linkedKPIs: ["INF-KPI-040", "INF-KPI-041"],
    interpretedMeaning:
      "Rate trajectory unsustainable for low-income households; public health and equity risk; political pressure for rate freeze; revenue collection risk.",
    requiredConfirmationSignals: [
      "Rate study",
      "Shutoff report",
      "Delinquency aging",
      "Assistance program enrollment data"
    ],
    narrative: `Shutoff=${shutoff}%, rateIncrease=${rateIncrease}%, delinquency=${delinquency}%, LI enrollment=${liEnrollment}%. ` +
      (triggered ? "Affordability crisis probable; political and regulatory risk." : "Rate trajectory manageable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(shutoff * 200000 + delinquency * 100000),
          confidence: "HIGH",
          basis: "NRDC/EPA estimate: uncollected revenue and emergency assistance cost per shutoff"
        }
      : undefined
  };
};

// --- INF-SIG-015: Fare Revenue Leakage ---
export const evaluateFareLeakage: SignalEvaluator = (input) => {
  const evasion = input.metrics["fare_evasion_observed_pct"] ?? 0;
  const revenueGap = input.metrics["revenue_discrepancy_pct"] ?? 0;
  const citationCollection = input.metrics["citation_collection_pct"] ?? 100;
  const triggered = evasion > 8 || revenueGap > 2 || citationCollection < 30;
  const confidence = computeConfidence(
    [evasion > 8, revenueGap > 2, citationCollection < 30],
    [0.20, 0.15, 0.15],
    0.32
  );
  return {
    ruleId: "INF-SIG-015",
    ruleName: "Fare Revenue Leakage",
    triggered,
    confidence,
    severity: evasion > 12 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-015"],
    linkedKPIs: ["INF-KPI-043", "INF-KPI-044"],
    interpretedMeaning:
      "Fare collection system ineffective; revenue recovery potential significant; enforcement cost may exceed recovery at current efficiency; AFC upgrade needed.",
    requiredConfirmationSignals: [
      "Evasion observation study",
      "Revenue reconciliation",
      "Citation collection report",
      "AFC audit"
    ],
    narrative: `Evasion=${evasion}%, revenueGap=${revenueGap}%, citationCollection=${citationCollection}%. ` +
      (triggered ? "Significant fare revenue leakage; AFC upgrade ROI positive." : "Revenue protection adequate."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(evasion * 1000000),
          confidence: "MEDIUM",
          basis: "APTA median: each 1pp evasion = $1M annual loss per 10M ridership"
        }
      : undefined
  };
};

// --- INF-SIG-016: PFAS Compliance Urgency ---
export const evaluatePFASUrgency: SignalEvaluator = (input) => {
  const pfasDetection = input.metrics["pfas_detection_ppt"] ?? 0;
  const mclThreshold = input.metrics["pfas_mcl_threshold_ppt"] ?? 4;
  const pilotStarted = input.flags["treatment_pilot_started"] ?? false;
  const labWait = input.metrics["lab_turnaround_days"] ?? 0;
  const cwsrfPending = input.metrics["cwsrf_pending_months"] ?? 0;
  const triggered = pfasDetection > mclThreshold || !pilotStarted || labWait > 30 || cwsrfPending > 12;
  const confidence = computeConfidence(
    [pfasDetection > mclThreshold, !pilotStarted, labWait > 30, cwsrfPending > 12],
    [0.25, 0.20, 0.15, 0.15],
    0.15
  );
  return {
    ruleId: "INF-SIG-016",
    ruleName: "PFAS Compliance Urgency",
    triggered,
    confidence,
    severity: pfasDetection > mclThreshold * 2 && !pilotStarted ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-016"],
    linkedKPIs: ["INF-KPI-046", "INF-KPI-047"],
    interpretedMeaning:
      "MCL effective date approaching; small systems face disproportionate cost; public communication challenge; potential EPA enforcement if untreated.",
    requiredConfirmationSignals: [
      "Lab results",
      "MCL timeline",
      "Treatment pilot status",
      "CWSRF application status"
    ],
    narrative: `PFAS=${pfasDetection}ppt vs MCL=${mclThreshold}, pilot=${pilotStarted}, labWait=${labWait}d, CWSRF=${cwsrfPending}mo. ` +
      (triggered ? "PFAS compliance timeline critical; treatment capital urgently needed." : "PFAS risk managed."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: 2000000,
          confidence: "HIGH",
          basis: "AWWA PFAS cost study median for GAC/IX treatment capital per system"
        }
      : undefined
  };
};

// --- INF-SIG-017: Airfield Pavement Failure Risk ---
export const evaluateAirfieldPavementRisk: SignalEvaluator = (input) => {
  const pci = input.metrics["primary_runway_pci"] ?? 100;
  const fod = input.metrics["fod_incidents_annual"] ?? 0;
  const crackBacklog = input.metrics["crack_sealing_backlog_months"] ?? 0;
  const triggered = pci < 70 || fod > 2 || crackBacklog > 12;
  const confidence = computeConfidence(
    [pci < 70, fod > 2, crackBacklog > 12],
    [0.25, 0.20, 0.15],
    0.28
  );
  return {
    ruleId: "INF-SIG-017",
    ruleName: "Airfield Pavement Failure Risk",
    triggered,
    confidence,
    severity: pci < 60 || fod > 5 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-017"],
    linkedKPIs: ["INF-KPI-049", "INF-KPI-051"],
    interpretedMeaning:
      "Pavement lifecycle compressed; reconstruction cost 5-10x maintenance; potential weight restriction or closure; AIP funding competitive.",
    requiredConfirmationSignals: [
      "Pavement condition survey",
      "FOD log",
      "Maintenance budget",
      "AIP project pipeline"
    ],
    narrative: `PCI=${pci}, FOD=${fod}/yr, crackBacklog=${crackBacklog}mo. ` +
      (triggered ? "Airfield pavement at risk; reconstruction cost escalation imminent." : "Pavement condition stable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round((100 - pci) * 50000 + fod * 200000),
          confidence: "HIGH",
          basis: "FAA ACRP: PCI decline below 70 accelerates cost 5-10x maintenance cost"
        }
      : undefined
  };
};

// --- INF-SIG-018: DER Interconnection Grid Lock ---
export const evaluateDERInterconnectionLock: SignalEvaluator = (input) => {
  const queue = input.metrics["interconnection_queue_count"] ?? 0;
  const reviewTime = input.metrics["avg_review_days"] ?? 0;
  const rejectionRate = input.metrics["rejection_modification_pct"] ?? 0;
  const hostingMap = input.flags["hosting_capacity_map_published"] ?? false;
  const triggered = queue > 1000 || reviewTime > 180 || rejectionRate > 40 || !hostingMap;
  const confidence = computeConfidence(
    [queue > 1000, reviewTime > 180, rejectionRate > 40, !hostingMap],
    [0.20, 0.20, 0.15, 0.15],
    0.16
  );
  return {
    ruleId: "INF-SIG-018",
    ruleName: "DER Interconnection Grid Lock",
    triggered,
    confidence,
    severity: queue > 3000 || reviewTime > 300 ? "CRITICAL" : "HIGH",
    linkedPains: ["INF-PAIN-018"],
    linkedKPIs: ["INF-KPI-052", "INF-KPI-053"],
    interpretedMeaning:
      "DER growth exceeding utility planning capacity; regulatory complaints rising; clean energy targets at risk; distribution system reinforcement needed.",
    requiredConfirmationSignals: [
      "Interconnection queue report",
      "Average review time report",
      "Hosting capacity analysis status",
      "PUC complaint data"
    ],
    narrative: `Queue=${queue}, reviewTime=${reviewTime}d, rejection=${rejectionRate}%, hostingMap=${hostingMap}. ` +
      (triggered ? "DER interconnection bottleneck; grid reinforcement and process automation needed." : "Interconnection flow manageable."),
    estimatedAnnualImpact: triggered
      ? {
          valueUSD: Math.round(queue * 1000 + reviewTime * 5000),
          confidence: "MEDIUM",
          basis: "NREL estimate: each queued project represents $1K-$5K in lost economic activity and regulatory cost"
        }
      : undefined
  };
};

// ============================================================================
// 4. SIGNAL RULE REGISTRY
// ============================================================================

export const ALL_SIGNAL_RULES: SignalEvaluator[] = [
  evaluateWaterMainBreakEscalation,
  evaluateTransitReliabilityDecline,
  evaluateOTCyberExposure,
  evaluateBridgeDeterioration,
  evaluateAirportPart139Risk,
  evaluateBroadbandBlockers,
  evaluateWastewaterSSOCrisis,
  evaluateFleetElectrificationBlocked,
  evaluateDistributionReliability,
  evaluateSmartCityFailure,
  evaluateNG911Lag,
  evaluateRecyclingCollapse,
  evaluatePortBottleneck,
  evaluateAffordabilityCrisis,
  evaluateFareLeakage,
  evaluatePFASUrgency,
  evaluateAirfieldPavementRisk,
  evaluateDERInterconnectionLock
];

// ============================================================================
// 5. KPI CALCULATION HELPERS
// ============================================================================

export class InfrastructureKPICalculator {
  static waterMainBreakRate(breaks: number, miles: number): number {
    return breaks / (miles / 100);
  }

  static unaccountedForWater(produced: number, billed: number, unbilled: number): number {
    return ((produced - billed + unbilled) / produced) * 100;
  }

  static transitOTP(onTime: number, total: number): number {
    return (onTime / total) * 100;
  }

  static fareboxRecovery(fareRevenue: number, opCost: number): number {
    return (fareRevenue / opCost) * 100;
  }

  static saidi(totalDuration: number, customers: number): number {
    return totalDuration / customers;
  }

  static saifi(totalInterruptions: number, customers: number): number {
    return totalInterruptions / customers;
  }

  static caidi(saidi: number, saifi: number): number {
    return saidi / saifi;
  }

  static sdBridgePct(sdBridges: number, totalBridges: number): number {
    return (sdBridges / totalBridges) * 100;
  }

  static broadbandAdoption(subscribers: number, serviceable: number): number {
    return (subscribers / serviceable) * 100;
  }

  static ssoRate(ssoEvents: number, sewerMiles: number): number {
    return ssoEvents / (sewerMiles / 100);
  }
}

// ============================================================================
// 6. BATCH EVALUATION ENGINE
// ============================================================================

export function evaluateAllSignals(input: SignalInput): SignalResult[] {
  return ALL_SIGNAL_RULES.map((rule) => rule(input));
}

export function getTriggeredSignals(input: SignalInput): SignalResult[] {
  return evaluateAllSignals(input).filter((r) => r.triggered);
}

export function getCriticalSignals(input: SignalInput): SignalResult[] {
  return evaluateAllSignals(input).filter((r) => r.triggered && r.severity === "CRITICAL");
}

// ============================================================================
// 7. EXAMPLE USAGE
// ============================================================================

/*
const exampleInput: SignalInput = {
  metrics: {
    water_main_break_rate_per_100mi: 32,
    repeat_breaks_same_line_annual: 4,
    cast_iron_pipe_age_years: 62,
    transit_otp_pct: 72,
    operator_vacancy_pct: 18,
    farebox_recovery_pct: 19,
    structurally_deficient_pct: 8.5,
    load_postings_increasing: 3,
    saidi_minutes: 280,
    saifi_interruptions: 2.2,
    major_event_days: 6,
    vegetation_outage_pct: 35,
    recycling_contamination_pct: 28,
    mrf_processing_cost_per_ton: 95,
    landfill_tip_fee_per_ton: 80,
    truck_turn_time_minutes: 65,
    container_dwell_days: 5.5,
    chassis_availability_pct: 82,
    interconnection_queue_count: 1200,
    avg_review_days: 210,
    rejection_modification_pct: 45,
    pfas_detection_ppt: 8.2,
    pfas_mcl_threshold_ppt: 4.0,
    lab_turnaround_days: 45,
    cwsrf_pending_months: 15,
    primary_runway_pci: 68,
    fod_incidents_annual: 3,
    crack_sealing_backlog_months: 14,
    psap_turnover_pct: 18,
    gis_z_axis_accuracy_pct: 88,
    bead_subgrantee_delay_months: 8,
    permitting_schedule_pct: 55,
    make_ready_cost_pct: 35,
    ev_procurement_delay_months: 15,
    iot_platform_count: 7,
    digital_twin_stale_days: 45,
    sensor_uptime_pct: 84,
    fare_evasion_observed_pct: 11,
    revenue_discrepancy_pct: 3.2,
    citation_collection_pct: 22,
    shutoff_rate_pct: 6.5,
    rate_increase_trajectory_pct: 7,
    delinquency_rate_pct: 9,
    low_income_enrollment_pct: 14,
    part139_inspection_findings: 3,
    arff_response_seconds: 195,
    sso_events_annual: 14,
    ii_volume_pct: 55
  },
  flags: {
    ot_network_flat: true,
    default_plc_passwords: true,
    unmanaged_remote_vpn: true,
    no_ot_ids: true,
    scada_on_windows7_xp: false,
    consent_decree_present: true,
    depot_electrical_sufficient: false,
    maintenance_bay_ev_ready: false,
    central_data_layer_exists: false,
    text_to_911_deployed: false,
    cama_still_primary: true,
    hosting_capacity_map_published: false,
    treatment_pilot_started: false
  },
  capturedAt: "2025-01-21T00:00:00Z"
};

const results = evaluateAllSignals(exampleInput);
const triggered = getTriggeredSignals(exampleInput);
const critical = getCriticalSignals(exampleInput);

console.log(`Total rules evaluated: ${results.length}`);
console.log(`Triggered: ${triggered.length}`);
console.log(`Critical: ${critical.length}`);
console.log("Critical signals:", critical.map((r) => `${r.ruleId}: ${r.ruleName}`));
*/
