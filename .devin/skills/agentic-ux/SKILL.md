---
skill_id: agentic-ux
name: agentic-ux
version: 1.0.0
description: UI patterns for agent-driven interfaces including streaming responses, tool execution visibility, confirmation flows, and progress indication
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Agentic UX Patterns

Use this skill when building frontend components that:
- Display streaming agent responses
- Show tool execution status and results
- Handle human-in-the-loop confirmations
- Visualize agent reasoning and decision steps
- Present uncertainty and confidence indicators

## Core Patterns

### Streaming Message Component
```typescript
// components/AgentMessage.tsx
import { useState, useEffect } from 'react';
import { StreamingText } from '@/components/ui/streaming-text';

interface AgentMessageProps {
  message: {
    id: string;
    content: string;
    status: 'streaming' | 'complete' | 'error';
    toolCalls?: ToolCall[];
    reasoning?: string;
    confidence?: number;
  };
  onInterrupt?: () => void;
}

export function AgentMessage({ message, onInterrupt }: AgentMessageProps) {
  return (
    <div className="agent-message">
      {/* Reasoning visibility toggle */}
      {message.reasoning && (
        <ReasoningChain steps={message.reasoning} />
      )}
      
      {/* Main content with streaming */}
      <StreamingText 
        content={message.content}
        isStreaming={message.status === 'streaming'}
        onInterrupt={onInterrupt}
      />
      
      {/* Confidence indicator */}
      {message.confidence !== undefined && (
        <ConfidenceBadge score={message.confidence} />
      )}
      
      {/* Tool execution log */}
      {message.toolCalls?.length > 0 && (
        <ToolExecutionPanel calls={message.toolCalls} />
      )}
    </div>
  );
}
```

### Tool Execution Visibility
```typescript
// components/ToolExecutionPanel.tsx
interface ToolCall {
  id: string;
  tool: string;
  input: Record<string, unknown>;
  output?: unknown;
  status: 'pending' | 'running' | 'success' | 'error';
  latencyMs?: number;
}

export function ToolExecutionPanel({ calls }: { calls: ToolCall[] }) {
  return (
    <div className="tool-panel border rounded-lg p-3 bg-muted/50">
      <h4 className="text-sm font-medium mb-2">Tools Used</h4>
      {calls.map(call => (
        <ToolCallRow key={call.id} call={call} />
      ))}
    </div>
  );
}

function ToolCallRow({ call }: { call: ToolCall }) {
  return (
    <div className="tool-call flex items-center gap-2 py-1">
      <StatusIcon status={call.status} />
      <code className="text-xs">{call.tool}</code>
      {call.latencyMs && (
        <span className="text-xs text-muted-foreground">
          {call.latencyMs}ms
        </span>
      )}
      <ToolOutputPreview output={call.output} />
    </div>
  );
}
```

### Human-in-the-Loop Confirmation
```typescript
// components/ConfirmationDialog.tsx
interface ConfirmationProps {
  isOpen: boolean;
  action: {
    type: 'tool' | 'workflow' | 'decision';
    description: string;
    parameters: Record<string, unknown>;
    riskLevel: 'low' | 'medium' | 'high';
  };
  onApprove: (withModifications?: Record<string, unknown>) => void;
  onReject: () => void;
  onModify: (params: Record<string, unknown>) => void;
}

export function ConfirmationDialog({
  isOpen, action, onApprove, onReject, onModify
}: ConfirmationProps) {
  return (
    <Dialog open={isOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldIcon className={riskColor(action.riskLevel)} />
            Approval Required
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4">
          <p className="text-sm text-muted-foreground">
            The agent wants to execute:
          </p>
          
          <ActionPreview action={action} />
          
          {/* Editable parameters for modification */}
          {Object.keys(action.parameters).length > 0 && (
            <ParameterEditor
              parameters={action.parameters}
              onChange={onModify}
            />
          )}
        </div>
        
        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={onReject}>
            Reject
          </Button>
          <Button onClick={() => onApprove()}>
            Approve
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
```

### Progress and State Visualization
```typescript
// components/WorkflowProgress.tsx
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react';

interface WorkflowStep {
  id: string;
  label: string;
  status: 'pending' | 'active' | 'completed' | 'error';
  detail?: string;
  elapsedMs?: number;
}

export function WorkflowProgress({ steps }: { steps: WorkflowStep[] }) {
  return (
    <div className="workflow-progress space-y-2">
      {steps.map((step, idx) => (
        <div 
          key={step.id}
          className={`flex items-center gap-3 p-2 rounded ${
            step.status === 'active' ? 'bg-primary/10' : ''
          }`}
        >
          <StepIcon status={step.status} />
          <div className="flex-1">
            <span className={stepLabelClass(step.status)}>
              {step.label}
            </span>
            {step.detail && (
              <p className="text-xs text-muted-foreground">{step.detail}</p>
            )}
          </div>
          {step.elapsedMs && step.status === 'completed' && (
            <span className="text-xs text-muted-foreground">
              {(step.elapsedMs / 1000).toFixed(1)}s
            </span>
          )}
          {step.status === 'active' && (
            <Loader2 className="h-4 w-4 animate-spin" />
          )}
        </div>
      ))}
    </div>
  );
}
```

### Uncertainty and Confidence Display
```typescript
// components/ConfidenceIndicators.tsx
export function ConfidenceBadge({ score }: { score: number }) {
  const { label, color } = confidenceLevel(score);
  
  return (
    <Badge variant="outline" className={color}>
      <div className="flex items-center gap-1.5">
        <ConfidenceBar score={score} />
        <span className="text-xs">{label} ({(score * 100).toFixed(0)}%)</span>
      </div>
    </Badge>
  );
}

function ConfidenceBar({ score }: { score: number }) {
  return (
    <div className="w-8 h-1.5 bg-muted rounded-full overflow-hidden">
      <div 
        className={`h-full ${scoreColor(score)}`}
        style={{ width: `${score * 100}%` }}
      />
    </div>
  );
}

function confidenceLevel(score: number) {
  if (score >= 0.9) return { label: 'High', color: 'text-green-600' };
  if (score >= 0.7) return { label: 'Medium', color: 'text-yellow-600' };
  return { label: 'Low', color: 'text-red-600' };
}
```

## Project-Specific Conventions

- **Component Location**: All agent UI components in `frontend/client/src/components/agent/`
- **State Management**: Use TanStack Query for streaming state via `frontend/client/src/hooks/useAgentStream.ts`
- **Styling**: Use shadcn/ui base components, extend in `frontend/client/src/components/ui/`
- **Icons**: Use Lucide icons consistently

## API Integration Pattern
```typescript
// hooks/useAgentStream.ts
export function useAgentStream() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ input, workflow }: AgentRequest) => {
      const response = await fetch('/api/v1/agent/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input, workflow })
      });
      
      // Handle streaming response
      const reader = response.body?.getReader();
      return streamToObservable(reader);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    }
  });
}
```

## Anti-Patterns to Avoid

- Don't block the UI waiting for agent responses (always stream)
- Don't hide tool execution details (users need visibility)
- Don't make confirmation dialogs generic (show specific action details)
- Don't ignore low-confidence outputs (surface uncertainty explicitly)
- Don't show raw JSON to users (transform to readable formats)
