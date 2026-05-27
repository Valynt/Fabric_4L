/**
 * State and Local Government Value Subpack — Signal Interpretation Examples
 * ID: state-local-v1
 * Parent Master: public-sector-master-v1
 * Generated: 2026-04-25
 * 
 * Usage: Import these types, rules, and examples into downstream reasoning engines,
 * CRM enrichment pipelines, or sales intelligence systems.
 */

// ============================================================
// CORE TYPES
// ============================================================

export type SignalConfidence = "HIGH" | "MEDIUM" | "LOW";
export type ValueDriverCategory = "Cost Savings" | "Risk Reduction" | "Mission Effectiveness" | "Working Capital" | "Revenue Uplift";
export type PainPrevalence = "HIGH" | "MEDIUM" | "LOW";

export interface SignalRule {
  id: string;
  name: string;
  signalPattern: string;
  interpretedPainId: string;
  valueDriverCategory: string;
  linkedKPIs: string[];
  affectedPersonaIds: string[];
  confidence: SignalConfidence;
  confidenceRationale: string;
  requiredEvidence: string[];
}

export interface TriggerEvent {
  id: string;
  triggerName: string;
  triggerType: string;
  timeWindow: string;
  linkedPainIds: string[];
  linkedPersonaIds: string[];
  signalSources: string[];
  confidence: SignalConfidence;
  actionRecommendation: string;
}

export interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  applicableSegments: string[];
  confidenceRules: string;
  exampleCalculation: string;
  valueDriver: ValueDriverCategory;
}

// ============================================================
// SIGNAL RULES REGISTRY
// ============================================================

export const STATE_LOCAL_SIGNAL_RULES: SignalRule[] = [
  {
    id: "SL-SR-101",
    name: "DMV Wait Time Crisis Signal",
    signalPattern: "DMV wait time >60 minutes OR appointment backlog >3 weeks OR citizen complaint volume to governor up >20% QoQ",
    interpretedPainId: "SL-PAIN-101",
    valueDriverCategory: "Cost Savings + Mission Effectiveness",
    linkedKPIs: ["SL-KPI-101", "SL-KPI-102"],
    affectedPersonaIds: ["SL-PERS-101", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "AAMVA and state DMV dashboards provide direct measurement; complaint volume spikes are leading indicators.",
    requiredEvidence: ["DMV queue management system reports", "Appointment system data", "Citizen complaint logs", "Staff turnover HR data"]
  },
  {
    id: "SL-SR-102",
    name: "911 Answer Rate Degradation",
    signalPattern: "911 answer rate <90% within 15 seconds for 2+ consecutive weeks OR abandoned call rate >5% OR PSAP vacancy rate >15%",
    interpretedPainId: "SL-PAIN-102",
    valueDriverCategory: "Risk Reduction + Mission Effectiveness",
    linkedKPIs: ["SL-KPI-104", "SL-KPI-105"],
    affectedPersonaIds: ["SL-PERS-105", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "NENA standards and FCC reporting requirements create consistent data streams.",
    requiredEvidence: ["911 call detail records", "PSAP staffing reports", "CAD system uptime logs", "APCO staffing survey data"]
  },
  {
    id: "SL-SR-103",
    name: "Property Tax Assessment Instability",
    signalPattern: "Appeal rate >8% OR assessment-to-sale ratio outside 0.85-1.15 OR CAMA system age >15 years",
    interpretedPainId: "SL-PAIN-103",
    valueDriverCategory: "Revenue Uplift + Risk Reduction",
    linkedKPIs: ["SL-KPI-107", "SL-KPI-108"],
    affectedPersonaIds: ["SL-PERS-104", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "IAAO ratio studies and state tax commission audits provide standardized measurement.",
    requiredEvidence: ["Assessment roll data", "Sales ratio study", "Appeal filing counts", "CAMA system inventory"]
  },
  {
    id: "SL-SR-104",
    name: "Court Backlog Accumulation",
    signalPattern: "Case disposition time >180 days for criminal AND growing >5% QoQ OR e-filing adoption <40% OR paper records retrieval >2 days",
    interpretedPainId: "SL-PAIN-104",
    valueDriverCategory: "Cost Savings + Risk Reduction",
    linkedKPIs: ["SL-KPI-110", "SL-KPI-111"],
    affectedPersonaIds: ["SL-PERS-106", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "Court case management systems produce standardized reports; NCSC collects national data.",
    requiredEvidence: ["Court CMS reports", "State court administrative office data", "Jail population reports", "E-filing system analytics"]
  },
  {
    id: "SL-SR-105",
    name: "Road Condition Deterioration",
    signalPattern: "Pothole response time >72 hours OR road condition index <60 OR liability claims from road defects up >15% YoY",
    interpretedPainId: "SL-PAIN-105",
    valueDriverCategory: "Cost Savings + Risk Reduction",
    linkedKPIs: ["SL-KPI-113", "SL-KPI-114", "SL-KPI-115"],
    affectedPersonaIds: ["SL-PERS-103", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "FHWA HPMS and municipal risk pools provide standardized condition and claim data.",
    requiredEvidence: ["Pavement condition assessments", "311 complaint data", "Liability claim reports", "GIS asset inventory"]
  },
  {
    id: "SL-SR-106",
    name: "Procurement Cycle Elongation",
    signalPattern: "Average procurement cycle >180 days AND increasing >10% YoY OR sole-source share >15% OR protest rate >3%",
    interpretedPainId: "SL-PAIN-106",
    valueDriverCategory: "Working Capital + Cost Savings",
    linkedKPIs: ["SL-KPI-116", "SL-KPI-117", "SL-KPI-118"],
    affectedPersonaIds: ["SL-PERS-102", "SL-PERS-101"],
    confidence: "HIGH",
    confidenceRationale: "NASPO and state procurement systems track cycle times accurately.",
    requiredEvidence: ["Procurement system data", "Sole-source justification logs", "Protest filings", "RFP release calendars"]
  },
  {
    id: "SL-SR-107",
    name: "Housing Voucher Underutilization",
    signalPattern: "HAP utilization <93% for 2+ consecutive quarters OR waitlist >24 months OR SEMAP score <80",
    interpretedPainId: "SL-PAIN-107",
    valueDriverCategory: "Mission Effectiveness + Working Capital",
    linkedKPIs: ["SL-KPI-119", "SL-KPI-120", "SL-KPI-121"],
    affectedPersonaIds: ["SL-PERS-102", "SL-PERS-104"],
    confidence: "HIGH",
    confidenceRationale: "HUD requires PHA financial and SEMAP reporting; data is standardized and audited.",
    requiredEvidence: ["HUD PHA financial reports", "SEMAP score history", "Waitlist management data", "HAP expenditure reports"]
  },
  {
    id: "SL-SR-108",
    name: "Permit Approval Bottleneck",
    signalPattern: "Average permit approval >60 days OR plan review backlog >30 days OR digital permit share <25%",
    interpretedPainId: "SL-PAIN-108",
    valueDriverCategory: "Revenue Uplift + Working Capital",
    linkedKPIs: ["SL-KPI-122", "SL-KPI-123"],
    affectedPersonaIds: ["SL-PERS-102", "SL-PERS-103", "SL-PERS-104"],
    confidence: "HIGH",
    confidenceRationale: "ABcD and ICC surveys track permit cycle times consistently across jurisdictions.",
    requiredEvidence: ["Permit tracking system data", "Plan review queue reports", "Developer complaint logs", "Fee revenue reports"]
  },
  {
    id: "SL-SR-109",
    name: "Cybersecurity Authorization Gap",
    signalPattern: "No StateRAMP or equivalent program OR cloud vendor onboarding >12 months OR ransomware incident in past 24 months OR cyber insurance premium increase >25%",
    interpretedPainId: "SL-PAIN-109",
    valueDriverCategory: "Risk Reduction + Cost Savings",
    linkedKPIs: ["SL-KPI-125", "SL-KPI-126", "SL-KPI-127"],
    affectedPersonaIds: ["SL-PERS-101", "SL-PERS-105"],
    confidence: "HIGH",
    confidenceRationale: "StateRAMP adoption tracker and MS-ISAC incident database provide direct evidence.",
    requiredEvidence: ["StateRAMP.org adoption status", "MS-ISAC incident reports", "Cyber insurance policy data", "Cloud vendor onboarding records"]
  },
  {
    id: "SL-SR-110",
    name: "Emergency Interoperability Failure",
    signalPattern: "No common operating picture platform OR radio interoperability <80% of agencies OR after-action recommendation implementation <50%",
    interpretedPainId: "SL-PAIN-110",
    valueDriverCategory: "Risk Reduction + Mission Effectiveness",
    linkedKPIs: ["SL-KPI-128", "SL-KPI-129", "SL-KPI-130"],
    affectedPersonaIds: ["SL-PERS-105", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "FEMA preparedness assessments and SAFECOM surveys provide standardized capability scores.",
    requiredEvidence: ["FEMA preparedness assessment", "SAFECOM survey results", "After-action reports", "Mutual aid agreement status"]
  },
  {
    id: "SL-SR-111",
    name: "Jail Overcrowding Risk",
    signalPattern: "Jail occupancy >90% for 30+ consecutive days OR pre-trial population >65% OR average pre-trial stay >21 days",
    interpretedPainId: "SL-PAIN-111",
    valueDriverCategory: "Cost Savings + Risk Reduction",
    linkedKPIs: ["SL-KPI-131", "SL-KPI-132", "SL-KPI-133"],
    affectedPersonaIds: ["SL-PERS-106", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "BJS and Vera Institute publish standardized jail population and cost data.",
    requiredEvidence: ["Daily jail population reports", "Pre-trial length of stay data", "Jail capacity assessment", "Court docket reports"]
  },
  {
    id: "SL-SR-112",
    name: "311 Service Fragmentation",
    signalPattern: "Duplicate requests >12% of volume OR first-contact resolution <45% OR response time variance >400% across channels",
    interpretedPainId: "SL-PAIN-112",
    valueDriverCategory: "Cost Savings + Mission Effectiveness",
    linkedKPIs: ["SL-KPI-134", "SL-KPI-135", "SL-KPI-136"],
    affectedPersonaIds: ["SL-PERS-102", "SL-PERS-103", "SL-PERS-101"],
    confidence: "MEDIUM",
    confidenceRationale: "311 data quality varies by jurisdiction; city auditor reports provide the most reliable evidence.",
    requiredEvidence: ["311 system transaction logs", "Channel-specific response time reports", "Citizen callback records", "Department work order data"]
  },
  {
    id: "SL-SR-113",
    name: "Fleet and Asset Decay",
    signalPattern: "Average fleet age >10 years OR breakdown rate >15% annually OR preventive maintenance completion <60%",
    interpretedPainId: "SL-PAIN-113",
    valueDriverCategory: "Cost Savings + Risk Reduction",
    linkedKPIs: ["SL-KPI-137", "SL-KPI-138", "SL-KPI-139"],
    affectedPersonaIds: ["SL-PERS-103", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "APWA fleet surveys and municipal fleet management systems provide standardized age and breakdown data.",
    requiredEvidence: ["Fleet inventory and age data", "Maintenance records (CMMS)", "Breakdown incident logs", "Replacement schedule"]
  },
  {
    id: "SL-SR-114",
    name: "Tax Revenue Collection Gap",
    signalPattern: "Collection rate <90% for major tax type OR delinquency rate >12% OR no automated IRS data match OR refund fraud >$2M annually",
    interpretedPainId: "SL-PAIN-114",
    valueDriverCategory: "Revenue Uplift + Risk Reduction",
    linkedKPIs: ["SL-KPI-140", "SL-KPI-141", "SL-KPI-142"],
    affectedPersonaIds: ["SL-PERS-104", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "State revenue department annual reports and FTA surveys provide standardized collection metrics.",
    requiredEvidence: ["Tax collection reports", "Delinquency aging reports", "IRS data match participation status", "Refund fraud case files"]
  },
  {
    id: "SL-SR-115",
    name: "Economic Development Incentive Opacity",
    signalPattern: "No unified incentive database OR clawback collections <$500K on >$10M awards OR GASB 77 disclosure incomplete OR job verification manual only",
    interpretedPainId: "SL-PAIN-115",
    valueDriverCategory: "Revenue Uplift + Risk Reduction",
    linkedKPIs: ["SL-KPI-143", "SL-KPI-144", "SL-KPI-145"],
    affectedPersonaIds: ["SL-PERS-104", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "Good Jobs First and GASB 77 compliance studies provide direct measurement of tracking gaps.",
    requiredEvidence: ["GASB 77 disclosures", "Incentive award database (or absence)", "Clawback collection records", "Job verification audit reports"]
  },
  {
    id: "SL-SR-116",
    name: "Open Data / Records Obsolescence",
    signalPattern: "Open data portal updates <quarterly OR API availability <40% of datasets OR records request backlog >90 days",
    interpretedPainId: "SL-PAIN-116",
    valueDriverCategory: "Mission Effectiveness + Cost Savings",
    linkedKPIs: ["SL-KPI-146", "SL-KPI-147", "SL-KPI-148"],
    affectedPersonaIds: ["SL-PERS-102", "SL-PERS-101"],
    confidence: "MEDIUM",
    confidenceRationale: "Sunlight Foundation surveys exist but adoption varies; FOIA backlog data is more reliable in states with statutory reporting.",
    requiredEvidence: ["Open data portal metadata", "API inventory", "FOIA/request backlog reports", "Records retention schedule compliance"]
  },
  {
    id: "SL-SR-117",
    name: "County-Municipal Boundary Misalignment",
    signalPattern: "Address conflicts >5% across county-municipal systems OR no shared parcel fabric OR GIS update frequency <annual OR mutual aid billing disputes active",
    interpretedPainId: "SL-PAIN-117",
    valueDriverCategory: "Cost Savings + Mission Effectiveness",
    linkedKPIs: ["SL-KPI-149", "SL-KPI-150", "SL-KPI-151"],
    affectedPersonaIds: ["SL-PERS-102", "SL-PERS-103", "SL-PERS-101"],
    confidence: "MEDIUM",
    confidenceRationale: "NACo and NSGIC surveys identify data sharing priorities but granular conflict rates require local assessment.",
    requiredEvidence: ["County and municipal GIS data comparison", "Address master database audit", "Mutual aid billing records", "Service district boundary maps"]
  },
  {
    id: "SL-SR-118",
    name: "UI System Technical Debt",
    signalPattern: "UI system age >20 years OR benefits delivery >21 days OR identity verification backlog >30 days OR DOL ETA compliance action pending",
    interpretedPainId: "SL-PAIN-118",
    valueDriverCategory: "Cost Savings + Risk Reduction + Mission Effectiveness",
    linkedKPIs: ["SL-KPI-152", "SL-KPI-153", "SL-KPI-154"],
    affectedPersonaIds: ["SL-PERS-104", "SL-PERS-101", "SL-PERS-102"],
    confidence: "HIGH",
    confidenceRationale: "DOL ETA and GAO reports provide standardized system age and performance data.",
    requiredEvidence: ["UI system inventory", "Benefits delivery time reports", "Identity verification queue data", "DOL ETA correspondence"]
  }
];

// ============================================================
// BUYING TRIGGERS REGISTRY
// ============================================================

export const STATE_LOCAL_BUYING_TRIGGERS: TriggerEvent[] = [
  {
    id: "SL-BT-101",
    triggerName: "New Governor / Mayor / County Administrator Appointment",
    triggerType: "Leadership Change",
    timeWindow: "First 6-12 months of new administration (highest receptivity)",
    linkedPainIds: ["SL-PAIN-101", "SL-PAIN-106", "SL-PAIN-109", "SL-PAIN-116"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-102", "SL-PERS-104"],
    signalSources: ["Election calendars", "Transition team announcements", "State/local press releases", "LinkedIn executive changes"],
    confidence: "HIGH",
    actionRecommendation: "Engage transition team early with 90-day quick-win proposals tied to campaign priorities."
  },
  {
    id: "SL-BT-102",
    triggerName: "Ransomware or Major Cybersecurity Incident",
    triggerType: "Crisis Event",
    timeWindow: "30-90 days post-incident (peak urgency); secondary window at 6-month insurance renewal",
    linkedPainIds: ["SL-PAIN-109", "SL-PAIN-102"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-105"],
    signalSources: ["MS-ISAC incident alerts", "Local news coverage", "Cyber insurance claim filings", "State CIO security bulletins"],
    confidence: "HIGH",
    actionRecommendation: "Offer incident response assessment + modernization roadmap within 48 hours of public disclosure."
  },
  {
    id: "SL-BT-103",
    triggerName: "Federal Grant Award (IIJA, IRA, SLFRF, BEAD, FEMA Preparedness)",
    triggerType: "Funding Availability",
    timeWindow: "Grant award announcement to obligation deadline (typically 12-36 months)",
    linkedPainIds: ["SL-PAIN-105", "SL-PAIN-110", "SL-PAIN-109", "SL-PAIN-113"],
    linkedPersonaIds: ["SL-PERS-102", "SL-PERS-103", "SL-PERS-105"],
    signalSources: ["Grants.gov", "USDOT/FHWA grant announcements", "NTIA BEAD allocation notices", "FEMA grant award letters"],
    confidence: "HIGH",
    actionRecommendation: "Map solution components directly to grant eligible activities and provide pre-written justification language."
  },
  {
    id: "SL-BT-104",
    triggerName: "State Audit or Inspector General Critical Findings",
    triggerType: "Compliance Event",
    timeWindow: "30-60 days post-report release (response plan deadline); 6-12 months (implementation deadline)",
    linkedPainIds: ["SL-PAIN-101", "SL-PAIN-103", "SL-PAIN-106", "SL-PAIN-109"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-102", "SL-PERS-104"],
    signalSources: ["State auditor websites", "IG report releases", "Legislative hearing schedules", "News coverage of audit findings"],
    confidence: "HIGH",
    actionRecommendation: "Reference audit finding numbers explicitly in proposal; offer corrective action plan template."
  },
  {
    id: "SL-BT-105",
    triggerName: "Bond Rating Review or Credit Downgrade Warning",
    triggerType: "Financial Pressure",
    timeWindow: "0-90 days post-warning (management response period); 6-12 months (next review cycle)",
    linkedPainIds: ["SL-PAIN-105", "SL-PAIN-111", "SL-PAIN-113", "SL-PAIN-114"],
    linkedPersonaIds: ["SL-PERS-102", "SL-PERS-103"],
    signalSources: ["Moody's/S&P municipal credit opinions", "CAFR disclosure of rating outlook", "Municipal bond offering documents"],
    confidence: "HIGH",
    actionRecommendation: "Frame solution as operational efficiency and risk reduction directly responsive to rating agency concerns."
  },
  {
    id: "SL-BT-106",
    triggerName: "Major Litigation or Class Action Settlement",
    triggerType: "Legal Event",
    timeWindow: "Settlement announcement to compliance deadline (varies 6-36 months)",
    linkedPainIds: ["SL-PAIN-102", "SL-PAIN-104", "SL-PAIN-105", "SL-PAIN-111"],
    linkedPersonaIds: ["SL-PERS-102", "SL-PERS-106", "SL-PERS-105"],
    signalSources: ["Court dockets (PACER/state)", "DOJ Civil Rights Division announcements", "Local news on verdicts", "Consent decree filings"],
    confidence: "HIGH",
    actionRecommendation: "Map solution capabilities to consent decree requirements; offer compliance reporting dashboards."
  },
  {
    id: "SL-BT-107",
    triggerName: "Key Staff Retirement / Turnover in Critical Role",
    triggerType: "Workforce Event",
    timeWindow: "Retirement announcement (6-12 months notice typical) to 6 months post-departure",
    linkedPainIds: ["SL-PAIN-101", "SL-PAIN-104", "SL-PAIN-113"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-106", "SL-PERS-103"],
    signalSources: ["LinkedIn profile updates", "State/local press releases", "Retirement board filings", "HR vacancy postings"],
    confidence: "MEDIUM",
    actionRecommendation: "Position solution as knowledge capture and institutional continuity, not just replacement."
  },
  {
    id: "SL-BT-108",
    triggerName: "State Legislative Mandate with Appropriation",
    triggerType: "Policy Event",
    timeWindow: "Bill passage to implementation deadline (typically 12-24 months); RFP release 3-6 months post-passage",
    linkedPainIds: ["SL-PAIN-102", "SL-PAIN-104", "SL-PAIN-109"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-106", "SL-PERS-105"],
    signalSources: ["State legislative tracking services", "Bill text databases", "Fiscal notes on legislation", "Governor signing announcements"],
    confidence: "HIGH",
    actionRecommendation: "Engage agency 6 months pre-passage if bill is tracked; provide draft RFP language aligned with statutory requirements."
  },
  {
    id: "SL-BT-109",
    triggerName: "Citizen Referendum or Service Level Commitment",
    triggerType: "Political Event",
    timeWindow: "Election result to first progress report (typically 6-12 months); budget cycle following election",
    linkedPainIds: ["SL-PAIN-105", "SL-PAIN-108", "SL-PAIN-112"],
    linkedPersonaIds: ["SL-PERS-102", "SL-PERS-103"],
    signalSources: ["Ballot measure tracking (Ballotpedia)", "Campaign platform documents", "City council resolutions", "Mayoral transition reports"],
    confidence: "MEDIUM",
    actionRecommendation: "Align metrics with campaign promises; offer public dashboard for transparency."
  },
  {
    id: "SL-BT-110",
    triggerName: "Federal Compliance Action (DOL ETA, HUD, CMS, DOJ)",
    triggerType: "Enforcement Event",
    timeWindow: "Compliance notice receipt to response deadline (typically 30-90 days); implementation period 6-18 months",
    linkedPainIds: ["SL-PAIN-107", "SL-PAIN-118"],
    linkedPersonaIds: ["SL-PERS-104", "SL-PERS-102"],
    signalSources: ["Federal Register notices", "HUD PHA designations", "DOL ETA letters to states", "CMS state audit reports"],
    confidence: "HIGH",
    actionRecommendation: "Provide corrective action plan template and reference federal compliance criteria explicitly in proposal."
  },
  {
    id: "SL-BT-111",
    triggerName: "Major Infrastructure Failure or Natural Disaster",
    triggerType: "Crisis Event",
    timeWindow: "0-30 days (emergency procurement window); 30-180 days (recovery grant applications); 6-12 months (capital planning cycle)",
    linkedPainIds: ["SL-PAIN-105", "SL-PAIN-110", "SL-PAIN-113"],
    linkedPersonaIds: ["SL-PERS-103", "SL-PERS-105", "SL-PERS-102"],
    signalSources: ["FEMA disaster declarations", "NIBS infrastructure incident reports", "Local news", "NTSB reports (for bridges)"],
    confidence: "HIGH",
    actionRecommendation: "Offer rapid assessment + long-term asset management strategy; position as preventing next failure."
  },
  {
    id: "SL-BT-112",
    triggerName: "Vendor End-of-Life or Support Termination Notice",
    triggerType: "Technology Event",
    timeWindow: "EOL announcement to end of support (typically 12-36 months); budget cycle preceding migration",
    linkedPainIds: ["SL-PAIN-101", "SL-PAIN-104", "SL-PAIN-113", "SL-PAIN-118"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-106", "SL-PERS-103"],
    signalSources: ["Vendor EOL notices", "State/local procurement calendars", "IT strategic plans", "NASCIO legacy system inventories"],
    confidence: "HIGH",
    actionRecommendation: "Map migration timeline to vendor deadline; offer phased approach to de-risk transition."
  },
  {
    id: "SL-BT-113",
    triggerName: "New Statewide Shared Services Initiative",
    triggerType: "Consolidation Event",
    timeWindow: "Initiative announcement to RFP release (typically 6-12 months); implementation 12-36 months",
    linkedPainIds: ["SL-PAIN-106", "SL-PAIN-109", "SL-PAIN-112"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-102"],
    signalSources: ["State CIO strategic plans", "Governor executive orders", "NASCIO shared services reports", "Legislative appropriation hearings"],
    confidence: "HIGH",
    actionRecommendation: "Position as shared-services-ready architecture; demonstrate multi-tenant capabilities and state-level security compliance."
  },
  {
    id: "SL-BT-114",
    triggerName: "Cyber Insurance Renewal with Premium Spike or Coverage Reduction",
    triggerType: "Financial Pressure",
    timeWindow: "60-90 days before renewal (decision window); annual cycle",
    linkedPainIds: ["SL-PAIN-109"],
    linkedPersonaIds: ["SL-PERS-101", "SL-PERS-102"],
    signalSources: ["Municipal risk pool announcements", "Insurance broker communications", "State association risk management alerts"],
    confidence: "HIGH",
    actionRecommendation: "Quantify insurance premium reduction ($50K-$500K) as part of ROI; map controls to carrier requirements."
  }
];

// ============================================================
// VALUE FORMULAS REGISTRY
// ============================================================

export const STATE_LOCAL_FORMULAS: ValueFormula[] = [
  {
    id: "SL-VF-101",
    name: "DMV Digital Channel Shift Value",
    formulaExpression: "V = Total_DMV_Transactions * (Target_Digital_% - Baseline_Digital_%) * (Cost_WalkIn - Cost_Online) + Staff_Avoidance_Value",
    requiredInputs: ["Total annual DMV transactions", "Baseline digital %", "Target digital %", "Cost per walk-in transaction", "Cost per online transaction", "FTE avoidance count and loaded cost"],
    outputUnit: "USD (annual)",
    applicableSegments: ["DMVs", "State DOTs"],
    confidenceRules: "HIGH if DMV cost accounting available; MEDIUM if using AAMVA estimates ($45 walk-in vs $8 online); LOW if no transaction volume data",
    exampleCalculation: "5M transactions, 30%->70% digital, $45 walk-in vs $8 online, 20 FTE @ $75K: 2M * $37 + $1.5M = $75.5M annual",
    valueDriver: "Cost Savings"
  },
  {
    id: "SL-VF-102",
    name: "911 PSAP Staffing Optimization Value",
    formulaExpression: "V = (Baseline_Abandonment_Rate - Target_Abandonment_Rate) * Annual_Call_Volume * Cost_Per_Abandoned_Call + Overtime_Reduction + Liability_Avoidance",
    requiredInputs: ["Baseline/target abandoned call rate", "Annual 911 call volume", "Cost per abandoned call (rework, callback, liability)", "Overtime reduction amount", "Estimated liability avoidance"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Public Safety", "Emergency Management"],
    confidenceRules: "HIGH if PSAP call data and staffing cost available; MEDIUM if using NENA benchmarks; LOW if no call volume data",
    exampleCalculation: "Abandonment 6%->2%, 500K calls, $150 per abandoned call, $500K overtime, $1M liability: 20K * $150 + $500K + $1M = $4.5M",
    valueDriver: "Risk Reduction"
  },
  {
    id: "SL-VF-103",
    name: "Property Tax Collection Improvement",
    formulaExpression: "V = Assessed_Property_Value * Tax_Rate * (Target_Collection_% - Baseline_Collection_%) + Appeal_Reduction_Value",
    requiredInputs: ["Total assessed property value", "Effective tax rate", "Baseline/target collection rate", "Appeal reduction value from improved assessment accuracy"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Tax / Revenue", "County Government"],
    confidenceRules: "HIGH if tax roll and collection data available; MEDIUM if using IAAO ratio study estimates; LOW if no assessment data",
    exampleCalculation: "$10B assessed, 1.2% rate, 94%->97% collection, $500K appeal reduction: $120M * 0.03 + $500K = $4.1M",
    valueDriver: "Revenue Uplift"
  },
  {
    id: "SL-VF-104",
    name: "Court Case Backlog Elimination Value",
    formulaExpression: "V = (Baseline_Backlog - Target_Backlog) * Cost_Per_Case_Processed + Jail_Cost_Avoidance + FTE_Optimization",
    requiredInputs: ["Baseline/target case backlog count", "Cost per case processed", "Daily jail cost per pre-trial detainee", "Average pre-trial days avoided", "FTE optimization value"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Courts", "County Government"],
    confidenceRules: "HIGH if court CMS and jail cost data available; MEDIUM if using Vera Institute jail cost estimates ($100-$200/day); LOW if no backlog count",
    exampleCalculation: "Backlog 10K->2K, $300/case, $150/day jail, 15 days avg avoided, 500 pre-trial: 8K*$300 + 500*15*$150*365 + $400K",
    valueDriver: "Cost Savings"
  },
  {
    id: "SL-VF-105",
    name: "Road Reactive-to-Preventive Maintenance Value",
    formulaExpression: "V = (Reactive_Cost_Per_Lane_Mile - Preventive_Cost_Per_Lane_Mile) * Lane_Miles_Maintained + Liability_Claim_Avoidance + User_Delay_Cost_Avoidance",
    requiredInputs: ["Reactive cost per lane-mile", "Preventive cost per lane-mile", "Total lane miles maintained", "Baseline liability claims", "Target liability reduction", "User delay cost per incident"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Public Works", "State DOT", "Municipal"],
    confidenceRules: "HIGH if CMMS and claims data available; MEDIUM if using FHWA/ASCE ratios; LOW if no lane-mile inventory",
    exampleCalculation: "$25K reactive vs $8K preventive, 5K lane-miles, $1M liability avoidance, $500K delay: $17K*5K + $1M + $500K = $86.5M (normalized over multi-year)",
    valueDriver: "Cost Savings"
  },
  {
    id: "SL-VF-106",
    name: "State/Local Procurement Acceleration Value",
    formulaExpression: "V = (Baseline_Days - Target_Days) / 365 * Annual_Procurement_Volume * Cost_of_Capital_Rate + Administrative_Cost_Savings + Protest_Avoidance_Value",
    requiredInputs: ["Baseline/target procurement cycle days", "Annual procurement volume", "Cost of capital rate", "Administrative cost per procurement", "Protest rate reduction value"],
    outputUnit: "USD (annual)",
    applicableSegments: ["State & Local Government"],
    confidenceRules: "HIGH if procurement system data available; MEDIUM if using NASPO averages; LOW if no procurement volume data",
    exampleCalculation: "200->90 days, $300M volume, 4% cost of capital, $500K admin savings, $300K protest avoidance: (110/365)*$300M*0.04 + $800K = $4.4M",
    valueDriver: "Working Capital"
  },
  {
    id: "SL-VF-107",
    name: "PHA HAP Utilization Recovery",
    formulaExpression: "V = (Target_HAP_Utilization - Baseline_HAP_Utilization) * Annual_HAP_Budget + Administrative_Efficiency_Gain",
    requiredInputs: ["Baseline/target HAP utilization %", "Annual HAP budget", "Administrative efficiency gain from automation"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Housing Authorities"],
    confidenceRules: "HIGH if HUD financial data available; MEDIUM if using PHA annual plan estimates; LOW if no HAP budget data",
    exampleCalculation: "90%->97% on $20M HAP budget, $200K admin gain: $20M * 0.07 + $200K = $1.6M",
    valueDriver: "Working Capital"
  },
  {
    id: "SL-VF-108",
    name: "Building Permit Digital Transformation Value",
    formulaExpression: "V = (Baseline_Cost_Per_Permit - Digital_Cost_Per_Permit) * Annual_Permit_Volume + Fee_Revenue_Uplift + Developer_Retention_Value",
    requiredInputs: ["Baseline cost per permit (manual)", "Digital cost per permit", "Annual permit volume", "Fee revenue increase from faster throughput", "Developer retention economic value"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Municipal", "County Government", "Economic Development"],
    confidenceRules: "HIGH if permit cost accounting available; MEDIUM if using ABcD benchmarks ($350 manual vs $75 digital); LOW if no permit volume",
    exampleCalculation: "$350->$75 per permit, 10K permits, $500K fee uplift, $1M developer value: $275*10K + $1.5M = $4.25M",
    valueDriver: "Revenue Uplift"
  },
  {
    id: "SL-VF-109",
    name: "StateRAMP Authorization Efficiency",
    formulaExpression: "V = (Baseline_Vendor_Onboarding_Months - Target_Months) * Avg_Annual_Contract_Value_Per_Vendor * Vendor_Count + Avoided_Shadow_IT_Risk + Security_Incident_Avoidance",
    requiredInputs: ["Baseline/target vendor onboarding months", "Average annual contract value per vendor", "Vendor count", "Shadow IT risk cost", "Security incident avoidance value"],
    outputUnit: "USD (annual)",
    applicableSegments: ["State & Local Government"],
    confidenceRules: "MEDIUM (StateRAMP is relatively new, limited longitudinal data); LOW if no vendor inventory",
    exampleCalculation: "18->6 months, $500K avg contract, 50 vendors, $1M shadow IT risk, $2M incident avoidance: (12/12)*$500K*50 + $3M = $28M (timing adjustment needed—use NPV)",
    valueDriver: "Risk Reduction"
  },
  {
    id: "SL-VF-110",
    name: "EOC / Interoperability Common Operating Picture Value",
    formulaExpression: "V = Disaster_Recovery_Cost_Avoidance + Mutual_Aid_Billing_Accuracy_Improvement + Resource_Deployment_Time_Value + Liability_Avoidance",
    requiredInputs: ["Historical disaster recovery cost", "Estimated reduction with COP", "Mutual aid billing error rate baseline/target", "Resource deployment time value per hour", "Liability exposure reduction"],
    outputUnit: "USD (per major event / annualized)",
    applicableSegments: ["Emergency Management", "Public Safety"],
    confidenceRules: "MEDIUM (disaster-dependent, probabilistic); HIGH if after-action cost data available; LOW if no historical event data",
    exampleCalculation: "$50M recovery cost, 20% reduction = $10M + $500K billing + $2M deployment + $1M liability = $13.5M per major event",
    valueDriver: "Risk Reduction"
  },
  {
    id: "SL-VF-111",
    name: "Jail Per-Diem Cost Reduction via Diversion",
    formulaExpression: "V = (Baseline_PreTrial_POP - Target_PreTrial_POP) * Daily_Jail_Cost * 365 + Electronic_Monitoring_Cost + Program_Cost",
    requiredInputs: ["Baseline/target pre-trial population", "Daily jail cost per inmate", "Electronic monitoring cost per participant", "Diversion program cost", "Net days avoided"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Courts", "Corrections", "County Government"],
    confidenceRules: "HIGH if jail cost accounting available; MEDIUM if using Vera Institute estimates ($100-$200/day); LOW if no population data",
    exampleCalculation: "300->200 pre-trial, $150/day, EM $15/day for 100 participants: 100*$150*365 - 100*$15*365 = $4.9M net annual savings",
    valueDriver: "Cost Savings"
  },
  {
    id: "SL-VF-112",
    name: "311 / Citizen Request Consolidation Value",
    formulaExpression: "V = (Duplicate_Requests_Eliminated * Cost_Per_Duplicate) + (Channel_Shift_Savings) + (First_Contact_Resolution_Improvement_Value) + FTE_Avoidance",
    requiredInputs: ["Duplicate request % baseline/target", "Annual request volume", "Cost per duplicate handling", "Channel shift % and cost delta", "FTE avoidance count and cost"],
    outputUnit: "USD (annual)",
    applicableSegments: ["Municipal", "County Government"],
    confidenceRules: "MEDIUM if 311 system data available; LOW if no request tracking system",
    exampleCalculation: "15%->5% duplicates on 400K requests, $25/duplicate, 30% channel shift saving $40/request, 8 FTE @ $70K: 40K*$25 + 120K*$40 + $560K = $6.56M",
    valueDriver: "Cost Savings"
  },
  {
    id: "SL-VF-113",
    name: "Fleet Telematics and Predictive Maintenance ROI",
    formulaExpression: "V = (Breakdown_Avoidance_Value + Fuel_Efficiency_Gain + Overtime_Reduction + Extended_Asset_Life_Value) - Telematics_TCO",
    requiredInputs: ["Fleet size", "Average breakdown cost", "Fuel efficiency improvement %", "Baseline fuel spend", "Overtime reduction", "Asset life extension value", "Telematics system TCO"],
    outputUnit: "USD (annual net)",
    applicableSegments: ["Public Works", "Municipal", "State DOT"],
    confidenceRules: "HIGH if fleet maintenance data available; MEDIUM if using APWA benchmarks; LOW if no fleet inventory",
    exampleCalculation: "500 vehicles, $3K breakdown avoidance, 8% fuel savings on $2M fuel, $400K overtime, $1M life extension, $800K TCO: $1.5M + $160K + $400K + $1M - $800K = $2.26M net",
    valueDriver: "Cost Savings"
  }
];

// ============================================================
// SIGNAL MATCHING ENGINE
// ============================================================

export interface SignalMatchResult {
  matched: boolean;
  ruleId: string;
  ruleName: string;
  confidence: SignalConfidence;
  matchedConditions: string[];
  missingEvidence: string[];
  recommendedNextSteps: string[];
  estimatedValueRange?: { low: number; high: number; unit: string };
}

/**
 * Example signal matching function.
 * In production, this would be backed by a rules engine or LLM prompt.
 */
export function matchStateLocalSignals(observedData: Record<string, any>): SignalMatchResult[] {
  const results: SignalMatchResult[] = [];

  // Example: DMV Wait Time Crisis (SL-SR-101)
  if (
    (observedData.dmv_wait_time_minutes && observedData.dmv_wait_time_minutes > 60) ||
    (observedData.dmv_appointment_backlog_days && observedData.dmv_appointment_backlog_days > 21) ||
    (observedData.dmv_complaint_volume_qoq_change && observedData.dmv_complaint_volume_qoq_change > 0.20)
  ) {
    const matchedConditions: string[] = [];
    if (observedData.dmv_wait_time_minutes > 60) matchedConditions.push("wait_time >60 min");
    if (observedData.dmv_appointment_backlog_days > 21) matchedConditions.push("appointment_backlog >3 weeks");
    if (observedData.dmv_complaint_volume_qoq_change > 0.20) matchedConditions.push("complaint_volume_up >20% QoQ");

    results.push({
      matched: true,
      ruleId: "SL-SR-101",
      ruleName: "DMV Wait Time Crisis Signal",
      confidence: matchedConditions.length >= 2 ? "HIGH" : "MEDIUM",
      matchedConditions,
      missingEvidence: ["DMV queue system reports", "Appointment system data", "Citizen complaint logs"],
      recommendedNextSteps: [
        "Validate current digital transaction share vs walk-in cost",
        "Assess legacy DMV system age and integration capability",
        "Calculate 3-year channel shift ROI using SL-VF-101"
      ],
      estimatedValueRange: { low: 15_000_000, high: 75_000_000, unit: "USD (3-year NPV)" }
    });
  }

  // Example: 911 Answer Rate Degradation (SL-SR-102)
  if (
    (observedData.nine_one_one_answer_rate && observedData.nine_one_one_answer_rate < 0.90) ||
    (observedData.psap_abandoned_call_rate && observedData.psap_abandoned_call_rate > 0.05) ||
    (observedData.psap_vacancy_rate && observedData.psap_vacancy_rate > 0.15)
  ) {
    const matchedConditions: string[] = [];
    if (observedData.nine_one_one_answer_rate < 0.90) matchedConditions.push("answer_rate <90%");
    if (observedData.psap_abandoned_call_rate > 0.05) matchedConditions.push("abandoned_calls >5%");
    if (observedData.psap_vacancy_rate > 0.15) matchedConditions.push("psap_vacancy >15%");

    results.push({
      matched: true,
      ruleId: "SL-SR-102",
      ruleName: "911 Answer Rate Degradation",
      confidence: "HIGH",
      matchedConditions,
      missingEvidence: ["CAD uptime logs", "PSAP staffing reports", "State NG911 plan status"],
      recommendedNextSteps: [
        "Assess NG911 migration funding and timeline",
        "Calculate PSAP staffing optimization ROI using SL-VF-102",
        "Review mutual aid and overflow routing agreements"
      ],
      estimatedValueRange: { low: 2_000_000, high: 10_000_000, unit: "USD (annual risk-adjusted)" }
    });
  }

  // Example: Procurement Cycle Elongation (SL-SR-106)
  if (
    (observedData.procurement_cycle_days && observedData.procurement_cycle_days > 180) ||
    (observedData.sole_source_share && observedData.sole_source_share > 0.15) ||
    (observedData.protest_rate && observedData.protest_rate > 0.03)
  ) {
    const matchedConditions: string[] = [];
    if (observedData.procurement_cycle_days > 180) matchedConditions.push("procurement_cycle >180 days");
    if (observedData.sole_source_share > 0.15) matchedConditions.push("sole_source >15%");
    if (observedData.protest_rate > 0.03) matchedConditions.push("protest_rate >3%");

    results.push({
      matched: true,
      ruleId: "SL-SR-106",
      ruleName: "Procurement Cycle Elongation",
      confidence: "HIGH",
      matchedConditions,
      missingEvidence: ["Procurement system data", "Sole-source justification logs", "RFP calendars"],
      recommendedNextSteps: [
        "Benchmark against NASPO state procurement survey",
        "Quantify working capital impact using SL-VF-106",
        "Assess e-procurement and cooperative purchasing options"
      ],
      estimatedValueRange: { low: 1_000_000, high: 8_000_000, unit: "USD (annual opportunity cost)" }
    });
  }

  return results;
}

// ============================================================
// EXAMPLE USAGE
// ============================================================

const exampleObservedData = {
  dmv_wait_time_minutes: 78,
  dmv_appointment_backlog_days: 28,
  dmv_complaint_volume_qoq_change: 0.35,
  nine_one_one_answer_rate: 0.87,
  psap_abandoned_call_rate: 0.06,
  procurement_cycle_days: 210,
  sole_source_share: 0.18
};

const exampleMatches = matchStateLocalSignals(exampleObservedData);
console.log(`Matched ${exampleMatches.length} signal rules:`);
for (const m of exampleMatches) {
  console.log(`- ${m.ruleId}: ${m.ruleName} (${m.confidence}) — Value: $${m.estimatedValueRange?.low?.toLocaleString()} - $${m.estimatedValueRange?.high?.toLocaleString()}`);
}

// Expected output:
// Matched 3 signal rules:
// - SL-SR-101: DMV Wait Time Crisis Signal (HIGH) — Value: $15,000,000 - $75,000,000
// - SL-SR-102: 911 Answer Rate Degradation (HIGH) — Value: $2,000,000 - $10,000,000
// - SL-SR-106: Procurement Cycle Elongation (HIGH) — Value: $1,000,000 - $8,000,000
