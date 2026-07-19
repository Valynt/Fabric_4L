/**
 * agentEventReducer — Pure state reducer for AG-UI protocol events.
 *
 * This module encapsulates all state transitions triggered by agent events.
 * It is intentionally free of React dependencies so it can be unit tested
 * without a DOM or hook harness.
 */

import type { AgentMessage } from "@/components/workspace/RightRail";
import type { WorkspacePageActionContract } from "@/hooks/useWorkspaceCase";
import {
  AgentEventType,
  type AgentEvent,
  type StepSnapshot,
  type RunMetadata,
} from "./events";

export type RunState = "idle" | "running" | "finished" | "error";

export interface AgentState {
  messages: AgentMessage[];
  steps: StepSnapshot[];
  runState: RunState;
  currentRunId: string | null;
  lastError: string | null;
  metadata: RunMetadata | null;
  /** Serializable structured action specs produced by the last run. */
  structuredActionSpecs: Array<{ label: string; page_action: WorkspacePageActionContract }>;
  /** Tool-call page action that must be executed by the hook consuming this reducer. */
  pendingToolPageAction: WorkspacePageActionContract | null;
}

export interface CreateInitialAgentStateOptions {
  activeTab?: string;
  accountName?: string;
  initialMessages?: AgentMessage[];
}

export function createInitialAgentState(
  options: CreateInitialAgentStateOptions = {},
): AgentState {
  const { activeTab = "workspace", accountName = "this account", initialMessages } = options;
  return {
    messages:
      initialMessages ??
      [
        {
          id: "welcome",
          role: "agent",
          content: `I'm ready to help you with the ${activeTab} view for ${accountName}. What would you like to explore?`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ],
    steps: [],
    runState: "idle",
    currentRunId: null,
    lastError: null,
    metadata: null,
    structuredActionSpecs: [],
    pendingToolPageAction: null,
  };
}

export function formatAgentTimestamp(timestamp?: string): string {
  return new Date(timestamp ?? Date.now()).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function initializeExpectedSteps(
  expectedSteps: Extract<AgentEvent, { type: AgentEventType.RUN_STARTED }>["expectedSteps"],
): StepSnapshot[] {
  return (expectedSteps ?? []).map((step) => ({
    id: step.id,
    label: step.label,
    status: "pending",
  }));
}

export function updateStep(
  steps: StepSnapshot[],
  stepId: string,
  patch: Omit<Partial<StepSnapshot>, "id">,
): StepSnapshot[] {
  return steps.map((step) => (step.id === stepId ? { ...step, ...patch } : step));
}

export function appendOrUpdateAgentMessage(
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

export function createAgentMessagePlaceholder(
  event: Extract<AgentEvent, { type: AgentEventType.TEXT_MESSAGE_START }>,
): AgentMessage {
  return {
    id: event.messageId,
    role: "agent",
    content: "",
    timestamp: formatAgentTimestamp(event.timestamp),
  };
}

export function createRunErrorMessage(
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

export function getCompleteRunMetadata(metadata?: RunMetadata | null) {
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

export function reduceAgentEvent(state: AgentState, event: AgentEvent): AgentState {
  switch (event.type) {
    case AgentEventType.RUN_STARTED: {
      return {
        ...state,
        currentRunId: event.runId ?? null,
        runState: "running",
        lastError: null,
        steps: initializeExpectedSteps(event.expectedSteps),
        structuredActionSpecs: [],
        pendingToolPageAction: null,
      };
    }

    case AgentEventType.STEP_STARTED: {
      return {
        ...state,
        steps: updateStep(state.steps, event.stepId, {
          status: "active",
          startedAt: event.timestamp,
        }),
      };
    }

    case AgentEventType.STEP_FINISHED: {
      return {
        ...state,
        steps: updateStep(state.steps, event.stepId, {
          status: event.status,
          finishedAt: event.timestamp,
          result: event.result,
        }),
      };
    }

    case AgentEventType.TEXT_MESSAGE_CONTENT: {
      return {
        ...state,
        messages: appendOrUpdateAgentMessage(state.messages, event),
      };
    }

    case AgentEventType.TEXT_MESSAGE_START: {
      return {
        ...state,
        messages: [...state.messages, createAgentMessagePlaceholder(event)],
      };
    }

    case AgentEventType.RUN_FINISHED: {
      const nextState: AgentState = {
        ...state,
        runState: "finished",
        pendingToolPageAction: null,
      };

      if (event.metadata) {
        nextState.metadata = event.metadata;
      }

      const output = event.output as {
        actions?: Array<{ label: string; page_action: WorkspacePageActionContract }>;
      } | undefined;
      const runMetadataIds = getCompleteRunMetadata(event.metadata);
      if (runMetadataIds && output?.actions?.length) {
        nextState.structuredActionSpecs = output.actions.map((action) => ({
          label: action.label,
          page_action: {
            ...action.page_action,
            runMetadataIds,
          },
        }));
      }

      return nextState;
    }

    case AgentEventType.RUN_ERROR: {
      return {
        ...state,
        runState: "error",
        lastError: event.message,
        messages: [...state.messages, createRunErrorMessage(event)],
      };
    }

    case AgentEventType.TOOL_CALL_START: {
      return {
        ...state,
        steps: [
          ...state.steps,
          {
            id: event.toolCallId,
            label: `Calling ${event.toolName}`,
            status: "active",
            startedAt: event.timestamp,
          },
        ],
      };
    }

    case AgentEventType.TOOL_CALL_END: {
      const eventResult = event.result as { pageAction?: WorkspacePageActionContract } | undefined;
      const nextState: AgentState = {
        ...state,
        steps: updateStep(state.steps, event.toolCallId, {
          status: event.success ? "done" : "error",
          finishedAt: event.timestamp,
          result: event.result,
        }),
      };

      if (event.success && eventResult?.pageAction) {
        const pageAction = eventResult.pageAction;
        nextState.pendingToolPageAction = {
          ...pageAction,
          runMetadataIds: {
            ...pageAction.runMetadataIds,
            runId: state.metadata?.runId ?? state.currentRunId ?? "unknown-run",
            traceId: state.metadata?.traceId ?? "unknown-trace",
            workflowId: state.metadata?.workflowId ?? "unknown-workflow",
            auditEventId: state.metadata?.auditEventId ?? "unknown-audit",
            toolCallId: event.toolCallId,
          },
        };
      }

      return nextState;
    }

    // STATE_DELTA, STATE_SNAPSHOT, CUSTOM — extensible, no-op for now
    default:
      return state;
  }
}
