/**
 * Intelligence Workspace — Shared Types
 */
import type { ComponentType } from "react";

export interface WorkspaceTabProps {
  accountId: string;
  workspaceId?: string;
  organizationId?: string;
}

export type IntelligenceTabId =
  | "overview"
  | "signals"
  | "stakeholders"
  | "ontology-match"
  | "enrichment"
  | "hypotheses"
  | "discovery-questions"
  | "persona-fit"
  | "assumptions"
  | "drivers"
  | "evidence"
  | "alternatives"
  | "solution-cost";

export type WorkspaceTabStatus = "active" | "stub";

export type WorkspaceTabCategory = "input" | "reasoning" | "output";

export interface WorkspaceTabDef {
  id: IntelligenceTabId;
  label: string;
  description: string;
  component: ComponentType<WorkspaceTabProps> | null;
  queryKey?: string;
  status: WorkspaceTabStatus;
  category: WorkspaceTabCategory;
  /**
   * Core views form the primary value-case workspace chain
   * (Overview → Signals → Drivers → Evidence → Stakeholders).
   * They lead the tab bar and are always visible; non-core tabs are secondary.
   */
  core?: boolean;
}
