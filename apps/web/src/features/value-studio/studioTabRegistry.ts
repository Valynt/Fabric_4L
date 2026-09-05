/**
 * Value Studio Workspace — Tab Registry
 *
 * Single source of truth for all Value Studio workspace tabs.
 */
import { lazy } from "react";
import type { StudioTabId, StudioTabDef } from "./types";
import { isValueStudioMissionPrototypeEnabled } from "./mission/prototype";
import ActionPlanRail from "./rails/ActionPlanRail";
import ValueModelRail from "./rails/ValueModelRail";
import DriverTreeRail from "./rails/DriverTreeRail";
import CalculatorRail from "./rails/CalculatorRail";
import NarrativeRail from "./rails/NarrativeRail";
import ValueCaseRail from "./rails/ValueCaseRail";
import RealizationRail from "./rails/RealizationRail";

const isProductionBuild = import.meta.env.PROD || import.meta.env.VITE_APP_ENV === "production";

const deferredStudioTabs: Record<string, { flag: string; owner: string }> = {
  "solution-cost": {
    flag: "VITE_ENABLE_VS_SOLUTION_COST_TAB",
    owner: "Value Studio / Value Modeling",
  },
};

const deferredStudioTabFlagValues: Record<string, string | undefined> = {
  VITE_ENABLE_VS_SOLUTION_COST_TAB: import.meta.env.VITE_ENABLE_VS_SOLUTION_COST_TAB,
};

function isDeferredTabEnabled(tabId: string): boolean {
  const config = deferredStudioTabs[tabId];
  if (!config) return true;
  return deferredStudioTabFlagValues[config.flag] === "true";
}

// ── Lazy-loaded tab components ────────────────────────────────────────────────
const ActionPlanTab = lazy(() => import("@/pages/studio/ActionPlanTab"));
const ValueModelTab = lazy(() => import("@/pages/studio/ValueModelTab"));
const NarrativeTab = lazy(() => import("@/pages/studio/NarrativeTab"));
const DriverTreeTab = lazy(() => import("@/pages/drivers/DriverTreePage"));
const CalculatorTab = lazy(() => import("@/pages/calculator/ROITab"));
const ValueCaseTab = lazy(() => import("@/pages/value-case/ValueCasePage"));
const RealizationTab = lazy(() => import("@/pages/realization/RealizationPage"));
const SolutionCostTab = lazy(() => import("@/features/intelligence-workspace/tabs/solution-cost/SolutionCostTab"));
const MissionTab = lazy(() => import("@/features/value-studio/mission/ValueStudioPage"));

// ── Registry ──────────────────────────────────────────────────────────────────
export const studioTabs: StudioTabDef[] = [
  {
    id: "mission",
    label: "Mission",
    description: "Mission-led value studio workspace (prototype preview).",
    component: MissionTab,
    status: "stub",
    category: "synthesis",
  },
  {
    id: "action-plan",
    label: "Action Plan",
    description: "Product-anchored intervention plan mapping pain to capabilities.",
    component: ActionPlanTab,
    rightRail: ActionPlanRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "value-model",
    label: "Value Model",
    description: "Quantified value model behind the business case.",
    component: ValueModelTab,
    queryKey: "value-model",
    rightRail: ValueModelRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "driver-tree",
    label: "Driver Tree",
    description: "Interactive value driver tree editor.",
    component: DriverTreeTab,
    rightRail: DriverTreeRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "calculator",
    label: "ROI Calculator",
    description: "Interactive ROI calculator inputs and outputs.",
    component: CalculatorTab,
    rightRail: CalculatorRail,
    status: "active",
    category: "synthesis",
  },
  {
    id: "narrative",
    label: "Narrative",
    description: "Storytelling layer for the value case.",
    component: NarrativeTab,
    queryKey: "narrative",
    rightRail: NarrativeRail,
    status: "active",
    category: "output",
  },
  {
    id: "value-case",
    label: "Executive Value Case",
    description: "Generates the final written narrative and messaging.",
    component: ValueCaseTab,
    queryKey: "value-case",
    rightRail: ValueCaseRail,
    status: "active",
    category: "output",
  },
  {
    id: "value-realization",
    label: "Realization Plan",
    description: "Step-by-step plan turning validated hypotheses into milestones.",
    component: RealizationTab,
    queryKey: "action-plan",
    rightRail: RealizationRail,
    status: "active",
    category: "output",
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
export const DEFAULT_STUDIO_TAB: StudioTabId = "action-plan";

export function getProductionStudioTabDefs(): StudioTabDef[] {
  return studioTabs.filter((tab) => {
    // Mission is the prototype-gated Slice 1 surface: dev default-on, prod
    // only when VITE_ENABLE_VS_MISSION_PROTOTYPE=true (mission/prototype.ts).
    if (tab.id === "mission") return isValueStudioMissionPrototypeEnabled;
    if (tab.status === "active") return true;
    return !isProductionBuild && isDeferredTabEnabled(tab.id);
  });
}

export function getStudioTabDef(tabId: StudioTabId): StudioTabDef | undefined {
  return getProductionStudioTabDefs().find((t) => t.id === tabId);
}

export function isValidStudioTab(tabId: string | undefined): tabId is StudioTabId {
  return Boolean(tabId) && getProductionStudioTabDefs().some((t) => t.id === tabId);
}

export function getStudioTabOrDefault(tabId: string | undefined): StudioTabId {
  return isValidStudioTab(tabId) ? tabId : DEFAULT_STUDIO_TAB;
}

export function getActiveStudioTabDefs(): StudioTabDef[] {
  return getProductionStudioTabDefs();
}

export const deferredStudioTabsRollout = deferredStudioTabs;
