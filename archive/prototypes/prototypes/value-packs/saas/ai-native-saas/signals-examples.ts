/**
 * AI-Native SaaS Subpack — Signal Interpretation Examples
 * ID: ai-native-saas-v1
 * Parent Master: saas-master-v1
 * 
 * TypeScript-style definitions for programmatic signal processing,
 * value formula calculation, and persona matching.
 */

// ============================================================================
// CORE TYPE DEFINITIONS
// ============================================================================

export type Confidence = "HIGH" | "MEDIUM" | "LOW";
export type Urgency = "HIGH" | "MEDIUM" | "LOW";
export type ValueCategory = "Revenue Uplift" | "Cost Savings" | "Risk Reduction" | "Working Capital";

export interface SignalReading {
  signalId: string;
  rawValue: number | string | boolean;
  timestamp: string;
  source: string;
  tenantId?: string;
}

export interface SignalInterpretation {
  signalRuleId: string;
  interpretedPainId: string;
  confidence: number; // 0.0–1.0
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
  recommendedActions: string[];
  affectedPersonaIds: string[];
  estimatedAnnualImpact?: {
    revenueUplift?: number;
    costSavings?: number;
    riskExposure?: number;
  };
}

// ============================================================================
// SIGNAL RULE DEFINITIONS (20 AI-Native Rules)
// ============================================================================

export const AI_NATIVE_SIGNAL_RULES = [
  {
    id: "SR-AI-001",
    name: "LLM API Bill Spike",
    trigger: (readings: SignalReading[]) => {
      const spend = readings.find(r => r.signalId === "llm_monthly_spend")?.rawValue as number;
      const prevSpend = readings.find(r => r.signalId === "llm_monthly_spend_prev")?.rawValue as number;
      const revenueGrowth = readings.find(r => r.signalId === "revenue_growth_mom")?.rawValue as number;
      return spend && prevSpend && revenueGrowth
        ? (spend - prevSpend) / prevSpend > 0.50 && revenueGrowth < 0.30
        : false;
    },
    interpretation: {
      painId: "P-AI-003",
      confidence: 0.85,
      severity: "HIGH" as const,
      actions: [
        "Run tenant-level token consumption audit",
        "Identify top 10% power users by token volume",
        "Evaluate model routing to cheaper alternatives for low-complexity tasks",
        "Implement caching layer for repeated query patterns"
      ],
      personas: ["PER-AI-005", "CFO"]
    }
  },
  {
    id: "SR-AI-002",
    name: "Hallucination Complaint Spike",
    trigger: (readings: SignalReading[]) => {
      const complaints = readings.find(r => r.signalId === "ai_error_complaints_30d")?.rawValue as number;
      const baseline = readings.find(r => r.signalId === "ai_error_complaints_baseline")?.rawValue as number;
      return complaints && baseline ? complaints > baseline * 3 : false;
    },
    interpretation: {
      painId: "P-AI-001",
      confidence: 0.90,
      severity: "CRITICAL" as const,
      actions: [
        "Run automated eval benchmark on production sample",
        "Check for recent model or prompt changes",
        "Segment complaints by customer cohort and feature",
        "Activate human-in-the-loop review for affected outputs"
      ],
      personas: ["PER-AI-001", "PER-AI-002", "Responsible AI Officer"]
    }
  },
  {
    id: "SR-AI-003",
    name: "AI Feature MAU Decline",
    trigger: (readings: SignalReading[]) => {
      const mau1 = readings.find(r => r.signalId === "ai_mau_month_1")?.rawValue as number;
      const mau2 = readings.find(r => r.signalId === "ai_mau_month_2")?.rawValue as number;
      const mau3 = readings.find(r => r.signalId === "ai_mau_month_3")?.rawValue as number;
      return mau1 && mau2 && mau3 ? mau3 < mau2 * 0.80 && mau2 < mau1 * 0.80 : false;
    },
    interpretation: {
      painId: "P-AI-008",
      confidence: 0.80,
      severity: "HIGH" as const,
      actions: [
        "Analyze activation funnel for AI features",
        "Conduct user interviews with churned AI users",
        "Review competitor AI feature launches in same period",
        "A/B test onboarding flow and feature discoverability"
      ],
      personas: ["PER-AI-001", "VP Product", "CRO"]
    }
  },
  {
    id: "SR-AI-004",
    name: "Enterprise Deal Stalled on AI Governance",
    trigger: (readings: SignalReading[]) => {
      const stalled = readings.find(r => r.signalId === "enterprise_deals_stalled_governance")?.rawValue as number;
      return stalled ? stalled >= 2 : false;
    },
    interpretation: {
      painId: "P-AI-002",
      confidence: 0.85,
      severity: "HIGH" as const,
      actions: [
        "Audit CRM for all deals with 'AI governance' stall reason",
        "Review security questionnaire completion status",
        "Prioritize model registry and model card generation",
        "Engage legal to draft standard AI governance responses"
      ],
      personas: ["PER-AI-003", "CRO", "CISO"]
    }
  },
  {
    id: "SR-AI-005",
    name: "Red-Team Jailbreak Success",
    trigger: (readings: SignalReading[]) => {
      const successRate = readings.find(r => r.signalId === "redteam_jailbreak_success_rate")?.rawValue as number;
      return successRate ? successRate > 0.10 : false;
    },
    interpretation: {
      painId: "P-AI-004",
      confidence: 0.90,
      severity: "CRITICAL" as const,
      actions: [
        "Immediately deploy input/output guardrails on all AI endpoints",
        "Run OWASP LLM Top 10 gap assessment",
        "Implement automated adversarial testing in CI/CD",
        "Schedule external penetration test focused on prompt injection"
      ],
      personas: ["CISO", "PER-AI-002", "PER-AI-005"]
    }
  },
  {
    id: "SR-AI-006",
    name: "Vector DB Latency Degradation",
    trigger: (readings: SignalReading[]) => {
      const p99 = readings.find(r => r.signalId === "vector_db_p99_latency")?.rawValue as number;
      const baseline = readings.find(r => r.signalId === "vector_db_p99_baseline")?.rawValue as number;
      return p99 && baseline ? p99 > baseline * 2 : false;
    },
    interpretation: {
      painId: "P-AI-009",
      confidence: 0.80,
      severity: "MEDIUM" as const,
      actions: [
        "Analyze vector count growth rate vs. index capacity",
        "Review query volume trend for hotspots",
        "Evaluate index type (HNSW vs. IVF) appropriateness",
        "Consider partition/sharding strategy for multi-tenant workloads"
      ],
      personas: ["PER-AI-006", "PER-AI-005", "CTO"]
    }
  },
  {
    id: "SR-AI-007",
    name: "Model Deployment Without Eval",
    trigger: (readings: SignalReading[]) => {
      const noEvalCount = readings.find(r => r.signalId === "model_deploys_without_eval_90d")?.rawValue as number;
      return noEvalCount ? noEvalCount >= 3 : false;
    },
    interpretation: {
      painId: "P-AI-015",
      confidence: 0.85,
      severity: "HIGH" as const,
      actions: [
        "Block deploy pipeline without eval gate",
        "Build automated evaluation pipeline in CI/CD",
        "Create held-out test sets for each AI feature",
        "Implement quality regression alerts post-deploy"
      ],
      personas: ["PER-AI-002", "PER-AI-001", "VP Product"]
    }
  },
  {
    id: "SR-AI-008",
    name: "Multi-Provider Lock-in Risk",
    trigger: (readings: SignalReading[]) => {
      const concentration = readings.find(r => r.signalId === "llm_provider_concentration")?.rawValue as number;
      const failoverTested = readings.find(r => r.signalId === "failover_tested")?.rawValue as boolean;
      return concentration ? concentration > 0.85 && !failoverTested : false;
    },
    interpretation: {
      painId: "P-AI-016",
      confidence: 0.80,
      severity: "MEDIUM" as const,
      actions: [
        "Implement LLM gateway with unified API abstraction",
        "Test failover to secondary provider for critical features",
        "Diversify 20-30% of traffic to alternative providers",
        "Document provider-specific capabilities and limitations"
      ],
      personas: ["PER-AI-006", "CTO", "PER-AI-005"]
    }
  },
  {
    id: "SR-AI-009",
    name: "AI Agent Human Fallback Surge",
    trigger: (readings: SignalReading[]) => {
      const fallbackRate = readings.find(r => r.signalId === "agent_human_fallback_rate")?.rawValue as number;
      const prevFallback = readings.find(r => r.signalId === "agent_human_fallback_rate_prev")?.rawValue as number;
      return fallbackRate && prevFallback ? fallbackRate > prevFallback + 0.10 : false;
    },
    interpretation: {
      painId: "P-AI-006",
      confidence: 0.75,
      severity: "HIGH" as const,
      actions: [
        "Audit agent workflow change log for recent modifications",
        "Analyze tool API error rates for degradation",
        "Review training data or prompt updates",
        "Implement graceful degradation paths for sub-tasks"
      ],
      personas: ["PER-AI-001", "PER-AI-002", "VP Customer Success"]
    }
  },
  {
    id: "SR-AI-010",
    name: "ML Engineer Attrition Alert",
    trigger: (readings: SignalReading[]) => {
      const departures = readings.find(r => r.signalId === "ml_engineer_departures_90d")?.rawValue as number;
      const fillTime = readings.find(r => r.signalId === "ml_role_time_to_fill")?.rawValue as number;
      return (departures ? departures >= 2 : false) || (fillTime ? fillTime > 120 : false);
    },
    interpretation: {
      painId: "P-AI-011",
      confidence: 0.85,
      severity: "HIGH" as const,
      actions: [
        "Conduct stay interviews with remaining ML team",
        "Benchmark compensation vs. market immediately",
        "Audit project backlog for critical dependencies",
        "Consider managed platform to reduce ML engineering toil"
      ],
      personas: ["CTO", "CHRO", "VP Engineering"]
    }
  },
  {
    id: "SR-AI-011",
    name: "Prompt Management Chaos",
    trigger: (readings: SignalReading[]) => {
      const repoCount = readings.find(r => r.signalId === "prompt_hardcoded_repos")?.rawValue as number;
      const registryCoverage = readings.find(r => r.signalId === "prompt_registry_coverage")?.rawValue as number;
      return (repoCount ? repoCount > 10 : false) || (registryCoverage ? registryCoverage < 0.50 : false);
    },
    interpretation: {
      painId: "P-AI-018",
      confidence: 0.80,
      severity: "MEDIUM" as const,
      actions: [
        "Scan all repos for hardcoded prompt strings",
        "Implement centralized prompt registry with versioning",
        "Establish prompt review process before production deploy",
        "Document prompt ownership and bus-factor mitigation"
      ],
      personas: ["PER-AI-004", "PER-AI-002", "VP Engineering"]
    }
  },
  {
    id: "SR-AI-012",
    name: "PII in Prompt Logs",
    trigger: (readings: SignalReading[]) => {
      const piiFound = readings.find(r => r.signalId === "pii_in_prompt_logs")?.rawValue as boolean;
      return piiFound === true;
    },
    interpretation: {
      painId: "P-AI-014",
      confidence: 0.90,
      severity: "CRITICAL" as const,
      actions: [
        "Immediately halt AI feature processing sensitive data",
        "Implement PII detection and masking on all AI inputs",
        "Audit DPA coverage with all LLM providers",
        "Engage legal for breach assessment and notification obligations"
      ],
      personas: ["CISO", "PER-AI-003", "VP Compliance"]
    }
  },
  {
    id: "SR-AI-013",
    name: "Fine-Tuned Model Sprawl",
    trigger: (readings: SignalReading[]) => {
      const modelCount = readings.find(r => r.signalId === "production_finetuned_models")?.rawValue as number;
      const hasRegistry = readings.find(r => r.signalId === "model_registry_exists")?.rawValue as boolean;
      return (modelCount ? modelCount > 20 : false) && !hasRegistry;
    },
    interpretation: {
      painId: "P-AI-010",
      confidence: 0.80,
      severity: "MEDIUM" as const,
      actions: [
        "Inventory all production fine-tuned models",
        "Implement model registry with cost tracking",
        "Define model lifecycle policy (create, update, deprecate, delete)",
        "Consolidate redundant or low-usage custom models"
      ],
      personas: ["PER-AI-002", "PER-AI-005", "CTO"]
    }
  },
  {
    id: "SR-AI-014",
    name: "Embedding Model Obsolescence",
    trigger: (readings: SignalReading[]) => {
      const daysSinceUpdate = readings.find(r => r.signalId === "embedding_model_days_since_update")?.rawValue as number;
      const mtebGap = readings.find(r => r.signalId === "mteb_leaderboard_gap")?.rawValue as number;
      return (daysSinceUpdate ? daysSinceUpdate > 180 : false) && (mtebGap ? mtebGap > 5 : false);
    },
    interpretation: {
      painId: "P-AI-005",
      confidence: 0.70,
      severity: "LOW" as const,
      actions: [
        "Benchmark current embedding vs. latest MTEB leaders on domain data",
        "Estimate re-embedding cost and downtime",
        "Plan A/B test with new embedding model on subset",
        "Schedule embedding infrastructure update in next quarter"
      ],
      personas: ["PER-AI-002", "PER-AI-006"]
    }
  },
  {
    id: "SR-AI-015",
    name: "AI Latency User Complaints",
    trigger: (readings: SignalReading[]) => {
      const complaintRate = readings.find(r => r.signalId === "ai_latency_complaint_rate_30d")?.rawValue as number;
      return complaintRate ? complaintRate > 0.05 : false;
    },
    interpretation: {
      painId: "P-AI-013",
      confidence: 0.75,
      severity: "MEDIUM" as const,
      actions: [
        "Break down latency by feature, device type, and geographic region",
        "Implement streaming/progressive response UX",
        "Evaluate edge deployment or caching for repeated queries",
        "Load test at 2x projected peak concurrency"
      ],
      personas: ["PER-AI-005", "PER-AI-001", "VP Product"]
    }
  },
  {
    id: "SR-AI-016",
    name: "Bias Testing Absence",
    trigger: (readings: SignalReading[]) => {
      const hasBiasTests = readings.find(r => r.signalId === "bias_test_coverage")?.rawValue as number;
      return hasBiasTests !== undefined ? hasBiasTests < 0.50 : false;
    },
    interpretation: {
      painId: "P-AI-012",
      confidence: 0.85,
      severity: "HIGH" as const,
      actions: [
        "Classify all AI features by decision impact level",
        "Implement bias testing for high-impact features immediately",
        "Document protected attributes and fairness metrics",
        "Prepare algorithmic impact assessment template"
      ],
      personas: ["PER-AI-003", "PER-AI-002", "VP Compliance"]
    }
  },
  {
    id: "SR-AI-017",
    name: "Training Data Copyright Gap",
    trigger: (readings: SignalReading[]) => {
      const provenanceCoverage = readings.find(r => r.signalId === "training_data_provenance_coverage")?.rawValue as number;
      const indemnificationRequests = readings.find(r => r.signalId === "enterprise_indemnification_requests")?.rawValue as number;
      return (provenanceCoverage ? provenanceCoverage < 0.50 : false) || (indemnificationRequests ? indemnificationRequests > 0 : false);
    },
    interpretation: {
      painId: "P-AI-007",
      confidence: 0.80,
      severity: "HIGH" as const,
      actions: [
        "Audit all training datasets for documented licenses",
        "Engage legal on IP indemnification strategy",
        "Budget for content licensing or synthetic data generation",
        "Review terms of service for generated content ownership clarity"
      ],
      personas: ["General Counsel", "PER-AI-003", "CEO"]
    }
  },
  {
    id: "SR-AI-018",
    name: "AI Support CSAT Gap",
    trigger: (readings: SignalReading[]) => {
      const aiCsat = readings.find(r => r.signalId === "ai_support_csat")?.rawValue as number;
      const humanCsat = readings.find(r => r.signalId === "human_support_csat")?.rawValue as number;
      return aiCsat && humanCsat ? aiCsat < humanCsat - 10 : false;
    },
    interpretation: {
      painId: "P-AI-017",
      confidence: 0.80,
      severity: "MEDIUM" as const,
      actions: [
        "Segment CSAT by ticket category and complexity",
        "Analyze escalation reasons for AI-handled tickets",
        "Improve escalation routing accuracy to correct queues",
        "A/B test human handoff timing (earlier vs. later)"
      ],
      personas: ["VP Customer Success", "PER-AI-001", "VP Support"]
    }
  },
  {
    id: "SR-AI-019",
    name: "Streaming UX Absence",
    trigger: (readings: SignalReading[]) => {
      const p95Latency = readings.find(r => r.signalId === "ai_feature_p95_latency")?.rawValue as number;
      const hasStreaming = readings.find(r => r.signalId === "streaming_ux_implemented")?.rawValue as boolean;
      return (p95Latency ? p95Latency > 1000 : false) && !hasStreaming;
    },
    interpretation: {
      painId: "P-AI-013",
      confidence: 0.70,
      severity: "LOW" as const,
      actions: [
        "Implement token-by-token streaming for real-time AI features",
        "Add skeleton/placeholder UI during AI 'thinking' phase",
        "A/B test streaming vs. batch UX on user engagement metrics",
        "Measure perceived latency (time to first token) vs. total latency"
      ],
      personas: ["PER-AI-001", "VP Product", "PER-AI-005"]
    }
  },
  {
    id: "SR-AI-020",
    name: "Governance Documentation Request Surge",
    trigger: (readings: SignalReading[]) => {
      const docRequests = readings.find(r => r.signalId === "enterprise_governance_doc_requests_90d")?.rawValue as number;
      return docRequests ? docRequests >= 3 : false;
    },
    interpretation: {
      painId: "P-AI-002",
      confidence: 0.85,
      severity: "HIGH" as const,
      actions: [
        "Catalog all requested governance artifacts",
        "Prioritize model cards, bias summaries, and data provenance docs",
        "Create standardized AI governance response package",
        "Assign governance documentation owner with SLA"
      ],
      personas: ["PER-AI-003", "CRO", "VP Sales"]
    }
  }
];

// ============================================================================
// VALUE FORMULA IMPLEMENTATIONS
// ============================================================================

export interface FormulaInputs {
  [key: string]: number;
}

export const AI_NATIVE_FORMULAS: Record<string, (inputs: FormulaInputs) => { result: number; unit: string; confidence: Confidence }> = {
  "VF-AI-001": (inputs) => {
    const { monthly_token_volume, cache_hit_rate, cached_token_cost_per_1k, uncached_token_cost_per_1k } = inputs;
    const annual_savings = (monthly_token_volume * cache_hit_rate * (uncached_token_cost_per_1k - cached_token_cost_per_1k) / 1000) * 12;
    return { result: Math.round(annual_savings), unit: "USD per year", confidence: "HIGH" };
  },
  "VF-AI-002": (inputs) => {
    const { monthly_ai_interactions, hallucination_rate, escalation_rate, cost_per_ticket } = inputs;
    const annual_cost = monthly_ai_interactions * hallucination_rate * escalation_rate * cost_per_ticket * 12;
    return { result: Math.round(annual_cost), unit: "USD per year", confidence: "MEDIUM" };
  },
  "VF-AI-003": (inputs) => {
    const { current_ai_mau, target_accuracy, current_accuracy, conversion_lift_per_point, arpu } = inputs;
    const impact = current_ai_mau * (target_accuracy - current_accuracy) * conversion_lift_per_point * arpu * 12;
    return { result: Math.round(impact), unit: "USD per year", confidence: "MEDIUM" };
  },
  "VF-AI-007": (inputs) => {
    const { tasks_automated_monthly, human_handle_time_hours, ai_handle_time_hours, hourly_labor_cost, ai_infrastructure_monthly_cost } = inputs;
    const annual_savings = tasks_automated_monthly * (human_handle_time_hours - ai_handle_time_hours) * hourly_labor_cost * 12;
    const annual_ai_cost = ai_infrastructure_monthly_cost * 12;
    return { result: Math.round(annual_savings - annual_ai_cost), unit: "USD per year", confidence: "MEDIUM" };
  },
  "VF-AI-009": (inputs) => {
    const { monthly_token_volume, original_tokens_per_prompt, optimized_tokens_per_prompt, cost_per_1k_tokens } = inputs;
    const annual_savings = (monthly_token_volume * (original_tokens_per_prompt - optimized_tokens_per_prompt) / 1000 * cost_per_1k_tokens) * 12;
    return { result: Math.round(annual_savings), unit: "USD per year", confidence: "HIGH" };
  }
};

// ============================================================================
// PERSONA MATCHING UTILITY
// ============================================================================

export const PERSONA_MATCHING_RULES = [
  {
    personaId: "PER-AI-001",
    matchSignals: ["ai_mau", "ai_feature_nps", "ai_activation_rate", "ai_churn_correlation"],
    matchPains: ["P-AI-001", "P-AI-008", "P-AI-013"],
    matchObjections: ["OBJ-AI-003"]
  },
  {
    personaId: "PER-AI-002",
    matchSignals: ["model_deploy_time", "eval_coverage", "inference_latency", "pipeline_failure_rate"],
    matchPains: ["P-AI-010", "P-AI-015", "P-AI-016"],
    matchObjections: ["OBJ-AI-004"]
  },
  {
    personaId: "PER-AI-003",
    matchSignals: ["bias_test_coverage", "explainability_coverage", "governance_doc_requests", "audit_findings"],
    matchPains: ["P-AI-002", "P-AI-012", "P-AI-014"],
    matchObjections: ["OBJ-AI-005", "OBJ-AI-007"]
  },
  {
    personaId: "PER-AI-004",
    matchSignals: ["prompt_registry_coverage", "prompt_ab_test_rate", "prompt_variance"],
    matchPains: ["P-AI-018"],
    matchObjections: ["OBJ-AI-008"]
  },
  {
    personaId: "PER-AI-005",
    matchSignals: ["llm_monthly_spend", "inference_p95_latency", "provider_outage_hours", "token_consumption_variance"],
    matchPains: ["P-AI-003", "P-AI-013", "P-AI-009"],
    matchObjections: ["OBJ-AI-002"]
  },
  {
    personaId: "PER-AI-006",
    matchSignals: ["llm_provider_concentration", "vector_db_p99_latency", "multi_cloud_ai_coverage", "model_serving_scale"],
    matchPains: ["P-AI-016", "P-AI-009", "P-AI-010"],
    matchObjections: ["OBJ-AI-009"]
  }
];

// ============================================================================
// BUYING TRIGGER DETECTION
// ============================================================================

export interface TriggerDetectionInput {
  eventType: string;
  severity: Urgency;
  affectedARR?: number;
  daysUntilImpact?: number;
}

export function detectBuyingTrigger(input: TriggerDetectionInput): {
  matchedTriggerIds: string[];
  recommendedDiscoveryQuestions: string[];
  recommendedPersonas: string[];
} {
  const matched: string[] = [];

  if (input.eventType === "llm_provider_outage" && input.severity === "HIGH") matched.push("BT-AI-001");
  if (input.eventType === "enterprise_deal_stalled_governance") matched.push("BT-AI-002");
  if (input.eventType === "hallucination_viral_incident") matched.push("BT-AI-003");
  if (input.eventType === "inference_bill_overrun") matched.push("BT-AI-004");
  if (input.eventType === "regulated_industry_launch") matched.push("BT-AI-005");
  if (input.eventType === "board_metrics_mandate") matched.push("BT-AI-006");
  if (input.eventType === "security_audit_flag") matched.push("BT-AI-007");
  if (input.eventType === "competitor_ai_launch") matched.push("BT-AI-008");
  if (input.eventType === "ml_engineer_departure") matched.push("BT-AI-009");
  if (input.eventType === "vector_db_scaling_limit") matched.push("BT-AI-010");
  if (input.eventType === "eu_market_entry") matched.push("BT-AI-011");
  if (input.eventType === "ai_mau_decline") matched.push("BT-AI-012");
  if (input.eventType === "prompt_chaos_incident") matched.push("BT-AI-013");
  if (input.eventType === "customer_explainability_demand") matched.push("BT-AI-014");
  if (input.eventType === "embedding_model_quality_gap") matched.push("BT-AI-015");

  return {
    matchedTriggerIds: matched,
    recommendedDiscoveryQuestions: matched.length > 0 
      ? ["DQ-AI-001", "DQ-AI-002", "DQ-AI-003", "DQ-AI-005"] 
      : [],
    recommendedPersonas: matched.length > 0
      ? ["PER-AI-001", "PER-AI-002", "PER-AI-003", "PER-AI-005"]
      : []
  };
}

// ============================================================================
// CONFIDENCE SCORING UTILITIES
// ============================================================================

export function calculateSignalConfidence(
  primarySignalStrength: number,
  confirmationSignals: boolean[],
  dataQuality: "production" | "sample" | "estimated"
): number {
  let score = primarySignalStrength;

  // Boost for confirmation signals
  const confirmationRate = confirmationSignals.filter(Boolean).length / confirmationSignals.length;
  score += confirmationRate * 0.15;

  // Adjust for data quality
  if (dataQuality === "production") score += 0.10;
  else if (dataQuality === "estimated") score -= 0.15;

  return Math.min(Math.max(score, 0.0), 1.0);
}

export function confidenceToLabel(score: number): Confidence {
  if (score >= 0.80) return "HIGH";
  if (score >= 0.60) return "MEDIUM";
  return "LOW";
}

export default {
  AI_NATIVE_SIGNAL_RULES,
  AI_NATIVE_FORMULAS,
  PERSONA_MATCHING_RULES,
  detectBuyingTrigger,
  calculateSignalConfidence,
  confidenceToLabel
};
