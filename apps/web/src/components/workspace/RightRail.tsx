/**
 * Right Rail — Contextual Support Panel
 *
 * Two modes:
 *   1. Detail Panel — Inspect a selected entity (signal, driver, evidence item)
 *   2. Agent Stream — Conversational co-pilot with structured actions
 *
 * The right rail is context-aware: it knows which workspace tab is active
 * and adjusts its suggestions accordingly.
 *
 * AG-UI Integration:
 *   The Agent Stream mode now accepts an optional `steps` prop (StepSnapshot[])
 *   from useAgentEvents. When steps are present, a ProcessSteps visualization
 *   is rendered inline between the last user message and the agent response,
 *   showing the user what the agent is doing in real time.
 *
 *   The `metadata` prop surfaces run trace/workflow IDs from the AG-UI
 *   RunFinished event for observability.
 *
 * Backward Compatibility:
 *   All AG-UI props are optional so existing detail-panel consumers continue
 *   to work without changes.
 */
import { useState } from "react";
import { cn } from "@/lib/utils";
import { X, MessageSquare, Info, Send, History } from "lucide-react";
import { ProcessSteps } from "./ProcessSteps";
import type { StepSnapshot, RunMetadata } from "@/agui/events";
import { Btn } from "@/components/ui/fabric";

// ── Types ─────────────────────────────────────────────────────────────────────

export type RightRailMode = "detail" | "agent" | "audit";

export interface DetailPanelProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  onClose?: () => void;
}

export interface AgentMessage {
  id: string;
  role: "agent" | "user";
  content: string;
  timestamp: string;
  actions?: AgentAction[];
  metadata?: {
    traceId?: string;
    workflowId?: string;
    tenantId?: string;
    auditEventId?: string;
  };
}

export interface AgentAction {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
}

interface RightRailProps {
  mode: RightRailMode;
  onModeChange: (mode: RightRailMode) => void;
  /** Detail panel content — rendered when mode === "detail" */
  detailContent?: React.ReactNode;
  /** Active workspace tab name — used to contextualize agent suggestions */
  activeTab: string;
  /** Agent messages */
  messages: AgentMessage[];
  /** Callback when user sends a message */
  onSendMessage: (message: string) => void;
  /** Suggested actions based on current context */
  suggestedActions?: AgentAction[];
  /** Close handler */
  onClose?: () => void;
  /** AG-UI: Current run step progression */
  steps?: StepSnapshot[];
  /** AG-UI: Whether the agent is actively processing */
  isStreaming?: boolean;
  /** AG-UI: Run metadata for observability */
  runMetadata?: RunMetadata | null;
  auditEntries?: Array<{
    id: string;
    kind: string;
    summary: string;
    actor: string;
    created_at: string;
  }>;
  isActionContextReady?: boolean;
  missingActionContextMessage?: string;
}

// ── Mode Toggle ───────────────────────────────────────────────────────────────

function ModeToggle({
  mode,
  onModeChange,
  onClose,
}: {
  mode: RightRailMode;
  onModeChange: (m: RightRailMode) => void;
  onClose?: () => void;
}) {
  return (
    <div className="flex items-center justify-between px-4 py-2.5 border-b border-border shrink-0">
      <div className="flex items-center gap-1">
        <button
          onClick={() => onModeChange("detail")}
          className={cn(
            "px-3 py-1 vf-text-caption font-semibold rounded-md transition-colors",
            mode === "detail"
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <Info size={12} className="inline mr-1" />
          Details
        </button>
        <button
          onClick={() => onModeChange("agent")}
          className={cn(
            "px-3 py-1 vf-text-caption font-semibold rounded-md transition-colors",
            mode === "agent"
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <MessageSquare size={12} className="inline mr-1" />
          Agent Stream
        </button>
        <button
          onClick={() => onModeChange("audit")}
          className={cn(
            "px-3 py-1 vf-text-caption font-semibold rounded-md transition-colors",
            mode === "audit"
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:text-foreground"
          )}
        >
          <History size={12} className="inline mr-1" />
          Audit
        </button>
      </div>
      {onClose && (
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground" aria-label="Close panel">
          <X size={14} />
        </button>
      )}
    </div>
  );
}

// ── Agent Stream ──────────────────────────────────────────────────────────────

function AgentStream({
  messages,
  onSendMessage,
  suggestedActions,
  activeTab,
  steps,
  isStreaming,
  runMetadata,
  isActionContextReady = true,
  missingActionContextMessage,
}: {
  messages: AgentMessage[];
  onSendMessage: (msg: string) => void;
  suggestedActions?: AgentAction[];
  activeTab: string;
  steps?: StepSnapshot[];
  isStreaming?: boolean;
  runMetadata?: RunMetadata | null;
  isActionContextReady?: boolean;
  missingActionContextMessage?: string;
}) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    onSendMessage(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const lastUserMsgIndex = messages.reduce(
    (acc, msg, i) => (msg.role === "user" ? i : acc),
    -1,
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4 space-y-4" role="status" aria-live={isStreaming ? "polite" : undefined} aria-atomic="false">
        {messages.length === 0 && (
          <div className="text-center py-8">
            <MessageSquare size={24} className="mx-auto text-muted-foreground/50 mb-2" />
            <p className="vf-text-body-s text-muted-foreground">
              Ask me anything about this {activeTab} view.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={msg.id}>
            <div
              className={cn(
                "vf-text-body-s leading-relaxed",
                msg.role === "agent" ? "text-foreground" : "text-foreground"
              )}
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-semibold vf-text-caption">
                  {msg.role === "agent" ? "ValuePilot" : "You"}
                </span>
                <span className="vf-text-micro text-muted-foreground">{msg.timestamp}</span>
              </div>
              <div
                className={cn(
                  "rounded-lg px-3 py-2",
                  msg.role === "agent"
                    ? "bg-muted/50"
                    : "bg-primary/10 ml-4"
                )}
              >
                {msg.content}
              </div>
              {msg.role === "agent" && msg.metadata && (
                <div className="mt-1 vf-text-micro text-muted-foreground">
                  {msg.metadata.traceId && <span className="mr-2">Trace: {msg.metadata.traceId}</span>}
                  {msg.metadata.workflowId && <span className="mr-2">Workflow: {msg.metadata.workflowId}</span>}
                  {msg.metadata.tenantId && <span className="mr-2">Tenant: {msg.metadata.tenantId}</span>}
                  {msg.metadata.auditEventId && <span>Audit: {msg.metadata.auditEventId}</span>}
                </div>
              )}
              {msg.actions && msg.actions.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-2">
                  {msg.actions.map((action, j) => (
                    <Btn key={j} variant="outline" onClick={action.onClick} className="vf-text-caption">
                      {action.icon}
                      {action.label}
                    </Btn>
                  ))}
                </div>
              )}
            </div>

            {i === lastUserMsgIndex && steps && steps.length > 0 && (
              <div className="mt-3 ml-7">
                <ProcessSteps steps={steps} />
              </div>
            )}
          </div>
        ))}

        {isStreaming && (!steps || steps.length === 0) && (
          <div className="flex items-center gap-2 vf-text-body-s text-muted-foreground">
            <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            <span>ValuePilot is thinking…</span>
          </div>
        )}
      </div>

      {runMetadata && (runMetadata.traceId || runMetadata.workflowId) && (
        <div className="px-4 py-1.5 border-t border-border/50 flex items-center gap-3 vf-text-micro text-muted-foreground/60">
          {runMetadata.traceId && <span>Trace: {runMetadata.traceId}</span>}
          {runMetadata.workflowId && <span>Workflow: {runMetadata.workflowId}</span>}
        </div>
      )}

      {suggestedActions && suggestedActions.length > 0 && (
        <div className="px-4 py-2 border-t border-border flex flex-wrap gap-2">
          {!isActionContextReady && missingActionContextMessage && (
            <p className="w-full vf-text-caption text-muted-foreground">{missingActionContextMessage}</p>
          )}
          {suggestedActions.map((action, i) => (
            <Btn key={i} variant="outline" onClick={action.onClick} disabled={!isActionContextReady} className="vf-text-caption">
              {action.icon}
              {action.label}
            </Btn>
          ))}
        </div>
      )}

      <div className="px-4 py-3 border-t border-border shrink-0">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a follow-up…"
            disabled={isStreaming}
            className={cn(
              "flex-1 h-8 px-3 vf-text-body-s rounded-md border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary",
              isStreaming && "opacity-50 cursor-not-allowed",
            )}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            aria-label="Send message"
            className={cn(
              "w-8 h-8 rounded-md flex items-center justify-center transition-colors",
              input.trim() && !isStreaming
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground"
            )}
          >
            <Send size={14} />
          </button>
        </div>
        <p className="vf-text-micro text-muted-foreground mt-1 text-center">
          AI can make mistakes. Verify critical data.
        </p>
      </div>
    </div>
  );
}

// ── Right Rail ────────────────────────────────────────────────────────────────

export default function RightRail({
  mode,
  onModeChange,
  detailContent,
  activeTab,
  messages,
  onSendMessage,
  suggestedActions,
  onClose,
  steps,
  isStreaming,
  runMetadata,
  auditEntries,
  isActionContextReady,
  missingActionContextMessage,
}: RightRailProps) {
  return (
    <div className="flex flex-col h-full bg-background">
      <ModeToggle mode={mode} onModeChange={onModeChange} onClose={onClose} />

      {mode === "detail" && detailContent && (
        <div className="flex-1 overflow-y-auto p-4">
          {detailContent}
        </div>
      )}

      {mode === "detail" && !detailContent && (
        <div className="flex-1 flex items-center justify-center p-4">
          <p className="vf-text-body-s text-muted-foreground text-center">
            Select an item to view details.
          </p>
        </div>
      )}

      {mode === "audit" && (
        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          <p className="vf-text-body-s font-semibold text-foreground">Workflow history</p>
          {!auditEntries?.length ? (
            <p className="vf-text-body-s text-muted-foreground">No workflow mutations recorded yet.</p>
          ) : (
            auditEntries.map((entry) => (
              <div key={entry.id} className="rounded-md border border-border p-2">
                <p className="vf-text-caption text-foreground">{entry.summary}</p>
                <p className="vf-text-micro text-muted-foreground">{entry.kind} • {entry.actor} • {new Date(entry.created_at).toLocaleString()}</p>
              </div>
            ))
          )}
        </div>
      )}

      {mode === "agent" && (
        <AgentStream
          messages={messages}
          onSendMessage={onSendMessage}
          suggestedActions={suggestedActions}
          activeTab={activeTab}
          steps={steps}
          isStreaming={isStreaming}
          runMetadata={runMetadata}
          isActionContextReady={isActionContextReady}
          missingActionContextMessage={missingActionContextMessage}
        />
      )}
    </div>
  );
}
