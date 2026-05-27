/**
 * SaaS Master ValuePack — Signal-to-Hypothesis Worked Examples
 * 
 * 3 complete TypeScript examples demonstrating:
 *   raw signal → interpreted signal → relevant pains → affected personas →
 *   KPIs impacted → value hypothesis → confidence → evidence needed → discovery questions
 * 
 * @version 1.0.0
 * @domain saas-master-v1
 */

// ============================================================================
// TYPE DEFINITIONS (for conceptual compilation)
// ============================================================================

type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";
type UrgencyLevel = "HIGH" | "MEDIUM" | "LOW";
type ValueDriverCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";
type Prevalence = "HIGH" | "MEDIUM" | "LOW";

interface Signal {
  id: string;
  source: string;
  rawData: string;
  timestamp: string;
  confidence: number; // 0.0 - 1.0
}

interface InterpretedSignal {
  signalId: string;
  signalName: string;
  interpretedMeaning: string;
  confidence: number;
  requiredConfirmations: string[];
}

interface PainRelevance {
  painId: string;
  painName: string;
  relevanceScore: number; // 0.0 - 1.0
  reasoning: string;
}

interface PersonaImpact {
  personaId: string;
  personaName: string;
  impactLevel: "HIGH" | "MEDIUM" | "LOW";
  estimatedBudgetAuthority: string;
}

interface KPIImpact {
  kpiId: string;
  kpiName: string;
  currentEstimate: string;
  benchmarkGap: string;
  financialImpact: string;
}

interface ValueHypothesis {
  hypothesisId: string;
  statement: string;
  valueCategory: ValueDriverCategory;
  quantifiedValueRange: string;
  paybackPeriodEstimate: string;
  confidence: ConfidenceLevel;
  confidenceRationale: string;
}

interface EvidenceRequirement {
  evidenceType: string;
  source: string;
  priority: "CRITICAL" | "IMPORTANT" | "NICE_TO_HAVE";
  howToObtain: string;
}

interface DiscoveryQuestion {
  questionId: string;
  question: string;
  targetPersona: string;
  purpose: string;
  followUpIfYes: string;
  followUpIfNo: string;
}

interface SignalToHypothesisChain {
  chainId: string;
  title: string;
  rawSignal: Signal;
  interpretedSignal: InterpretedSignal;
  relevantPains: PainRelevance[];
  affectedPersonas: PersonaImpact[];
  kpiImpacts: KPIImpact[];
  valueHypothesis: ValueHypothesis;
  evidenceNeeded: EvidenceRequirement[];
  discoveryQuestions: DiscoveryQuestion[];
}

// ============================================================================
// EXAMPLE 1: Job Posting Surge + Earnings Call Churn Mention
// Horizontal SaaS Growth Stage Company
// ============================================================================

const example1: SignalToHypothesisChain = {
  chainId: "CHAIN-001",
  title: "Growth-Stage SaaS Facing NRR Compression and Sales Scaling Challenge",

  rawSignal: {
    id: "SIG-2026-04-001",
    source: "LinkedIn Jobs + Seeking Alpha Earnings Transcript",
    rawData: "SaaS company (Series C, $45M ARR) posted 6 sales roles and 3 customer success roles in 30 days. Earnings call Q1 2026 transcript contains 8 mentions of 'retention', 'churn', and 'logo attrition' in prepared remarks and Q&A.",
    timestamp: "2026-04-15",
    confidence: 0.85
  },

  interpretedSignal: {
    signalId: "SR001+SR006",
    signalName: "Job Posting Surge in Sales/CS + Earnings Call Churn Mention",
    interpretedMeaning: "Company is aggressively scaling GTM while simultaneously acknowledging retention challenges to investors. This pattern strongly suggests NRR compression is a board-level concern and the company is attempting to outgrow churn through new logo acquisition—a unit-economically risky strategy.",
    confidence: 0.82,
    requiredConfirmations: [
      "NRR disclosed in earnings or benchmark data",
      "Sales team quota attainment trend",
      "Customer success team creation or expansion timing"
    ]
  },

  relevantPains: [
    {
      painId: "P002",
      painName: "Net Revenue Retention (NRR) Compression",
      relevanceScore: 0.95,
      reasoning: "Earnings call retention mentions at this frequency indicate board-level concern. Job postings in CS confirm reactive investment in retention infrastructure."
    },
    {
      painId: "P001",
      painName: "High Customer Acquisition Cost (CAC) Escalation",
      relevanceScore: 0.75,
      reasoning: "Scaling sales team rapidly often precedes or coincides with CAC pressure, especially when retention is weak (leaky bucket requires more filling)."
    },
    {
      painId: "P023",
      painName: "Customer Success Proactive Engagement Deficit",
      relevanceScore: 0.80,
      reasoning: "3 CS roles in 30 days suggests either team creation or rapid expansion, implying existing CS capacity insufficient for proactive engagement."
    },
    {
      painId: "P003",
      painName: "Prolonged Sales Cycles",
      relevanceScore: 0.60,
      reasoning: "6 sales roles may indicate cycle lengthening requiring more capacity, but less direct than other pains."
    }
  ],

  affectedPersonas: [
    {
      personaId: "PER002",
      personaName: "Chief Revenue Officer (CRO)",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$500K-$2M annual for GTM tools"
    },
    {
      personaId: "PER004",
      personaName: "Chief Customer Officer / VP Customer Success",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$200K-$800K annual for CS platforms"
    },
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "Board-level; influences all departmental budgets"
    },
    {
      personaId: "PER005",
      personaName: "VP Revenue Operations (RevOps)",
      impactLevel: "MEDIUM",
      estimatedBudgetAuthority: "$100K-$300K for data/analytics tools"
    }
  ],

  kpiImpacts: [
    {
      kpiId: "K005",
      kpiName: "Net Revenue Retention (NRR)",
      currentEstimate: "90-100% (estimated from churn mentions)",
      benchmarkGap: "Below median 101-102%; 15+ points below top quartile 116%",
      financialImpact: "At $45M ARR, every 1% NRR improvement = $450K incremental ARR; 10-point improvement = $4.5M ARR = ~$27M-$45M valuation uplift at 6-10x multiple"
    },
    {
      kpiId: "K001",
      kpiName: "Customer Acquisition Cost (CAC)",
      currentEstimate: "$25K-$40K (estimated for mid-market SaaS at this stage)",
      benchmarkGap: "May be approaching or exceeding sustainable thresholds",
      financialImpact: "If CAC payback extends from 15 to 24 months, cash flow strain increases; may require bridge financing or valuation compression"
    },
    {
      kpiId: "K008",
      kpiName: "Logo Churn Rate (Monthly)",
      currentEstimate: "2.5-4% monthly (estimated from context)",
      benchmarkGap: "2-4x above enterprise target of <1%",
      financialImpact: "At 3% monthly churn, annual retention is only 69%; customer base nearly halves every 2 years without new logos"
    }
  ],

  valueHypothesis: {
    hypothesisId: "VH-001",
    statement: "By implementing a unified customer success platform with predictive health scoring, automated playbooks, and expansion pipeline management, this SaaS company can improve NRR from ~95% to 110% within 18 months while reducing CAC payback through better expansion-led growth.",
    valueCategory: "Revenue Uplift",
    quantifiedValueRange: "$6.75M-$11.25M incremental ARR over 3 years ($45M base × 15% NRR improvement × 3 years at 75% margin)",
    paybackPeriodEstimate: "6-12 months (software cost typically <10% of value created)",
    confidence: "HIGH",
    confidenceRationale: "NRR improvement is well-documented lever with strong benchmark data (High Alpha, Bessemer). Customer success platform ROI is established category with proven case studies. Primary uncertainty is execution quality and change management."
  },

  evidenceNeeded: [
    {
      evidenceType: "Current NRR and GRR metrics",
      source: "Earnings call, board deck, or direct disclosure",
      priority: "CRITICAL",
      howToObtain: "Review latest earnings transcript; ask directly in discovery call with CRO/CFO"
    },
    {
      evidenceType: "Churn reason breakdown",
      source: "Customer success team or exit interview data",
      priority: "CRITICAL",
      howToObtain: "Discovery question: 'What are the top 3 reasons customers give for leaving?'"
    },
    {
      evidenceType: "CS team time allocation",
      source: "Internal time tracking or survey",
      priority: "IMPORTANT",
      howToObtain: "Discovery question: 'What percentage of CS team time is reactive vs. proactive?'"
    },
    {
      evidenceType: "Expansion ARR history",
      source: "Finance/CRM data",
      priority: "IMPORTANT",
      howToObtain: "Discovery question: 'How much of your quarterly new ARR comes from existing customers vs. new logos?'"
    },
    {
      evidenceType: "Current CS tooling stack",
      source: "IT/CS leadership",
      priority: "NICE_TO_HAVE",
      howToObtain: "Discovery question: 'What tools does CS currently use for health scoring, QBRs, and expansion tracking?'"
    }
  ],

  discoveryQuestions: [
    {
      questionId: "DQ-001-1",
      question: "Your team has been expanding sales and CS capacity. What's driving that investment—customer base growth, or are you working to address retention challenges?",
      targetPersona: "CRO",
      purpose: "Validate NRR vs. growth hypothesis; determine if hiring is proactive or reactive",
      followUpIfYes: "What's your current NRR target, and how far are you from it?",
      followUpIfNo: "What metrics are you using to determine the right CS coverage ratio?"
    },
    {
      questionId: "DQ-001-2",
      question: "On your last earnings call, retention came up several times. What's the board's view on your current NRR trajectory?",
      targetPersona: "CFO",
      purpose: "Gauge board pressure and timeline urgency",
      followUpIfYes: "What initiatives are you running to address it, and what's the timeline?",
      followUpIfNo: "How do you report NRR to the board, and how frequently?"
    },
    {
      questionId: "DQ-001-3",
      question: "If you could wave a wand and have perfect visibility into every customer's health and expansion likelihood, what would you do differently in Q3?",
      targetPersona: "Chief Customer Officer",
      purpose: "Surface latent demand for CS intelligence and expansion pipeline visibility",
      followUpIfYes: "What's preventing you from having that visibility today?",
      followUpIfNo: "How do you currently prioritize which accounts to focus on for QBRs?"
    }
  ]
};

// ============================================================================
// EXAMPLE 2: Cloud Cost Budget Breach + DORA Metrics Below Elite
// Infrastructure and Platform SaaS Company
// ============================================================================

const example2: SignalToHypothesisChain = {
  chainId: "CHAIN-002",
  title: "Infrastructure SaaS Facing Cloud Cost Crisis and Engineering Velocity Bottleneck",

  rawSignal: {
    id: "SIG-2026-04-002",
    source: "Cloud billing dashboard alert + Glassdoor engineering reviews + Company tech blog",
    rawData: "Infrastructure SaaS ($80M ARR) breached cloud budget by 35% in Q1. Glassdoor reviews mention 'technical debt', 'slow releases', and 'firefighting culture'. Engineering blog post discusses 'scaling challenges with Kubernetes'.",
    timestamp: "2026-04-20",
    confidence: 0.80
  },

  interpretedSignal: {
    signalId: "SR013+SR019+SR020",
    signalName: "Cloud Cost Breach + Engineering Culture Signals + Scaling Content",
    interpretedMeaning: "Engineering organization under dual pressure: infrastructure costs unsustainable and development velocity constrained by technical debt and operational burden. Company is publicly acknowledging scaling challenges, indicating internal recognition and potential budget availability for solutions.",
    confidence: 0.78,
    requiredConfirmations: [
      "Cloud spend vs. revenue trend over 4 quarters",
      "Engineering team DORA metrics or equivalent",
      "Kubernetes cluster count and team structure"
    ]
  },

  relevantPains: [
    {
      painId: "P007",
      painName: "Cloud Cost Overrun and Waste",
      relevanceScore: 0.95,
      reasoning: "35% budget breach is acute financial crisis. Immediate action required. FinOps or cloud optimization tools are high-probability procurement."
    },
    {
      painId: "P006",
      painName: "Engineering Velocity Bottlenecks",
      relevanceScore: 0.85,
      reasoning: "Glassdoor + blog signals confirm velocity issues. Technical debt and firefighting culture are classic DORA 'low performer' symptoms."
    },
    {
      painId: "P020",
      painName: "Multi-Cloud and Kubernetes Complexity",
      relevanceScore: 0.80,
      reasoning: "Blog explicitly mentions Kubernetes scaling challenges. Likely cluster sprawl and governance gaps."
    },
    {
      painId: "P014",
      painName: "Gross Margin Compression",
      relevanceScore: 0.70,
      reasoning: "Cloud costs directly impact COGS. At $80M ARR, 35% cloud overrun could compress margin by 5-8 points."
    }
  ],

  affectedPersonas: [
    {
      personaId: "PER003",
      personaName: "Chief Technology Officer (CTO)",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$1M-$3M for infrastructure optimization"
    },
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "Board-level; cloud spend is material P&L item"
    },
    {
      personaId: "PER013",
      personaName: "VP DevOps / Platform Engineering Lead",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$200K-$1M for tooling and automation"
    },
    {
      personaId: "PER007",
      personaName: "VP Engineering / Head of Engineering",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$100K-$500K for developer productivity tools"
    }
  ],

  kpiImpacts: [
    {
      kpiId: "K023",
      kpiName: "Cloud Cost as % of Revenue",
      currentEstimate: "25-30% (from 35% breach on growing revenue)",
      benchmarkGap: "5-15 points above efficient SaaS target of <15%",
      financialImpact: "At $80M ARR, reducing cloud from 25% to 15% of revenue frees $8M annually—directly improving EBITDA and valuation multiple"
    },
    {
      kpiId: "K019",
      kpiName: "Deployment Frequency",
      currentEstimate: "<1 per week (estimated from 'slow releases')",
      benchmarkGap: "Elite performers deploy >1/day; 7x+ frequency gap",
      financialImpact: "Slower deployment = delayed features, competitive disadvantage, and higher cost of change. Est. 20-30% productivity loss."
    },
    {
      kpiId: "K025",
      kpiName: "Resource Utilization Rate",
      currentEstimate: "30-50% (typical for companies without FinOps)",
      benchmarkGap: "20-30 points below efficient threshold of 60%+",
      financialImpact: "Industry benchmark: 25-35% of cloud spend is waste. At $20M cloud spend, $5M-$7M annually is potentially recoverable."
    },
    {
      kpiId: "K064",
      kpiName: "Kubernetes Cluster Sprawl Index",
      currentEstimate: "4-8 clusters per team",
      benchmarkGap: "2-4x above managed threshold of 1-2 per team",
      financialImpact: "Each cluster carries management overhead, security surface area, and cost. Consolidation reduces ops burden 30-50%."
    }
  ],

  valueHypothesis: {
    hypothesisId: "VH-002",
    statement: "By implementing a unified FinOps platform with automated cost optimization, rightsizing, and tagging governance, combined with a platform engineering self-service layer for Kubernetes and CI/CD, this company can reduce cloud waste by 40-60% while doubling deployment frequency and halving incident MTTR.",
    valueCategory: "Cost Savings",
    quantifiedValueRange: "$3M-$5M annual cloud savings + $2M-$4M equivalent engineering capacity value = $5M-$9M total annual value",
    paybackPeriodEstimate: "3-6 months (cloud savings are immediate; platform productivity gains in 6-12 months)",
    confidence: "HIGH",
    confidenceRationale: "Cloud waste reduction is well-quantified (FinOps Foundation: 25-35% waste typical). Platform engineering ROI is established (DORA research: elite performers deploy 973x more frequently). Combined solution addresses both acute cost crisis and chronic velocity problem."
  },

  evidenceNeeded: [
    {
      evidenceType: "Cloud spend breakdown by service and team",
      source: "AWS/Azure/GCP billing console or FinOps tool",
      priority: "CRITICAL",
      howToObtain: "Discovery question: 'What's your monthly cloud spend, and how is it allocated by service and team?'"
    },
    {
      evidenceType: "Current DORA metrics or equivalent engineering KPIs",
      source: "Engineering leadership or internal dashboards",
      priority: "CRITICAL",
      howToObtain: "Discovery question: 'How often do you deploy, and what's your mean time to recovery?'"
    },
    {
      evidenceType: "Kubernetes cluster inventory and utilization",
      source: "Platform team or cloud console",
      priority: "IMPORTANT",
      howToObtain: "Discovery question: 'How many Kubernetes clusters do you run, and how do you track their utilization?'"
    },
    {
      evidenceType: "Engineering time allocation survey",
      source: "Engineering management or HR/People team",
      priority: "IMPORTANT",
      howToObtain: "Discovery question: 'What percentage of engineering time goes to maintenance vs. new features?'"
    },
    {
      evidenceType: "Current tooling stack and integration gaps",
      source: "Platform engineering or DevOps team",
      priority: "NICE_TO_HAVE",
      howToObtain: "Discovery question: 'What tools do you currently use for cost monitoring, deployment automation, and incident management?'"
    }
  ],

  discoveryQuestions: [
    {
      questionId: "DQ-002-1",
      question: "I noticed your cloud spend has been growing faster than revenue. What percentage of your cloud bill would you estimate is going to idle or underutilized resources?",
      targetPersona: "CTO",
      purpose: "Quantify waste awareness and FinOps maturity",
      followUpIfYes: "What's your process for right-sizing instances and managing reserved capacity?",
      followUpIfNo: "How do you currently allocate cloud costs back to engineering teams?"
    },
    {
      questionId: "DQ-002-2",
      question: "Your engineering blog mentioned Kubernetes scaling challenges. How many clusters are you managing today, and how much platform engineering time goes to cluster maintenance?",
      targetPersona: "VP DevOps / Platform Lead",
      purpose: "Quantify Kubernetes sprawl and platform team bottleneck",
      followUpIfYes: "What's your target state for platform self-service?",
      followUpIfNo: "How do engineering teams request new infrastructure today?"
    },
    {
      questionId: "DQ-002-3",
      question: "If you could free up 20% of your engineering team's time from maintenance and ops, what would you reallocate that capacity toward?",
      targetPersona: "CTO",
      purpose: "Surface strategic opportunity cost of current technical debt",
      followUpIfYes: "What's the business value of delivering those initiatives 3-6 months earlier?",
      followUpIfNo: "How do you currently measure engineering productivity and ROI?"
    }
  ]
};

// ============================================================================
// EXAMPLE 3: New CRO Hire + PLG-to-Enterprise Conversion Gap
// AI-Native SaaS Company
// ============================================================================

const example3: SignalToHypothesisChain = {
  chainId: "CHAIN-003",
  title: "AI-Native SaaS with New CRO Mandated to Build Enterprise Motion from PLG Base",

  rawSignal: {
    id: "SIG-2026-04-003",
    source: "LinkedIn + Company Blog + G2 Reviews",
    rawData: "AI-Native SaaS ($25M ARR, 90% PLG revenue) hired new CRO from enterprise SaaS background (ex-Salesforce). G2 reviews mention 'missing enterprise features' including SSO, audit logs, and admin controls. Blog announces 'enterprise-ready' initiative.",
    timestamp: "2026-04-18",
    confidence: 0.88
  },

  interpretedSignal: {
    signalId: "BT002+SR012+P012",
    signalName: "New CRO Hire from Enterprise + PLG Feature Gap Signals",
    interpretedMeaning: "Company at critical PLG-to-enterprise transition inflection point. New CRO has explicit mandate to build enterprise sales motion. Product currently lacks enterprise table stakes (SSO, audit, admin). High probability of enterprise GTM stack procurement, product security upgrades, and sales methodology implementation.",
    confidence: 0.90,
    requiredConfirmations: [
      "Enterprise revenue target communicated internally",
      "Product roadmap for enterprise features",
      "Sales team creation timeline"
    ]
  },

  relevantPains: [
    {
      painId: "P012",
      painName: "Product-Led Growth (PLG) to Enterprise Transition Friction",
      relevanceScore: 0.98,
      reasoning: "Perfect signal match: 90% PLG revenue + enterprise feature gaps + new CRO hire. This is the defining strategic challenge."
    },
    {
      painId: "P009",
      painName: "Compliance and Security Audit Fatigue",
      relevanceScore: 0.85,
      reasoning: "Enterprise deals require SOC 2, SSO, audit logs. G2 reviews confirm these are missing. Each enterprise prospect triggers security review bottleneck."
    },
    {
      painId: "P003",
      painName: "Prolonged Sales Cycles",
      relevanceScore: 0.75,
      reasoning: "New enterprise motion without proper tooling or methodology will experience elongated cycles. First enterprise deals typically 2-3x longer than planned."
    },
    {
      painId: "P021",
      painName: "Lead Quality and ICP Misalignment",
      relevanceScore: 0.70,
      reasoning: "PLG user base is not the same as enterprise buyer. New CRO must define and operationalize enterprise ICP."
    }
  ],

  affectedPersonas: [
    {
      personaId: "PER002",
      personaName: "Chief Revenue Officer (CRO)",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$500K-$1.5M for GTM stack and enablement"
    },
    {
      personaId: "PER012",
      personaName: "VP Product / Chief Product Officer",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$200K-$800K for security/compliance features"
    },
    {
      personaId: "PER003",
      personaName: "Chief Technology Officer (CTO)",
      impactLevel: "HIGH",
      estimatedBudgetAuthority: "$100K-$500K for SSO, audit logging, infrastructure"
    },
    {
      personaId: "PER001",
      personaName: "Chief Financial Officer (CFO)",
      impactLevel: "MEDIUM",
      estimatedBudgetAuthority: "Monitors CAC and unit economics of new enterprise motion"
    }
  ],

  kpiImpacts: [
    {
      kpiId: "K039",
      kpiName: "PLG-to-Enterprise Conversion Rate",
      currentEstimate: "2-5% (typical for PLG-native companies without enterprise motion)",
      benchmarkGap: "10+ points below good performance of >15%",
      financialImpact: "At 100K PLG users, improving conversion from 3% to 15% with $30K ACV = $360M potential pipeline. Even 5% capture = $120M."
    },
    {
      kpiId: "K041",
      kpiName: "Product-Led Conversion Rate",
      currentEstimate: "3-5%",
      benchmarkGap: "Below PLG benchmark of 3-8%",
      financialImpact: "Low free-to-paid conversion limits monetization of top-of-funnel investment"
    },
    {
      kpiId: "K030",
      kpiName: "Security Review Completion Time",
      currentEstimate: "30-60 days (due to missing documentation/features)",
      benchmarkGap: "3-10x above fast standard of <5 days",
      financialImpact: "Each 30-day delay increases no-decision risk and competitive exposure. At 20 enterprise evaluations/year, 25 days saved = 500 days of accelerated revenue."
    },
    {
      kpiId: "K040",
      kpiName: "Average Revenue Per Account (ARPA)",
      currentEstimate: "$500-$2,000 (PLG typical)",
      benchmarkGap: "10-50x below enterprise target of >$10K",
      financialImpact: "Enterprise ARPA of $30K with 100 customers = $3M ARR. Same effort in PLG requires 1,500 customers at $2K."
    }
  ],

  valueHypothesis: {
    hypothesisId: "VH-003",
    statement: "By implementing enterprise-grade security and compliance automation (SSO, audit logs, SOC 2 readiness) combined with a sales engagement and revenue intelligence platform, this AI-Native SaaS can reduce enterprise sales cycle from 150+ days to 60-90 days and increase enterprise deal velocity 3-5x within 12 months.",
    valueCategory: "Revenue Uplift",
    quantifiedValueRange: "$5M-$15M incremental enterprise ARR within 18 months (100-200 enterprise customers at $25K-$75K ACV)",
    paybackPeriodEstimate: "6-9 months (enterprise deals have higher upfront value; security investment unlocks entire segment)",
    confidence: "MEDIUM",
    confidenceRationale: "New CRO has track record but company is early in enterprise transition. PLG-to-enterprise motion is well-documented but execution risk is real (OpenView data: only 20-30% of PLG companies successfully add enterprise motion). Product gaps are confirmed (G2 reviews) but remediation timeline uncertain."
  },

  evidenceNeeded: [
    {
      evidenceType: "Enterprise revenue target and timeline",
      source: "CRO or CEO strategic plan",
      priority: "CRITICAL",
      howToObtain: "Discovery question: 'What's your enterprise revenue target for next year, and how many enterprise customers do you need to get there?'"
    },
    {
      evidenceType: "Product roadmap for enterprise features",
      source: "VP Product or product roadmap documentation",
      priority: "CRITICAL",
      howToObtain: "Discovery question: 'What's on your roadmap to make the product enterprise-ready, and when will SSO and audit logs be available?'"
    },
    {
      evidenceType: "Current enterprise evaluation pipeline",
      source: "CRM or sales leadership",
      priority: "IMPORTANT",
      howToObtain: "Discovery question: 'How many enterprise evaluations are in your pipeline today, and what's blocking them from closing?'"
    },
    {
      evidenceType: "Current security/compliance posture",
      source: "CISO or security documentation",
      priority: "IMPORTANT",
      howToObtain: "Discovery question: 'What's your current SOC 2 status, and how long does it take to respond to enterprise security questionnaires?'"
    },
    {
      evidenceType: "CRO's previous GTM stack and methodology",
      source: "LinkedIn, public background, or direct inquiry",
      priority: "NICE_TO_HAVE",
      howToObtain: "Discovery question: 'What sales methodology and tools have worked best in your previous roles?'"
    }
  ],

  discoveryQuestions: [
    {
      questionId: "DQ-003-1",
      question: "You joined to build the enterprise motion. What's your 12-month enterprise customer and revenue target?",
      targetPersona: "CRO",
      purpose: "Quantify enterprise ambition and timeline urgency",
      followUpIfYes: "What's the biggest gap between where you are today and that target?",
      followUpIfNo: "How are you thinking about the right enterprise ICP given your current user base?"
    },
    {
      questionId: "DQ-003-2",
      question: "G2 reviews mention missing enterprise features like SSO and audit logs. How is that showing up in your enterprise sales conversations?",
      targetPersona: "VP Product",
      purpose: "Validate product gap severity and sales friction",
      followUpIfYes: "What percentage of enterprise deals are blocked by security/feature requirements?",
      followUpIfNo: "How do you prioritize between PLG feature requests and enterprise requirements?"
    },
    {
      questionId: "DQ-003-3",
      question: "If you could have enterprise-grade security and compliance automation in place by Q3, how would that change your go-to-market plan for the second half of the year?",
      targetPersona: "CRO",
      purpose: "Surface strategic value of security/compliance acceleration",
      followUpIfYes: "What markets or accounts would you target that you can't today?",
      followUpIfNo: "What's your current approach to handling security reviews and procurement cycles?"
    }
  ]
};

// ============================================================================
// EXPORT ALL EXAMPLES
// ============================================================================

export const signalToHypothesisExamples: SignalToHypothesisChain[] = [
  example1,
  example2,
  example3
];

export type {
  Signal,
  InterpretedSignal,
  PainRelevance,
  PersonaImpact,
  KPIImpact,
  ValueHypothesis,
  EvidenceRequirement,
  DiscoveryQuestion,
  SignalToHypothesisChain,
  ConfidenceLevel,
  UrgencyLevel,
  ValueDriverCategory,
  Prevalence
};
