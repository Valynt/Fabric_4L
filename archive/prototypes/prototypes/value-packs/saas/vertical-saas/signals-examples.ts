/**
 * Vertical SaaS Subpack - Signal Interpretation Examples (TypeScript)
 * ID: vertical-saas-v1
 * Parent Master: saas-master-v1
 * 
 * This file provides executable examples of how to apply the Vertical SaaS
 * signal rules, value formulas, and buying triggers in production code.
 */

// ============================================================
// TYPE DEFINITIONS (aligned with SubpackValuePack schema)
// ============================================================

interface VerticalPain {
  id: string;
  name: string;
  affectedVerticals: string[];
  prevalence: "HIGH" | "MEDIUM" | "LOW";
  confidence: "HIGH" | "MEDIUM" | "LOW";
}

interface VerticalKPI {
  id: string;
  name: string;
  formula: string;
  unit: string;
  benchmarkRange: string;
  typicalRange: string;
}

interface SignalRule {
  id: string;
  signalName: string;
  rawSignalPattern: string;
  interpretedMeaning: string;
  linkedPains: string[];
  linkedKPIs: string[];
  confidenceScore: number;
  requiredConfirmationSignals: string[];
}

interface ValueFormula {
  id: string;
  name: string;
  formulaExpression: string;
  requiredInputs: string[];
  outputUnit: string;
  exampleCalculation: string;
}

interface BuyingTrigger {
  id: string;
  name: string;
  triggerEvent: string;
  urgencyLevel: "HIGH" | "MEDIUM" | "LOW";
  typicalTiming: string;
  affectedVerticals: string[];
  linkedPains: string[];
}

// ============================================================
// VERTICAL PAIN REGISTRY
// ============================================================

const VERTICAL_PAINS: Record<string, VerticalPain> = {
  "VS-P001": { id: "VS-P001", name: "Industry-Specific Workflow Gaps in Generic CRM/ERP", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "ConstructionTech", "PropTech", "LegalTech", "AgTech", "InsurTech"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P002": { id: "VS-P002", name: "Vertical Regulatory Compliance Burden", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "GovTech", "EdTech", "InsurTech", "EnergyTech", "LegalTech"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P003": { id: "VS-P003", name: "Multi-Tenant Data Isolation for Vertical Customers", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "GovTech", "EdTech", "InsurTech"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P004": { id: "VS-P004", name: "Vertical Sales Talent Scarcity and Long Ramp Times", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "LegalTech", "ConstructionTech", "GovTech", "InsurTech"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P005": { id: "VS-P005", name: "Integration with Legacy Industry Systems", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "InsurTech", "LogisticsTech", "Manufacturing SaaS"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P006": { id: "VS-P006", name: "Vertical Market Size and TAM Constraints", affectedVerticals: ["AgTech", "RestaurantTech", "ConstructionTech", "LegalTech", "EnergyTech", "RetailTech"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P007": { id: "VS-P007", name: "Seasonal and Cyclical Revenue Volatility", affectedVerticals: ["AgTech", "ConstructionTech", "RetailTech", "RestaurantTech", "EnergyTech"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P008": { id: "VS-P008", name: "Customer Concentration in Fragmented Vertical Markets", affectedVerticals: ["RestaurantTech", "AgTech", "RetailTech", "ConstructionTech", "LegalTech"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P009": { id: "VS-P009", name: "Payments and Financial Services Monetization Complexity", affectedVerticals: ["Fintech SaaS", "RestaurantTech", "RetailTech", "ConstructionTech", "Healthcare SaaS"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P010": { id: "VS-P010", name: "GovTech Procurement and Sales Cycle Complexity", affectedVerticals: ["GovTech", "EdTech", "Healthcare SaaS"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P011": { id: "VS-P011", name: "Offline-to-Online Workflow Bridging in Analog Industries", affectedVerticals: ["ConstructionTech", "AgTech", "LogisticsTech", "Manufacturing SaaS", "EnergyTech", "RestaurantTech"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P012": { id: "VS-P012", name: "Vertical Network Effects and Marketplace Build-Out Costs", affectedVerticals: ["RestaurantTech", "RetailTech", "ConstructionTech", "AgTech", "Fintech SaaS"], prevalence: "MEDIUM", confidence: "MEDIUM" },
  "VS-P013": { id: "VS-P013", name: "Localization and Multi-Jurisdiction Rollout Complexity", affectedVerticals: ["RetailTech", "RestaurantTech", "Fintech SaaS", "LogisticsTech", "Healthcare SaaS"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P014": { id: "VS-P014", name: "AI Hallucination and Liability Risk in Regulated Verticals", affectedVerticals: ["Healthcare SaaS", "LegalTech", "Fintech SaaS", "InsurTech", "GovTech"], prevalence: "MEDIUM", confidence: "MEDIUM" },
  "VS-P015": { id: "VS-P015", name: "Vertical Customer Acquisition Channel Saturation", affectedVerticals: ["AgTech", "ConstructionTech", "LegalTech", "RestaurantTech", "EnergyTech"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P016": { id: "VS-P016", name: "Fragmented Industry Data Standards and Ontologies", affectedVerticals: ["Healthcare SaaS", "PropTech", "InsurTech", "ConstructionTech", "Fintech SaaS"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P017": { id: "VS-P017", name: "Vertical Talent and Domain Expertise Gap", affectedVerticals: ["Healthcare SaaS", "LegalTech", "ConstructionTech", "AgTech", "InsurTech", "Fintech SaaS"], prevalence: "HIGH", confidence: "HIGH" },
  "VS-P018": { id: "VS-P018", name: "Vertical SaaS Platform Extensibility and API Demand", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "PropTech", "ConstructionTech", "RetailTech"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P019": { id: "VS-P019", name: "Hardware and IoT Integration Complexity", affectedVerticals: ["Manufacturing SaaS", "EnergyTech", "LogisticsTech", "AgTech", "RestaurantTech", "Healthcare SaaS"], prevalence: "MEDIUM", confidence: "HIGH" },
  "VS-P020": { id: "VS-P020", name: "Vertical M&A and Consolidation Risk", affectedVerticals: ["Healthcare SaaS", "LegalTech", "RetailTech", "RestaurantTech", "ConstructionTech", "InsurTech"], prevalence: "MEDIUM", confidence: "MEDIUM" },
};

// ============================================================
// VERTICAL KPI REGISTRY
// ============================================================

const VERTICAL_KPIS: Record<string, VerticalKPI> = {
  "VS-K001": { id: "VS-K001", name: "Vertical Workflow Fit Score", formula: "(Native Vertical Features / Total Required Vertical Features) x 100", unit: "Percentage", typicalRange: "30%-90%", benchmarkRange: "Poor fit: <50%; Strong: >80%" },
  "VS-K002": { id: "VS-K002", name: "Vertical Customization Index", formula: "(Custom Fields + Custom Objects + Custom Workflows) / Standard Configuration Count", unit: "Ratio", typicalRange: "0.5-5.0", benchmarkRange: "Low: <1.0; Unsustainable: >4.0" },
  "VS-K003": { id: "VS-K003", name: "Time-to-Vertical-Value (TTVV)", formula: "Days from Contract to First Industry-Specific Outcome", unit: "Days", typicalRange: "14-180", benchmarkRange: "PLG: <14; Enterprise: <60; At Risk: >90" },
  "VS-K004": { id: "VS-K004", name: "Vertical Compliance Coverage Rate", formula: "(Compliances Certified) / (Required Compliances) x 100", unit: "Percentage", typicalRange: "40%-100%", benchmarkRange: "Blocking: <60%; Market-ready: >80%" },
  "VS-K005": { id: "VS-K005", name: "Security Questionnaire Completion Time (Vertical)", formula: "Sum(Hours per Questionnaire) / Number", unit: "Hours", typicalRange: "20-120", benchmarkRange: "Fast: <40; Deal-killer: >120" },
  "VS-K006": { id: "VS-K006", name: "Audit Finding Rate (Industry-Specific)", formula: "(Industry Findings) / (Total Findings) x 100", unit: "Percentage", typicalRange: "10%-80%", benchmarkRange: "Well-controlled: <20%; Critical: >70%" },
  "VS-K007": { id: "VS-K007", name: "Tenant Isolation Cost per Customer", formula: "(Isolation Infrastructure Cost) / (Tenant Count)", unit: "USD per customer", typicalRange: "$50-$2,000", benchmarkRange: "Efficient: <$200; Unsustainable: >$1,500" },
  "VS-K008": { id: "VS-K008", name: "Data Residency Compliance Rate", formula: "(Compliant Customers) / (Requiring Customers) x 100", unit: "Percentage", typicalRange: "50%-100%", benchmarkRange: "Blocking: <70%; Full: 100%" },
  "VS-K009": { id: "VS-K009", name: "Cross-Tenant Query Performance", formula: "Average Query Response Time", unit: "Seconds", typicalRange: "0.5-30", benchmarkRange: "Fast: <2s; Unusable: >10s" },
  "VS-K010": { id: "VS-K010", name: "Vertical Sales Rep Ramp Time", formula: "Days from Hire to First Closed-Won Deal", unit: "Days", typicalRange: "90-270", benchmarkRange: "Fast: <120; Concerning: >270" },
  "VS-K011": { id: "VS-K011", name: "Vertical Win Rate Premium", formula: "(Vertical Rep Win Rate - Generalist Win Rate) / Generalist x 100", unit: "Percentage", typicalRange: "10%-60%", benchmarkRange: "Minimal: <15%; Elite: >50%" },
  "VS-K012": { id: "VS-K012", name: "Vertical CAC vs. Horizontal CAC Ratio", formula: "(Vertical CAC) / (Horizontal CAC)", unit: "Ratio", typicalRange: "0.8-2.5", benchmarkRange: "Efficient: <1.0; Unsustainable: >2.0" },
  "VS-K013": { id: "VS-K013", name: "Legacy System Integration Success Rate", formula: "(Successful) / (Total Attempts) x 100", unit: "Percentage", typicalRange: "40%-90%", benchmarkRange: "Poor: <50%; Excellent: >85%" },
  "VS-K014": { id: "VS-K014", name: "Integration Time to First Data Flow", formula: "Days from Start to Bi-Directional Exchange", unit: "Days", typicalRange: "7-180", benchmarkRange: "Fast: <21; Blocker: >120" },
  "VS-K015": { id: "VS-K015", name: "Industry Standard Format Support Coverage", formula: "(Formats Supported) / (Top 10 in Vertical) x 100", unit: "Percentage", typicalRange: "30%-100%", benchmarkRange: "Blocking: <50%; Complete: >90%" },
  "VS-K016": { id: "VS-K016", name: "Vertical Market Penetration Rate", formula: "(Your Customers) / (Addressable Businesses) x 100", unit: "Percentage", typicalRange: "0.5%-20%", benchmarkRange: "Early: <2%; Dominant: >15%" },
  "VS-K017": { id: "VS-K017", name: "Adjacent Vertical Expansion Revenue", formula: "(Non-Core Vertical ARR) / (Total ARR) x 100", unit: "Percentage", typicalRange: "0%-30%", benchmarkRange: "Single: <5%; Multi: 15%-30%" },
  "VS-K018": { id: "VS-K018", name: "Horizontal Competitor Feature Parity Gap", formula: "(Horizontal Vertical Features) / (Your Vertical Features) x 100", unit: "Percentage", typicalRange: "20%-150%", benchmarkRange: "Defensible: <50%; Overtaken: >110%" },
  "VS-K019": { id: "VS-K019", name: "Seasonality Revenue Concentration Index", formula: "(Peak Quarter Revenue) / (Annual Revenue) x 100", unit: "Percentage", typicalRange: "25%-50%", benchmarkRange: "Stable: <30%; Extreme: >45%" },
  "VS-K020": { id: "VS-K020", name: "Off-Season Cash Burn Multiple", formula: "(Trough Burn) / (Peak Burn)", unit: "Ratio", typicalRange: "0.8-1.8", benchmarkRange: "Efficient: <1.0; Crisis: >1.5" },
  "VS-K021": { id: "VS-K021", name: "Peak Load Infrastructure Surge Factor", formula: "(Peak Compute) / (Average Compute)", unit: "Ratio", typicalRange: "2-15", benchmarkRange: "Smooth: <3; Extreme: >8" },
  "VS-K022": { id: "VS-K022", name: "SMB Logo Concentration Ratio", formula: "(ACV <$500/month) / (Total Customers) x 100", unit: "Percentage", typicalRange: "40%-90%", benchmarkRange: "Enterprise: <40%; Micro-SMB: >80%" },
  "VS-K023": { id: "VS-K023", name: "Customer Concentration Risk (Top 10)", formula: "(Top 10 ARR) / (Total ARR) x 100", unit: "Percentage", typicalRange: "5%-60%", benchmarkRange: "Diversified: <15%; High Risk: >40%" },
  "VS-K024": { id: "VS-K024", name: "SMB Support Cost per Dollar ARR", formula: "(SMB Support Costs) / (SMB ARR)", unit: "USD/USD", typicalRange: "$0.05-$0.40", benchmarkRange: "Efficient: <$0.10; Unsustainable: >$0.30" },
  "VS-K025": { id: "VS-K025", name: "Embedded Payments Take Rate", formula: "(Payments Revenue) / (Payment Volume) x 100", unit: "Percentage", typicalRange: "0.3%-2.5%", benchmarkRange: "Low: <0.5%; Premium: >1.5%" },
};

// ============================================================
// SIGNAL RULES REGISTRY
// ============================================================

const SIGNAL_RULES: Record<string, SignalRule> = {
  "VS-S001": {
    id: "VS-S001",
    signalName: "Vertical Trade Show Booth Traffic Decline",
    rawSignalPattern: "Booth visitor count at industry flagship event down >30% YoY; competitor booths larger/more prominent",
    interpretedMeaning: "Market consolidation underway; buying committees shifting to digital evaluation before events; potential budget pressure in vertical",
    linkedPains: ["VS-P015", "VS-P020"],
    linkedKPIs: ["VS-K015", "VS-K043"],
    confidenceScore: 0.72,
    requiredConfirmationSignals: ["LinkedIn job postings for competitor sales roles in vertical", "Industry publication ad rate decline"]
  },
  "VS-S002": {
    id: "VS-S002",
    signalName: "Horizontal Platform Vertical Module Launch",
    rawSignalPattern: "Horizontal platform announces vertical-specific module or industry cloud; incumbent announces association partnership",
    interpretedMeaning: "Horizontal players encroaching on vertical turf; vertical SaaS must differentiate via workflow depth and compliance expertise",
    linkedPains: ["VS-P006", "VS-P020", "VS-P001"],
    linkedKPIs: ["VS-K016", "VS-K018"],
    confidenceScore: 0.78,
    requiredConfirmationSignals: ["Horizontal vendor hiring vertical SMEs", "Customer RFPs mentioning horizontal platform as alternative"]
  },
  "VS-S003": {
    id: "VS-S003",
    signalName: "Regulatory Deadline or Enforcement Action in Vertical",
    rawSignalPattern: "New regulation published with 12-18 month compliance deadline; enforcement action against peer company in same vertical",
    interpretedMeaning: "Urgent compliance demand window opening; vertical SaaS with pre-built compliance will see accelerated sales cycles",
    linkedPains: ["VS-P002", "VS-P010"],
    linkedKPIs: ["VS-K004", "VS-K005"],
    confidenceScore: 0.85,
    requiredConfirmationSignals: ["Customer inquiry volume spike about compliance", "RFPs including new regulation as mandatory requirement"]
  },
  "VS-S004": {
    id: "VS-S004",
    signalName: "Legacy System End-of-Life Announcement",
    rawSignalPattern: "Major legacy system vendor announces EOL or sunsetting of product used by target vertical",
    interpretedMeaning: "Massive replacement cycle beginning; vertical SaaS positioned as modern alternative will see 18-36 month demand surge",
    linkedPains: ["VS-P005", "VS-P001"],
    linkedKPIs: ["VS-K013", "VS-K014"],
    confidenceScore: 0.88,
    requiredConfirmationSignals: ["Industry consultant firms publishing migration guides", "Job postings for integration engineers at vertical SaaS companies"]
  },
  "VS-S005": {
    id: "VS-S005",
    signalName: "Vertical Private Equity Roll-Up Activity",
    rawSignalPattern: "PE firm announces 3rd or 4th add-on acquisition in vertical; portfolio company count >10 by single sponsor",
    interpretedMeaning: "Customer base consolidating; ACV may rise but logo count will fall; must sell to PE platform team or risk losing accounts",
    linkedPains: ["VS-P020", "VS-P008"],
    linkedKPIs: ["VS-K022", "VS-K023", "VS-K058"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["Portfolio company executive turnover post-acquisition", "RFPs from PE-backed platform companies"]
  },
  "VS-S006": {
    id: "VS-S006",
    signalName: "Seasonal Customer Activation Surge",
    rawSignalPattern: "Daily active users spiking 3-5x above baseline in predictable seasonal window; support ticket volume correlating",
    interpretedMeaning: "Peak season operational strain; risk of downtime/performance issues during critical revenue period",
    linkedPains: ["VS-P007", "VS-P011"],
    linkedKPIs: ["VS-K019", "VS-K021"],
    confidenceScore: 0.82,
    requiredConfirmationSignals: ["Past-season incident reports or post-mortems", "Customer complaints about performance during peak"]
  },
  "VS-S007": {
    id: "VS-S007",
    signalName: "Industry-Specific Security Incident or Breach",
    rawSignalPattern: "Breach affecting competitor or peer in same vertical; OCR HIPAA settlement; state AG action against fintech",
    interpretedMeaning: "Security and compliance urgency elevated; buyers will prioritize vendors with demonstrated vertical security posture",
    linkedPains: ["VS-P002", "VS-P003"],
    linkedKPIs: ["VS-K005", "VS-K006"],
    confidenceScore: 0.86,
    requiredConfirmationSignals: ["Customer security inquiries spike", "Board-level cybersecurity agenda item"]
  },
  "VS-S008": {
    id: "VS-S008",
    signalName: "Vertical SaaS Company Hiring Spree in Sales/Customer Success",
    rawSignalPattern: "Vertical SaaS competitor hiring 10+ vertical sales or CS roles in 90 days",
    interpretedMeaning: "Competitor is scaling GTM aggressively; market is heating up; incumbent customers may be targeted",
    linkedPains: ["VS-P004", "VS-P015"],
    linkedKPIs: ["VS-K010", "VS-K011"],
    confidenceScore: 0.74,
    requiredConfirmationSignals: ["Competitor funding announcement", "Customer mentioning competitor in calls"]
  },
  "VS-S009": {
    id: "VS-S009",
    signalName: "Government Budget Allocation Increase in Vertical",
    rawSignalPattern: "State or federal budget for vertical IT increasing >15% YoY; stimulus or grant program announced",
    interpretedMeaning: "GovTech/education/healthcare funding wave incoming; 12-24 month procurement cycle will begin",
    linkedPains: ["VS-P010", "VS-P002"],
    linkedKPIs: ["VS-K028", "VS-K029"],
    confidenceScore: 0.81,
    requiredConfirmationSignals: ["RFP volume increase on government procurement sites", "Industry association lobbying success reports"]
  },
  "VS-S010": {
    id: "VS-S010",
    signalName: "IoT/Connected Device Mandate in Vertical",
    rawSignalPattern: "Regulation mandating IoT data collection in vertical; industry consortium releasing device standard",
    interpretedMeaning: "Hardware-software integration demand surge; vertical SaaS with IoT capabilities will see accelerated adoption",
    linkedPains: ["VS-P019", "VS-P005"],
    linkedKPIs: ["VS-K055", "VS-K056"],
    confidenceScore: 0.79,
    requiredConfirmationSignals: ["Device OEM partnerships being announced", "Customer inquiries about sensor integration"]
  },
  "VS-S011": {
    id: "VS-S011",
    signalName: "Vertical Customer Churn Spike in Q1",
    rawSignalPattern: "Logo churn 2x higher in Q1 vs. other quarters; cancellations clustered in specific vertical segment",
    interpretedMeaning: "Seasonal business model stress; customers acquired during peak season not retaining; pricing may not align with seasonal cash flows",
    linkedPains: ["VS-P007", "VS-P008", "VS-P010"],
    linkedKPIs: ["VS-K019", "VS-K022", "VS-K024"],
    confidenceScore: 0.76,
    requiredConfirmationSignals: ["NRR compression in same period", "Support ticket themes around billing/seasonal usage"]
  },
  "VS-S012": {
    id: "VS-S012",
    signalName: "Embedded Payments Regulatory Scrutiny",
    rawSignalPattern: "CFPB, state regulator, or card network issuing guidance on embedded payments; compliance action against vertical SaaS with payments",
    interpretedMeaning: "Payments monetization model under pressure; compliance costs rising; take rates may compress",
    linkedPains: ["VS-P009", "VS-P002"],
    linkedKPIs: ["VS-K025", "VS-K026"],
    confidenceScore: 0.77,
    requiredConfirmationSignals: ["Payment processor fee increase notice", "Legal counsel hiring for payments compliance"]
  },
  "VS-S013": {
    id: "VS-S013",
    signalName: "AI Regulation or Guidance in Vertical",
    rawSignalPattern: "FDA issuing AI/ML SaMD guidance; state bar issuing AI ethics rules; NAIC releasing AI bulletin; EU AI Act enforcement",
    interpretedMeaning: "AI features in regulated verticals face new compliance requirements; vendors with explainable AI and human-in-the-loop advantaged",
    linkedPains: ["VS-P014", "VS-P002"],
    linkedKPIs: ["VS-K040", "VS-K041"],
    confidenceScore: 0.83,
    requiredConfirmationSignals: ["Customer AI risk assessments in RFPs", "Product team delaying AI feature launch for compliance review"]
  },
  "VS-S014": {
    id: "VS-S014",
    signalName: "Vertical Marketplace or Network Launch by Incumbent",
    rawSignalPattern: "Leading vertical SaaS announcing marketplace, network, or two-sided platform; supplier onboarding campaign",
    interpretedMeaning: "Platform strategy activation; revenue diversification attempt; competitive pressure on single-product vertical SaaS",
    linkedPains: ["VS-P012", "VS-P006"],
    linkedKPIs: ["VS-K034", "VS-K035"],
    confidenceScore: 0.71,
    requiredConfirmationSignals: ["Supplier/partner sign-up rates", "Customer adoption of marketplace features"]
  },
  "VS-S015": {
    id: "VS-S015",
    signalName: "Field Workforce Mobile App Adoption Decline",
    rawSignalPattern: "Mobile DAU declining while desktop stable; app store ratings dropping; offline sync complaints increasing",
    interpretedMeaning: "Mobile-first vertical product failing field use cases; competitors with better offline/field capabilities will win",
    linkedPains: ["VS-P011", "VS-P001"],
    linkedKPIs: ["VS-K031", "VS-K032"],
    confidenceScore: 0.79,
    requiredConfirmationSignals: ["Customer success notes about field worker frustration", "Competitor mobile feature releases"]
  },
  "VS-S016": {
    id: "VS-S016",
    signalName: "Vertical Data Exchange or Interoperability Mandate",
    rawSignalPattern: "CMS mandating FHIR APIs; TEFCA going live; state mandating real estate data sharing; open banking expanding",
    interpretedMeaning: "Interoperability is becoming table stakes; vertical SaaS must support industry standard APIs or face exclusion",
    linkedPains: ["VS-P005", "VS-P016"],
    linkedKPIs: ["VS-K046", "VS-K047"],
    confidenceScore: 0.84,
    requiredConfirmationSignals: ["Customer RFPs mentioning interoperability requirements", "Engineering backlog for standard API support"]
  },
  "VS-S017": {
    id: "VS-S017",
    signalName: "Competitor Vertical Acquisition or Merger",
    rawSignalPattern: "Horizontal platform acquiring vertical SaaS player; two vertical SaaS competitors merging; PE take-private",
    interpretedMeaning: "Competitive landscape restructuring; potential customer uncertainty; opportunity to poach customers concerned about roadmap changes",
    linkedPains: ["VS-P020", "VS-P006"],
    linkedKPIs: ["VS-K018", "VS-K058"],
    confidenceScore: 0.75,
    requiredConfirmationSignals: ["Customer concern about vendor stability", "Competitor product roadmap delays post-merger"]
  },
  "VS-S018": {
    id: "VS-S018",
    signalName: "Localization Failure in International Expansion",
    rawSignalPattern: "International churn 2x domestic; support tickets clustered around local compliance/tax; negative reviews in non-US app stores",
    interpretedMeaning: "Vertical localization underestimated; international expansion burning cash without returns; need to invest or retrench",
    linkedPains: ["VS-P013", "VS-P008"],
    linkedKPIs: ["VS-K037", "VS-K038"],
    confidenceScore: 0.80,
    requiredConfirmationSignals: ["International NRR <80%", "Local competitor gaining market share"]
  },
  "VS-S019": {
    id: "VS-S019",
    signalName: "Talent Poaching by Horizontal Platforms",
    rawSignalPattern: "Horizontal platform hiring from vertical SaaS companies for industry cloud teams; vertical SaaS exec departures to horizontal",
    interpretedMeaning: "Horizontal platforms investing in vertical depth; vertical SaaS losing institutional knowledge; competitive threat escalating",
    linkedPains: ["VS-P017", "VS-P004"],
    linkedKPIs: ["VS-K049", "VS-K050"],
    confidenceScore: 0.73,
    requiredConfirmationSignals: ["LinkedIn moves showing vertical talent to horizontal", "Horizontal industry cloud product releases"]
  },
  "VS-S020": {
    id: "VS-S020",
    signalName: "Vertical SaaS Customer Requesting API/Platform Capabilities",
    rawSignalPattern: "Enterprise customers requesting custom APIs, webhooks, or developer access; integration partner inquiries increasing",
    interpretedMeaning: "Product has achieved workflow centrality but lacks extensibility; platform opportunity emerging; risk of customer building competing solution",
    linkedPains: ["VS-P018", "VS-P001"],
    linkedKPIs: ["VS-K052", "VS-K053"],
    confidenceScore: 0.77,
    requiredConfirmationSignals: ["Customer RFPs mentioning platform requirements", "Competitor developer ecosystem growth metrics"]
  },
};

// ============================================================
// VALUE FORMULAS REGISTRY
// ============================================================

const VALUE_FORMULAS: Record<string, ValueFormula> = {
  "VS-VF001": {
    id: "VS-VF001",
    name: "Vertical Workflow Gap Cost",
    formulaExpression: "(Hours_Workaround x Cost_Hour x Users) + (Integration_Dev / Amortization) + Opportunity_Cost",
    requiredInputs: ["hours_workaround_per_user_month", "loaded_cost_per_hour", "users_affected", "integration_dev_cost", "amortization_months", "delayed_feature_revenue"],
    outputUnit: "USD per month",
    exampleCalculation: "(8 hrs x $75 x 200) + ($120K/24) + $5K = $125,000/month"
  },
  "VS-VF002": {
    id: "VS-VF002",
    name: "Vertical Compliance Delay Cost",
    formulaExpression: "(Blocked_Deals x ACV) + Audit_Remediation + (Legal_Hours x Rate) + Delayed_Market_NPV",
    requiredInputs: ["deals_blocked_count", "average_acv", "audit_remediation_cost", "legal_review_hours", "attorney_rate", "delayed_market_entry_npv"],
    outputUnit: "USD per year",
    exampleCalculation: "(15 x $85K) + $180K + (200 x $450) + $500K = $2,185,000/year"
  },
  "VS-VF003": {
    id: "VS-VF003",
    name: "Tenant Isolation Infrastructure ROI",
    formulaExpression: "(Revenue_Compliance_Customers - Isolation_Cost) / Isolation_Cost x 100",
    requiredInputs: ["compliance_customer_revenue", "isolation_infra_cost", "shared_infra_cost_baseline"],
    outputUnit: "Percentage ROI",
    exampleCalculation: "($3.2M - $480K) / $480K x 100 = 567% ROI"
  },
  "VS-VF004": {
    id: "VS-VF004",
    name: "Vertical Sales Talent Premium Payback",
    formulaExpression: "(Incremental_Revenue - Incremental_Comp) / Incremental_Comp x 100",
    requiredInputs: ["vertical_rep_revenue", "generalist_rep_revenue", "vertical_rep_comp", "generalist_rep_comp", "vertical_rep_count", "generalist_rep_count"],
    outputUnit: "Percentage payback",
    exampleCalculation: "($1.8M - $320K) / $320K x 100 = 463% payback"
  },
  "VS-VF005": {
    id: "VS-VF005",
    name: "Legacy System Integration Value",
    formulaExpression: "(Success_Rate x Deals x ACV) - (Failed_Cost + Maintenance + Backlog_Opportunity)",
    requiredInputs: ["integration_success_rate", "deals_requiring_integration", "average_acv", "failed_integration_cost", "annual_maintenance_cost", "backlog_opportunity_cost"],
    outputUnit: "USD per year",
    exampleCalculation: "(0.65 x 80 x $72K) - ($340K + $180K + $420K) = $2,334,000/year"
  },
  "VS-VF006": {
    id: "VS-VF006",
    name: "Vertical TAM Saturation Impact",
    formulaExpression: "(Penetration - Threshold) x Addressable_Businesses x ACV x (1 - Churn)",
    requiredInputs: ["current_penetration_pct", "saturation_threshold_pct", "total_addressable_businesses", "average_acv", "annual_churn_rate"],
    outputUnit: "USD available ARR",
    exampleCalculation: "(12% - 15%) x 45,000 x $18K x 0.88 = -$2.1M (saturation)"
  },
  "VS-VF007": {
    id: "VS-VF007",
    name: "Seasonality Cash Flow Gap Cost",
    formulaExpression: "(Peak_Revenue - Trough_Revenue) x Financing_Rate + (Excess_Burn - Trough_Revenue) + Turnover_Cost",
    requiredInputs: ["peak_quarter_revenue", "trough_quarter_revenue", "financing_rate", "off_season_excess_burn", "seasonal_turnover_cost"],
    outputUnit: "USD per year",
    exampleCalculation: "($2.8M - $0.9M) x 0.08 + ($1.4M - $0.9M) + $180K = $892,000/year"
  },
  "VS-VF008": {
    id: "VS-VF008",
    name: "Embedded Payments Margin Contribution",
    formulaExpression: "(Volume x Take_Rate) - (Processor_Fees + Compliance + Fraud + Chargebacks)",
    requiredInputs: ["total_payment_volume", "take_rate", "processor_fee_rate", "annual_compliance_cost", "fraud_loss_rate", "chargeback_rate"],
    outputUnit: "USD per year",
    exampleCalculation: "($45M x 1.2%) - ($45M x 0.6% + $220K + $45M x 0.05% + $45M x 0.1%) = $270,000/year"
  },
  "VS-VF009": {
    id: "VS-VF009",
    name: "GovTech Sales Cycle Working Capital Impact",
    formulaExpression: "(ACV x Cycle_Days / 365 x Cost_Capital) + (Proposal_Cost x Win_Rate_Inverse) + Net_90_Impact",
    requiredInputs: ["average_deal_value", "avg_sales_cycle_days", "cost_of_capital", "proposal_cost_per_deal", "win_rate", "net_90_revenue_pct", "days_payment_delay"],
    outputUnit: "USD per deal",
    exampleCalculation: "($125K x 270/365 x 10%) + ($18K x 4) + ($125K x 60/365 x 10%) = $117,192/deal"
  },
  "VS-VF010": {
    id: "VS-VF010",
    name: "Field Mobile Infrastructure Cost Avoidance",
    formulaExpression: "(Offline_Sync_Cost + Field_Support_Cost + Lost_Productivity) - Mobile_Infra_Investment",
    requiredInputs: ["offline_sync_failures_monthly", "cost_per_sync_failure", "field_support_tickets_monthly", "cost_per_field_ticket", "affected_field_users", "lost_hours_per_crash", "mobile_infra_investment"],
    outputUnit: "USD per year",
    exampleCalculation: "(450 x $85 + 680 x $120 + 1,200 x 2 x $45) - $320K = $145,600/year"
  },
  "VS-VF011": {
    id: "VS-VF011",
    name: "Vertical Network Effect Revenue Potential",
    formulaExpression: "(Participants x Transactions x Take_Rate x Avg_Value) - (Subsidy + Platform_Ops)",
    requiredInputs: ["network_participants", "expected_transactions", "take_rate", "avg_transaction_value", "subsidy_per_participant", "platform_ops_cost"],
    outputUnit: "USD per year",
    exampleCalculation: "(8,000 x 24 x 1.5% x $350) - (8,000 x $45 + $280K) = $284,000/year"
  },
  "VS-VF012": {
    id: "VS-VF012",
    name: "Localization Expansion ROI",
    formulaExpression: "(Revenue_Year_3 - Investment_Year_3) / Investment_Year_3 x 100",
    requiredInputs: ["localization_engineering_cost", "legal_compliance_cost", "local_hiring_cost", "marketing_localization_cost", "year_3_revenue_forecast", "year_3_support_cost"],
    outputUnit: "Percentage ROI",
    exampleCalculation: "($2.1M - $1.8M) / $1.8M x 100 = 17% ROI by year 3"
  },
  "VS-VF013": {
    id: "VS-VF013",
    name: "AI Liability Risk Exposure in Regulated Vertical",
    formulaExpression: "(Decisions x Error_Rate x Liability_Per_Error) + (Fine_Probability x Fine_Amount) + Premium_Increase",
    requiredInputs: ["ai_decisions_annual", "ai_error_rate", "avg_liability_per_error", "fine_probability", "avg_fine_amount", "premium_increase"],
    outputUnit: "USD per year",
    exampleCalculation: "(2.5M x 0.8% x $12,500) + (0.15 x $450K) + $85K = $3,217,500/year"
  },
  "VS-VF014": {
    id: "VS-VF014",
    name: "Vertical Customer Concentration Risk Value",
    formulaExpression: "(Top_10_Revenue x Merger_Probability) + (Top_10_Revenue x Consolidation_Discount)",
    requiredInputs: ["top_10_revenue", "merger_probability", "bankruptcy_probability", "consolidated_price_discount", "replacement_cost_per_customer"],
    outputUnit: "USD at risk",
    exampleCalculation: "($4.2M x 0.25) + ($4.2M x 0.15) = $1,680,000 at-risk"
  },
  "VS-VF015": {
    id: "VS-VF015",
    name: "Vertical Platform Extensibility Revenue Uplift",
    formulaExpression: "(API_Revenue + Marketplace_Revenue + Dev_Seat_Revenue) - (Eng_Cost + DevRel_Cost + API_Infra_Cost)",
    requiredInputs: ["api_call_revenue", "marketplace_take_rate_revenue", "developer_seat_revenue", "platform_eng_cost", "dev_rel_cost", "api_infra_cost"],
    outputUnit: "USD per year",
    exampleCalculation: "($180K + $95K + $120K) - ($240K + $85K + $65K) = $5,000/year (early stage)"
  },
};

// ============================================================
// BUYING TRIGGERS REGISTRY
// ============================================================

const BUYING_TRIGGERS: Record<string, BuyingTrigger> = {
  "VS-BT001": { id: "VS-BT001", name: "Vertical Regulatory Deadline Looming", triggerEvent: "New industry regulation with 12-18 month enforcement deadline", urgencyLevel: "HIGH", typicalTiming: "6-12 months before enforcement", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "GovTech", "EdTech", "InsurTech", "ConstructionTech"], linkedPains: ["VS-P002", "VS-P010"] },
  "VS-BT002": { id: "VS-BT002", name: "Legacy System End-of-Life or Vendor Acquisition", triggerEvent: "Core legacy system vendor announces EOL, price increase, or acquisition", urgencyLevel: "HIGH", typicalTiming: "12-24 months before EOL", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "InsurTech", "LogisticsTech", "Manufacturing SaaS"], linkedPains: ["VS-P005", "VS-P001"] },
  "VS-BT003": { id: "VS-BT003", name: "Vertical Industry Association Technology Mandate", triggerEvent: "Industry association endorses or mandates specific technology standard", urgencyLevel: "MEDIUM", typicalTiming: "3-6 months post-mandate", affectedVerticals: ["Healthcare SaaS", "LegalTech", "ConstructionTech", "AgTech", "InsurTech"], linkedPains: ["VS-P001", "VS-P016"] },
  "VS-BT004": { id: "VS-BT004", name: "Horizontal Platform Vertical Module Launch", triggerEvent: "Salesforce, Microsoft, SAP launches vertical-specific module", urgencyLevel: "MEDIUM", typicalTiming: "6-12 months post-announcement", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "LegalTech", "RetailTech", "ConstructionTech"], linkedPains: ["VS-P020", "VS-P006", "VS-P001"] },
  "VS-BT005": { id: "VS-BT005", name: "Vertical Private Equity Roll-Up in Customer Base", triggerEvent: "PE firm acquires 3+ customers in same vertical", urgencyLevel: "HIGH", typicalTiming: "3-9 months post-PE platform formation", affectedVerticals: ["RestaurantTech", "AgTech", "RetailTech", "ConstructionTech", "LegalTech", "Healthcare SaaS"], linkedPains: ["VS-P020", "VS-P008"] },
  "VS-BT006": { id: "VS-BT006", name: "Seasonal Peak Preparation Window", triggerEvent: "3-4 months before seasonal peak", urgencyLevel: "HIGH", typicalTiming: "Pre-peak operational period", affectedVerticals: ["AgTech", "ConstructionTech", "RetailTech", "RestaurantTech", "EnergyTech", "Fintech SaaS"], linkedPains: ["VS-P007", "VS-P011"] },
  "VS-BT007": { id: "VS-BT007", name: "Cybersecurity Incident in Vertical Peer", triggerEvent: "Ransomware, breach, or OCR action against peer in same vertical", urgencyLevel: "HIGH", typicalTiming: "1-3 months post-incident", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "GovTech", "EdTech", "LegalTech"], linkedPains: ["VS-P002", "VS-P003", "VS-P007"] },
  "VS-BT008": { id: "VS-BT008", name: "Government Budget Cycle Approval", triggerEvent: "Budget approved with specific line item for vertical IT modernization", urgencyLevel: "HIGH", typicalTiming: "Q1-Q2 for fiscal year; 3-6 months post-stimulus", affectedVerticals: ["GovTech", "EdTech", "Healthcare SaaS", "EnergyTech"], linkedPains: ["VS-P010", "VS-P002"] },
  "VS-BT009": { id: "VS-BT009", name: "IoT/Connected Device Mandate Effective Date", triggerEvent: "ELD mandate expansion, smart meter requirements, food safety IoT rules", urgencyLevel: "HIGH", typicalTiming: "3-6 months before mandate effective date", affectedVerticals: ["LogisticsTech", "EnergyTech", "RestaurantTech", "Manufacturing SaaS", "Healthcare SaaS"], linkedPains: ["VS-P019", "VS-P005", "VS-P011"] },
  "VS-BT010": { id: "VS-BT010", name: "Vertical SaaS Funding or IPO Announcement", triggerEvent: "Competitor or peer announces Series C+, IPO, or major partnership", urgencyLevel: "MEDIUM", typicalTiming: "3-6 months post-announcement", affectedVerticals: ["All Vertical SaaS"], linkedPains: ["VS-P015", "VS-P020"] },
  "VS-BT011": { id: "VS-BT011", name: "Customer Expansion into New Geography", triggerEvent: "Customer opens locations in new state or country requiring localization", urgencyLevel: "MEDIUM", typicalTiming: "2-4 months before go-live", affectedVerticals: ["RetailTech", "RestaurantTech", "Healthcare SaaS", "Fintech SaaS", "LogisticsTech"], linkedPains: ["VS-P013", "VS-P002"] },
  "VS-BT012": { id: "VS-BT012", name: "AI Regulation or Guidance Publication", triggerEvent: "FDA AI/ML guidance, EU AI Act, NAIC AI bulletin", urgencyLevel: "MEDIUM", typicalTiming: "6-18 months before enforcement", affectedVerticals: ["Healthcare SaaS", "LegalTech", "Fintech SaaS", "InsurTech"], linkedPains: ["VS-P014", "VS-P002"] },
  "VS-BT013": { id: "VS-BT013", name: "Post-Merger Technology Consolidation", triggerEvent: "Customer acquired or merged; parent mandates tech standardization", urgencyLevel: "HIGH", typicalTiming: "6-12 months post-merger", affectedVerticals: ["Healthcare SaaS", "LegalTech", "RetailTech", "ConstructionTech", "InsurTech"], linkedPains: ["VS-P020", "VS-P001"] },
  "VS-BT014": { id: "VS-BT014", name: "Vertical Data Interoperability Mandate", triggerEvent: "CMS TEFCA, open banking, real estate data sharing, supply chain traceability", urgencyLevel: "HIGH", typicalTiming: "6-12 months before mandatory effective date", affectedVerticals: ["Healthcare SaaS", "Fintech SaaS", "PropTech", "LogisticsTech", "Manufacturing SaaS"], linkedPains: ["VS-P005", "VS-P016"] },
  "VS-BT015": { id: "VS-BT015", name: "New Vertical Market Entry by Customer", triggerEvent: "Existing customer expands into your target vertical", urgencyLevel: "MEDIUM", typicalTiming: "6-12 months before vertical launch", affectedVerticals: ["Healthcare SaaS", "InsurTech", "Fintech SaaS", "RetailTech"], linkedPains: ["VS-P002", "VS-P001", "VS-P005"] },
};

// ============================================================
// EXECUTABLE EXAMPLES
// ============================================================

/**
 * Example 1: Evaluate a signal against a target vertical
 */
function evaluateSignal(
  signalId: string,
  targetVertical: string,
  confirmationSignals: string[]
): { active: boolean; confidence: number; linkedPains: string[] } {
  const rule = SIGNAL_RULES[signalId];
  if (!rule) return { active: false, confidence: 0, linkedPains: [] };

  // Check if signal applies to target vertical via linked pains
  const applicablePains = rule.linkedPains.filter(
    painId => VERTICAL_PAINS[painId]?.affectedVerticals.includes(targetVertical)
  );

  if (applicablePains.length === 0) {
    return { active: false, confidence: 0, linkedPains: [] };
  }

  // Boost confidence if confirmation signals present
  const confirmationMatch = confirmationSignals.filter(cs =>
    rule.requiredConfirmationSignals.some(rs => cs.toLowerCase().includes(rs.toLowerCase()))
  ).length;
  const confidenceBoost = confirmationMatch > 0 ? 0.1 : 0;
  const finalConfidence = Math.min(rule.confidenceScore + confidenceBoost, 0.95);

  return {
    active: true,
    confidence: finalConfidence,
    linkedPains: applicablePains
  };
}

/**
 * Example 2: Calculate workflow gap cost (VS-VF001)
 */
function calculateWorkflowGapCost(inputs: {
  hoursWorkaroundPerUserMonth: number;
  loadedCostPerHour: number;
  usersAffected: number;
  integrationDevCost: number;
  amortizationMonths: number;
  delayedFeatureRevenue: number;
}): number {
  const monthlyWorkaroundCost = inputs.hoursWorkaroundPerUserMonth * inputs.loadedCostPerHour * inputs.usersAffected;
  const monthlyAmortization = inputs.integrationDevCost / inputs.amortizationMonths;
  return monthlyWorkaroundCost + monthlyAmortization + inputs.delayedFeatureRevenue;
}

/**
 * Example 3: Calculate compliance delay cost (VS-VF002)
 */
function calculateComplianceDelayCost(inputs: {
  dealsBlocked: number;
  averageACV: number;
  auditRemediationCost: number;
  legalReviewHours: number;
  attorneyRate: number;
  delayedMarketNPV: number;
}): number {
  return (inputs.dealsBlocked * inputs.averageACV)
    + inputs.auditRemediationCost
    + (inputs.legalReviewHours * inputs.attorneyRate)
    + inputs.delayedMarketNPV;
}

/**
 * Example 4: Calculate embedded payments margin (VS-VF008)
 */
function calculatePaymentsMargin(inputs: {
  totalVolume: number;
  takeRate: number;
  processorFeeRate: number;
  annualComplianceCost: number;
  fraudLossRate: number;
  chargebackRate: number;
}): number {
  const revenue = inputs.totalVolume * inputs.takeRate;
  const processorFees = inputs.totalVolume * inputs.processorFeeRate;
  const fraudLosses = inputs.totalVolume * inputs.fraudLossRate;
  const chargebackCost = inputs.totalVolume * inputs.chargebackRate;
  return revenue - (processorFees + inputs.annualComplianceCost + fraudLosses + chargebackCost);
}

/**
 * Example 5: Check if buying trigger is active for a vertical
 */
function isBuyingTriggerActive(
  triggerId: string,
  targetVertical: string,
  daysUntilEvent: number
): { active: boolean; urgency: string; daysToAct: number } {
  const trigger = BUYING_TRIGGERS[triggerId];
  if (!trigger) return { active: false, urgency: "LOW", daysToAct: 0 };

  if (!trigger.affectedVerticals.includes(targetVertical) && !trigger.affectedVerticals.includes("All Vertical SaaS")) {
    return { active: false, urgency: "LOW", daysToAct: 0 };
  }

  // Parse typical timing
  const timingMap: Record<string, number> = {
    "6-12 months before enforcement": 270,
    "12-24 months before EOL": 540,
    "3-6 months post-mandate": 135,
    "6-12 months post-announcement": 270,
    "3-9 months post-PE platform formation": 180,
    "Pre-peak operational period": 120,
    "1-3 months post-incident": 60,
    "Q1-Q2 for fiscal year; 3-6 months post-stimulus": 135,
    "3-6 months before mandate effective date": 135,
    "3-6 months post-announcement": 135,
    "2-4 months before go-live": 90,
    "6-18 months before enforcement": 360,
    "6-12 months post-merger": 270,
    "6-12 months before mandatory effective date": 270,
    "6-12 months before vertical launch": 270,
  };

  const daysToAct = timingMap[trigger.typicalTiming] || 180;
  const isActive = daysUntilEvent <= daysToAct;

  return {
    active: isActive,
    urgency: trigger.urgencyLevel,
    daysToAct: Math.max(0, daysToAct - daysUntilEvent)
  };
}

/**
 * Example 6: Find all applicable pains for a vertical
 */
function getPainsForVertical(vertical: string): VerticalPain[] {
  return Object.values(VERTICAL_PAINS).filter(p => p.affectedVerticals.includes(vertical));
}

/**
 * Example 7: Calculate seasonality impact (VS-VF007)
 */
function calculateSeasonalityCost(inputs: {
  peakQuarterRevenue: number;
  troughQuarterRevenue: number;
  financingRate: number;
  offSeasonExcessBurn: number;
  seasonalTurnoverCost: number;
}): number {
  const revenueGapCost = (inputs.peakQuarterRevenue - inputs.troughQuarterRevenue) * inputs.financingRate;
  const burnGap = inputs.offSeasonExcessBurn - inputs.troughQuarterRevenue;
  return revenueGapCost + burnGap + inputs.seasonalTurnoverCost;
}

/**
 * Example 8: Find high-confidence signals for a vertical
 */
function getHighConfidenceSignals(vertical: string, minConfidence = 0.80): SignalRule[] {
  return Object.values(SIGNAL_RULES).filter(rule => {
    const applicable = rule.linkedPains.some(painId =>
      VERTICAL_PAINS[painId]?.affectedVerticals.includes(vertical)
    );
    return applicable && rule.confidenceScore >= minConfidence;
  });
}

// ============================================================
// EXPORT
// ============================================================

export {
  VERTICAL_PAINS,
  VERTICAL_KPIS,
  SIGNAL_RULES,
  VALUE_FORMULAS,
  BUYING_TRIGGERS,
  evaluateSignal,
  calculateWorkflowGapCost,
  calculateComplianceDelayCost,
  calculatePaymentsMargin,
  isBuyingTriggerActive,
  getPainsForVertical,
  calculateSeasonalityCost,
  getHighConfidenceSignals,
};

export type {
  VerticalPain,
  VerticalKPI,
  SignalRule,
  ValueFormula,
  BuyingTrigger,
};
