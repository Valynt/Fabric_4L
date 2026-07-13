import { describe, it, expect } from 'vitest';
import { reduceAgentEvent, createInitialAgentState, type AgentState } from './agentEventReducer';
import { AgentEventType } from './events';

describe('reduceAgentEvent', () => {
  it('handles RUN_STARTED', () => {
    const state = createInitialAgentState();
    const next = reduceAgentEvent(state, {
      type: AgentEventType.RUN_STARTED,
      runId: 'run-1',
      expectedSteps: [{ id: 's1', label: 'Step 1' }],
      timestamp: new Date().toISOString(),
    });
    expect(next.runState).toBe('running');
    expect(next.currentRunId).toBe('run-1');
    expect(next.steps).toHaveLength(1);
    expect(next.steps[0]).toMatchObject({ id: 's1', label: 'Step 1', status: 'pending' });
  });

  it('appends text message deltas to the same message', () => {
    const state = createInitialAgentState({ activeTab: 'signals', accountName: 'Acme', initialMessages: [] });
    const withPlaceholder = reduceAgentEvent(state, {
      type: AgentEventType.TEXT_MESSAGE_START,
      messageId: 'm1',
      role: 'agent',
      timestamp: new Date().toISOString(),
    });
    const withContent = reduceAgentEvent(withPlaceholder, {
      type: AgentEventType.TEXT_MESSAGE_CONTENT,
      messageId: 'm1',
      delta: 'hello',
      timestamp: new Date().toISOString(),
    });
    const withMoreContent = reduceAgentEvent(withContent, {
      type: AgentEventType.TEXT_MESSAGE_CONTENT,
      messageId: 'm1',
      delta: ' world',
      timestamp: new Date().toISOString(),
    });
    expect(withMoreContent.messages).toHaveLength(1);
    expect(withMoreContent.messages[0].content).toBe('hello world');
  });

  it('transitions step from pending to active to done', () => {
    let state: AgentState = createInitialAgentState();
    state = reduceAgentEvent(state, {
      type: AgentEventType.RUN_STARTED,
      runId: 'run-1',
      expectedSteps: [{ id: 's1', label: 'Analyze' }],
      timestamp: new Date().toISOString(),
    });
    state = reduceAgentEvent(state, {
      type: AgentEventType.STEP_STARTED,
      stepId: 's1',
      label: 'Analyze',
      timestamp: new Date().toISOString(),
    });
    expect(state.steps[0].status).toBe('active');

    state = reduceAgentEvent(state, {
      type: AgentEventType.STEP_FINISHED,
      stepId: 's1',
      status: 'done',
      timestamp: new Date().toISOString(),
    });
    expect(state.steps[0].status).toBe('done');
  });

  it('records RUN_ERROR and appends an error message', () => {
    const state = createInitialAgentState();
    const next = reduceAgentEvent(state, {
      type: AgentEventType.RUN_ERROR,
      message: 'Something went wrong',
      retryable: true,
      timestamp: new Date().toISOString(),
    });
    expect(next.runState).toBe('error');
    expect(next.lastError).toBe('Something went wrong');
    expect(next.messages[next.messages.length - 1].content).toContain('Something went wrong');
  });

  it('surfaces tool calls as custom steps', () => {
    const state = createInitialAgentState();
    const withToolStart = reduceAgentEvent(state, {
      type: AgentEventType.TOOL_CALL_START,
      toolCallId: 'tc-1',
      toolName: 'searchEvidence',
      timestamp: new Date().toISOString(),
    });
    expect(withToolStart.steps).toHaveLength(1);
    expect(withToolStart.steps[0]).toMatchObject({
      id: 'tc-1',
      label: 'Calling searchEvidence',
      status: 'active',
    });

    const withToolEnd = reduceAgentEvent(withToolStart, {
      type: AgentEventType.TOOL_CALL_END,
      toolCallId: 'tc-1',
      success: true,
      timestamp: new Date().toISOString(),
    });
    expect(withToolEnd.steps[0].status).toBe('done');
  });

  it('stores a pending page action on successful TOOL_CALL_END with pageAction', () => {
    const state: AgentState = {
      ...createInitialAgentState(),
      currentRunId: 'run-1',
      metadata: {
        runId: 'run-1',
        traceId: 'trace-1',
        workflowId: 'wf-1',
        auditEventId: 'audit-1',
      },
    };

    const next = reduceAgentEvent(state, {
      type: AgentEventType.TOOL_CALL_END,
      toolCallId: 'tc-1',
      success: true,
      result: {
        pageAction: {
          entityType: 'signal',
          entityId: 'sig-1',
          accountId: 'acc-1',
          caseId: 'case-1',
          intendedOperation: 'signal_review',
          payload: {},
        } as const,
      },
      timestamp: new Date().toISOString(),
    });

    expect(next.pendingToolPageAction).not.toBeNull();
    expect(next.pendingToolPageAction?.runMetadataIds).toMatchObject({
      runId: 'run-1',
      traceId: 'trace-1',
      workflowId: 'wf-1',
      auditEventId: 'audit-1',
      toolCallId: 'tc-1',
    });
  });

  it('marks a tool call step as error on failed TOOL_CALL_END', () => {
    const state = createInitialAgentState();
    const withToolStart = reduceAgentEvent(state, {
      type: AgentEventType.TOOL_CALL_START,
      toolCallId: 'tc-1',
      toolName: 'searchEvidence',
      timestamp: new Date().toISOString(),
    });
    const withToolEnd = reduceAgentEvent(withToolStart, {
      type: AgentEventType.TOOL_CALL_END,
      toolCallId: 'tc-1',
      success: false,
      error: 'Tool failed',
      timestamp: new Date().toISOString(),
    });
    expect(withToolEnd.steps[0].status).toBe('error');
    expect(withToolEnd.pendingToolPageAction).toBeNull();
  });

  it('is a no-op for unhandled event types', () => {
    const state = createInitialAgentState();
    const next = reduceAgentEvent(state, {
      type: AgentEventType.CUSTOM,
      name: 'ping',
      timestamp: new Date().toISOString(),
    });
    expect(next).toBe(state);
  });
});
