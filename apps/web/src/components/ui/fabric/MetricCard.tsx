import { FabricCard } from "./FabricCard";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

export interface MetricCardProps {
  label: string;
  value: string;
  /**
   * Trend display. Accepts either:
   * - `{ value: string; positive: boolean | null }` — canonical form
   * - `string` — legacy shorthand (use with `trendUp` for direction)
   */
  trend?: { value: string; positive: boolean | null } | string;
  /** Used with legacy string `trend` to indicate direction. */
  trendUp?: boolean;
  className?: string;
}

export function MetricCard({ label, value, trend, trendUp, className }: MetricCardProps) {
  // Normalise legacy string trend to the canonical object form.
  const resolvedTrend: { value: string; positive: boolean | null } | undefined =
    typeof trend === "string"
      ? { value: trend, positive: trendUp === undefined ? null : trendUp }
      : trend;
  return (
    <FabricCard padding="normal" shadow="sm" className={cn("h-full", className)}>
      <p className="vf-text-body-s font-medium text-muted-foreground uppercase tracking-wider">
        {label}
      </p>
      <p className="vf-display-l font-bold text-foreground mt-1">
        {value}
      </p>
      {resolvedTrend && (
        <div className={cn("flex items-center gap-1 mt-2 vf-text-body-s font-medium",
          resolvedTrend.positive === true && "text-success dark:text-success",
          resolvedTrend.positive === false && "text-destructive dark:text-destructive",
          resolvedTrend.positive === null && "text-muted-foreground"
        )}>
          {resolvedTrend.positive === true && <TrendingUp className="h-3.5 w-3.5" />}
          {resolvedTrend.positive === false && <TrendingDown className="h-3.5 w-3.5" />}
          {resolvedTrend.positive === null && <Minus className="h-3.5 w-3.5" />}
          {resolvedTrend.value}
        </div>
      )}
    </FabricCard>
  );
}
