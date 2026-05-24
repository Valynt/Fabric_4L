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
}
