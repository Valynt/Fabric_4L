/**
 * Value Studio (mission-led) — impact summary (contract §9.6, FE-IMP-*).
 *
 * Renders the case economics exactly as projected: annual benefit with its
 * backend governance label, program cost ("Pending" when the server reports
 * null — never zero), ROI ("Not yet calculable" when null), and the
 * server-rendered formula explanation. No recalculation in the browser.
 */

import { FabricCard } from "@/components/ui/fabric/FabricCard";
import { MetricCard } from "@/components/ui/fabric/MetricCard";
import type { ValueStudioCaseProjection } from "../types";
import {
  formatGovernanceLabel,
  formatMoneyAnnual,
  formatProgramCost,
  formatRoi,
} from "../viewModel";

export interface ImpactSummaryProps {
  readonly economics: ValueStudioCaseProjection["economics"];
}

export function ImpactSummary({ economics }: ImpactSummaryProps) {
  return (
    <section aria-label="Value impact summary" className="space-y-3">
      <h2 className="vf-heading-m font-semibold text-foreground">Value impact</h2>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Annual benefit"
          value={formatMoneyAnnual(economics.annualBenefit)}
          trend={{
            value: formatGovernanceLabel(economics.annualBenefit.governanceLabel),
            positive: null,
          }}
        />
        <MetricCard label="Program cost" value={formatProgramCost(economics.programCost)} />
        <MetricCard label="ROI" value={formatRoi(economics.roi)} />
        <FabricCard padding="normal" shadow="sm" className="h-full">
          <p className="vf-text-body-s font-medium text-muted-foreground uppercase tracking-wider">
            Benefit formula
          </p>
          <p className="vf-text-body-m text-foreground mt-2">{economics.formulaDisplay}</p>
          <p className="vf-text-caption text-muted-foreground mt-1">
            Formula {economics.formulaId}
          </p>
        </FabricCard>
      </div>
    </section>
  );
}
