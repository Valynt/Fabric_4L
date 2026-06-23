import { useMemo } from "react";
import { useLocation } from "react-router-dom";
import { WORKFLOW_CONTEXT_QUERY_KEYS, type WorkflowContext } from "@/stores/navigationContext";

export function useWorkflowContext(): Partial<WorkflowContext> {
  const location = useLocation();

  return useMemo(() => {
    const query = new URLSearchParams(location.search);
    const accountId = query.get(WORKFLOW_CONTEXT_QUERY_KEYS.accountId) ?? undefined;
    const sessionId = query.get(WORKFLOW_CONTEXT_QUERY_KEYS.sessionId) ?? undefined;
    const activeTab = query.get(WORKFLOW_CONTEXT_QUERY_KEYS.activeTab) ?? undefined;
    const stepIndex = query.get(WORKFLOW_CONTEXT_QUERY_KEYS.activeStep);

    return {
      accountId,
      sessionId,
      step: {
        stepIndex: stepIndex !== null ? Number(stepIndex) : 0,
        stepKey: "unknown",
        activeTab,
      },
      workspaceCaseId: query.get(WORKFLOW_CONTEXT_QUERY_KEYS.workspaceCaseId) ?? undefined,
      driverTreeId: query.get(WORKFLOW_CONTEXT_QUERY_KEYS.driverTreeId) ?? undefined,
      scenarioId: query.get(WORKFLOW_CONTEXT_QUERY_KEYS.scenarioId) ?? undefined,
      businessCaseId: query.get(WORKFLOW_CONTEXT_QUERY_KEYS.businessCaseId) ?? undefined,
    };
  }, [location.search]);
}
