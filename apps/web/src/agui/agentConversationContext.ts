/**
 * agentConversationContext — Build the conversation context sent to the agent.
 *
 * This pure helper selects the system prompt for the active workspace tab and
 * assembles the recent message window into the format expected by the backend.
 */

import { TAB_SYSTEM_PROMPTS } from './systemPrompts';
import type { AgentMessage } from '@/components/workspace/RightRail';

export interface ConversationMessage {
  role: 'system' | 'user' | 'assistant';
  content: string;
}

export interface BuildConversationContextArgs {
  activeTab: string;
  accountName: string;
  userInput: string;
  recentMessages: AgentMessage[];
}

export function buildConversationContext(args: BuildConversationContextArgs): ConversationMessage[] {
  const systemPrompt =
    TAB_SYSTEM_PROMPTS[args.activeTab] ??
    'You are ValuePilot, an AI co-pilot for value selling. Keep responses concise.';

  return [
    { role: 'system', content: systemPrompt },
    ...args.recentMessages.slice(-10).map((m) => ({
      role: (m.role === 'agent' ? 'assistant' : 'user') as 'system' | 'user' | 'assistant',
      content: m.content,
    })),
    { role: 'user', content: args.userInput },
  ];
}
