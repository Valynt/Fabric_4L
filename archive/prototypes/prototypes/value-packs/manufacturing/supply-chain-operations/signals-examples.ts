/**
 * Supply Chain and Operations Subpack - Signal Interpretation Examples
 * 
 * ID: supply-chain-operations-v1
 * Parent Master: manufacturing-master-v1
 * 
 * This file provides concrete TypeScript implementations of signal detection,
 * interpretation, and hypothesis generation for supply chain and operations
 * scenarios. These examples are designed for integration into customer
 * intelligence platforms, CRM enrichment systems, and sales enablement tools.
 */

// ============================================================================
// Core Types (aligned with Subpack Schema)
// ============================================================================

interface SignalDetection {
  signalId: string;
  rawSignal: string;
  sourceSystem: string;
  detectedAt: Date;
  confidenceScore: number;
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  linkedPains: string[];
  linkedKPIs: string[];
  affectedPersonas: string[];
  financialImpactEstimate?: FinancialImpact;
}

interface FinancialImpact {
  category: "RevenueUplift" | "CostSavings" | "RiskReduction" | "WorkingCapital";
  annualValueUsd: number;
  valueRange: [number, number];
  confidence: "HIGH" | "MEDIUM" | "LOW";
  rationale: string;
}

interface Hypothesis {
  hypothesisId: string;
  title: string;
  description: string;
  signals: SignalDetection[];
  recommendedDiscoveryQuestions: string[];
  valueFormulaIds: string[];
  priorityScore: number; // 0-100
}

// ============================================================================
// Signal Detection Rules (Concrete Implementations)
// ============================================================================

/**
 * Rule: sco-sig-001 - Supplier PPM Spike from Geopolitical Disruption
 * 
 * Detects: Supplier defect rate escalation reported in quality review or 
 * customer scorecard. Correlates with geopolitical disruption signals.
 */
function detectSupplierPPMSpike(
  baselinePPM: number,
  currentPPM: number,
  customerScorecardStatus: "GREEN" | "YELLOW" | "RED",
  supplierChangeNotifications: number, // per month
  geopoliticalRiskIndex: number // 0-100
): SignalDetection | null {
  const ppmRatio = currentPPM / baselinePPM;
  
  // Confidence scoring based on signal strength
  let confidence = 0.60;
  if (ppmRatio > 3.0) confidence += 0.15;
  if (customerScorecardStatus === "RED") confidence += 0.10;
  if (supplierChangeNotifications > 5) confidence += 0.08;
  if (geopoliticalRiskIndex > 70) confidence += 0.05;
  confidence = Math.min(confidence, 0.95);

  if (ppmRatio > 2.0 || customerScorecardStatus === "RED") {
    return {
      signalId: "sco-sig-001",
      rawSignal: `Supplier PPM increased from ${baselinePPM} to ${currentPPM} (${(ppmRatio * 100).toFixed(0)}% of baseline). Scorecard: ${customerScorecardStatus}. Supplier changes: ${supplierChangeNotifications}/month.`,
      sourceSystem: "quality_management_system",
      detectedAt: new Date(),
      confidenceScore: parseFloat(confidence.toFixed(2)),
      severity: ppmRatio > 3.0 ? "CRITICAL" : "HIGH",
      linkedPains: ["sco-pain-001", "sco-pain-005", "sco-pain-015"],
      linkedKPIs: ["kpi-supplier-ppm", "kpi-sqcr", "kpi-supplier-scorecard"],
      affectedPersonas: ["pers-sqe", "pers-sc", "pers-quality", "pers-coo"],
      financialImpactEstimate: estimateSupplierPPMImpact(currentPPM, baselinePPM)
    };
  }
  return null;
}

/**
 * Rule: sco-sig-004 - Freight Rate Index Increase >20% Quarterly
 * 
 * Detects: Sharp increase in freight indices indicating logistics cost pressure.
 */
function detectFreightRateInflation(
  currentFreightIndex: number,
  priorQuarterIndex: number,
  spotMarketExposurePct: number,
  modalMixAirPct: number
): SignalDetection | null {
  const changePct = ((currentFreightIndex - priorQuarterIndex) / priorQuarterIndex) * 100;
  
  let confidence = 0.70;
  if (changePct > 30) confidence += 0.10;
  if (spotMarketExposurePct > 30) confidence += 0.08;
  if (modalMixAirPct > 15) confidence += 0.05;
  confidence = Math.min(confidence, 0.95);

  if (changePct > 20) {
    return {
      signalId: "sco-sig-004",
      rawSignal: `Freight index increased ${changePct.toFixed(1)}% QoQ. Spot exposure: ${spotMarketExposurePct}%. Air freight: ${modalMixAirPct}% of mix.`,
      sourceSystem: "freight_index_or_tms",
      detectedAt: new Date(),
      confidenceScore: parseFloat(confidence.toFixed(2)),
      severity: changePct > 30 ? "CRITICAL" : "HIGH",
      linkedPains: ["sco-pain-014", "sco-pain-006"],
      linkedKPIs: ["kpi-freight-cost", "kpi-cost-per-unit-shipped", "kpi-carrier-otd"],
      affectedPersonas: ["pers-logistics", "pers-cfo", "pers-sc", "pers-coo"],
      financialImpactEstimate: {
        category: "CostSavings",
        annualValueUsd: estimateFreightImpact(currentFreightIndex, priorQuarterIndex, spotMarketExposurePct),
        valueRange: [0, 0], // To be calculated with customer-specific data
        confidence: "MEDIUM",
        rationale: `Freight index up ${changePct.toFixed(1)}% with ${spotMarketExposurePct}% spot exposure indicates controllable cost escalation opportunity`
      }
    };
  }
  return null;
}

/**
 * Rule: sco-sig-006 - OSHA Serious Violation
 * 
 * Detects: OSHA enforcement database entry for serious or willful violation.
 */
function detectOSHASeriousViolation(
  hasCitation: boolean,
  citationType: "SERIOUS" | "WILLFUL" | "REPEAT" | "OTHER",
  facilityTRIR: number,
  industryAverageTRIR: number,
  previousCitations: number // in past 3 years
): SignalDetection | null {
  if (!hasCitation) return null;

  let confidence = 0.80;
  if (citationType === "WILLFUL" || citationType === "REPEAT") confidence += 0.10;
  if (facilityTRIR > industryAverageTRIR * 1.5) confidence += 0.05;
  if (previousCitations > 1) confidence += 0.05;
  confidence = Math.min(confidence, 0.95);

  return {
    signalId: "sco-sig-006",
    rawSignal: `OSHA ${citationType} citation detected. Facility TRIR: ${facilityTRIR} (industry avg: ${industryAverageTRIR}). Previous citations: ${previousCitations}.`,
    sourceSystem: "osha_enforcement_database",
    detectedAt: new Date(),
    confidenceScore: parseFloat(confidence.toFixed(2)),
    severity: citationType === "WILLFUL" ? "CRITICAL" : "HIGH",
    linkedPains: ["sco-pain-008", "pain-015"],
    linkedKPIs: ["kpi-incident-rate", "kpi-audit-findings", "kpi-compliance-cost"],
    affectedPersonas: ["pers-ehs-mgr", "pers-ehs", "pers-coo", "pers-cfo"],
    financialImpactEstimate: estimateEHSImpact(facilityTRIR, industryAverageTRIR)
  };
}

/**
 * Rule: sco-sig-008 - Backorder Rate >5%
 * 
 * Detects: Chronic backorders indicating inventory or planning failure.
 */
function detectBackorderEscalation(
  backorderRatePct: number,
  otdToCustomerPct: number,
  customerPenaltyUsdQuarterly: number,
  safetyStockDaysUniform: boolean, // true if same days across all SKUs
  skuCount: number
): SignalDetection | null {
  if (backorderRatePct < 5 && otdToCustomerPct >= 90) return null;

  let confidence = 0.75;
  if (backorderRatePct > 8) confidence += 0.07;
  if (customerPenaltyUsdQuarterly > 100000) confidence += 0.05;
  if (safetyStockDaysUniform) confidence += 0.05;
  if (otdToCustomerPct < 85) confidence += 0.05;
  confidence = Math.min(confidence, 0.92);

  return {
    signalId: "sco-sig-008",
    rawSignal: `Backorder rate: ${backorderRatePct}%. Customer OTD: ${otdToCustomerPct}%. Quarterly penalties: $${(customerPenaltyUsdQuarterly / 1000).toFixed(0)}K. Safety stock uniform: ${safetyStockDaysUniform}.`,
    sourceSystem: "erp_or_customer_portal",
    detectedAt: new Date(),
    confidenceScore: parseFloat(confidence.toFixed(2)),
    severity: backorderRatePct > 8 ? "CRITICAL" : "HIGH",
    linkedPains: ["sco-pain-017", "sco-pain-010", "sco-pain-004"],
    linkedKPIs: ["kpi-backorder-rate", "kpi-otd", "kpi-perfect-order", "kpi-fill-rate"],
    affectedPersonas: ["pers-scm", "pers-dp", "pers-csm", "pers-coo"],
    financialImpactEstimate: estimateBackorderImpact(
      backorderRatePct, 
      customerPenaltyUsdQuarterly,
      skuCount
    )
  };
}

/**
 * Rule: sco-sig-014 - WMS Replacement or Upgrade Announced
 * 
 * Detects: WMS vendor selection, RF scanning upgrade, or warehouse 
 * automation pilot announced.
 */
function detectWMSModernizationSignal(
  wmsAgeYears: number,
  hasRFPAnnounced: boolean,
  hasAutomationPilot: boolean,
  paperBasedProcessesPersisting: boolean,
  warehouseExpansionPlanned: boolean
): SignalDetection | null {
  if (!hasRFPAnnounced && !hasAutomationPilot && wmsAgeYears < 10) return null;

  let confidence = 0.70;
  if (wmsAgeYears > 15) confidence += 0.08;
  if (paperBasedProcessesPersisting) confidence += 0.05;
  if (warehouseExpansionPlanned) confidence += 0.05;
  if (hasRFPAnnounced) confidence += 0.10;
  confidence = Math.min(confidence, 0.90);

  return {
    signalId: "sco-sig-014",
    rawSignal: `WMS modernization signal: age=${wmsAgeYears}yrs, RFP=${hasRFPAnnounced}, automation=${hasAutomationPilot}, paper=${paperBasedProcessesPersisting}, expansion=${warehouseExpansionPlanned}.`,
    sourceSystem: "job_postings_news procurement",
    detectedAt: new Date(),
    confidenceScore: parseFloat(confidence.toFixed(2)),
    severity: hasRFPAnnounced ? "HIGH" : "MEDIUM",
    linkedPains: ["sco-pain-003", "sco-pain-012"],
    linkedKPIs: ["kpi-whs-productivity", "kpi-dock-to-stock", "kpi-cube-utilization"],
    affectedPersonas: ["pers-whs", "pers-logistics", "pers-cio", "pers-coo"],
    financialImpactEstimate: {
      category: "CostSavings",
      annualValueUsd: 0, // Requires facility-specific data
      valueRange: [500000, 3000000],
      confidence: "MEDIUM",
      rationale: `WMS modernization typically yields $500K-$3M annually depending on facility size and current state`
    }
  };
}

/**
 * Rule: sco-sig-015 - Tariff or Trade Policy Change
 * 
 * Detects: Tariff announcements affecting key supplier regions.
 */
function detectTradePolicyChange(
  tariffImposed: boolean,
  affectedRegionPctOfSpend: number, // % of direct spend from affected region
  hasDualSourceStrategy: boolean,
  supplierConcentrationInRegion: number // 0-100
): SignalDetection | null {
  if (!tariffImposed) return null;

  let confidence = 0.80;
  if (affectedRegionPctOfSpend > 40) confidence += 0.05;
  if (!hasDualSourceStrategy) confidence += 0.05;
  if (supplierConcentrationInRegion > 60) confidence += 0.05;
  confidence = Math.min(confidence, 0.95);

  return {
    signalId: "sco-sig-015",
    rawSignal: `Trade policy change affecting ${affectedRegionPctOfSpend}% of spend. Dual source: ${hasDualSourceStrategy}. Regional concentration: ${supplierConcentrationInRegion}%.`,
    sourceSystem: "customs_trade_government_data",
    detectedAt: new Date(),
    confidenceScore: parseFloat(confidence.toFixed(2)),
    severity: affectedRegionPctOfSpend > 50 ? "CRITICAL" : "HIGH",
    linkedPains: ["sco-pain-006", "sco-pain-001", "pain-019"],
    linkedKPIs: ["kpi-supplier-lead-time-var", "kpi-total-logistics-cost", "kpi-supplier-concentration"],
    affectedPersonas: ["pers-sc", "pers-proc", "pers-coo", "pers-cfo"],
    financialImpactEstimate: {
      category: "RiskReduction",
      annualValueUsd: affectedRegionPctOfSpend * 10000000, // Placeholder - requires actual spend
      valueRange: [1000000, 10000000],
      confidence: "MEDIUM",
      rationale: `Trade policy disruption with ${affectedRegionPctOfSpend}% regional exposure creates sourcing and inventory risk requiring dual-sourcing and buffer stock investment`
    }
  };
}

// ============================================================================
// Financial Impact Estimation Helpers
// ============================================================================

function estimateSupplierPPMImpact(currentPPM: number, baselinePPM: number): FinancialImpact {
  const ppmReduction = currentPPM - Math.min(currentPPM, 500); // Target 500 PPM
  const annualParts = 10000000; // Placeholder - would come from customer data
  const costPerDefect = 260; // Inspection + rework + line stop
  const value = (ppmReduction / 1000000) * annualParts * costPerDefect;
  
  return {
    category: "CostSavings",
    annualValueUsd: value,
    valueRange: [value * 0.5, value * 1.5],
    confidence: "HIGH",
    rationale: `PPM reduction from ${currentPPM} to 500 yields defect cost avoidance at $${costPerDefect}/defect with ${annualParts.toLocaleString()} annual parts`
  };
}

function estimateFreightImpact(
  currentIndex: number, 
  priorIndex: number, 
  spotExposurePct: number
): number {
  const changePct = ((currentIndex - priorIndex) / priorIndex);
  // Assumes $10M annual freight with spot exposure being the controllable portion
  const baselineFreight = 10000000;
  const controllablePortion = baselineFreight * (spotExposurePct / 100);
  return controllablePortion * changePct * 0.5; // Assume 50% of increase is recoverable
}

function estimateEHSImpact(facilityTRIR: number, industryAvgTRIR: number): FinancialImpact {
  const totalHours = 2000000; // Placeholder
  const incidentsAvoided = ((facilityTRIR - industryAvgTRIR) * totalHours) / 200000;
  const costPerIncident = 75000; // Direct + indirect
  const value = incidentsAvoided * costPerIncident;
  
  return {
    category: "RiskReduction",
    annualValueUsd: Math.max(0, value),
    valueRange: [Math.max(0, value * 0.7), Math.max(0, value * 1.3)],
    confidence: "MEDIUM",
    rationale: `TRIR reduction from ${facilityTRIR} to ${industryAvgTRIR} avoids ${incidentsAvoided.toFixed(1)} incidents at $${costPerIncident}/incident`
  };
}

function estimateBackorderImpact(
  backorderRatePct: number,
  quarterlyPenalties: number,
  skuCount: number
): FinancialImpact {
  const annualPenalties = quarterlyPenalties * 4;
  // Assume revenue at risk proportional to backorder rate
  const annualRevenueAtRisk = 50000000 * (backorderRatePct / 100) * 0.3; // 30% churn risk
  
  return {
    category: "RevenueUplift",
    annualValueUsd: annualPenalties + annualRevenueAtRisk,
    valueRange: [annualPenalties, annualPenalties + annualRevenueAtRisk * 2],
    confidence: "MEDIUM",
    rationale: `Backorder rate ${backorderRatePct}% drives $${(annualPenalties / 1000).toFixed(0)}K annual penalties plus churn risk on $${(annualRevenueAtRisk / 1000).toFixed(0)}K at-risk revenue`
  };
}

// ============================================================================
// Hypothesis Generation Engine
// ============================================================================

/**
 * Combines multiple signals into a prioritized business hypothesis
 * for supply chain and operations improvement.
 */
function generateHypothesis(
  signals: SignalDetection[],
  customerRevenueUsd: number,
  customerIndustry: string
): Hypothesis {
  // Calculate composite priority score
  const signalScore = signals.reduce((sum, s) => sum + s.confidenceScore, 0) / signals.length;
  const severityMultiplier = signals.some(s => s.severity === "CRITICAL") ? 1.5 :
                           signals.some(s => s.severity === "HIGH") ? 1.2 : 1.0;
  const priorityScore = Math.min(100, Math.round(signalScore * 100 * severityMultiplier));

  // Determine dominant pain theme
  const painCounts: Record<string, number> = {};
  signals.forEach(s => {
    s.linkedPains.forEach(p => {
      painCounts[p] = (painCounts[p] || 0) + 1;
    });
  });
  const dominantPain = Object.entries(painCounts)
    .sort((a, b) => b[1] - a[1])[0]?.[0] || "unknown";

  const painToHypothesisTitle: Record<string, string> = {
    "sco-pain-001": "Supplier Quality Crisis Recovery Program",
    "sco-pain-002": "MRO Critical Availability and Inventory Optimization",
    "sco-pain-003": "Warehouse Capacity and Productivity Enhancement",
    "sco-pain-004": "Demand Planning and S&OP Maturity Upgrade",
    "sco-pain-005": "Supplier Performance Management Implementation",
    "sco-pain-006": "Cross-Border Logistics and Customs Optimization",
    "sco-pain-007": "Finite Capacity Production Planning Deployment",
    "sco-pain-008": "EHS Digital Transformation and Compliance Automation",
    "sco-pain-009": "Customer Delivery Excellence Program",
    "sco-pain-010": "Statistical Safety Stock and Service Level Optimization",
    "sco-pain-011": "Procurement Compliance and Maverick Spend Reduction",
    "sco-pain-012": "Inbound Velocity and Receiving Automation",
    "sco-pain-013": "Supply Chain Transparency and Traceability Platform",
    "sco-pain-014": "Freight Cost Management and Modal Optimization",
    "sco-pain-015": "End-to-End Quality Data Integration",
    "sco-pain-016": "Supplier Collaboration and SRM Platform",
    "sco-pain-017": "Backorder Elimination and Revenue Protection",
    "sco-pain-018": "Cross-Dock and Flow-Through Implementation"
  };

  const painToDescription: Record<string, string> = {
    "sco-pain-001": "Integrated supplier quality portal with real-time PPM, automated SCAR workflow, and alternate supplier qualification acceleration.",
    "sco-pain-002": "Criticality-based MRO stocking policy with VMI for high-velocity items and predictive spare parts demand forecasting.",
    "sco-pain-003": "WMS modernization with slotting optimization, RF scanning, and labor standards to increase throughput without facility expansion.",
    "sco-pain-004": "Statistical forecasting platform with consensus S&OP workflow, POS/channel integration, and promotion modeling.",
    "sco-pain-005": "Supplier scorecard automation with real-time KPI collection, development program workflow, and sourcing decision support.",
    "sco-pain-006": "Trade compliance automation with customs broker integration, landed cost analytics, and shipment visibility platform.",
    "sco-pain-007": "APS deployment with finite capacity scheduling, material-capacity simultaneous optimization, and what-if scenario planning.",
    "sco-pain-008": "Unified EHS platform with mobile incident reporting, digital permit-to-work, sensor integration, and automated regulatory reporting.",
    "sco-pain-009": "Last-mile optimization with route planning, carrier scorecards, packaging redesign, and real-time customer tracking.",
    "sco-pain-010": "ABC/XYZ inventory segmentation with statistically derived safety stock, service level optimization, and automated policy updates.",
    "sco-pain-011": "e-Procurement with catalog-based buying, automated compliance checking, and spend analytics with category intelligence.",
    "sco-pain-012": "ASN/EDI integration with mobile receiving, automated put-away directives, and real-time inventory availability.",
    "sco-pain-013": "Blockchain or digital traceability platform for conflict minerals, REACH compliance, and full supply chain genealogy.",
    "sco-pain-014": "TMS with modal optimization, load consolidation, freight audit, and carrier performance management.",
    "sco-pain-015": "Integrated QMS connecting supplier quality, incoming inspection, in-process, final inspection, and field failure data.",
    "sco-pain-016": "Supplier portal with PO visibility, ASN submission, invoice matching, quality document exchange, and VMI capabilities.",
    "sco-pain-017": "Integrated planning and inventory optimization eliminating root causes of backorders through demand sensing and safety stock alignment.",
    "sco-pain-018": "Cross-dock lane design with appointment scheduling, pre-sold order flow-through, and reduced handling steps."
  };

  return {
    hypothesisId: `hyp-${Date.now()}`,
    title: painToHypothesisTitle[dominantPain] || "Supply Chain and Operations Improvement Initiative",
    description: painToDescription[dominantPain] || "Comprehensive supply chain optimization based on detected signals.",
    signals,
    recommendedDiscoveryQuestions: getDiscoveryQuestionsForPain(dominantPain),
    valueFormulaIds: getFormulasForPain(dominantPain),
    priorityScore
  };
}

// ============================================================================
// Helper: Map Pains to Discovery Questions
// ============================================================================

function getDiscoveryQuestionsForPain(painId: string): string[] {
  const mapping: Record<string, string[]> = {
    "sco-pain-001": ["sco-dq-001", "sco-dq-008", "sco-dq-016"],
    "sco-pain-002": ["sco-dq-002", "sco-dq-017"],
    "sco-pain-003": ["sco-dq-003", "sco-dq-007"],
    "sco-pain-004": ["sco-dq-004", "sco-dq-014", "sco-dq-010"],
    "sco-pain-005": ["sco-dq-001", "sco-dq-018"],
    "sco-pain-006": ["sco-dq-005", "sco-dq-013"],
    "sco-pain-007": ["sco-dq-010", "sco-dq-004"],
    "sco-pain-008": ["sco-dq-006", "sco-dq-017"],
    "sco-pain-009": ["sco-dq-012", "sco-dq-015"],
    "sco-pain-010": ["sco-dq-014", "sco-dq-009"],
    "sco-pain-011": ["sco-dq-011", "sco-dq-018"],
    "sco-pain-012": ["sco-dq-007", "sco-dq-003"],
    "sco-pain-013": ["sco-dq-008", "sco-dq-016"],
    "sco-pain-014": ["sco-dq-005", "sco-dq-015"],
    "sco-pain-015": ["sco-dq-016", "sco-dq-001"],
    "sco-pain-016": ["sco-dq-018", "sco-dq-011"],
    "sco-pain-017": ["sco-dq-009", "sco-dq-014", "sco-dq-004"],
    "sco-pain-018": ["sco-dq-003", "sco-dq-007"]
  };
  return mapping[painId] || ["sco-dq-004", "sco-dq-009", "sco-dq-016"];
}

function getFormulasForPain(painId: string): string[] {
  const mapping: Record<string, string[]> = {
    "sco-pain-001": ["sco-form-002"],
    "sco-pain-002": ["sco-form-003"],
    "sco-pain-003": ["sco-form-004"],
    "sco-pain-004": ["sco-form-006"],
    "sco-pain-005": ["sco-form-002"],
    "sco-pain-006": ["sco-form-005"],
    "sco-pain-007": ["sco-form-011"],
    "sco-pain-008": ["sco-form-007"],
    "sco-pain-009": ["sco-form-009"],
    "sco-pain-010": ["sco-form-001"],
    "sco-pain-011": ["sco-form-010"],
    "sco-pain-012": ["sco-form-012"],
    "sco-pain-013": ["sco-form-010"],
    "sco-pain-014": ["sco-form-005"],
    "sco-pain-015": ["sco-form-002"],
    "sco-pain-016": ["sco-form-010"],
    "sco-pain-017": ["sco-form-009", "sco-form-001"],
    "sco-pain-018": ["sco-form-008"]
  };
  return mapping[painId] || ["sco-form-001"];
}

// ============================================================================
// Example Usage: Orchestrator Integration
// ============================================================================

/**
 * Example: Detect and interpret supply chain signals for a specific customer.
 */
function runSignalDetectionExample(): void {
  const signals: SignalDetection[] = [];

  // Example 1: Automotive supplier with PPM crisis
  const ppmSignal = detectSupplierPPMSpike(
    800,    // baseline PPM
    3200,   // current PPM
    "RED",  // customer scorecard
    12,     // supplier changes per month
    85      // geopolitical risk index
  );
  if (ppmSignal) signals.push(ppmSignal);

  // Example 2: Chemical manufacturer with OSHA citation
  const oshaSignal = detectOSHASeriousViolation(
    true,
    "SERIOUS",
    4.2,
    2.8,
    1
  );
  if (oshaSignal) signals.push(oshaSignal);

  // Example 3: Food company with freight inflation
  const freightSignal = detectFreightRateInflation(
    145,    // current freight index
    110,    // prior quarter
    35,     // spot exposure %
    18      // air freight %
  );
  if (freightSignal) signals.push(freightSignal);

  // Generate hypothesis from combined signals
  if (signals.length > 0) {
    const hypothesis = generateHypothesis(signals, 400000000, "Automotive/EV");
    
    console.log("=== SC&Ops Signal Detection Results ===");
    console.log(`Hypothesis: ${hypothesis.title}`);
    console.log(`Priority Score: ${hypothesis.priorityScore}/100`);
    console.log(`Signals Detected: ${hypothesis.signals.length}`);
    
    hypothesis.signals.forEach((sig, i) => {
      console.log(`\nSignal ${i + 1}: ${sig.signalId}`);
      console.log(`  Confidence: ${sig.confidenceScore}`);
      console.log(`  Severity: ${sig.severity}`);
      console.log(`  Raw: ${sig.rawSignal}`);
      if (sig.financialImpactEstimate) {
        console.log(`  Impact: $${(sig.financialImpactEstimate.annualValueUsd / 1000000).toFixed(2)}M/year (${sig.financialImpactEstimate.category})`);
      }
    });
    
    console.log(`\nRecommended Discovery Questions: ${hypothesis.recommendedDiscoveryQuestions.join(", ")}`);
    console.log(`Value Formulas: ${hypothesis.valueFormulaIds.join(", ")}`);
  }
}

// Export for module usage
export {
  SignalDetection,
  FinancialImpact,
  Hypothesis,
  detectSupplierPPMSpike,
  detectFreightRateInflation,
  detectOSHASeriousViolation,
  detectBackorderEscalation,
  detectWMSModernizationSignal,
  detectTradePolicyChange,
  generateHypothesis,
  getDiscoveryQuestionsForPain,
  getFormulasForPain,
  runSignalDetectionExample
};
