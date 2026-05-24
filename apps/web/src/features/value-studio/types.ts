/**
 * Value Studio Workspace — Shared Types
 */
import type { ComponentType } from "react";

export interface StudioTabProps {
  accountId: string;
  workspaceId?: string;
  organizationId?: string;
}

export type StudioTabId =
  | "action-plan"
  | "value-model"
  | "driver-tree"
  | "calculator"
  | "narrative"
  | "value-case"
  | "value-realization"
  | "solution-cost";

export type StudioTabStatus = "active" | "stub";

export type StudioTabCategory = "input" | "synthesis" | "output";

export interface StudioTabDef {
  id: StudioTabId;
  label: string;
  description: string;
  component: ComponentType<StudioTabProps> | null;
  queryKey?: string;
  status: StudioTabStatus;
  category: StudioTabCategory;
}
