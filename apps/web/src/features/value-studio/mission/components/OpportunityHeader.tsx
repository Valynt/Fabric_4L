/**
 * Value Studio (mission-led) — opportunity header (contract §9.1, FE-HDR-*).
 *
 * Renders the case projection header exactly as supplied by the server:
 * account, opportunity, ARR, decision date, champion, the backend-owned
 * governance label (FE-HDR-003), publication state, and model version.
 * No economic values are derived here.
 */

import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/formatters";
import type { ValueStudioCaseProjection } from "../types";
import {
  formatGovernanceLabel,
  formatMoneyFull,
  PUBLICATION_STATE_DISPLAY,
} from "../viewModel";

export interface OpportunityHeaderProps {
  readonly projection: ValueStudioCaseProjection;
}

const PUBLICATION_BADGE_VARIANT: Record<string, "destructive" | "secondary" | "outline"> = {
  BLOCKED: "destructive",
  PROVISIONAL: "secondary",
  READY_FOR_REVIEW: "outline",
  APPROVED: "outline",
};

export function OpportunityHeader({ projection }: OpportunityHeaderProps) {
  const { account, opportunity, economics, governance, modelVersion, updatedAt } = projection;
  const publicationLabel = PUBLICATION_STATE_DISPLAY[governance.publicationState];
  const badgeVariant = PUBLICATION_BADGE_VARIANT[governance.publicationState] ?? "outline";

  return (
    <header aria-label="Opportunity summary" className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <h1 className="vf-display-m font-semibold text-foreground">
          {account.name} — {opportunity.opportunityId}
        </h1>
        <Badge variant="secondary" aria-label={`Governance label: ${formatGovernanceLabel(economics.annualBenefit.governanceLabel)}`}>
          {formatGovernanceLabel(economics.annualBenefit.governanceLabel)}
        </Badge>
        <Badge variant={badgeVariant} aria-label={`Publication state: ${publicationLabel}`}>
          {publicationLabel}
        </Badge>
      </div>
      <dl className="flex flex-wrap gap-x-6 gap-y-1 vf-text-body-s text-muted-foreground">
        <div className="flex gap-1.5">
          <dt className="font-medium text-foreground">ARR</dt>
          <dd>{formatMoneyFull(opportunity.arr)}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="font-medium text-foreground">Decision</dt>
          <dd>
            <time dateTime={opportunity.decisionDate}>{formatDate(opportunity.decisionDate)}</time>
          </dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="font-medium text-foreground">Champion</dt>
          <dd>{opportunity.champion.displayName}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="font-medium text-foreground">Model</dt>
          <dd>{modelVersion}</dd>
        </div>
        <div className="flex gap-1.5">
          <dt className="font-medium text-foreground">Updated</dt>
          <dd>
            <time dateTime={updatedAt}>{formatDate(updatedAt)}</time>
          </dd>
        </div>
      </dl>
    </header>
  );
}
