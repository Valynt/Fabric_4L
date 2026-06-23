/**
 * useAgentEvents — React hook for AG-UI protocol event consumption.
 *
 * This hook replaces `useAgentStream` as the primary interface between
 * workspace tabs and the agent co-pilot. It exposes:
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
  type StepSnapshot,
  type RunMetadata,
} from "./events";
import { sendAgentMessage } from "./AgentEventClient";
import { getDefaultSuggestedActions } from "@/hooks/useAgentStream";
import { useApplyWorkspacePageAction, type WorkspacePageActionContract } from "@/hooks/useWorkspaceCase";
import { useWorkflowContext } from "@/hooks/useWorkflowContext";

// ── Tab System Prompts (reused from useAgentStream) ─────────────────────────

const TAB_SYSTEM_PROMPTS: Record<string, string> = {
  signals: `You are ValuePilot, an AI co-pilot embedded in the Intelligence → Signals workspace.
You help sales engineers analyze AI-surfaced pain signals for a prospect account.
You can summarize signals, compare them, explain confidence scores, suggest which signals
to prioritize, and recommend next steps like generating a value driver tree or drafting
an action plan. Keep responses concise (2-3 sentences max) and actionable.`,

  drivers: `You are ValuePilot, an AI co-pilot embedded in the Intelligence → Drivers workspace.
You help sales engineers understand root cause analysis connecting prospect pain signals
to underlying business drivers. You can explain driver hierarchies, suggest missing drivers,
and help map drivers to product capabilities. Keep responses concise and actionable.`,

  evidence: `You are ValuePilot, an AI co-pilot embedded in the Intelligence → Evidence workspace.
You help sales engineers validate claims with source documents, benchmarks, and case studies.
You can explain evidence match scores, suggest additional evidence sources, and flag claims
that need stronger proof. Keep responses concise and actionable.`,

  stakeholders: `You are ValuePilot, an AI co-pilot embedded in the Intelligence → Stakeholders workspace.
You help sales engineers map buyer personas and understand stakeholder priorities.
You can suggest messaging angles for different roles, identify missing stakeholders,
and recommend engagement strategies. Keep responses concise and actionable.`,

  "action-plan": `You are ValuePilot, an AI co-pilot embedded in the Value Studio → Action Plan workspace.
You help sales engineers build product-anchored recommendations that map validated prospect
pain to specific product capabilities. You can refine recommendations, adjust priorities,
and strengthen the "why us" argument. Keep responses concise and actionable.`,

  "value-model": `You are ValuePilot, an AI co-pilot embedded in the Value Studio → Value Model workspace.
You help sales engineers build and refine quantified business cases. You can explain
financial projections, adjust assumptions, compare scenarios, and validate calculations.
Keep responses concise and actionable.`,

  narrative: `You are ValuePilot, an AI co-pilot embedded in the Value Studio → Narrative workspace.
You help sales engineers package the value case for stakeholder presentations.
You can refine messaging, adjust tone for different audiences, and suggest narrative
structures. Keep responses concise and actionable.`,
};

// ── Run State ───────────────────────────────────────────────────────────────

export type RunState = "idle" | "running" | "finished" | "error";

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
  steps: StepSnapshot[];
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
  metadata: RunMetadata | null;
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

function formatAgentTimestamp(timestamp?: string): string {
  return new Date(timestamp ?? Date.now()).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function initializeExpectedSteps(
  expectedSteps: Extract<AgentEvent, { type: AgentEventType.RUN_STARTED }>["expectedSteps"],
): StepSnapshot[] {
  return (expectedSteps ?? []).map((step) => ({
    id: step.id,
    label: step.label,
    status: "pending",
  }));
}

function updateStep(
  steps: StepSnapshot[],
  stepId: string,
  patch: Omit<Partial<StepSnapshot>, "id">,
): StepSnapshot[] {
  return steps.map((step) => (step.id === stepId ? { ...step, ...patch } : step));
}

function appendOrUpdateAgentMessage(
  messages: AgentMessage[],
  event: Extract<AgentEvent, { type: AgentEventType.TEXT_MESSAGE_CONTENT }>,
): AgentMessage[] {
  const existing = messages.find((message) => message.id === event.messageId);
  if (existing) {
    return messages.map((message) =>
      message.id === event.messageId
        ? { ...message, content: message.content + event.delta }
        : message,
    );
  }

  return [
    ...messages,
    {
      id: event.messageId,
      role: "agent",
      content: event.delta,
      timestamp: formatAgentTimestamp(event.timestamp),
    },
  ];
}

function createAgentMessagePlaceholder(
  event: Extract<AgentEvent, { type: AgentEventType.TEXT_MESSAGE_START }>,
): AgentMessage {
  return {
    id: event.messageId,
    role: "agent",
    content: "",
    timestamp: formatAgentTimestamp(event.timestamp),
  };
}

function createRunErrorMessage(
  event: Extract<AgentEvent, { type: AgentEventType.RUN_ERROR }>,
): AgentMessage {
  return {
    id: `err-${Date.now()}`,
    role: "agent",
    content: event.retryable
      ? `I couldn't complete that request: ${event.message}. Please try again.`
      : `An error occurred: ${event.message}`,
    timestamp: formatAgentTimestamp(event.timestamp),
  };
}

function getCompleteRunMetadata(metadata?: RunMetadata | null) {
  if (
    metadata &&
    typeof metadata.runId === "string" &&
    typeof metadata.traceId === "string" &&
    typeof metadata.workflowId === "string" &&
    typeof metadata.auditEventId === "string"
  ) {
    return {
      runId: metadata.runId,
      traceId: metadata.traceId,
      workflowId: metadata.workflowId,
      auditEventId: metadata.auditEventId,
    };
  }
  return null;
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
  const [messages, setMessages] = useState<AgentMessage[]>(
    initialMessages ?? [
      {
        id: "welcome",
        role: "agent",
        content: `I'm ready to help you with the ${activeTab} view for ${accountName}. What would you like to explore?`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ],
  );

  const [steps, setSteps] = useState<StepSnapshot[]>([]);
  const [runState, setRunState] = useState<RunState>("idle");
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [metadata, setMetadata] = useState<RunMetadata | null>(null);
  const [structuredActions, setStructuredActions] = useState<AgentAction[]>([]);
  const applyWorkspacePageAction = useApplyWorkspacePageAction();
  const workflowContext = useWorkflowContext();

  const abortRef = useRef<AbortController | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // ── Event Reducer ───────────────────────────────────────────────────────

  const processEvent = useCallback((event: AgentEvent) => {
    switch (event.type) {
      case AgentEventType.RUN_STARTED: {
        setCurrentRunId(event.runId ?? null);
        setRunState("running");
        setLastError(null);
        setSteps(initializeExpectedSteps(event.expectedSteps));
        break;
      }

      case AgentEventType.STEP_STARTED: {
        setSteps((prev) =>
          updateStep(prev, event.stepId, {
            status: "active",
            startedAt: event.timestamp,
          }),
        );
        break;
      }

      case AgentEventType.STEP_FINISHED: {
        setSteps((prev) =>
          updateStep(prev, event.stepId, {
            status: event.status,
            finishedAt: event.timestamp,
            result: event.result,
          }),
        );
        break;
      }

      case AgentEventType.TEXT_MESSAGE_CONTENT: {
        setMessages((prev) => appendOrUpdateAgentMessage(prev, event));
        break;
      }

      case AgentEventType.TEXT_MESSAGE_START: {
        setMessages((prev) => [...prev, createAgentMessagePlaceholder(event)]);
        break;
      }

      case AgentEventType.RUN_FINISHED: {
        setRunState("finished");
        if (event.metadata) {
          setMetadata(event.metadata);
        }
        const output = event.output as {
          actions?: Array<{ label: string; page_action: WorkspacePageActionContract }>;
        } | undefined;
        const runMetadataIds = getCompleteRunMetadata(event.metadata);
        if (runMetadataIds && output?.actions?.length) {
          setStructuredActions(
            output.actions.map((action) => ({
              label: action.label,
              onClick: () =>
                applyWorkspacePageAction.mutate({
                  ...action.page_action,
                  runMetadataIds,
                }),
            })),
          );
        }
        break;
      }

      case AgentEventType.RUN_ERROR: {
        setRunState("error");
        setLastError(event.message);
        setMessages((prev) => [...prev, createRunErrorMessage(event)]);
        break;
      }

      case AgentEventType.TOOL_CALL_START: {
        // Surface tool calls as a custom step
        setSteps((prev) => [
          ...prev,
          {
            id: event.toolCallId,
            label: `Calling ${event.toolName}`,
            status: "active",
            startedAt: event.timestamp,
          },
        ]);
        break;
      }

      case AgentEventType.TOOL_CALL_END: {
        const eventResult = event.result as { pageAction?: WorkspacePageActionContract } | undefined;
        if (event.success && eventResult?.pageAction) {
          const pageAction = eventResult.pageAction;
          applyWorkspacePageAction.mutate({
            ...pageAction,
            runMetadataIds: {
              ...pageAction.runMetadataIds,
              runId: metadata?.runId ?? currentRunId ?? "unknown-run",
              traceId: metadata?.traceId ?? "unknown-trace",
              workflowId: metadata?.workflowId ?? "unknown-workflow",
              auditEventId: metadata?.auditEventId ?? "unknown-audit",
              toolCallId: event.toolCallId,
            },
          });
        }
        setSteps((prev) =>
          updateStep(prev, event.toolCallId, {
            status: event.success ? "done" : "error",
            finishedAt: event.timestamp,
            result: event.result,
          }),
        );
        break;
      }

      // STATE_DELTA, STATE_SNAPSHOT, CUSTOM — extensible, no-op for now
      default:
        break;
    }
  }, [applyWorkspacePageAction, currentRunId, metadata?.auditEventId, metadata?.runId, metadata?.traceId, metadata?.workflowId]);

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
      setMessages((prev) => [...prev, userMsg]);

      // Build conversation context
      const systemPrompt =
        TAB_SYSTEM_PROMPTS[activeTab] ??
        "You are ValuePilot, an AI co-pilot for value selling. Keep responses concise.";

      const conversationMessages: Array<{ role: "system" | "user" | "assistant"; content: string }> = [
        { role: "system", content: systemPrompt },
        ...messages.slice(-10).map((m) => ({
          role: (m.role === "agent" ? "assistant" : "user") as "system" | "user" | "assistant",
          content: m.content,
        })),
        { role: "user", content: userInput },
      ];

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
          setRunState("error");
          setLastError(error instanceof Error ? error.message : "Unknown error");
        }
      })();
    },
    [activeTab, accountId, accountName, accountTier, selectedSignalId, selectedHypothesisId, selectedDriverId, selectedEvidenceId, selectedValuePath, selectedDriverTreeId, selectedScenarioId, selectedBusinessCaseId, workspaceCaseId, workflowContext, entityContext, messages, processEvent],
  );

  // ── Suggested Actions ─────────────────────────────────────────────────

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
    messages,
    steps,
    runState,
    sendMessage,
    suggestedActions,
    currentRunId,
    lastError,
    metadata,
    isStreaming: runState === "running",
    isActionContextReady: !missingActionContextMessage,
    missingActionContextMessage,
  };
}
