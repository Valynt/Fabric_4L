/**
 * Navigation Service — Centralized Navigation with State Machine Support
 *
 * Replaces imperative useNavigate() calls with declarative state-based navigation.
 * All routes use canonical /t/:tenantSlug prefix.
 */

import type { ReactNode } from "react";
import type { NavigateOptions, To } from "react-router-dom";
import type { UserTier } from "@/routes/types";

// ─────────────────────────────────────────────────────────────────────────────
// Route State Definitions (Canonical)
// ─────────────────────────────────────────────────────────────────────────────

export type RouteState =
  // Legacy aliases (temporary for component compatibility during migration)
  | "hypothesis"
  | "drivers"
  | "drivers-evidence"
  | "calculator"
  | "value-case"
  | "realization"
  | "formula-builder"
  | "formula-new"
  | "business-case-detail"
  | "business-cases"
  | "business-case-interactive"
  | "business-case-new"
  | "decision-trace"
  | "model-detail"
  | "integrations"
  | "cfo-view"
  | "executive-view"
  | "technical-view"
  | "interactive-calculator"
  | "opportunities"
  | "opportunity-scan"
  // Auth
  | "login"
  | "signup"
  | "login-callback"
  // Home
  | "root"
  | "home"
  | "workspaces"
  | "command-center"
  | "forbidden"
  // Accounts
  | "accounts"
  | "account-detail"
  | "account-overview"
  // Intelligence Workspace (account-scoped)
  | "intelligence"
  | "intelligence-overview"
  | "intelligence-signals"
  | "intelligence-stakeholders"
  | "intelligence-enrichment"
  | "intelligence-ontology"
  | "intelligence-hypotheses"
  | "intelligence-discovery"
  | "intelligence-persona"
  | "intelligence-assumptions"
  | "intelligence-drivers"
  | "intelligence-evidence"
  | "intelligence-alternatives"
  | "intelligence-solution-cost"
  // Value Studio Workspace (account-scoped)
  | "studio"
  | "studio-action-plan"
  | "studio-value-model"
  | "studio-driver-tree"
  | "studio-calculator"
  | "studio-narrative"
  | "studio-value-case"
  | "studio-value-realization"
  | "studio-solution-cost"
  // Deliverables (account-scoped)
  | "deliverables"
  | "deliverables-business-cases"
  | "deliverables-business-case-detail"
  | "deliverables-proposals"
  | "deliverables-exports"
  | "deliverables-cfo-view"
  | "deliverables-executive-view"
  | "deliverables-technical-view"
  // Context Engine (tenant-scoped)
  | "context"
  | "context-sources"
  | "context-source-detail"
  | "context-entities"
  | "context-entity-detail"
  | "context-graph"
  | "context-ingestion-runs"
  | "context-ingestion-run-detail"
  | "context-extraction"
  | "context-ontology"
  | "context-agents"
  | "context-integrations"
  // Governance (tenant-scoped)
  | "governance"
  | "governance-traces"
  | "governance-evidence"
  | "governance-provenance"
  | "governance-compliance"
  | "governance-formulas"
  | "governance-formula-detail"
  | "governance-benchmarks"
  | "governance-benchmark-detail"
  | "governance-value-packs"
  | "governance-value-pack-detail"
  | "governance-policies"
  | "governance-audit-log"
  | "governance-health"
  | "governance-billing"
  // Agents & Workflows (account-scoped)
  | "agents"
  | "agents-thread"
  | "workflows"
  | "workflow-run"
  // Academy (tenant-scoped)
  | "academy"
  | "academy-pillar"
  | "academy-quiz"
  | "academy-resources"
  | "academy-profile"
  // Settings — Personal (global)
  | "settings-profile"
  | "settings-security"
  | "settings-preferences"
  | "settings-notifications"
  | "settings-sessions"
  | "settings-activity"
  // Settings — Tenant (tenant-scoped)
  | "tenant-settings"
  | "tenant-settings-workspace"
  | "tenant-settings-billing"
  | "tenant-settings-subscription"
  | "tenant-settings-usage"
  | "tenant-settings-payment-methods"
  | "tenant-settings-invoices"
  | "tenant-settings-users"
  | "tenant-settings-roles"
  | "tenant-settings-permissions"
  | "tenant-settings-api-keys"
  | "tenant-settings-data-sources"
  | "tenant-settings-integrations"
  | "tenant-settings-variables"
  | "tenant-settings-value-packs"
  | "tenant-settings-ingestion-rules"
  | "tenant-settings-governance-policies"
  | "tenant-settings-governance-compliance"
  | "tenant-settings-governance-health"
  | "tenant-settings-governance-audit"
  | "tenant-settings-governance-admin"
  // Dev Tools
  | "dev-integration"
  // Legacy settings
  | "personal-profile"
  | "personal-security"
  | "personal-preferences"
  | "personal-notifications"
  | "personal-sessions";

// ─────────────────────────────────────────────────────────────────────────────
// Route Configuration Map
// ─────────────────────────────────────────────────────────────────────────────

export interface RouteConfig {
  path: string;
  params?: string[];
  analyticsRouteId: string;
}

const ROUTE_MAP: Record<RouteState, RouteConfig> = {
  // Auth
  login: { path: "/login", analyticsRouteId: "auth.login" },
  signup: { path: "/signup", analyticsRouteId: "auth.signup" },
  "login-callback": { path: "/login/callback", analyticsRouteId: "auth.callback" },

  // Home
  root: { path: "/", analyticsRouteId: "home.root" },
  home: { path: "/home", analyticsRouteId: "home.dashboard" },
  workspaces: { path: "/workspaces", analyticsRouteId: "auth.workspaces" },
  "command-center": { path: "/command-center", analyticsRouteId: "home.command-center" },
  forbidden: { path: "/forbidden", analyticsRouteId: "auth.forbidden" },

  // Accounts
  accounts: { path: "/t/:tenantSlug/accounts", params: ["tenantSlug"], analyticsRouteId: "accounts.list" },
  "account-detail": { path: "/t/:tenantSlug/accounts/:accountId", params: ["tenantSlug", "accountId"], analyticsRouteId: "accounts.detail" },
  "account-overview": { path: "/t/:tenantSlug/accounts/:accountId/overview", params: ["tenantSlug", "accountId"], analyticsRouteId: "accounts.overview" },

  // Intelligence Workspace
  intelligence: { path: "/t/:tenantSlug/accounts/:accountId/intelligence", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.workspace" },
  "intelligence-overview": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/overview", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.overview" },
  "intelligence-signals": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/signals", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.signals" },
  "intelligence-stakeholders": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/stakeholders", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.stakeholders" },
  "intelligence-enrichment": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/enrichment", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.enrichment" },
  "intelligence-ontology": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/ontology", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.ontology" },
  "intelligence-hypotheses": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/hypotheses", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.hypotheses" },
  "intelligence-discovery": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/discovery-questions", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.discovery" },
  "intelligence-persona": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/persona-fit", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.persona" },
  "intelligence-assumptions": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/assumptions", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.assumptions" },
  "intelligence-drivers": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/drivers", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.drivers" },
  "intelligence-evidence": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/evidence", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.evidence" },
  "intelligence-alternatives": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/alternatives", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.alternatives" },
  "intelligence-solution-cost": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/solution-cost", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.solution-cost" },

  // Value Studio Workspace
  studio: { path: "/t/:tenantSlug/accounts/:accountId/studio", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.workspace" },
  "studio-action-plan": { path: "/t/:tenantSlug/accounts/:accountId/studio/action-plan", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.action-plan" },
  "studio-value-model": { path: "/t/:tenantSlug/accounts/:accountId/studio/value-model", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.value-model" },
  "studio-driver-tree": { path: "/t/:tenantSlug/accounts/:accountId/studio/driver-tree", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.driver-tree" },
  "studio-calculator": { path: "/t/:tenantSlug/accounts/:accountId/studio/calculator", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.calculator" },
  "studio-narrative": { path: "/t/:tenantSlug/accounts/:accountId/studio/narrative", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.narrative" },
  "studio-value-case": { path: "/t/:tenantSlug/accounts/:accountId/studio/value-case", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.value-case" },
  "studio-value-realization": { path: "/t/:tenantSlug/accounts/:accountId/studio/value-realization", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.value-realization" },
  "studio-solution-cost": { path: "/t/:tenantSlug/accounts/:accountId/studio/solution-cost", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.solution-cost" },

  // Deliverables
  deliverables: { path: "/t/:tenantSlug/accounts/:accountId/deliverables", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.workspace" },
  "deliverables-business-cases": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.business-cases" },
  "deliverables-business-case-detail": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases/:caseId", params: ["tenantSlug", "accountId", "caseId"], analyticsRouteId: "deliverables.business-case-detail" },
  "deliverables-proposals": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/proposals", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.proposals" },
  "deliverables-exports": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/exports", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.exports" },
  "deliverables-cfo-view": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/cfo", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.cfo-view" },
  "deliverables-executive-view": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/executive", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.executive-view" },
  "deliverables-technical-view": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/technical", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.technical-view" },

  // Context Engine
  context: { path: "/t/:tenantSlug/context", params: ["tenantSlug"], analyticsRouteId: "context.workspace" },
  "context-sources": { path: "/t/:tenantSlug/context/sources", params: ["tenantSlug"], analyticsRouteId: "context.sources" },
  "context-source-detail": { path: "/t/:tenantSlug/context/sources/:sourceId", params: ["tenantSlug", "sourceId"], analyticsRouteId: "context.source-detail" },
  "context-entities": { path: "/t/:tenantSlug/context/entities", params: ["tenantSlug"], analyticsRouteId: "context.entities" },
  "context-entity-detail": { path: "/t/:tenantSlug/context/entities/:entityId", params: ["tenantSlug", "entityId"], analyticsRouteId: "context.entity-detail" },
  "context-graph": { path: "/t/:tenantSlug/context/graph", params: ["tenantSlug"], analyticsRouteId: "context.graph" },
  "context-ingestion-runs": { path: "/t/:tenantSlug/context/ingestion-runs", params: ["tenantSlug"], analyticsRouteId: "context.ingestion-runs" },
  "context-ingestion-run-detail": { path: "/t/:tenantSlug/context/ingestion-runs/:runId", params: ["tenantSlug", "runId"], analyticsRouteId: "context.ingestion-run-detail" },
  "context-extraction": { path: "/t/:tenantSlug/context/extraction", params: ["tenantSlug"], analyticsRouteId: "context.extraction" },
  "context-ontology": { path: "/t/:tenantSlug/context/ontology", params: ["tenantSlug"], analyticsRouteId: "context.ontology" },
  "context-agents": { path: "/t/:tenantSlug/context/agents", params: ["tenantSlug"], analyticsRouteId: "context.agents" },
  "context-integrations": { path: "/t/:tenantSlug/context/integrations", params: ["tenantSlug"], analyticsRouteId: "context.integrations" },

  // Governance
  governance: { path: "/t/:tenantSlug/governance", params: ["tenantSlug"], analyticsRouteId: "governance.workspace" },
  "governance-traces": { path: "/t/:tenantSlug/governance/traces", params: ["tenantSlug"], analyticsRouteId: "governance.traces" },
  "governance-evidence": { path: "/t/:tenantSlug/governance/evidence", params: ["tenantSlug"], analyticsRouteId: "governance.evidence" },
  "governance-provenance": { path: "/t/:tenantSlug/governance/provenance", params: ["tenantSlug"], analyticsRouteId: "governance.provenance" },
  "governance-compliance": { path: "/t/:tenantSlug/governance/compliance", params: ["tenantSlug"], analyticsRouteId: "governance.compliance" },
  "governance-formulas": { path: "/t/:tenantSlug/governance/formulas", params: ["tenantSlug"], analyticsRouteId: "governance.formulas" },
  "governance-formula-detail": { path: "/t/:tenantSlug/governance/formulas/:formulaId", params: ["tenantSlug", "formulaId"], analyticsRouteId: "governance.formula-detail" },
  "governance-benchmarks": { path: "/t/:tenantSlug/governance/benchmarks", params: ["tenantSlug"], analyticsRouteId: "governance.benchmarks" },
  "governance-benchmark-detail": { path: "/t/:tenantSlug/governance/benchmarks/:benchmarkId", params: ["tenantSlug", "benchmarkId"], analyticsRouteId: "governance.benchmark-detail" },
  "governance-value-packs": { path: "/t/:tenantSlug/governance/value-packs", params: ["tenantSlug"], analyticsRouteId: "governance.value-packs" },
  "governance-value-pack-detail": { path: "/t/:tenantSlug/governance/value-packs/:packId", params: ["tenantSlug", "packId"], analyticsRouteId: "governance.value-pack-detail" },
  "governance-policies": { path: "/t/:tenantSlug/governance/policies", params: ["tenantSlug"], analyticsRouteId: "governance.policies" },
  "governance-audit-log": { path: "/t/:tenantSlug/governance/audit-log", params: ["tenantSlug"], analyticsRouteId: "governance.audit-log" },
  "governance-health": { path: "/t/:tenantSlug/governance/health", params: ["tenantSlug"], analyticsRouteId: "governance.health" },
  "governance-billing": { path: "/t/:tenantSlug/governance/billing", params: ["tenantSlug"], analyticsRouteId: "governance.billing" },

  // Agents & Workflows
  agents: { path: "/t/:tenantSlug/accounts/:accountId/agents", params: ["tenantSlug", "accountId"], analyticsRouteId: "agents.console" },
  "agents-thread": { path: "/t/:tenantSlug/accounts/:accountId/agents/threads/:threadId", params: ["tenantSlug", "accountId", "threadId"], analyticsRouteId: "agents.thread" },
  workflows: { path: "/t/:tenantSlug/accounts/:accountId/workflows", params: ["tenantSlug", "accountId"], analyticsRouteId: "agents.workflows" },
  "workflow-run": { path: "/t/:tenantSlug/accounts/:accountId/workflows/:workflowRunId", params: ["tenantSlug", "accountId", "workflowRunId"], analyticsRouteId: "agents.workflow-run" },

  // Academy (tenant-scoped)
  academy: { path: "/t/:tenantSlug/academy", params: ["tenantSlug"], analyticsRouteId: "academy.workspace" },
  "academy-pillar": { path: "/t/:tenantSlug/academy/pillars/:pillarId", params: ["tenantSlug", "pillarId"], analyticsRouteId: "academy.pillar" },
  "academy-quiz": { path: "/t/:tenantSlug/academy/pillars/:pillarId/quiz", params: ["tenantSlug", "pillarId"], analyticsRouteId: "academy.quiz" },
  "academy-resources": { path: "/t/:tenantSlug/academy/resources", params: ["tenantSlug"], analyticsRouteId: "academy.resources" },
  "academy-profile": { path: "/t/:tenantSlug/academy/profile", params: ["tenantSlug"], analyticsRouteId: "academy.profile" },

  // Settings — Personal (global)
  "settings-profile": { path: "/settings/profile", analyticsRouteId: "settings.profile" },
  "settings-security": { path: "/settings/security", analyticsRouteId: "settings.security" },
  "settings-preferences": { path: "/settings/preferences", analyticsRouteId: "settings.preferences" },
  "settings-notifications": { path: "/settings/notifications", analyticsRouteId: "settings.notifications" },
  "settings-sessions": { path: "/settings/sessions", analyticsRouteId: "settings.sessions" },
  "settings-activity": { path: "/settings/activity", analyticsRouteId: "settings.activity" },

  // Settings — Tenant (tenant-scoped)
  "tenant-settings": { path: "/t/:tenantSlug/settings", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.workspace" },
  "tenant-settings-workspace": { path: "/t/:tenantSlug/settings/workspace", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.workspace-profile" },
  "tenant-settings-billing": { path: "/t/:tenantSlug/settings/billing", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.billing" },
  "tenant-settings-subscription": { path: "/t/:tenantSlug/settings/billing/subscription", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.subscription" },
  "tenant-settings-usage": { path: "/t/:tenantSlug/settings/billing/usage", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.usage" },
  "tenant-settings-payment-methods": { path: "/t/:tenantSlug/settings/billing/payment-methods", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.payment-methods" },
  "tenant-settings-invoices": { path: "/t/:tenantSlug/settings/billing/invoices", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.invoices" },
  "tenant-settings-users": { path: "/t/:tenantSlug/settings/users", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.users" },
  "tenant-settings-roles": { path: "/t/:tenantSlug/settings/roles", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.roles" },
  "tenant-settings-permissions": { path: "/t/:tenantSlug/settings/permissions", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.permissions" },
  "tenant-settings-api-keys": { path: "/t/:tenantSlug/settings/api-keys", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.api-keys" },
  "tenant-settings-data-sources": { path: "/t/:tenantSlug/settings/data-sources", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.data-sources" },
  "tenant-settings-integrations": { path: "/t/:tenantSlug/settings/integrations", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.integrations" },
  "tenant-settings-variables": { path: "/t/:tenantSlug/settings/variables", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.variables" },
  "tenant-settings-value-packs": { path: "/t/:tenantSlug/settings/value-packs", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.value-packs" },
  "tenant-settings-ingestion-rules": { path: "/t/:tenantSlug/settings/ingestion-rules", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.ingestion-rules" },
  "tenant-settings-governance-policies": { path: "/t/:tenantSlug/settings/governance/policies", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.governance-policies" },
  "tenant-settings-governance-compliance": { path: "/t/:tenantSlug/settings/governance/compliance", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.governance-compliance" },
  "tenant-settings-governance-health": { path: "/t/:tenantSlug/settings/governance/health", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.governance-health" },
  "tenant-settings-governance-audit": { path: "/t/:tenantSlug/settings/governance/audit", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.governance-audit" },
  "tenant-settings-governance-admin": { path: "/t/:tenantSlug/settings/governance/admin", params: ["tenantSlug"], analyticsRouteId: "tenant-settings.governance-admin" },

  // Dev Tools
  "dev-integration": { path: "/dev/integration", analyticsRouteId: "dev.integration" },

  // Legacy aliases (map old route states to canonical paths)
  hypothesis: { path: "/t/:tenantSlug/accounts/:accountId/intelligence/hypotheses", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.hypotheses" },
  drivers: { path: "/t/:tenantSlug/accounts/:accountId/intelligence/drivers", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.drivers" },
  "drivers-evidence": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/evidence", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.evidence" },
  calculator: { path: "/t/:tenantSlug/accounts/:accountId/studio/calculator", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.calculator" },
  "value-case": { path: "/t/:tenantSlug/accounts/:accountId/studio/value-case", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.value-case" },
  realization: { path: "/t/:tenantSlug/accounts/:accountId/studio/value-realization", params: ["tenantSlug", "accountId"], analyticsRouteId: "studio.value-realization" },
  "formula-builder": { path: "/t/:tenantSlug/context/formulas/:formulaId", params: ["tenantSlug", "formulaId"], analyticsRouteId: "context.formula-detail" },
  "formula-new": { path: "/t/:tenantSlug/context/formulas/new", params: ["tenantSlug"], analyticsRouteId: "context.formulas-new" },
  "business-case-detail": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases/:caseId", params: ["tenantSlug", "accountId", "caseId"], analyticsRouteId: "deliverables.business-case-detail" },
  "business-cases": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.business-cases" },
  "business-case-interactive": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/calculators", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.calculators" },
  "business-case-new": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases/new", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.business-case-new" },
  "decision-trace": { path: "/t/:tenantSlug/governance/traces", params: ["tenantSlug"], analyticsRouteId: "governance.traces" },
  "model-detail": { path: "/t/:tenantSlug/context/models/:modelId", params: ["tenantSlug", "modelId"], analyticsRouteId: "context.model-detail" },
  integrations: { path: "/t/:tenantSlug/context/integrations", params: ["tenantSlug"], analyticsRouteId: "context.integrations" },
  "cfo-view": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/cfo", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.cfo-view" },
  "executive-view": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/executive", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.executive-view" },
  "technical-view": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/technical", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.technical-view" },
  "interactive-calculator": { path: "/t/:tenantSlug/accounts/:accountId/deliverables/calculators", params: ["tenantSlug", "accountId"], analyticsRouteId: "deliverables.calculators" },
  opportunities: { path: "/t/:tenantSlug/accounts/:accountId/intelligence/signals", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.signals" },
  "opportunity-scan": { path: "/t/:tenantSlug/accounts/:accountId/intelligence/signals", params: ["tenantSlug", "accountId"], analyticsRouteId: "intelligence.signals" },
  // Legacy personal settings aliases
  "personal-profile": { path: "/settings/profile", analyticsRouteId: "settings.profile" },
  "personal-security": { path: "/settings/security", analyticsRouteId: "settings.security" },
  "personal-preferences": { path: "/settings/preferences", analyticsRouteId: "settings.preferences" },
  "personal-notifications": { path: "/settings/notifications", analyticsRouteId: "settings.notifications" },
  "personal-sessions": { path: "/settings/sessions", analyticsRouteId: "settings.sessions" },
};

// ─────────────────────────────────────────────────────────────────────────────
// Navigation Functions
// ─────────────────────────────────────────────────────────────────────────────

export type NavigationParams = Record<string, string | number | undefined>;

/**
 * Build a URL path by substituting parameters into the route template.
 */
export function buildPath(
  pathTemplate: string,
  params: NavigationParams = {}
): string {
  let path = pathTemplate;

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) continue;
    path = path.replace(`:${key}`, String(value));
  }

  // Remove any remaining optional params that weren't provided
  path = path.replace(/\/:[^/]+/g, "");

  return path;
}

/**
 * Get the URL path for a given route state with parameters.
 */
export function getStatePath(
  state: RouteState,
  params?: NavigationParams
): string {
  const config = ROUTE_MAP[state];
  if (!config) {
    throw new Error(`Unknown route state: ${state}`);
  }
  return buildPath(config.path, params);
}

/**
 * Resolve a navigation target for react-router's navigate() function.
 */
export function getNavigateTarget(
  state: RouteState,
  params?: NavigationParams
): { to: To; options?: NavigateOptions } {
  const path = getStatePath(state, params);
  return { to: path };
}

/**
 * Check if a route state requires specific parameters.
 */
export function stateRequiresParams(state: RouteState): string[] {
  return ROUTE_MAP[state]?.params ?? [];
}

/**
 * Validate that all required parameters are provided for a route state.
 */
export function validateStateParams(
  state: RouteState,
  params?: NavigationParams
): { valid: boolean; missing: string[] } {
  const required = stateRequiresParams(state);
  const missing = required.filter((param) => params?.[param] === undefined);
  return { valid: missing.length === 0, missing };
}

// ── Legacy compatibility helpers ─────────────────────────────────────────────

const WORKSPACE_PREFIXES = [
  "/t/:tenantSlug/accounts/:accountId/intelligence",
  "/t/:tenantSlug/accounts/:accountId/studio",
  "/t/:tenantSlug/accounts/:accountId/deliverables",
  "/t/:tenantSlug/accounts/:accountId/agents",
  "/t/:tenantSlug/accounts/:accountId/workflows",
];

/**
 * Resolve a workspace path with an account ID and tenant slug.
 */
export function resolveWorkspacePath(
  path: string,
  accountId: string | null,
  tenantSlug?: string | null
): string {
  if (!accountId) return path;

  if (path.includes(accountId)) return path;

  for (const prefix of WORKSPACE_PREFIXES) {
    const template = prefix.replace(":tenantSlug", tenantSlug ?? ":tenantSlug");
    if (path === template) {
      return template.replace(":accountId", accountId);
    }
    if (path.startsWith(`${template}/`)) {
      const suffix = path.slice(template.length + 1);
      return `${template.replace(":accountId", accountId)}/${suffix}`;
    }
  }

  return path;
}

// ─────────────────────────────────────────────────────────────────────────────
// Re-export for convenience
// ─────────────────────────────────────────────────────────────────────────────

export type { UserTier } from "@/routes/types";

export interface NavItem {
  id: string;
  label: string;
  icon?: ReactNode;
  path: string;
  tier: Exclude<UserTier, "unknown">;
  children?: NavItem[];
  badge?: string | number;
  description?: string;
}

export function isItemVisible(
  item: NavItem,
  userTier: Exclude<UserTier, "unknown">
): boolean {
  if (userTier === "admin") return true;
  if (userTier === "advanced") return item.tier !== "admin";
  return item.tier === "standard";
}

export function isRouteActive(location: string, resolvedPath: string): boolean {
  const normalize = (value: string) => value.replace(/\/+$/, "") || "/";
  const current = normalize(location);
  const route = normalize(resolvedPath.replace(/\/\*$/, ""));

  if (route === "/") {
    return current === "/";
  }

  return current === route || current.startsWith(route + "/");
}
