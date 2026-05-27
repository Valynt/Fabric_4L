/**
 * Process Manufacturing Subpack - Signal Examples TypeScript
 * ID: process-manufacturing-v1
 * Parent: manufacturing-master-v1
 * 
 * This file provides executable signal interpretation patterns and
 * type-safe structures for consuming process-manufacturing vertical
 * intelligence in downstream systems.
 */

// ============================================================================
// Core Types (inherited from Master Pack, extended with vertical specifics)
// ============================================================================

export type SignalConfidence = 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 | 1.0;

export type ProcessSegment =
  | "Chemicals & Specialty Chemicals"
  | "Pharmaceuticals"
  | "Food & Beverage"
  | "Paints, Coatings & Adhesives"
  | "Plastics & Polymers"
  | "Metals & Steel"
  | "Pulp & Paper"
  | "Cement & Building Materials"
  | "Oil Refining & Petrochemicals";

export type UrgencyLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface ProcessSignalInput {
  signalId: string;
  signalName: string;
  rawEvidence: string[];
  segmentContext?: ProcessSegment;
  confidenceOverride?: SignalConfidence;
  timestamp: string;
}

export interface ProcessSignalInterpretation {
  signalId: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  linkedBuyingTriggers: string[];
  recommendedActions: string[];
  confidenceScore: SignalConfidence;
  requiresConfirmation: string[];
  financialImpactEstimate?: {
    minAnnualValue: number;
    maxAnnualValue: number;
    valueDriver: string;
    basis: string;
  };
}

// ============================================================================
// Vertical Signal Rule Definitions (18 rules)
// ============================================================================

export const PROCESS_SIGNAL_RULES: Record<string, {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  linkedBuyingTriggers: string[];
  confidenceScore: SignalConfidence;
  requiredConfirmationSignals: string[];
  typicalFinancialImpact: { min: number; max: number; unit: string; driver: string };
}> = {
  "sig-pm-001": {
    id: "sig-pm-001",
    signalName: "FDA Form 483 Observation Surge",
    rawSignalPattern: "Multiple FDA 483 observations citing batch records, deviations, or data integrity in single inspection",
    interpretedMeaning: "Critical cGMP compliance failure; electronic batch records, MES, and QMS modernization demand acute",
    linkedPains: ["pain-pm-001", "pain-pm-004", "pain-pm-007"],
    linkedKPIs: ["kpi-deviation-rate", "kpi-audit-findings", "kpi-capa-cycle-time"],
    linkedBuyingTriggers: ["bt-pm-001", "bt-pm-004"],
    confidenceScore: 0.93,
    requiredConfirmationSignals: ["Warning letter follow-up", "Consent decree history", "Management quality commitment statements"],
    typicalFinancialImpact: { min: 2000000, max: 15000000, unit: "USD/year", driver: "vdrv-risk-reduction" }
  },
  "sig-pm-002": {
    id: "sig-pm-002",
    signalName: "Batch Yield Declining Trend",
    rawSignalPattern: "Production reports or earnings commentary showing yield compression over 3+ quarters",
    interpretedMeaning: "Process degradation or raw material quality decline; yield analytics and PAT investment trigger",
    linkedPains: ["pain-pm-003", "pain-pm-010"],
    linkedKPIs: ["kpi-yield-delta", "kpi-material-balance", "kpi-copq"],
    linkedBuyingTriggers: ["bt-pm-008", "bt-pm-014"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: ["Raw material COA variance", "Process parameter drift trends", "Competitor yield positioning"],
    typicalFinancialImpact: { min: 1000000, max: 8000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  },
  "sig-pm-003": {
    id: "sig-pm-003",
    signalName: "Chemical Plant Explosion or Near-Miss",
    rawSignalPattern: "CSB investigation, OSHA serious violation, or industry incident at peer facility",
    interpretedMeaning: "Sector-wide PSM and asset integrity investment wave; SIS, alarm management, and MOC tool demand elevated",
    linkedPains: ["pain-pm-011", "pain-pm-016"],
    linkedKPIs: ["kpi-trir", "kpi-audit-findings", "kpi-pump-cavitation"],
    linkedBuyingTriggers: ["bt-pm-005"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["OSHA inspection history", "HAZOP overdue status", "Insurance premium changes"],
    typicalFinancialImpact: { min: 500000, max: 5000000, unit: "USD/year", driver: "vdrv-process-safety" }
  },
  "sig-pm-004": {
    id: "sig-pm-004",
    signalName: "Product Recall in Food or Pharma",
    rawSignalPattern: "Public FDA or FSIS recall announcement for process-related contamination or mislabeling",
    interpretedMeaning: "Traceability and batch genealogy system failure; electronic records and rapid containment tool demand critical",
    linkedPains: ["pain-pm-001", "pain-pm-004", "pain-pm-008"],
    linkedKPIs: ["kpi-recall-scope", "kpi-capa-cycle-time", "kpi-deviation-rate"],
    linkedBuyingTriggers: ["bt-pm-004", "bt-pm-001"],
    confidenceScore: 0.91,
    requiredConfirmationSignals: ["Recall root cause category", "Lot traceability coverage %", "Customer notification timeline"],
    typicalFinancialImpact: { min: 1000000, max: 10000000, unit: "USD/year", driver: "vdrv-regulatory-readiness" }
  },
  "sig-pm-005": {
    id: "sig-pm-005",
    signalName: "EPA Consent Decree or Major Settlement",
    rawSignalPattern: "EPA announcement of significant enforcement action against chemical/refining/pulp facility",
    interpretedMeaning: "Environmental compliance system overhaul required; emissions monitoring, reporting automation, and permit management demand acute",
    linkedPains: ["pain-pm-009", "pain-pm-015", "pain-pm-018"],
    linkedKPIs: ["kpi-epa-reportable", "kpi-compliance-cost", "kpi-scope1-2-emissions"],
    linkedBuyingTriggers: ["bt-pm-002", "bt-pm-011"],
    confidenceScore: 0.89,
    requiredConfirmationSignals: ["Consent decree terms and deadlines", "Facility discharge permit status", "Remediation cost estimates"],
    typicalFinancialImpact: { min: 500000, max: 5000000, unit: "USD/year", driver: "vdrv-regulatory-readiness" }
  },
  "sig-pm-006": {
    id: "sig-pm-006",
    signalName: "Job Postings for PAT/Process Analytics Roles",
    rawSignalPattern: "Multiple postings for Process Analytical Technology, multivariate analysis, or real-time release testing positions",
    interpretedMeaning: "Pharma or chemical company investing in advanced process control and quality by design; PAT platform and integration demand",
    linkedPains: ["pain-pm-003", "pain-pm-008", "pain-pm-017"],
    linkedKPIs: ["kpi-yield-delta", "kpi-spec-limit-breaches", "kpi-lims-turnaround"],
    linkedBuyingTriggers: ["bt-pm-003", "bt-pm-014"],
    confidenceScore: 0.76,
    requiredConfirmationSignals: ["R&D investment trend", "Patent filings on analytical methods", "Regulatory submission mentions of PAT"],
    typicalFinancialImpact: { min: 500000, max: 3000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  },
  "sig-pm-007": {
    id: "sig-pm-007",
    signalName: "New Plant Manager from Ex-DuPont/Ex-BASF Background",
    rawSignalPattern: "Executive hire from world-class chemical operations with known operational excellence track record",
    interpretedMeaning: "Operational transformation including yield, energy, and reliability programs likely within 12 months",
    linkedPains: ["pain-pm-003", "pain-pm-013", "pain-pm-014"],
    linkedKPIs: ["kpi-yield-delta", "kpi-energy-intensity", "kpi-reactor-util"],
    linkedBuyingTriggers: ["bt-pm-009", "bt-pm-013"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["Prior transformation track record", "Public statements on operational priorities", "Consulting firm engagements"],
    typicalFinancialImpact: { min: 500000, max: 5000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  },
  "sig-pm-008": {
    id: "sig-pm-008",
    signalName: "Solvent Price Spike or Supply Constraint",
    rawSignalPattern: "Key process solvent (acetone, ethanol, toluene, etc.) price increase >30% or force majeure declared",
    interpretedMeaning: "Solvent recovery, substitution, and process intensification investment trigger; immediate cost pressure",
    linkedPains: ["pain-pm-003", "pain-pm-015", "pain-pm-010"],
    linkedKPIs: ["kpi-solvent-loss", "kpi-material-balance", "kpi-raw-mat-var"],
    linkedBuyingTriggers: ["bt-pm-012", "bt-pm-008"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["Solvent consumption volume", "Current recovery rate", "Alternative supplier qualification status"],
    typicalFinancialImpact: { min: 200000, max: 2000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  },
  "sig-pm-009": {
    id: "sig-pm-009",
    signalName: "Capacity Expansion Announcement in Process Industry",
    rawSignalPattern: "New reactor train, fermenter battery, or continuous line announced with commissioning timeline",
    interpretedMeaning: "Recipe transfer, scale-up validation, and batch management system demand; technology platform selection window open",
    linkedPains: ["pain-pm-002", "pain-pm-006", "pain-pm-014"],
    linkedKPIs: ["kpi-reactor-util", "kpi-recipe-adherence", "kpi-batch-cycle-time"],
    linkedBuyingTriggers: ["bt-pm-006"],
    confidenceScore: 0.74,
    requiredConfirmationSignals: ["Expansion technology choices", "Vendor selection timeline", "Training and commissioning budget"],
    typicalFinancialImpact: { min: 1000000, max: 10000000, unit: "USD/year", driver: "vdrv-batch-efficiency" }
  },
  "sig-pm-010": {
    id: "sig-pm-010",
    signalName: "10-K Risk Factor: Data Integrity or Cybersecurity",
    rawSignalPattern: "Annual report cites data integrity, cybersecurity, or operational technology security as material risk",
    interpretedMeaning: "IT/OT convergence and validation-ready cybersecurity investment trigger for regulated process manufacturing",
    linkedPains: ["pain-pm-004", "pain-pm-007"],
    linkedKPIs: ["kpi-data-latency", "kpi-system-uptime", "kpi-security-findings"],
    linkedBuyingTriggers: ["bt-pm-007"],
    confidenceScore: 0.81,
    requiredConfirmationSignals: ["CISO appointment", "Cybersecurity audit findings", "Insurance requirements"],
    typicalFinancialImpact: { min: 300000, max: 3000000, unit: "USD/year", driver: "vdrv-regulatory-readiness" }
  },
  "sig-pm-011": {
    id: "sig-pm-011",
    signalName: "Customer Sustainability Scorecard Demands",
    rawSignalPattern: "Major customer (e.g., Unilever, P&G, automotive OEM) issues Scope 3 or supplier sustainability requirements",
    interpretedMeaning: "Process manufacturer must demonstrate emissions and water data transparency; EHS and sustainability platform demand",
    linkedPains: ["pain-pm-009", "pain-pm-018"],
    linkedKPIs: ["kpi-carbon-intensity", "kpi-water-reuse", "kpi-scope1-2-emissions"],
    linkedBuyingTriggers: ["bt-pm-010"],
    confidenceScore: 0.79,
    requiredConfirmationSignals: ["Customer contract terms", "Current emissions data maturity", "Board sustainability commitments"],
    typicalFinancialImpact: { min: 200000, max: 2000000, unit: "USD/year", driver: "vdrv-energy-water" }
  },
  "sig-pm-012": {
    id: "sig-pm-012",
    signalName: "Raw Material Force Majeure or Supplier Change",
    rawSignalPattern: "Critical raw material supply disruption forcing qualification of new suppliers or formulation changes",
    interpretedMeaning: "Immediate sourcing crisis; alternative supplier qualification, inventory buffer analysis, and supply chain risk tools demand",
    linkedPains: ["pain-pm-010", "pain-pm-002"],
    linkedKPIs: ["kpi-raw-mat-var", "kpi-supplier-risk-score", "kpi-supplier-otd"],
    linkedBuyingTriggers: ["bt-pm-012"],
    confidenceScore: 0.87,
    requiredConfirmationSignals: ["Single-source exposure %", "Alternative supplier status", "Safety stock coverage"],
    typicalFinancialImpact: { min: 500000, max: 5000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  },
  "sig-pm-013": {
    id: "sig-pm-013",
    signalName: "ERP to MES Integration Project Announced",
    rawSignalPattern: "Public disclosure of ERP replacement or MES upgrade with integration scope",
    interpretedMeaning: "Recipe management, batch execution, and lab integration opportunity window; vertical-specific solution demand high",
    linkedPains: ["pain-pm-002", "pain-pm-007", "pain-pm-004"],
    linkedKPIs: ["kpi-data-latency", "kpi-lims-turnaround", "kpi-recipe-adherence"],
    linkedBuyingTriggers: ["bt-pm-007"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: ["ERP vendor selection", "MES vendor shortlist", "Integration budget and timeline"],
    typicalFinancialImpact: { min: 500000, max: 5000000, unit: "USD/year", driver: "vdrv-batch-efficiency" }
  },
  "sig-pm-014": {
    id: "sig-pm-014",
    signalName: "Commodity Chemical Margin Compression",
    rawSignalPattern: "Earnings show gross margin decline in commodity chemical segment for 2+ quarters",
    interpretedMeaning: "Yield optimization, energy efficiency, and cost reduction programs prioritized; process analytics and utility optimization demand",
    linkedPains: ["pain-pm-003", "pain-pm-013", "pain-pm-008"],
    linkedKPIs: ["kpi-yield-delta", "kpi-energy-intensity", "kpi-copq"],
    linkedBuyingTriggers: ["bt-pm-008", "bt-pm-013"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["Feedstock cost trend", "Capacity utilization by product", "Competitor margin positioning"],
    typicalFinancialImpact: { min: 1000000, max: 10000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  },
  "sig-pm-015": {
    id: "sig-pm-015",
    signalName: "Pharma New Drug Application (NDA) Submission",
    rawSignalPattern: "Company announces NDA or BLA submission with commercial manufacturing readiness requirement",
    interpretedMeaning: "Commercial batch validation, PPQ campaigns, and compliant manufacturing systems must be operational; significant investment trigger",
    linkedPains: ["pain-pm-001", "pain-pm-006", "pain-pm-007"],
    linkedKPIs: ["kpi-batch-efficiency", "kpi-reactor-util", "kpi-lims-turnaround"],
    linkedBuyingTriggers: ["bt-pm-003"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: ["PDUFA date", "Manufacturing site readiness", "Validation protocol status"],
    typicalFinancialImpact: { min: 2000000, max: 15000000, unit: "USD/year", driver: "vdrv-regulatory-readiness" }
  },
  "sig-pm-016": {
    id: "sig-pm-016",
    signalName: "Water Scarcity Declaration in Operating Region",
    rawSignalPattern: "Municipal or state water restrictions declared in facility location",
    interpretedMeaning: "Water reuse, closed-loop cooling, and wastewater treatment investment trigger; operational and regulatory risk acute",
    linkedPains: ["pain-pm-018", "pain-pm-009", "pain-pm-013"],
    linkedKPIs: ["kpi-water-reuse", "kpi-utility-cost", "kpi-compliance-cost"],
    linkedBuyingTriggers: ["bt-pm-011"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["Facility water consumption vs permit", "Current reuse ratio", "Alternative water source feasibility"],
    typicalFinancialImpact: { min: 300000, max: 3000000, unit: "USD/year", driver: "vdrv-energy-water" }
  },
  "sig-pm-017": {
    id: "sig-pm-017",
    signalName: "Board Addition with Process Safety Background",
    rawSignalPattern: "New board member with chemical process safety, CSB, or CCPS background appointed",
    interpretedMeaning: "Board-level focus on PSM and asset integrity; safety system, alarm management, and risk analytics investment likely",
    linkedPains: ["pain-pm-011", "pain-pm-016"],
    linkedKPIs: ["kpi-trir", "kpi-audit-findings", "kpi-pump-cavitation"],
    linkedBuyingTriggers: ["bt-pm-005"],
    confidenceScore: 0.77,
    requiredConfirmationSignals: ["Board committee assignment", "Proxy statement risk priorities", "Insurance/board communication"],
    typicalFinancialImpact: { min: 300000, max: 3000000, unit: "USD/year", driver: "vdrv-process-safety" }
  },
  "sig-pm-018": {
    id: "sig-pm-018",
    signalName: "AI/ML Platform Job Postings for Process Optimization",
    rawSignalPattern: "Multiple postings for data scientists, process modelers, or ML engineers in manufacturing operations",
    interpretedMeaning: "Digital transformation initiative focusing on process optimization; digital twin, predictive analytics, and APC demand elevated",
    linkedPains: ["pain-pm-003", "pain-pm-008", "pain-pm-017"],
    linkedKPIs: ["kpi-yield-delta", "kpi-spec-limit-breaches", "kpi-deviation-rate"],
    linkedBuyingTriggers: ["bt-pm-014"],
    confidenceScore: 0.73,
    requiredConfirmationSignals: ["Digital transformation roadmap", "Data infrastructure assessment", "Existing APC deployment status"],
    typicalFinancialImpact: { min: 500000, max: 5000000, unit: "USD/year", driver: "vdrv-yield-optimization" }
  }
};

// ============================================================================
// Signal Interpreter Engine
// ============================================================================

export class ProcessSignalInterpreter {
  /**
   * Interprets a raw signal against the process manufacturing vertical rulebook.
   * Returns full interpretation with linked pains, KPIs, buying triggers, and
   * financial impact estimate.
   */
  static interpret(input: ProcessSignalInput): ProcessSignalInterpretation {
    const rule = PROCESS_SIGNAL_RULES[input.signalId];
    
    if (!rule) {
      throw new Error(`Unknown signal ID: ${input.signalId}`);
    }

    const confidence = input.confidenceOverride ?? rule.confidenceScore;
    
    // Adjust confidence based on segment context alignment
    const segmentBoost = input.segmentContext && 
      (rule.linkedPains.some(p => p.includes("pharma")) && input.segmentContext === "Pharmaceuticals" ||
       rule.linkedPains.some(p => p.includes("chemical")) && input.segmentContext === "Chemicals & Specialty Chemicals")
      ? 0.05 : 0;
    
    const adjustedConfidence = Math.min(1.0, confidence + segmentBoost) as SignalConfidence;

    return {
      signalId: rule.id,
      interpretedMeaning: rule.interpretedMeaning,
      linkedPains: rule.linkedPains,
      linkedKPIs: rule.linkedKPIs,
      linkedBuyingTriggers: rule.linkedBuyingTriggers,
      recommendedActions: [
        `Validate via: ${rule.requiredConfirmationSignals.join(", ")}`,
        `Engage personas: ${this._derivePersonas(rule.linkedPains).join(", ")}`,
        `Quantify using: ${this._deriveFormulas(rule.linkedKPIs).join(", ")}`
      ],
      confidenceScore: adjustedConfidence,
      requiresConfirmation: rule.requiredConfirmationSignals,
      financialImpactEstimate: {
        minAnnualValue: rule.typicalFinancialImpact.min,
        maxAnnualValue: rule.typicalFinancialImpact.max,
        valueDriver: rule.typicalFinancialImpact.driver,
        basis: `Derived from ${rule.signalName} benchmark data and formula ${this._deriveFormulas(rule.linkedKPIs)[0] ?? "vf-pm-001"}`
      }
    };
  }

  /**
   * Batch interprets multiple signals and returns ranked by financial impact.
   */
  static interpretBatch(inputs: ProcessSignalInput[]): ProcessSignalInterpretation[] {
    return inputs
      .map(input => this.interpret(input))
      .sort((a, b) => {
        const aImpact = a.financialImpactEstimate?.maxAnnualValue ?? 0;
        const bImpact = b.financialImpactEstimate?.maxAnnualValue ?? 0;
        return bImpact - aImpact;
      });
  }

  /**
   * Derive urgency from signal-buying trigger mapping.
   */
  static deriveUrgency(signalId: string): UrgencyLevel {
    const triggerMap: Record<string, UrgencyLevel> = {
      "bt-pm-001": "CRITICAL", "bt-pm-002": "CRITICAL", "bt-pm-004": "CRITICAL",
      "bt-pm-003": "HIGH", "bt-pm-005": "HIGH", "bt-pm-006": "HIGH",
      "bt-pm-008": "HIGH", "bt-pm-011": "HIGH", "bt-pm-012": "HIGH", "bt-pm-013": "HIGH",
      "bt-pm-007": "MEDIUM", "bt-pm-009": "MEDIUM", "bt-pm-010": "MEDIUM", "bt-pm-014": "MEDIUM"
    };
    
    const rule = PROCESS_SIGNAL_RULES[signalId];
    if (!rule) return "LOW";
    
    const urgencies = rule.linkedBuyingTriggers.map(t => triggerMap[t] ?? "LOW");
    if (urgencies.includes("CRITICAL")) return "CRITICAL";
    if (urgencies.includes("HIGH")) return "HIGH";
    if (urgencies.includes("MEDIUM")) return "MEDIUM";
    return "LOW";
  }

  // Internal helpers
  private static _derivePersonas(painIds: string[]): string[] {
    const personaMap: Record<string, string[]> = {
      "pain-pm-001": ["pers-quality", "pers-process-eng", "pers-batch-op"],
      "pain-pm-002": ["pers-recipe", "pers-quality"],
      "pain-pm-003": ["pers-yield", "pers-process-eng", "pers-cfo"],
      "pain-pm-004": ["pers-quality", "pers-cio"],
      "pain-pm-005": ["pers-process-eng", "pers-batch-op"],
      "pain-pm-006": ["pers-plan", "pers-process-eng"],
      "pain-pm-007": ["pers-qa-metro", "pers-cio"],
      "pain-pm-008": ["pers-quality", "pers-yield"],
      "pain-pm-009": ["pers-env-comp", "pers-ehs"],
      "pain-pm-010": ["pers-quality", "pers-sc"],
      "pain-pm-011": ["pers-ehs", "pers-process-eng"],
      "pain-pm-012": ["pers-process-eng", "pers-plant"],
      "pain-pm-013": ["pers-process-eng", "pers-plant"],
      "pain-pm-014": ["pers-hr", "pers-batch-op"],
      "pain-pm-015": ["pers-env-comp", "pers-process-eng"],
      "pain-pm-016": ["pers-maint", "pers-process-eng"],
      "pain-pm-017": ["pers-process-eng", "pers-batch-op"],
      "pain-pm-018": ["pers-env-comp", "pers-process-eng"]
    };
    const personas = new Set<string>();
    painIds.forEach(pid => {
      (personaMap[pid] ?? []).forEach(p => personas.add(p));
    });
    return Array.from(personas);
  }

  private static _deriveFormulas(kpiIds: string[]): string[] {
    const formulaMap: Record<string, string> = {
      "kpi-deviation-rate": "vf-pm-001",
      "kpi-yield-delta": "vf-pm-002",
      "kpi-batch-record-errors": "vf-pm-003",
      "kpi-cleaning-time": "vf-pm-004",
      "kpi-reactor-util": "vf-pm-005",
      "kpi-lims-turnaround": "vf-pm-006",
      "kpi-spec-limit-breaches": "vf-pm-007",
      "kpi-epa-reportable": "vf-pm-008",
      "kpi-grade-transition-loss": "vf-pm-009",
      "kpi-solvent-loss": "vf-pm-010",
      "kpi-turnover": "vf-pm-011",
      "kpi-pump-cavitation": "vf-pm-012",
      "kpi-ph-deviation": "vf-pm-013",
      "kpi-temp-exursion": "vf-pm-013"
    };
    const formulas = new Set<string>();
    kpiIds.forEach(kid => {
      const fid = formulaMap[kid];
      if (fid) formulas.add(fid);
    });
    return Array.from(formulas);
  }
}

// ============================================================================
// Usage Examples
// ============================================================================

/** 
 * Example 1: Single signal interpretation for FDA 483
 */
export const exampleFDA483Signal: ProcessSignalInput = {
  signalId: "sig-pm-001",
  signalName: "FDA Form 483 Observation Surge",
  rawEvidence: [
    "FDA 483 issued to XYZ Pharma on 2026-03-15 with 8 observations",
    "Observations 3, 5, 7 relate to batch record completeness and data integrity",
    "Warning letter expected within 60 days based on precedent"
  ],
  segmentContext: "Pharmaceuticals",
  timestamp: "2026-04-25T00:00:00Z"
};

/**
 * Example 2: Batch signal interpretation for multi-trigger analysis
 */
export const exampleBatchSignals: ProcessSignalInput[] = [
  exampleFDA483Signal,
  {
    signalId: "sig-pm-002",
    signalName: "Batch Yield Declining Trend",
    rawEvidence: [
      "Q1 2026 earnings call: API segment yield declined 1.2pp YoY",
      "Raw material cost inflation of 18% noted in 10-K"
    ],
    segmentContext: "Pharmaceuticals",
    timestamp: "2026-04-25T00:00:00Z"
  },
  {
    signalId: "sig-pm-015",
    signalName: "Pharma New Drug Application (NDA) Submission",
    rawEvidence: [
      "Company announced NDA submission for oncology drug XYZ-789",
      "PDUFA date set for Q4 2026",
      "Commercial manufacturing site in Indianapolis not yet validated"
    ],
    segmentContext: "Pharmaceuticals",
    timestamp: "2026-04-25T00:00:00Z"
  }
];

/**
 * Example 3: Execute interpretation and rank by financial impact
 */
export function runExampleInterpretation(): ProcessSignalInterpretation[] {
  const results = ProcessSignalInterpreter.interpretBatch(exampleBatchSignals);
  
  console.log("=== Process Manufacturing Signal Rankings ===");
  results.forEach((r, i) => {
    console.log(`${i + 1}. ${r.signalId} | Confidence: ${r.confidenceScore} | ` +
      `Max Impact: $${r.financialImpactEstimate?.maxAnnualValue.toLocaleString()} | ` +
      `Urgency: ${ProcessSignalInterpreter.deriveUrgency(r.signalId)}`);
  });
  
  return results;
}

// ============================================================================
// Export comprehensive type map for downstream consumers
// ============================================================================

export const ProcessManufacturingSubpack = {
  id: "process-manufacturing-v1",
  parentMasterId: "manufacturing-master-v1",
  version: "1.0.0",
  verticalFocus: [
    "Chemicals & Specialty Chemicals",
    "Pharmaceuticals",
    "Food & Beverage",
    "Paints, Coatings & Adhesives",
    "Plastics & Polymers",
    "Metals & Steel",
    "Pulp & Paper",
    "Cement & Building Materials",
    "Oil Refining & Petrochemicals"
  ] as ProcessSegment[],
  signalRules: PROCESS_SIGNAL_RULES,
  interpreter: ProcessSignalInterpreter,
  
  // Convenience accessors
  getPainIds(): string[] {
    return Object.values(PROCESS_SIGNAL_RULES).flatMap(r => r.linkedPains);
  },
  getKpiIds(): string[] {
    return Object.values(PROCESS_SIGNAL_RULES).flatMap(r => r.linkedKPIs);
  },
  getBuyingTriggerIds(): string[] {
    return Object.values(PROCESS_SIGNAL_RULES).flatMap(r => r.linkedBuyingTriggers);
  }
};
