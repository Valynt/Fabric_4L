import { Bot, Minimize2, Send, X } from "lucide-react";

interface AgentSidePanelProps {
  onClose: () => void;
  onMinimize: () => void;
}

export function AgentSidePanel({
  onClose,
  onMinimize,
}: AgentSidePanelProps) {
  return (
    <aside aria-label="Agent assistant panel" className="hidden h-screen min-w-[360px] max-w-[420px] border-l bg-background shadow-xl md:flex md:flex-col">
      <div className="flex h-14 shrink-0 items-center justify-between border-b px-4">
        <div className="flex items-center gap-2">
          <div className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <Bot className="h-4 w-4" />
          </div>

          <div>
            <div className="text-sm font-semibold">Agent Assistant</div>
            <div className="text-xs text-muted-foreground">Workspace-aware</div>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onMinimize}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent"
            aria-label="Minimize agent panel"
          >
            <Minimize2 className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-8 w-8 items-center justify-center rounded-md hover:bg-accent"
            aria-label="Close agent panel"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
        <div className="rounded-lg bg-muted p-3 text-sm">
          I noticed you are in Settings. I can help explain which controls belong under personal settings, tenant configuration, or governance.
        </div>

        <div className="rounded-lg border p-3 text-sm">
          Suggested task: Review RBAC rules for Team & Access.
        </div>
      </div>

      <form className="flex shrink-0 items-center gap-2 border-t p-3">
        <input
          className="h-9 min-w-0 flex-1 rounded-md border bg-background px-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          placeholder="Ask the agent..."
          aria-label="Agent message"
        />

        <button
          type="submit"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground hover:opacity-90"
          aria-label="Send message"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>
    </aside>
  );
}
