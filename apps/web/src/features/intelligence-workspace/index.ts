export { default as IntelligenceWorkspace } from "./IntelligenceWorkspace";
export { default as IntelligenceWorkspaceTabs } from "./IntelligenceWorkspaceTabs";
export { workspaceTabs, getTabDef, isValidTab, getTabOrDefault, DEFAULT_TAB } from "./workspaceTabRegistry";
export { workspacePath, workspaceBasePath, parseWorkspaceRoute } from "./workspaceRoutes";
export type { WorkspaceTabProps, IntelligenceTabId, WorkspaceTabDef } from "./types";
export { useWorkspaceContext, useWorkspaceReadiness } from "./hooks";
