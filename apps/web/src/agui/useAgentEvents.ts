/**
 * useAgentEvents — React hook for AG-UI protocol event consumption.
 *
 * This hook is the primary interface between workspace tabs and the agent
 * co-pilot. It exposes:
 *
 *   - `messages`         : Chat history (same shape as before for backward compat)
 *   - `steps`            : Current run's step progression (for ProcessSteps component)
 *   - `runState`         : Lifecycle state (idle | running | finished | error)
 *   - `sendMessage`      : Send a user message and trigger an agent run
 *   - `suggestedActions`  : Context-aware action buttons
 *   - `currentRunId`     : Active run correlation ID
 *   - `lastError`        : Most recent error message
 *   - `metadata`         : Run metadata (trace, workflow, tenant IDs)
 *
 * UI Contract (Behavior):
 *   - Calling `sendMessage` transitions runState: idle → running → finished|error
 *   - Steps progress from pending → active → done as events arrive
 *   - Messages accumulate across runs (conversation history)
 *   - The hook is fully backward-compatible with the RightRail props interface
 *
 * UI Contract (Data):
 *   - `messages` array uses the same `AgentMessage` type from RightRail
 *   - `steps` array uses `StepSnapshot` from AG-UI events
 *   - `suggestedActions` uses the same `AgentAction` type from RightRail
 */

import { useState, useCallback, useRef, useEffect } from "react";
import type { AgentMessage, AgentAction } from "@/components/workspace/RightRail";
import {
  AgentEventType,
  type AgentEvent,
} from "./events";
import { sendAgentMessage } from "./AgentEventClient";
import { useApplyWorkspacePageAction, type WorkspacePageActionContract } from "@/hooks/useWorkspaceCase";
import { useWorkflowContext } from "@/hooks/useWorkflowContext";
import {
  createInitialAgentState,
  reduceAgentEvent,
  type AgentState,
  type RunState,
} from "./agentEventReducer";
import { buildConversationContext } from "./agentConversationContext";

// ── Suggested Actions by Tab ────────────────────────────────────────────────

export function getDefaultSuggestedActions(
  activeTab: string,
  sendMessage?: (input: string) => void,
): AgentAction[] {
  const send = sendMessage ?? (() => {});
  switch (activeTab) {
    case "signals":
      return [
        { label: "Generate value driver tree", onClick: () => send("Generate a value driver tree from the current signals") },
        { label: "Summarize evidence", onClick: () => send("Summarize the evidence for the top signals") },
        { label: "Draft action plan", onClick: () => send("Draft an action plan based on these signals") },
        { label: "Compare all signals", onClick: () => send("Compare all signals by confidence and impact") },
      ];
    case "drivers":
      return [
        { label: "Map to product capabilities", onClick: () => send("Map these drivers to our product capabilities") },
        { label: "Find missing drivers", onClick: () => send("Are there any missing drivers we should consider?") },
        { label: "Prioritize by impact", onClick: () => send("Prioritize the drivers by estimated business impact") },
      ];
    case "evidence":
      return [
        { label: "Find more evidence", onClick: () => send("Find additional evidence to support our claims") },
        { label: "Audit weak claims", onClick: () => send("Audit the claims and flag any that need stronger evidence") },
        { label: "Export evidence summary", onClick: () => send("Create an evidence summary I can export") },
      ];
    case "stakeholders":
      return [
        { label: "Suggest messaging angles", onClick: () => send("Suggest messaging angles for each stakeholder") },
        { label: "Identify missing buyers", onClick: () => send("Identify any missing buyer personas we should engage") },
        { label: "Map influence network", onClick: () => send("Map the influence network among these stakeholders") },
      ];
    case "action-plan":
      return [
        { label: "Strengthen proof points", onClick: () => send("Strengthen the proof points in this action plan") },
        { label: "Re-prioritize recommendations", onClick: () => send("Re-prioritize the recommendations by urgency") },
        { label: "Add custom recommendation", onClick: () => send("Suggest a custom recommendation for this account") },
      ];
    case "value-model":
      return [
        { label: "Run sensitivity analysis", onClick: () => send("Run a sensitivity analysis on the value model") },
        { label: "Compare scenarios", onClick: () => send("Compare the optimistic, pessimistic, and base case scenarios") },
        { label: "Validate assumptions", onClick: () => send("Validate the key assumptions in this value model") },
      ];
    case "narrative":
      return [
        { label: "Adjust for CFO audience", onClick: () => send("Adjust this narrative for a CFO audience") },
        { label: "Shorten executive summary", onClick: () => send("Shorten the executive summary to under 100 words") },
        { label: "Add competitive positioning", onClick: () => send("Add competitive positioning to the narrative") },
      ];
    default:
      return [];
  }
}

// ── Run State ───────────────────────────────────────────────────────────────

export type { RunState };

// ── Hook Options ────────────────────────────────────────────────────────────

export interface UseAgentEventsOptions {
  /** Active workspace tab — determines system prompt and step templates */
  activeTab: string;
  /** Account context */
  accountId?: string;
  accountName?: string;
  accountTier?: string;
  /** Selected entity context for contextual co-pilot */
  selectedSignalId?: string;
  selectedHypothesisId?: string;
  selectedDriverId?: string;
  selectedEvidenceId?: string;
  selectedValuePath?: string;
  selectedDriverTreeId?: string;
  selectedScenarioId?: string;
  selectedBusinessCaseId?: string;
  workspaceCaseId?: string;
  entityContext?: Record<string, unknown>;
  /** Initial messages (e.g. restored from session) */
  initialMessages?: AgentMessage[];
}

// ── Hook Return ─────────────────────────────────────────────────────────────

export interface UseAgentEventsReturn {
  /** Chat message history (backward-compatible with RightRail) */
  messages: AgentMessage[];
  /** Current run's step progression */
  steps: import("./events").StepSnapshot[];
  /** Lifecycle state of the current/last run */
  runState: RunState;
  /** Send a user message and trigger an agent run */
  sendMessage: (input: string) => void;
  /** Context-aware suggested actions */
  suggestedActions: AgentAction[];
  /** Active run correlation ID */
  currentRunId: string | null;
  /** Most recent error message */
  lastError: string | null;
  /** Run metadata from the last completed run */
  metadata: import("./events").RunMetadata | null;
  /** Whether the agent is actively processing (alias for runState === "running") */
  isStreaming: boolean;
  isActionContextReady: boolean;
  missingActionContextMessage?: string;
}

export function getMissingActionContextMessage(options: Pick<UseAgentEventsOptions, "activeTab" | "accountId" | "selectedSignalId" | "selectedEvidenceId">): string | undefined {
  if (!options.accountId) return "Select an account first to enable agent actions.";
  if (options.activeTab === "signals" && !options.selectedSignalId) return "Select a signal first to enable signal actions.";
  if (options.activeTab === "evidence" && !options.selectedEvidenceId) return "Select an evidence item first to enable evidence actions.";
  return undefined;
}

function createStructuredActions(
  specs: Array<{ label: string; page_action: WorkspacePageActionContract }>,
  applyWorkspacePageAction: ReturnType<typeof useApplyWorkspacePageAction>,
): AgentAction[] {
  return specs.map((action) => ({
    label: action.label,
    onClick: () => applyWorkspacePageAction.mutate(action.page_action),
  }));
}

// ── Hook Implementation ─────────────────────────────────────────────────────

export function useAgentEvents({
  activeTab,
  accountId,
  accountName = "this account",
  accountTier,
  selectedSignalId,
  selectedHypothesisId,
  selectedDriverId,
  selectedEvidenceId,
  selectedValuePath,
  selectedDriverTreeId,
  selectedScenarioId,
  selectedBusinessCaseId,
  workspaceCaseId,
  entityContext,
  initialMessages,
}: UseAgentEventsOptions): UseAgentEventsReturn {
  const [agentState, setAgentState] = useState<AgentState>(() =>
    createInitialAgentState({ activeTab, accountName, initialMessages }),
  );
  const applyWorkspacePageAction = useApplyWorkspacePageAction();
  const workflowContext = useWorkflowContext();

  const abortRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // Flush any page action produced by a tool call. The reducer cannot execute
  // side effects, so the hook consumes the pending action and clears it.
  useEffect(() => {
    if (agentState.pendingToolPageAction) {
      applyWorkspacePageAction.mutate(agentState.pendingToolPageAction);
      setAgentState((prev) => ({ ...prev, pendingToolPageAction: null }));
    }
  }, [agentState.pendingToolPageAction, applyWorkspacePageAction]);

  // ── Event Reducer ───────────────────────────────────────────────────────

  const processEvent = useCallback((event: AgentEvent) => {
    setAgentState((prev) => reduceAgentEvent(prev, event));
  }, []);

  // ── Send Message ────────────────────────────────────────────────────────

  const sendMessage = useCallback(
    (userInput: string) => {
      // Abort any in-flight run
      abortRef.current?.abort();
      abortRef.current = new AbortController();

      // Add user message to chat
      const userMsg: AgentMessage = {
        id: `u-${Date.now()}`,
        role: "user",
        content: userInput,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setAgentState((prev) => ({
        ...prev,
        messages: [...prev.messages, userMsg],
      }));

      // Build conversation context
      const conversationMessages = buildConversationContext({
        activeTab,
        accountName,
        userInput,
        recentMessages: agentState.messages,
      });

      // Consume the event stream
      (async () => {
        try {
          const stream = sendAgentMessage(
            conversationMessages,
            {
              activeTab,
              accountId: accountId ?? workflowContext.accountId,
              accountName,
              accountTier,
              selectedSignalId,
              selectedHypothesisId,
              selectedDriverId,
              selectedEvidenceId,
              selectedValuePath,
              selectedDriverTreeId: selectedDriverTreeId ?? workflowContext.driverTreeId,
              selectedScenarioId: selectedScenarioId ?? workflowContext.scenarioId,
              selectedBusinessCaseId: selectedBusinessCaseId ?? workflowContext.businessCaseId,
              workspaceCaseId: workspaceCaseId ?? workflowContext.workspaceCaseId,
              workflowContext,
              entityContext,
            },
            abortRef.current?.signal,
          );

          for await (const event of stream) {
            if (abortRef.current?.signal.aborted) break;
            processEvent(event);
          }
        } catch (error) {
          if (abortRef.current?.signal.aborted) return;
          setAgentState((prev) => ({
            ...prev,
            runState: "error",
            lastError: error instanceof Error ? error.message : "Unknown error",
          }));
        }
      })();
    },
    [
      activeTab,
      accountId,
      accountName,
      accountTier,
      selectedSignalId,
      selectedHypothesisId,
      selectedDriverId,
      selectedEvidenceId,
      selectedValuePath,
      selectedDriverTreeId,
      selectedScenarioId,
      selectedBusinessCaseId,
      workspaceCaseId,
      workflowContext,
      entityContext,
      agentState.messages,
      processEvent,
    ],
  );

  // ── Suggested Actions ─────────────────────────────────────────────────

  const structuredActions = createStructuredActions(
    agentState.structuredActionSpecs,
    applyWorkspacePageAction,
  );

  const suggestedActions = structuredActions.length > 0
    ? structuredActions
    : getDefaultSuggestedActions(activeTab, sendMessage);

  const missingActionContextMessage = getMissingActionContextMessage({
    activeTab,
    accountId,
    selectedSignalId,
    selectedEvidenceId,
  });

  return {
    messages: agentState.messages,
    steps: agentState.steps,
    runState: agentState.runState,
    sendMessage,
    suggestedActions,
    currentRunId: agentState.currentRunId,
    lastError: agentState.lastError,
    metadata: agentState.metadata,
    isStreaming: agentState.runState === "running",
    isActionContextReady: !missingActionContextMessage,
    missingActionContextMessage,
  };
}
