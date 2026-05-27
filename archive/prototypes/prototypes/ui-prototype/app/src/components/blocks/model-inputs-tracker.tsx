import { useState } from "react";
import { cn } from "@/lib/utils";
import { CheckCircle2, AlertTriangle, BrainCircuit } from "lucide-react";

export type InputStatus = "complete" | "missing" | "inferred";

export interface ModelInput {
  id: string;
  label: string;
  status: InputStatus;
  value?: string;
  source?: string;
  onClick?: () => void;
}

interface ModelInputsTrackerProps {
  inputs: ModelInput[];
  className?: string;
}

const statusConfig: Record<InputStatus, { icon: typeof CheckCircle2; iconClass: string; label: string }> = {
  complete: { icon: CheckCircle2, iconClass: "text-emerald-500", label: "Complete" },
  inferred: { icon: BrainCircuit, iconClass: "text-primary", label: "Inferred" },
  missing: { icon: AlertTriangle, iconClass: "text-amber-500", label: "Missing" },
};

export function ModelInputsTracker({ inputs, className }: ModelInputsTrackerProps) {
  const [collapsed, setCollapsed] = useState(false);
  const completeCount = inputs.filter((i) => i.status === "complete").length;
  const inferredCount = inputs.filter((i) => i.status === "inferred").length;
  const missingCount = inputs.filter((i) => i.status === "missing").length;

  return (
    <section
      className={cn("bg-card rounded-xl border border-border overflow-hidden", className)}
      aria-label="Model inputs tracker"
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/50 transition-colors"
        aria-expanded={!collapsed}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-foreground">Value Model Inputs</span>
          <div className="flex items-center gap-2">
            {completeCount > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-emerald-500 font-medium">
                <CheckCircle2 className="w-3 h-3" />{completeCount}
              </span>
            )}
            {inferredCount > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-primary font-medium">
                <BrainCircuit className="w-3 h-3" />{inferredCount}
              </span>
            )}
            {missingCount > 0 && (
              <span className="flex items-center gap-1 text-[10px] text-amber-500 font-medium">
                <AlertTriangle className="w-3 h-3" />{missingCount}
              </span>
            )}
          </div>
        </div>
        <svg
          className={cn("w-4 h-4 text-muted-foreground transition-transform", collapsed && "-rotate-90")}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!collapsed && (
        <div className="px-4 pb-3 space-y-1">
          {inputs.map((input) => {
            const config = statusConfig[input.status];
            const Icon = config.icon;
            return (
              <button
                key={input.id}
                onClick={input.onClick}
                className={cn(
                  "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-left transition-colors",
                  input.onClick ? "hover:bg-muted cursor-pointer" : "cursor-default"
                )}
              >
                <Icon className={cn("w-4 h-4 shrink-0", config.iconClass)} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-foreground">{input.label}</span>
                    {input.value && (
                      <span className="text-[10px] text-muted-foreground truncate">{input.value}</span>
                    )}
                  </div>
                  {input.source && (
                    <span className="text-[10px] text-muted-foreground/60">{input.source}</span>
                  )}
                </div>
                <span className={cn("text-[10px] font-medium shrink-0", config.iconClass)}>
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
