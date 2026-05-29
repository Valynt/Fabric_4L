/**
 * Navigation context utilities — URL-serialisable cross-page state.
 *
 * Formerly @/workflow/context. Moved here so navigation-context
 * serialisation is decoupled from the (now-deleted) workflow wizard.
 */

export const WORKFLOW_CONTEXT_QUERY_KEYS = {
  sessionId: "wfSessionId",
  accountId: "wfAccountId",
  workspaceCaseId: "wfWorkspaceCaseId",
  activeStep: "wfStep",
  activeTab: "wfTab",
  driverTreeId: "wfDriverTreeId",
  scenarioId: "wfScenarioId",
  businessCaseId: "wfBusinessCaseId",
} as const;

export interface WorkflowStepMetadata {
  stepIndex: number;
  stepKey: string;
  activeTab?: string;
}

export interface WorkflowContext {
  sessionId: string;
  accountId: string;
  step: WorkflowStepMetadata;
  workspaceCaseId?: string;
  driverTreeId?: string;
  scenarioId?: string;
  businessCaseId?: string;
}

export function serializeWorkflowContextToQuery(
  context: Partial<WorkflowContext>,
): Record<string, string> {
  const query: Record<string, string> = {};
  if (context.sessionId)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.sessionId] = context.sessionId;
  if (context.accountId)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.accountId] = context.accountId;
  if (context.workspaceCaseId)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.workspaceCaseId] = context.workspaceCaseId;
  if (context.step?.activeTab)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.activeTab] = context.step.activeTab;
  if (typeof context.step?.stepIndex === "number")
    query[WORKFLOW_CONTEXT_QUERY_KEYS.activeStep] = String(
      context.step.stepIndex,
    );
  if (context.driverTreeId)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.driverTreeId] = context.driverTreeId;
  if (context.scenarioId)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.scenarioId] = context.scenarioId;
  if (context.businessCaseId)
    query[WORKFLOW_CONTEXT_QUERY_KEYS.businessCaseId] = context.businessCaseId;
  return query;
}
