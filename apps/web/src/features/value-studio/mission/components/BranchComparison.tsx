/**
 * Value Studio (mission-led) — branch comparison (contract §9.7, FE-BR-*).
 *
 * Renders backend-calculated branch values only. Bars are proportional to the
 * server-supplied amounts (presentation scaling of given values, never new
 * arithmetic). "Preferred" is shown only when the decision projection marks
 * the branch recommended (FE-BR-004). When the projection reports
 * AWAITING_AUTHORITATIVE_CALCULATION, no numbers are shown at all.
 */

import { BadgeCheck } from "lucide-react";
import { FabricCard } from "@/components/ui/fabric/FabricCard";
import { cn } from "@/lib/utils";
import type { BranchComparisonProjection } from "../types";
import { formatMoneyAnnual } from "../viewModel";

export interface BranchComparisonProps {
  readonly comparison: BranchComparisonProjection;
}

export function BranchComparison({ comparison }: BranchComparisonProps) {
  if (comparison.status === "AWAITING_AUTHORITATIVE_CALCULATION") {
    return (
      <FabricCard title={comparison.title} padding="normal">
        <p className="vf-text-body-s text-muted-foreground" role="status">
          Awaiting authoritative calculation. Branch economics are not shown until the
          deterministic calculation service returns values.
        </p>
      </FabricCard>
    );
  }

  const maxAmount = Math.max(
    ...comparison.branches.flatMap((b) => b.metrics.map((m) => m.value.amount)),
    1,
  );

  return (
    <FabricCard
      title={comparison.title}
      description={
        [comparison.horizonLabel, comparison.timingConventionLabel]
          .filter((label): label is string => label !== null)
          .join(" · ") || undefined
      }
      padding="normal"
    >
      <ul className="space-y-4" aria-label="Scenario branches">
        {comparison.branches.map((branch) => (
          <li key={branch.branchId} className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-2">
              <p className="vf-text-body-s font-medium text-foreground">{branch.label}</p>
              {branch.recommended && (
                <span className="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                  <BadgeCheck className="h-3 w-3" aria-hidden="true" />
                  Preferred
                </span>
              )}
              <span className="vf-text-caption text-muted-foreground">{branch.evidenceState}</span>
            </div>
            {branch.metrics.map((metric) => (
              <div key={metric.label} className="space-y-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="vf-text-caption text-muted-foreground">{metric.label}</span>
                  <span className="vf-text-body-s font-semibold text-foreground">
                    {formatMoneyAnnual(metric.value)}
                  </span>
                </div>
                <div
                  className="h-2 rounded-full bg-muted"
                  role="img"
                  aria-label={`${metric.label}: ${formatMoneyAnnual(metric.value)}`}
                >
                  <div
                    className={cn(
                      "h-2 rounded-full",
                      branch.recommended ? "bg-primary" : "bg-muted-foreground/40",
                    )}
                    style={{ width: `${Math.round((metric.value.amount / maxAmount) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </li>
        ))}
      </ul>
    </FabricCard>
  );
}
