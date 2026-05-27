import { cn } from "@/lib/utils";
import { ProgressBar } from "./progress-bar";
import { AlertTriangle, TrendingUp, CheckCircle2 } from "lucide-react";

export interface ReadinessOpportunity {
  label: string;
  impact: number; // percentage points
}

interface ModelReadinessMeterProps {
  score: number; // 0-100
  opportunities: ReadinessOpportunity[];
  className?: string;
  variant?: "compact" | "full";
}

function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-500";
  if (score >= 50) return "text-amber-500";
  return "text-destructive";
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-emerald-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-destructive";
}

function scoreIcon(score: number) {
  if (score >= 80) return CheckCircle2;
  return AlertTriangle;
}

export function ModelReadinessMeter({ score, opportunities, className, variant = "full" }: ModelReadinessMeterProps) {
  const Icon = scoreIcon(score);
  const colorClass = scoreColor(score);
  const bgClass = scoreBg(score);

  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-3 px-4 py-3 bg-card border border-border rounded-xl", className)}>
        <div className={cn("w-10 h-10 rounded-full flex items-center justify-center shrink-0", bgClass, "bg-opacity-10")}>
          <Icon className={cn("w-5 h-5", colorClass)} />
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-semibold text-foreground">Model Readiness</span>
            <span className={cn("text-sm font-bold", colorClass)}>{score}%</span>
          </div>
          <ProgressBar value={score} max={100} size="sm" barClassName={bgClass} />
        </div>
      </div>
    );
  }

  return (
    <div className={cn("bg-card border border-border rounded-xl overflow-hidden", className)}>
      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center", bgClass, "bg-opacity-10")}>
              {score >= 80 ? (
                <CheckCircle2 className={cn("w-5 h-5", colorClass)} />
              ) : (
                <TrendingUp className={cn("w-5 h-5", colorClass)} />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Model Readiness</h3>
              <p className="text-[11px] text-muted-foreground">
                {score >= 80
                  ? "Model is well-supported. Generate when ready."
                  : score >= 50
                    ? "Model will be usable but has gaps."
                    : "Critical inputs missing. Model credibility will be low."}
              </p>
            </div>
          </div>
          <span className={cn("text-2xl font-bold", colorClass)}>{score}%</span>
        </div>
        <ProgressBar value={score} max={100} size="md" barClassName={bgClass} />
      </div>

      {opportunities.length > 0 && (
        <div className="border-t border-border/60 px-5 py-3">
          <p className="text-[10px] text-muted-foreground uppercase font-medium tracking-wider mb-2">Improvement Opportunities</p>
          <div className="space-y-1.5">
            {opportunities.map((o) => (
              <div key={o.label} className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{o.label}</span>
                <span className={cn("text-[10px] font-semibold", colorClass)}>+{o.impact}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
