/**
 * Intelligence Workspace — Tab Registry
 *
 * Single source of truth for all intelligence workspace tabs.
 */
import { lazy } from "react";
import type { IntelligenceTabId, WorkspaceTabDef } from "./types";

const isProductionBuild = import.meta.env.PROD || import.meta.env.VITE_APP_ENV === "production";

const deferredIntelligenceTabs: Record<string, { flag: string; owner: string }> = {
  "ontology-match": {
    flag: "VITE_ENABLE_IW_ONTOLOGY_MATCH_TAB",
    owner: "Intelligence Workspace / Layer 4 Agents",
  },
  alternatives: {
    flag: "VITE_ENABLE_IW_ALTERNATIVES_TAB",
    owner: "Intelligence Workspace / Product Strategy",
  },
  "solution-cost": {
    flag: "VITE_ENABLE_IW_SOLUTION_COST_TAB",
    owner: "Intelligence Workspace / Value Modeling",
  },
};

function isDeferredTabEnabled(tabId: string): boolean {
  const config = deferredIntelligenceTabs[tabId];
  if (!config) return true;
  return import.meta.env[config.flag] === "true";
}

// ── Lazy-loaded tab components ────────────────────────────────────────────────
const SignalsTab = lazy(() => import("./tabs/signals/SignalsTab"));
const StakeholdersTab = lazy(() => import("./tabs/stakeholders/StakeholdersTab"));
const OntologyMatchTab = lazy(() => import("./tabs/ontology-match/OntologyMatchTab"));
const EnrichmentTab = lazy(() => import("./tabs/enrichment/EnrichmentTab"));
const HypothesesTab = lazy(() => import("./tabs/hypotheses/HypothesesTab"));
const DiscoveryQuestionsTab = lazy(() => import("@/pages/hypothesis/DiscoveryQuestionsTab"));
const PersonaFitTab = lazy(() => import("@/pages/hypothesis/PersonaFitTab"));
const AssumptionsTab = lazy(() => import("@/pages/hypothesis/AssumptionsTab"));
const DriversTab = lazy(() => import("./tabs/drivers/DriversTab"));
const EvidenceTab = lazy(() => import("./tabs/evidence/EvidenceTab"));
const AlternativesTab = lazy(() => import("./tabs/alternatives/AlternativesTab"));
const SolutionCostTab = lazy(() => import("./tabs/solution-cost/SolutionCostTab"));

// ── Registry ──────────────────────────────────────────────────────────────────
export const workspaceTabs: WorkspaceTabDef[] = [
  {
    id: "signals",
    label: "Signals",
    description: "Displays raw market signals and triggers workspace generation.",
    component: SignalsTab,
    queryKey: "signals",
    status: "active",
    category: "input",
  },
  {
    id: "enrichment",
    label: "Account Enrichment",
    description: "Shows deep account enrichment data including firmographics and tech stack.",
    component: EnrichmentTab,
    status: "active",
    category: "input",
  },
  {
    id: "stakeholders",
    label: "Stakeholders",
    description: "Identifies key buyer personas and their priorities.",
    component: StakeholdersTab,
    queryKey: "stakeholders",
    status: "active",
    category: "input",
  },
  {
    id: "ontology-match",
    label: "Value Ontology",
    description: "Maps account context to the value ontology.",
    component: OntologyMatchTab,
    status: "stub",
    category: "reasoning",
  },
  {
    id: "hypotheses",
    label: "Value Hypotheses",
    description: "Manages AI-generated value hypotheses for the account.",
    component: HypothesesTab,
    status: "active",
    category: "reasoning",
  },
  {
    id: "discovery-questions",
    label: "Discovery Questions",
    description: "Structured discovery questions for prospect engagement.",
    component: DiscoveryQuestionsTab,
    status: "active",
    category: "reasoning",
  },
  {
    id: "persona-fit",
    label: "Persona Fit",
    description: "Maps hypotheses to buyer personas.",
    component: PersonaFitTab,
    status: "active",
    category: "reasoning",
  },
  {
    id: "assumptions",
    label: "Assumptions",
    description: "Tracks key assumptions and their validation status.",
    component: AssumptionsTab,
    status: "active",
    category: "reasoning",
  },
  {
    id: "drivers",
    label: "Value Drivers",
    description: "Maps signals to specific business value drivers.",
    component: DriversTab,
    queryKey: "drivers",
    status: "active",
    category: "reasoning",
  },
  {
    id: "evidence",
    label: "Evidence",
    description: "Lists verified evidence points supporting the drivers.",
    component: EvidenceTab,
    queryKey: "evidence",
    status: "active",
    category: "reasoning",
  },
  {
    id: "alternatives",
    label: "Alternatives",
    description: "Competitor and alternative solution comparison.",
    component: AlternativesTab,
    status: "stub",
    category: "input",
  },
  {
    id: "solution-cost",
    label: "Solution Cost",
    description: "Pricing and cost inputs for the business case.",
    component: SolutionCostTab,
    status: "stub",
    category: "input",
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────
export const DEFAULT_TAB: IntelligenceTabId = "signals";

export function getProductionTabDefs(): WorkspaceTabDef[] {
  return workspaceTabs.filter((tab) => {
    if (tab.status === "active") return true;
    return !isProductionBuild && isDeferredTabEnabled(tab.id);
  });
}

export function getTabDef(tabId: IntelligenceTabId): WorkspaceTabDef | undefined {
  return getProductionTabDefs().find((t) => t.id === tabId);
}

export function isValidTab(tabId: string | undefined): tabId is IntelligenceTabId {
  return Boolean(tabId) && getProductionTabDefs().some((t) => t.id === tabId);
}

export function getTabOrDefault(tabId: string | undefined): IntelligenceTabId {
  return isValidTab(tabId) ? tabId : DEFAULT_TAB;
}

export function getActiveTabDefs(): WorkspaceTabDef[] {
  return getProductionTabDefs();
}

export const deferredTabsRollout = deferredIntelligenceTabs;
