import { describe, it, expect } from 'vitest';
import { buildConversationContext } from './agentConversationContext';

describe('buildConversationContext', () => {
  it('uses the active tab system prompt', () => {
    const result = buildConversationContext({
      activeTab: 'signals',
      accountName: 'Acme',
      userInput: 'Summarize',
      recentMessages: [],
    });
    expect(result[0].role).toBe('system');
    expect(result[0].content).toContain('signals');
  });

  it('includes the last 10 messages', () => {
    const recentMessages = Array.from({ length: 15 }, (_, i) => ({
      id: `m${i}`,
      role: 'agent' as const,
      content: `msg-${i}`,
      timestamp: '12:00',
    }));
    const result = buildConversationContext({
      activeTab: 'drivers',
      accountName: 'Acme',
      userInput: 'go',
      recentMessages,
    });
    expect(result).toHaveLength(12); // system + 10 recent + user
    expect(result[1].content).toBe('msg-5');
    expect(result[result.length - 1]).toEqual({ role: 'user', content: 'go' });
  });

  it('maps agent role to assistant and user role to user', () => {
    const result = buildConversationContext({
      activeTab: 'evidence',
      accountName: 'Acme',
      userInput: 'Next',
      recentMessages: [
        { id: 'm1', role: 'agent', content: 'hello', timestamp: '12:00' },
        { id: 'm2', role: 'user', content: 'hi', timestamp: '12:01' },
      ],
    });
    expect(result[1]).toEqual({ role: 'assistant', content: 'hello' });
    expect(result[2]).toEqual({ role: 'user', content: 'hi' });
    expect(result[3]).toEqual({ role: 'user', content: 'Next' });
  });

  it('falls back to the default prompt for unknown tabs', () => {
    const result = buildConversationContext({
      activeTab: 'unknown-tab',
      accountName: 'Acme',
      userInput: 'Hello',
      recentMessages: [],
    });
    expect(result[0].role).toBe('system');
    expect(result[0].content).toContain('ValuePilot');
  });
});
