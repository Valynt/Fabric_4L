/**
 * Infrastructure and Platform SaaS - Signal Rules & Patterns (S2.4)
 * ID: infrastructure-saas-v1
 * Parent Master: saas-master-v1
 * Generated: 2026-04-25
 * Agent Swarm: kimi-k2.6-swarm-saas-infra
 *
 * This file contains TypeScript-style type definitions and signal rule implementations
 * for the Infrastructure and Platform SaaS vertical subpack.
 */

// =============================================================================
// INHERITED TYPE DEFINITIONS (Referenced, Not Duplicated)
// =============================================================================
// Inherited from saas-master-v1: SignalSource, RawSignal, InterpretedSignal,
// EvidenceSource, ValueDriverID, SegmentID, PersonaID, KPIID, PainID

// =============================================================================
// VERTICAL-SPECIFIC TYPE DEFINITIONS
// =============================================================================

type InfrastructureVerticalFocus =
  | "cloud-management"
  | "observability"
  | "apm"
  | "data-pipelines"
  | "data-warehouses"
  | "api-platforms"
  | "ipaas"
  | "cicd"
  | "feature-flags"
  | "testing"
  | "k8s-management"
  | "finops"
  | "dx-platforms";

type InfrastructurePersonaRole =
  | "Platform Engineer"
  | "SRE Lead"
  | "Data Platform Architect"
  | "FinOps Analyst"
  | "API Product Manager"
  | "DevEx Lead";

// =============================================================================
// INFRASTRUCTURE SIGNAL RULE DEFINITIONS
// =============================================================================

interface InfrastructureSignalRule {
  id: string;
  signalName: string;
  verticalFocus: InfrastructureVerticalFocus[];
  rawSignalPattern: string;
  interpretation: {
    meaning: string;
    urgencyLevel: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
    confidenceScore: number; // 0.0 - 1.0
    confidenceRationale: string;
  };
  linkedPains: PainID[];
  linkedKPIs: KPIID[];
  linkedPersonas: InfrastructurePersonaRole[];
  requiredConfirmationSignals: string[];
  recommendedActions: string[];
  timing: {
    typicalTriggerWindow: string;
    procurementWindow: string;
    budgetCycleAlignment: string;
  };
}

// =============================================================================
// SIGNAL RULES ARRAY (20 Rules)
// =============================================================================

export const INFRASTRUCTURE_SIGNAL_RULES: InfrastructureSignalRule[] = [
  {
    id: "INF-SR001",
    signalName: "Observability Vendor Pricing Change",
    verticalFocus: ["observability", "finops"],
    rawSignalPattern:
      "Datadog, New Relic, or Splunk announces per-host or per-GB price increase >15%",
    interpretation: {
      meaning:
        "Customer base will face immediate cost pressure and evaluate alternatives. Switching cost is high but ROI case for alternative is strong. Expect 30-90 day renewal evaluation cycle.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.85,
      confidenceRationale:
        "Highly correlated with customer observability cost spikes. Public pricing changes create urgency. LOW confidence if customer is locked in multi-year contract without out-clause.",
    },
    linkedPains: ["INF-P001", "INF-P018"],
    linkedKPIs: ["INF-K001", "INF-K002"],
    linkedPersonas: ["SRE Lead", "FinOps Analyst", "CTO"],
    requiredConfirmationSignals: [
      "Customer observability spend data",
      "Contract renewal timing",
      "Engineer complaints on social/Reddit/HN",
    ],
    recommendedActions: [
      "Offer TCO comparison with 3-year NPV",
      "Propose data migration assessment",
      "Reference peer migration case studies",
      "Highlight per-GB cost differential",
    ],
    timing: {
      typicalTriggerWindow: "30-90 days before renewal",
      procurementWindow: "1-3 months",
      budgetCycleAlignment: "Q4 planning or renewal cycle",
    },
  },

  {
    id: "INF-SR002",
    signalName: "Kubernetes Downtime or CVE",
    verticalFocus: ["k8s-management", "observability"],
    rawSignalPattern:
      "Major Kubernetes CVE published or cloud provider K8s outage affects >1000 customers",
    interpretation: {
      meaning:
        "Security and reliability teams will prioritize cluster hardening, upgrade cycles, and governance tooling. Managed K8s and security scanning tools see elevated demand.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "CVEs and outages reliably trigger infrastructure tooling investments. MEDIUM confidence if customer already uses managed K8s service with auto-patching.",
    },
    linkedPains: ["INF-P002", "INF-P017"],
    linkedKPIs: ["INF-K004", "INF-K005", "INF-K006"],
    linkedPersonas: ["Platform Engineer", "SRE Lead", "CISO"],
    requiredConfirmationSignals: [
      "Customer K8s version distribution",
      "Security team hiring",
      "Cluster upgrade announcements",
    ],
    recommendedActions: [
      "Offer security posture assessment",
      "Highlight CVE remediation automation",
      "Show multi-cluster governance ROI",
      "Reference security-first customer case studies",
    ],
    timing: {
      typicalTriggerWindow: "0-30 days after CVE publication",
      procurementWindow: "1-3 months",
      budgetCycleAlignment: "Security budget or Q1 planning",
    },
  },

  {
    id: "INF-SR003",
    signalName: "CI/CD Pipeline Platform Disruption",
    verticalFocus: ["cicd", "dx-platforms"],
    rawSignalPattern:
      "GitHub Actions experiences extended outage (>2 hrs) or changes runner pricing/minutes by >20%",
    interpretation: {
      meaning:
        "Engineering teams dependent on disrupted CI/CD will evaluate alternatives. Multi-CI strategies become attractive. Build speed and reliability gaps are exposed.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.75,
      confidenceRationale:
        "Outage-driven evaluation is reliable but many teams accept outages as cost of managed service. MEDIUM confidence without evidence of engineering leadership dissatisfaction.",
    },
    linkedPains: ["INF-P003", "INF-P009"],
    linkedKPIs: ["INF-K007", "INF-K008", "INF-K009"],
    linkedPersonas: ["DevEx Lead", "Platform Engineer", "VP Engineering"],
    requiredConfirmationSignals: [
      "Customer CI/CD vendor",
      "Engineering team size",
      "Pipeline criticality assessment",
      "Current build time benchmarks",
    ],
    recommendedActions: [
      "Offer build speed comparison",
      "Highlight caching and parallelism gains",
      "Propose hybrid CI architecture",
      "Show developer productivity impact quantified",
    ],
    timing: {
      typicalTriggerWindow: "0-14 days after outage",
      procurementWindow: "1-6 months",
      budgetCycleAlignment: "Engineering tooling budget or annual review",
    },
  },

  {
    id: "INF-SR004",
    signalName: "Data Warehouse Pricing Pressure",
    verticalFocus: ["data-warehouses", "finops", "data-pipelines"],
    rawSignalPattern:
      "Snowflake, Databricks, or BigQuery announces credit pricing change or new consumption model with >15% effective increase",
    interpretation: {
      meaning:
        "Data teams face cost scrutiny. FinOps for data platforms becomes urgent. Query optimization, caching strategies, and warehouse governance tools in demand.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "Pricing changes reliably trigger warehouse optimization investments. HIGH confidence when combined with customer data volume growth >50% YoY.",
    },
    linkedPains: ["INF-P004", "INF-P010", "INF-P016"],
    linkedKPIs: ["INF-K028", "INF-K029", "INF-K010"],
    linkedPersonas: ["Data Platform Architect", "FinOps Analyst", "CTO"],
    requiredConfirmationSignals: [
      "Customer warehouse spend trend",
      "Data team headcount",
      "Query volume growth",
      "Current materialized view strategy",
    ],
    recommendedActions: [
      "Offer query performance audit",
      "Calculate compute cost per query",
      "Show caching optimization value",
      "Reference similar warehouse optimization outcomes",
    ],
    timing: {
      typicalTriggerWindow: "0-60 days after pricing announcement",
      procurementWindow: "2-6 months",
      budgetCycleAlignment: "Data infrastructure budget or Q2 planning",
    },
  },

  {
    id: "INF-SR005",
    signalName: "API Platform Scalability Incident",
    verticalFocus: ["api-platforms", "observability"],
    rawSignalPattern:
      "Company status page reports API rate limiting, latency degradation (P99 >2x baseline), or error rate spike affecting >10% of traffic",
    interpretation: {
      meaning:
        "API infrastructure is under stress. Need for API gateway, rate limiting, traffic management, and developer experience improvements is acute.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.85,
      confidenceRationale:
        "API incidents directly impact revenue and partnerships. HIGH confidence when incident duration >30 minutes or partner complaints public.",
    },
    linkedPains: ["INF-P005", "INF-P012"],
    linkedKPIs: ["INF-K013", "INF-K014", "INF-K015"],
    linkedPersonas: ["API Product Manager", "SRE Lead", "CTO"],
    requiredConfirmationSignals: [
      "API traffic growth data",
      "Infrastructure scaling announcements",
      "Engineering hiring for API roles",
      "Partner integration backlog data",
    ],
    recommendedActions: [
      "Offer API architecture assessment",
      "Show gateway performance benchmarks",
      "Propose developer portal strategy",
      "Quantify partner onboarding time reduction",
    ],
    timing: {
      typicalTriggerWindow: "0-30 days post-incident",
      procurementWindow: "1-4 months",
      budgetCycleAlignment: "Product/platform budget or post-incident review",
    },
  },

  {
    id: "INF-SR006",
    signalName: "Major Cloud Provider Outage",
    verticalFocus: ["cloud-management", "k8s-management", "observability"],
    rawSignalPattern:
      "AWS, Azure, or GCP regional outage affects multiple services for >2 hours; affects customer directly or their dependencies",
    interpretation: {
      meaning:
        "Multi-cloud resilience and disaster recovery become board-level topics. Customers invest in multi-region, multi-cloud tooling, and enhanced observability.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "Outages reliably trigger multi-cloud conversations. MEDIUM confidence if customer already has multi-region architecture.",
    },
    linkedPains: ["INF-P011", "INF-P012", "INF-P007"],
    linkedKPIs: ["INF-K031", "INF-K034", "INF-K019"],
    linkedPersonas: ["SRE Lead", "Platform Engineer", "CTO"],
    requiredConfirmationSignals: [
      "Customer cloud provider concentration",
      "RTO/RPO requirements",
      "Business continuity planning status",
      "Current egress costs",
    ],
    recommendedActions: [
      "Offer multi-cloud observability assessment",
      "Show service mesh value for cross-cloud",
      "Calculate egress cost avoidance",
      "Reference multi-cloud migration playbooks",
    ],
    timing: {
      typicalTriggerWindow: "0-90 days post-outage",
      procurementWindow: "3-9 months",
      budgetCycleAlignment: "Disaster recovery budget or board-level initiative",
    },
  },

  {
    id: "INF-SR007",
    signalName: "Engineering Glassdoor Reviews on Tooling",
    verticalFocus: ["dx-platforms", "cicd", "k8s-management"],
    rawSignalPattern:
      "Glassdoor reviews show negative trend mentioning 'slow builds', 'broken CI', 'outdated tooling', 'on-call burnout' with <3.5 average rating",
    interpretation: {
      meaning:
        "Developer experience issues are affecting retention. Leadership likely evaluating DX and platform engineering investments within 3-6 months.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.7,
      confidenceRationale:
        "Glassdoor signal is noisy but directional. LOW confidence without engineering turnover data above 20%. Higher confidence with public DX survey complaints.",
    },
    linkedPains: ["INF-P003", "INF-P008", "INF-P009", "INF-P015"],
    linkedKPIs: ["INF-K007", "INF-K023", "INF-K025", "INF-K043"],
    linkedPersonas: ["DevEx Lead", "VP Engineering", "CTO"],
    requiredConfirmationSignals: [
      "Engineering turnover data",
      "DX survey results if public",
      "Platform engineering job postings",
      "Internal NPS trends",
    ],
    recommendedActions: [
      "Offer DX assessment framework",
      "Show build time and onboarding benchmarks",
      "Quantify retention cost of poor DX",
      "Reference peer DX transformation stories",
    ],
    timing: {
      typicalTriggerWindow: "3-6 months after sustained negative trend",
      procurementWindow: "2-6 months",
      budgetCycleAlignment: "Annual planning or retention initiative",
    },
  },

  {
    id: "INF-SR008",
    signalName: "Series B/C with Infrastructure Use of Proceeds",
    verticalFocus: [
      "cloud-management",
      "k8s-management",
      "observability",
      "dx-platforms",
    ],
    rawSignalPattern:
      "Funding round >$20M with explicit mention of 'platform engineering', 'infrastructure scaling', 'observability', or 'developer experience' in use of proceeds",
    interpretation: {
      meaning:
        "Fresh capital earmarked for infrastructure and platform investments. 6-12 month procurement window for infra SaaS with multi-year deal potential.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "Explicit use of proceeds is strong signal. MEDIUM confidence if only generic 'engineering growth' mentioned without specific tooling.",
    },
    linkedPains: ["INF-P002", "INF-P007", "INF-P015", "INF-P012"],
    linkedKPIs: ["INF-K004", "INF-K019", "INF-K043"],
    linkedPersonas: ["CTO", "VP Engineering", "Platform Engineer", "FinOps Analyst"],
    requiredConfirmationSignals: [
      "Use of proceeds details",
      "Post-funding engineering hiring",
      "Infrastructure roadmap announcements",
      "Cloud spend trajectory",
    ],
    recommendedActions: [
      "Position for multi-year deal",
      "Show scaling ROI aligned to growth",
      "Offer dedicated onboarding resources",
      "Reference similar-stage customer outcomes",
    ],
    timing: {
      typicalTriggerWindow: "0-6 months post-close",
      procurementWindow: "6-18 months",
      budgetCycleAlignment: "Post-funding investment cycle",
    },
  },

  {
    id: "INF-SR009",
    signalName: "SOC 2 Finding on Change Management",
    verticalFocus: ["cicd", "feature-flags", "observability"],
    rawSignalPattern:
      "SOC 2 audit finding related to 'inadequate change management', 'lack of deployment controls', 'missing audit logs', or 'no feature flag governance'",
    interpretation: {
      meaning:
        "Compliance gap directly implicates CI/CD, feature flags, and deployment governance tooling. Immediate procurement need with board visibility.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.85,
      confidenceRationale:
        "SOC 2 findings have mandatory remediation timelines. HIGH confidence when finding is in Type II report.",
    },
    linkedPains: ["INF-P003", "INF-P006", "INF-P017"],
    linkedKPIs: ["INF-K007", "INF-K016", "INF-K050"],
    linkedPersonas: ["CISO", "Platform Engineer", "DevEx Lead", "VP Engineering"],
    requiredConfirmationSignals: [
      "Audit report details",
      "Remediation timeline",
      "Compliance team hiring",
      "Previous audit findings recurrence",
    ],
    recommendedActions: [
      "Offer compliance audit trail demo",
      "Show deployment governance controls",
      "Quantify audit remediation cost reduction",
      "Reference SOC 2 customer success stories",
    ],
    timing: {
      typicalTriggerWindow: "0-3 months from finding",
      procurementWindow: "1-3 months",
      budgetCycleAlignment: "Compliance or audit remediation budget",
    },
  },

  {
    id: "INF-SR010",
    signalName: "Data Breach or Exposed Credentials",
    verticalFocus: ["observability", "security", "api-platforms"],
    rawSignalPattern:
      "Company discloses data breach, exposed S3 bucket, leaked API keys/secrets in public repository, or container registry exposure",
    interpretation: {
      meaning:
        "Security posture overhaul likely. Secret management, CSPM, runtime security, API security, and data governance tools in urgent demand.",
      urgencyLevel: "CRITICAL",
      confidenceScore: 0.9,
      confidenceRationale:
        "Security incidents have highest correlation with immediate procurement. Confidence drops only if incident is minor with no customer data impact.",
    },
    linkedPains: ["INF-P014", "INF-P017", "INF-P005"],
    linkedKPIs: ["INF-K049", "INF-K050", "INF-K040"],
    linkedPersonas: ["CISO", "Platform Engineer", "Data Platform Architect", "CTO"],
    requiredConfirmationSignals: [
      "Breach scope and root cause",
      "Security team expansion",
      "Vendor security review notices",
      "Regulatory notification requirements",
    ],
    recommendedActions: [
      "Offer security posture assessment",
      "Show secrets detection and rotation",
      "Quantify breach cost avoidance",
      "Reference regulated industry deployments",
    ],
    timing: {
      typicalTriggerWindow: "0-30 days post-breach disclosure",
      procurementWindow: "1-6 months",
      budgetCycleAlignment: "Security emergency budget or board mandate",
    },
  },

  {
    id: "INF-SR011",
    signalName: "Feature Flag Causes Production Incident",
    verticalFocus: ["feature-flags", "cicd"],
    rawSignalPattern:
      "Company status page or engineering blog mentions incident caused by feature flag misconfiguration, experiment bug, or untoggled flag in critical path",
    interpretation: {
      meaning:
        "Feature flag governance gap is acute. Kill switch capability, flag lifecycle management, and experimentation statistical rigor become immediate priorities.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "Flag-related incidents reliably trigger governance tooling purchases. Confidence moderate if company already has basic flag tool but lacks governance.",
    },
    linkedPains: ["INF-P006", "INF-P003"],
    linkedKPIs: ["INF-K016", "INF-K017", "INF-K018"],
    linkedPersonas: ["VP Product", "SRE Lead", "Platform Engineer", "DevEx Lead"],
    requiredConfirmationSignals: [
      "Flag tooling vendor in use",
      "Engineering post-mortem availability",
      "Product team hiring for experimentation",
    ],
    recommendedActions: [
      "Offer flag audit and governance assessment",
      "Show kill switch demo on critical paths",
      "Quantify incident cost avoidance",
      "Reference experimentation maturity framework",
    ],
    timing: {
      typicalTriggerWindow: "0-30 days post-incident",
      procurementWindow: "1-3 months",
      budgetCycleAlignment: "Product/platform budget or incident review cycle",
    },
  },

  {
    id: "INF-SR012",
    signalName: "Earnings Call Infrastructure Efficiency Mention",
    verticalFocus: ["cloud-management", "finops", "observability"],
    rawSignalPattern:
      "Earnings call transcript mentions 'observability investment', 'FinOps', 'cloud optimization', 'platform engineering', or 'infrastructure efficiency'",
    interpretation: {
      meaning:
        "Infrastructure efficiency is board-level topic. CFO/COO/CTO alignment creates elevated access for vendors in cloud cost, observability, and platform engineering.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "Earnings call mentions indicate C-suite priority. HIGH confidence when combined with margin pressure or cost reduction guidance.",
    },
    linkedPains: ["INF-P001", "INF-P007", "INF-P015", "INF-P012"],
    linkedKPIs: ["INF-K001", "INF-K019", "INF-K043"],
    linkedPersonas: ["CFO", "CTO", "FinOps Analyst", "SRE Lead"],
    requiredConfirmationSignals: [
      "CFO/CTO commentary",
      "Capital allocation guidance",
      "Infrastructure spend forecast",
      "Gross margin trends",
    ],
    recommendedActions: [
      "Align ROI to margin improvement",
      "Show unit cost reduction benchmarks",
      "Quantify valuation multiple impact",
      "Reference public company outcomes",
    ],
    timing: {
      typicalTriggerWindow: "0-6 months after mention",
      procurementWindow: "3-12 months",
      budgetCycleAlignment: "Annual planning or efficiency initiative",
    },
  },

  {
    id: "INF-SR013",
    signalName: "Data Team Hiring Surge",
    verticalFocus: ["data-pipelines", "data-warehouses", "ai-infrastructure"],
    rawSignalPattern:
      "Company posts >5 data engineering, analytics, ML infrastructure, or data platform roles in 30-day window",
    interpretation: {
      meaning:
        "Data platform scaling. Data pipeline, warehouse, and MLOps tooling procurement window is open. Team growth creates urgency for standardization.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.75,
      confidenceRationale:
        "Hiring surge is directional but not all hires lead to tooling purchases. HIGH confidence when combined with warehouse spend growth >50% or new product launch.",
    },
    linkedPains: ["INF-P004", "INF-P010", "INF-P014", "INF-P020"],
    linkedKPIs: ["INF-K010", "INF-K028", "INF-K040"],
    linkedPersonas: ["Data Platform Architect", "CTO", "VP Engineering", "FinOps Analyst"],
    requiredConfirmationSignals: [
      "Data team growth rate",
      "Warehouse spend trend",
      "ML/AI product announcements",
      "Current tool stack maturity",
    ],
    recommendedActions: [
      "Offer data platform architecture review",
      "Show pipeline reliability benchmarks",
      "Quantify data team productivity per head",
      "Reference similar growth-stage outcomes",
    ],
    timing: {
      typicalTriggerWindow: "0-6 months during hiring surge",
      procurementWindow: "2-6 months",
      budgetCycleAlignment: "Data team budget or new headcount approval",
    },
  },

  {
    id: "INF-SR014",
    signalName: "Platform Engineering Team Formation",
    verticalFocus: ["dx-platforms", "k8s-management", "cicd"],
    rawSignalPattern:
      "Company creates dedicated 'Platform Engineering', 'Developer Experience', or 'Internal Developer Platform' team with public job postings",
    interpretation: {
      meaning:
        "Infrastructure self-service and developer platform investments beginning. IDP, DX, and platform tooling evaluation likely within 3-6 months.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.85,
      confidenceRationale:
        "Team formation is strong signal of commitment. HIGH confidence when job descriptions mention specific tooling categories.",
    },
    linkedPains: ["INF-P015", "INF-P009", "INF-P003"],
    linkedKPIs: ["INF-K043", "INF-K025", "INF-K007"],
    linkedPersonas: ["Platform Engineer", "DevEx Lead", "VP Engineering", "CTO"],
    requiredConfirmationSignals: [
      "Team charter/job description details",
      "Platform team headcount plan",
      "Technology stack mentioned in postings",
      "Current platform team backlog data",
    ],
    recommendedActions: [
      "Offer platform engineering maturity assessment",
      "Show IDP adoption benchmarks",
      "Quantify platform team ROI",
      "Reference internal platform transformation stories",
    ],
    timing: {
      typicalTriggerWindow: "0-6 months after team formation",
      procurementWindow: "3-9 months",
      budgetCycleAlignment: "Platform team charter budget",
    },
  },

  {
    id: "INF-SR015",
    signalName: "Multi-Cloud Strategy Commitment",
    verticalFocus: ["cloud-management", "k8s-management", "observability"],
    rawSignalPattern:
      "Company announces multi-cloud deployment, cloud-agnostic architecture commitment, or secondary cloud provider adoption in blog/earnings/job postings",
    interpretation: {
      meaning:
        "Cloud management complexity increasing. Need for unified observability, cost management, K8s governance, and developer experience across clouds.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.8,
      confidenceRationale:
        "Multi-cloud commitment is reliable signal but procurement can be delayed 6-12 months. MEDIUM confidence without evidence of migration spend allocation.",
    },
    linkedPains: ["INF-P011", "INF-P007", "INF-P002"],
    linkedKPIs: ["INF-K031", "INF-K019", "INF-K004"],
    linkedPersonas: ["SRE Lead", "Platform Engineer", "CTO", "FinOps Analyst"],
    requiredConfirmationSignals: [
      "Secondary cloud spend data",
      "Migration timeline and milestones",
      "Engineering hiring for cloud roles",
      "Current egress costs",
    ],
    recommendedActions: [
      "Offer multi-cloud observability architecture",
      "Show unified cost management across clouds",
      "Calculate egress and networking savings",
      "Reference multi-cloud governance playbooks",
    ],
    timing: {
      typicalTriggerWindow: "3-12 months after commitment",
      procurementWindow: "6-18 months",
      budgetCycleAlignment: "Cloud migration or multi-cloud initiative budget",
    },
  },

  {
    id: "INF-SR016",
    signalName: "AI/ML Model Deployment Scale-Up",
    verticalFocus: ["ai-infrastructure", "data-pipelines", "data-warehouses"],
    rawSignalPattern:
      "Company blog, conference talk, or press release mentions 10x increase in model deployment frequency, new AI product line, or MLOps investment plan",
    interpretation: {
      meaning:
        "MLOps and AI infrastructure scaling. Model serving, feature stores, training infrastructure, and ML pipelines become procurement priorities.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.7,
      confidenceRationale:
        "AI scaling announcements are strong but many companies struggle with execution. MEDIUM confidence without evidence of GPU/cloud ML spend growth.",
    },
    linkedPains: ["INF-P020", "INF-P004", "INF-P010"],
    linkedKPIs: ["INF-K058", "INF-K059", "INF-K010"],
    linkedPersonas: ["Data Platform Architect", "CTO", "VP Engineering", "FinOps Analyst"],
    requiredConfirmationSignals: [
      "ML team headcount plan",
      "Model count growth trajectory",
      "GPU/cloud ML spend trend",
      "Current model deployment process maturity",
    ],
    recommendedActions: [
      "Offer ML infrastructure assessment",
      "Show GPU utilization optimization",
      "Quantify model deployment acceleration",
      "Reference MLOps maturity framework",
    ],
    timing: {
      typicalTriggerWindow: "3-6 months before product launch",
      procurementWindow: "3-9 months",
      budgetCycleAlignment: "AI/ML product launch budget",
    },
  },

  {
    id: "INF-SR017",
    signalName: "API Developer Portal Launch",
    verticalFocus: ["api-platforms", "ipaas"],
    rawSignalPattern:
      "Company launches or significantly updates developer portal, API documentation, partner program, or API marketplace",
    interpretation: {
      meaning:
        "API platform strategy accelerating. API management, gateway, developer experience, and partner integration tools becoming critical.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.75,
      confidenceRationale:
        "Portal launch indicates strategic investment but tooling need depends on current backend maturity. HIGH confidence if partner revenue >10% of ARR.",
    },
    linkedPains: ["INF-P005", "INF-P013"],
    linkedKPIs: ["INF-K013", "INF-K015", "INF-K037"],
    linkedPersonas: ["API Product Manager", "VP Product", "CTO"],
    requiredConfirmationSignals: [
      "API traffic growth data",
      "Partner revenue trend",
      "Developer portal engagement metrics",
      "Current gateway infrastructure",
    ],
    recommendedActions: [
      "Offer API platform maturity assessment",
      "Show developer onboarding optimization",
      "Quantify partner integration velocity",
      "Reference API ecosystem growth stories",
    ],
    timing: {
      typicalTriggerWindow: "0-6 months after portal launch",
      procurementWindow: "2-6 months",
      budgetCycleAlignment: "Product/platform or partner ecosystem budget",
    },
  },

  {
    id: "INF-SR018",
    signalName: "New CTO from Platform-First Company",
    verticalFocus: [
      "cloud-management",
      "dx-platforms",
      "observability",
      "k8s-management",
    ],
    rawSignalPattern:
      "New CTO hired from Google, Netflix, Spotify, Meta, or other platform-engineering-mature company; visible in LinkedIn/press",
    interpretation: {
      meaning:
        "Tool consolidation likely; preferred vendor stack from previous role. Platform engineering, observability, and developer experience investments expected within 3-12 months.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.75,
      confidenceRationale:
        "CTO background is directional but constrained by existing team and tech debt. HIGH confidence when combined with platform engineering job postings.",
    },
    linkedPains: ["INF-P015", "INF-P009", "INF-P001", "INF-P012"],
    linkedKPIs: ["INF-K043", "INF-K025", "INF-K001", "INF-K034"],
    linkedPersonas: ["CTO", "Platform Engineer", "DevEx Lead", "SRE Lead"],
    requiredConfirmationSignals: [
      "CTO background and previous tooling choices",
      "Platform engineering job postings",
      "Engineering reorganization signals",
      "Current tool stack audit",
    ],
    recommendedActions: [
      "Research CTO's previous vendor relationships",
      "Offer platform architecture assessment",
      "Show benchmark comparisons to top-tier companies",
      "Reference similar CTO-led transformations",
    ],
    timing: {
      typicalTriggerWindow: "3-12 months after hire",
      procurementWindow: "3-9 months",
      budgetCycleAlignment: "Annual planning or CTO 90-day initiative",
    },
  },

  {
    id: "INF-SR019",
    signalName: "Container Registry Vulnerability Backlog",
    verticalFocus: ["security", "k8s-management", "cicd"],
    rawSignalPattern:
      "Public security scan or disclosure shows >100 unremediated CVEs in container images; or company blog discusses security scanning transformation",
    interpretation: {
      meaning:
        "Container security posture is immature. Runtime scanning, vulnerability management, and DevSecOps pipeline integration become urgent.",
      urgencyLevel: "HIGH",
      confidenceScore: 0.8,
      confidenceRationale:
        "CVE backlog is concrete, measurable signal. HIGH confidence when combined with SOC 2 or customer security questionnaire failures.",
    },
    linkedPains: ["INF-P017", "INF-P002"],
    linkedKPIs: ["INF-K049", "INF-K050", "INF-K051"],
    linkedPersonas: ["CISO", "Platform Engineer", "DevEx Lead"],
    requiredConfirmationSignals: [
      "Container registry scan results",
      "SOC 2 security findings",
      "Customer security questionnaire responses",
      "Security team hiring",
    ],
    recommendedActions: [
      "Offer container security assessment",
      "Show vulnerability remediation automation",
      "Quantify security review acceleration",
      "Reference regulated industry deployments",
    ],
    timing: {
      typicalTriggerWindow: "0-30 days after disclosure",
      procurementWindow: "1-4 months",
      budgetCycleAlignment: "Security or compliance budget",
    },
  },

  {
    id: "INF-SR020",
    signalName: "Developer Platform Adoption Stagnation",
    verticalFocus: ["dx-platforms", "cicd"],
    rawSignalPattern:
      "Internal surveys or Glassdoor mentions show low adoption of existing developer tools; or engineering leadership discusses 'tool fatigue' publicly",
    interpretation: {
      meaning:
        "Current tool stack is not delivering promised productivity. Platform consolidation, IDP investment, or developer experience overhaul likely.",
      urgencyLevel: "MEDIUM",
      confidenceScore: 0.7,
      confidenceRationale:
        "Adoption stagnation is softer signal. MEDIUM confidence without specific metrics. HIGH confidence when combined with negative DX NPS.",
    },
    linkedPains: ["INF-P009", "INF-P015", "INF-P018"],
    linkedKPIs: ["INF-K025", "INF-K026", "INF-K043"],
    linkedPersonas: ["DevEx Lead", "Platform Engineer", "VP Engineering"],
    requiredConfirmationSignals: [
      "Internal tool adoption metrics",
      "Developer NPS or satisfaction scores",
      "Tool consolidation initiatives",
      "Engineering turnover in platform teams",
    ],
    recommendedActions: [
      "Offer developer experience audit",
      "Show platform adoption benchmarks",
      "Quantify tool consolidation savings",
      "Reference DX transformation outcomes",
    ],
    timing: {
      typicalTriggerWindow: "3-6 months after stagnation identified",
      procurementWindow: "2-6 months",
      budgetCycleAlignment: "Annual planning or retention initiative",
    },
  },
];

// =============================================================================
// SIGNAL RULE IMPLEMENTATION FUNCTIONS
// =============================================================================

/**
 * Evaluates a raw signal against infrastructure signal rules.
 * Returns matching rules with confidence-adjusted scoring.
 */
export function evaluateInfrastructureSignal(
  rawSignal: string,
  companyContext: {
    segment: SegmentID;
    ars?: number;
    cloudSpend?: number;
    engineeringHeadcount?: number;
    currentTools?: string[];
  }
): Array<{
  rule: InfrastructureSignalRule;
  matchScore: number;
  confidenceAdjusted: number;
  recommendedAction: string;
}> {
  const matches: Array<{
    rule: InfrastructureSignalRule;
    matchScore: number;
    confidenceAdjusted: number;
    recommendedAction: string;
  }> = [];

  for (const rule of INFRASTRUCTURE_SIGNAL_RULES) {
    let matchScore = 0;

    // Simple keyword matching against rawSignal pattern
    const patternKeywords = rule.rawSignalPattern
      .toLowerCase()
      .split(/[\s,()./]+/)
      .filter((k) => k.length > 3);
    const signalWords = rawSignal.toLowerCase().split(/\s+/);

    const matchedKeywords = patternKeywords.filter((k) =>
      signalWords.some((w) => w.includes(k) || k.includes(w))
    );

    matchScore = matchedKeywords.length / patternKeywords.length;

    if (matchScore > 0.3) {
      // Adjust confidence based on company context
      let contextMultiplier = 1.0;
      if (
        companyContext.segment === "Infrastructure and Platform SaaS" ||
        companyContext.segment === "AI-Native SaaS"
      ) {
        contextMultiplier = 1.15;
      }
      if (
        companyContext.cloudSpend &&
        companyContext.ars &&
        companyContext.cloudSpend / companyContext.ars > 0.2
      ) {
        contextMultiplier *= 1.1; // High cloud spend ratio increases urgency
      }

      const confidenceAdjusted = Math.min(
        0.95,
        rule.interpretation.confidenceScore * contextMultiplier
      );

      matches.push({
        rule,
        matchScore: Math.round(matchScore * 100) / 100,
        confidenceAdjusted: Math.round(confidenceAdjusted * 100) / 100,
        recommendedAction: rule.recommendedActions[0],
      });
    }
  }

  return matches.sort((a, b) => b.confidenceAdjusted - a.confidenceAdjusted);
}

/**
 * Generates a buying trigger timeline based on current date and detected signals.
 */
export function generateBuyingTriggerTimeline(
  detectedSignals: InfrastructureSignalRule[],
  currentDate: Date = new Date()
): Array<{
  triggerName: string;
  expectedDecisionMonth: string;
  urgency: string;
  linkedPains: PainID[];
  recommendedEngagement: string;
}> {
  const timeline: Array<{
    triggerName: string;
    expectedDecisionMonth: string;
    urgency: string;
    linkedPains: PainID[];
    recommendedEngagement: string;
  }> = [];

  const monthNames = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];

  for (const signal of detectedSignals) {
    const procurementMonths = parseInt(
      signal.timing.procurementWindow.split("-")[1] || "3"
    );
    const decisionDate = new Date(
      currentDate.getFullYear(),
      currentDate.getMonth() + procurementMonths,
      1
    );

    timeline.push({
      triggerName: signal.signalName,
      expectedDecisionMonth: `${monthNames[decisionDate.getMonth()]} ${decisionDate.getFullYear()}`,
      urgency: signal.interpretation.urgencyLevel,
      linkedPains: signal.linkedPains,
      recommendedEngagement:
        signal.interpretation.urgencyLevel === "CRITICAL"
          ? "Executive escalation + board-level business case"
          : signal.interpretation.urgencyLevel === "HIGH"
          ? "Economic buyer engagement + ROI workshop"
          : "Technical champion cultivation + pilot proposal",
    });
  }

  return timeline.sort(
    (a, b) =>
      new Date(a.expectedDecisionMonth).getTime() -
      new Date(b.expectedDecisionMonth).getTime()
  );
}

// =============================================================================
// EXPORT TYPES
// =============================================================================

export type {
  InfrastructureVerticalFocus,
  InfrastructurePersonaRole,
  InfrastructureSignalRule,
};

export default INFRASTRUCTURE_SIGNAL_RULES;
