/**
 * ModelInputsTracker — Collapsible tracker showing value-model input completeness.
 *
 * UI Contract (Data):
 *   - `inputs` : array of ModelInput objects, each with id, label, status, and
 *                optional value, source, and onClick handler
 *   - `status` : one of "complete" | "inferred" | "missing"
 *
 * UI Contract (Behavior):
 *   - Clicking the header toggles collapsed/expanded state (internal)
 *   - Clicking an individual input row calls its `onClick` if provided
 *   - Rows without `onClick` are non-interactive (cursor-default)
 *
 * UI Contract (Rendering):
 *   - Header always shows summary counts: ✓ complete, ⚡ inferred, ⚠ missing
 *   - Collapsed state hides the input list but keeps the header visible
 *   - Each input row shows: status icon → label + value → source → status text
 *   - Status colours are deterministic: emerald (complete), primary (inferred), amber (missing)
 *   - `aria-expanded` and `aria-label` for accessibility
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/model-inputs-tracker.tsx
 */
import { useState } from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertTriangle, BrainCircuit, ChevronDown } from "lucide-react";

export type InputStatus = "complete" | "missing" | "inferred";

export interface ModelInput {
  /** Unique input identifier */
  id: string;
  /** Human-readable label */
  label: string;
  /** Completeness status */
  status: InputStatus;
  /** Current value (if available) */
  value?: string;
  /** Data source attribution */
  source?: string;
  /** Click handler for drill-down */
  onClick?: () => void;
}

export interface ModelInputsTrackerProps {
  /** List of model inputs to track */
  inputs: ModelInput[];
  /** Additional wrapper classes */
  className?: string;
}

const statusConfig: Record<
  InputStatus,
  { icon: typeof CheckCircle2; iconClass: string; label: string }
> = {
  complete: { icon: CheckCircle2,  iconClass: "text-success", label: "Complete" },
  inferred: { icon: BrainCircuit,  iconClass: "text-primary",     label: "Inferred" },
  missing:  { icon: AlertTriangle, iconClass: "text-warning",   label: "Missing" },
};

export function ModelInputsTracker({ inputs, className }: ModelInputsTrackerProps) {
  const [collapsed, setCollapsed] = useState(false);

  const completeCount = inputs.filter((i) => i.status === "complete").length;
  const inferredCount = inputs.filter((i) => i.status === "inferred").length;
  const missingCount  = inputs.filter((i) => i.status === "missing").length;

  return (
    <section
      className={cn("bg-card rounded-xl border border-border overflow-hidden", className)}
      aria-label="Model inputs tracker"
    >
      {/* Collapsible header */}
      <button type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
        aria-expanded={!collapsed}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-foreground">Value Model Inputs</span>
          <div className="flex items-center gap-2">
            {completeCount > 0 && (
              <span className="flex items-center gap-1 vf-text-micro text-success font-medium">
                <CheckCircle2 className="w-3 h-3" />
                {completeCount}
              </span>
            )}
            {inferredCount > 0 && (
              <span className="flex items-center gap-1 vf-text-micro text-primary font-medium">
                <BrainCircuit className="w-3 h-3" />
                {inferredCount}
              </span>
            )}
            {missingCount > 0 && (
              <span className="flex items-center gap-1 vf-text-micro text-warning font-medium">
                <AlertTriangle className="w-3 h-3" />
                {missingCount}
              </span>
            )}
          </div>
        </div>
        <ChevronDown
          className={cn(
            "w-4 h-4 text-muted-foreground transition-transform",
            collapsed && "-rotate-90",
          )}
        />
      </button>

      {/* Input list */}
      {!collapsed && (
        <div className="px-4 pb-3 space-y-1">
          {inputs.map((input) => {
            const config = statusConfig[input.status];
            const Icon = config.icon;
            return (
              <button type="button"
                key={input.id}
                onClick={input.onClick}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-colors",
                  input.onClick ? "hover:bg-muted cursor-pointer" : "cursor-default",
                )}
              >
                <Icon className={cn("w-4 h-4 shrink-0", config.iconClass)} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground">{input.label}</span>
                    {input.value && (
                      <span className="vf-text-micro text-muted-foreground truncate">
                        {input.value}
                      </span>
                    )}
                  </div>
                  {input.source && (
                    <span className="vf-text-micro text-muted-foreground/60">{input.source}</span>
                  )}
                </div>
                <span className={cn("vf-text-micro font-medium shrink-0", config.iconClass)}>
                  {config.label}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </section>
  );
}
