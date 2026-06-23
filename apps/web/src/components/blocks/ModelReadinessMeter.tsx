/**
 * ModelReadinessMeter — Score-based readiness indicator with improvement opportunities.
 *
 * UI Contract (Data):
 *   - `score`         : 0–100 readiness percentage
 *   - `opportunities` : list of { label, impact } improvement suggestions
 *   - `variant`       : "compact" (inline summary) or "full" (detailed card)
 *
 * UI Contract (Rendering):
 *   - Score thresholds determine colour and icon:
 *       ≥ 80 → emerald (CheckCircle2) — "Model is well-supported"
 *       ≥ 50 → amber   (TrendingUp)   — "Model will be usable but has gaps"
 *       < 50 → destructive (AlertTriangle) — "Critical inputs missing"
 *   - Compact variant: single row with icon, label, percentage, and small progress bar
 *   - Full variant: card with explanatory copy, large percentage, progress bar,
 *     and optional improvement opportunities list
 *   - Opportunities section only renders when the array is non-empty
 *
 * Depends on: ./ProgressBar (internal block dependency)
 *
 * Extracted from: _ui-prototype/app/src/components/blocks/model-readiness-meter.tsx
 */
import { cn } from "@/lib/utils";
import { ProgressBar } from "./ProgressBar";
import { AlertTriangle, TrendingUp, CheckCircle2 } from "lucide-react";

export interface ReadinessOpportunity {
  /** Description of the improvement */
  label: string;
  /** Percentage-point impact if addressed */
  impact: number;
}

export interface ModelReadinessMeterProps {
  /** Readiness score (0–100) */
  score: number;
  /** Improvement opportunities */
  opportunities: ReadinessOpportunity[];
  /** Additional wrapper classes */
  className?: string;
  /** Display variant */
  variant?: "compact" | "full";
}

/* ── Threshold helpers ─────────────────────────────────────────────────── */

function scoreColor(score: number): string {
  if (score >= 80) return "text-success";
  if (score >= 50) return "text-warning";
  return "text-destructive";
}

function scoreBg(score: number): string {
  if (score >= 80) return "bg-success/100";
  if (score >= 50) return "bg-warning/100";
  return "bg-destructive";
}

function scoreIcon(score: number) {
  if (score >= 80) return CheckCircle2;
  return AlertTriangle;
}

/* ── Component ─────────────────────────────────────────────────────────── */

export function ModelReadinessMeter({
  score,
  opportunities,
  className,
  variant = "full",
}: ModelReadinessMeterProps) {
  const Icon = scoreIcon(score);
  const colorClass = scoreColor(score);
  const bgClass = scoreBg(score);

  /* ── Compact variant ─────────────────────────────────────────────────── */
  if (variant === "compact") {
    return (
      <div
        className={cn(
          "flex items-center gap-3 px-4 py-3 bg-card border border-border rounded-xl",
          className,
        )}
      >
        <div
          className={cn(
            "w-10 h-10 rounded-full flex items-center justify-center shrink-0",
            bgClass,
            "bg-opacity-10",
          )}
        >
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

  /* ── Full variant ────────────────────────────────────────────────────── */
  return (
    <div className={cn("bg-card border border-border rounded-xl overflow-hidden", className)}>
      <div className="px-5 py-4">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2.5">
            <div
              className={cn(
                "w-10 h-10 rounded-xl flex items-center justify-center",
                bgClass,
                "bg-opacity-10",
              )}
            >
              {score >= 80 ? (
                <CheckCircle2 className={cn("w-5 h-5", colorClass)} />
              ) : (
                <TrendingUp className={cn("w-5 h-5", colorClass)} />
              )}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Model Readiness</h3>
              <p className="vf-text-caption text-muted-foreground">
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
          <p className="vf-text-micro text-muted-foreground uppercase font-medium tracking-wider mb-2">
            Improvement Opportunities
          </p>
          <div className="space-y-1.5">
            {opportunities.map((o) => (
              <div key={o.label} className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">{o.label}</span>
                <span className={cn("vf-text-micro font-semibold", colorClass)}>+{o.impact}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
