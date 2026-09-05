/**
 * Value Studio (mission-led) — Review Required decision rail (contract §9.9,
 * FE-RAIL-001…009).
 *
 * Renders the decision projection verbatim: escalation reason, working vs
 * alternative values, read-only calculated impact, sensitivity, Flo's
 * recommendation, governance rows, evidence access (Restricted entries never
 * reveal excerpts), and the "Why Flo stopped" detail. Action buttons render
 * ONLY for backend-authorized allowedActions, and submission is disabled
 * while stale or offline (FE-RAIL-008/009). When the projection carries a
 * resolution, the rail shows the resolved state from that payload — the UI
 * never infers resolution (FE-DEC-004) and never invents a "Locked" label
 * (FE-DEC-005).
 *
 * Focus: the rail heading receives focus when the decision changes (deep
 * link), and focus returns to the previously focused element on close.
 */

import { useEffect, useRef, useState } from "react";
import { Lock, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Btn } from "@/components/ui/fabric/Btn";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { formatDate } from "@/lib/formatters";
import type { DecisionRequestProjection, EvidenceReference } from "../types";
import { VALUE_STUDIO_ACTIONS } from "../types";
import { formatMoneyAnnual } from "../viewModel";

export interface DeferDecisionInput {
  readonly ownerDisplayName: string;
  readonly dueAt: string;
  readonly reason: string;
}

export interface DecisionRailProps {
  readonly decision: DecisionRequestProjection;
  readonly stale: boolean;
  readonly offline?: boolean;
  readonly submitting: boolean;
  readonly onAccept: () => void;
  readonly onEdit: () => void;
  readonly onDefer: (input: DeferDecisionInput) => void;
  readonly onOpenEvidence: (evidence: EvidenceReference) => void;
  readonly onClose: () => void;
}

export function DecisionRail({
  decision,
  stale,
  offline = false,
  submitting,
  onAccept,
  onEdit,
  onDefer,
  onOpenEvidence,
  onClose,
}: DecisionRailProps) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const restoreFocusRef = useRef<Element | null>(null);
  const [deferOpen, setDeferOpen] = useState(false);
  const [deferOwner, setDeferOwner] = useState("");
  const [deferDue, setDeferDue] = useState("");
  const [deferReason, setDeferReason] = useState("");

  // Deep-link focus: move focus to the rail heading when the decision changes
  // (FE-A11Y-009), and restore focus to the invoking element on unmount.
  useEffect(() => {
    restoreFocusRef.current = document.activeElement;
    headingRef.current?.focus();
    return () => {
      const previous = restoreFocusRef.current;
      if (previous instanceof HTMLElement) previous.focus();
    };
  }, [decision.decisionId]);

  const canSubmit = decision.allowedActions.includes(VALUE_STUDIO_ACTIONS.decisionSubmit);
  const canEdit = decision.allowedActions.includes(VALUE_STUDIO_ACTIONS.decisionEdit);
  const canDefer = decision.allowedActions.includes(VALUE_STUDIO_ACTIONS.decisionDefer);
  const canViewEvidence = decision.allowedActions.includes(VALUE_STUDIO_ACTIONS.evidenceView);
  const mutationsPaused = stale || offline;
  const isOpen = decision.status === "OPEN";
  const resolved = decision.status === "RESOLVED" && decision.resolution !== undefined;

  const deferReady =
    deferOwner.trim().length > 0 && deferDue.trim().length > 0 && deferReason.trim().length > 0;

  return (
    <aside
      aria-label={`Review required: ${decision.title}`}
      className="rounded-lg border border-border bg-card p-4 space-y-4"
      data-testid="decision-rail"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h2
            ref={headingRef}
            tabIndex={-1}
            className="vf-heading-m font-semibold text-foreground outline-none"
          >
            Review required — {decision.decisionId}
          </h2>
          <p className="vf-text-caption text-muted-foreground">
            Decision version {decision.decisionVersion} · model {decision.modelVersion} · status{" "}
            {decision.status}
          </p>
        </div>
        <Btn variant="ghost" size="icon" onClick={onClose} aria-label="Close decision rail">
          <X className="h-4 w-4" aria-hidden="true" />
        </Btn>
      </div>

      {stale && (
        <div
          role="alert"
          className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2"
        >
          <p className="vf-text-body-s font-medium text-destructive">
            This decision changed on the server.
          </p>
          <p className="vf-text-caption text-muted-foreground mt-0.5">
            Submissions are paused until the latest projection loads.
          </p>
        </div>
      )}
      {!stale && offline && (
        <p
          role="status"
          className="rounded-md border border-warning/40 bg-warning/10 px-3 py-2 vf-text-caption text-foreground"
        >
          Offline: decision actions are paused until the connection returns.
        </p>
      )}

      <div className="space-y-1">
        <h3 className="vf-text-body-s font-semibold text-foreground">{decision.title}</h3>
        <p className="vf-text-body-s text-muted-foreground">{decision.reasonForEscalation}</p>
      </div>

      <dl className="grid grid-cols-2 gap-2 vf-text-body-s">
        <div className="rounded-md bg-muted/50 px-3 py-2">
          <dt className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
            Working target
          </dt>
          <dd className="text-foreground font-semibold mt-0.5">
            {decision.currentWorkingValue.value} {decision.currentWorkingValue.unit}
          </dd>
        </div>
        <div className="rounded-md bg-muted/50 px-3 py-2">
          <dt className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
            Alternative
          </dt>
          <dd className="text-foreground font-semibold mt-0.5">
            {decision.alternative.value} {decision.alternative.unit}
          </dd>
          <dd className="vf-text-caption text-muted-foreground">
            {decision.alternative.proposedScope}
          </dd>
        </div>
        <div className="rounded-md bg-muted/50 px-3 py-2">
          <dt className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
            Working benefit
          </dt>
          <dd className="text-foreground font-semibold mt-0.5">
            {formatMoneyAnnual(decision.calculatedImpact.workingAnnualBenefit)}
          </dd>
        </div>
        <div className="rounded-md bg-muted/50 px-3 py-2">
          <dt className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
            Alternative benefit
          </dt>
          <dd className="text-foreground font-semibold mt-0.5">
            {formatMoneyAnnual(decision.calculatedImpact.alternativeAnnualBenefit)}
          </dd>
        </div>
      </dl>

      <p className="vf-text-caption text-muted-foreground">{decision.sensitivity.display}</p>

      <div className="rounded-md border border-primary/30 bg-primary/5 px-3 py-2">
        <p className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
          Flo's recommendation
        </p>
        <p className="vf-text-body-s text-foreground mt-0.5">{decision.recommendation}</p>
      </div>

      <dl className="space-y-1.5 vf-text-body-s" aria-label="Governance">
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Traceability</dt>
          <dd className="text-foreground text-right">{decision.governance.traceability}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Validation</dt>
          <dd className="text-foreground text-right">{decision.governance.validation}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Approval</dt>
          <dd className="text-foreground text-right">{decision.governance.approval}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Economic inclusion</dt>
          <dd className="text-foreground text-right">{decision.governance.economicInclusion}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt className="text-muted-foreground">Required authority</dt>
          <dd className="text-foreground text-right">{decision.governance.requiredAuthority}</dd>
        </div>
      </dl>

      <div className="space-y-1.5">
        <h3 className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
          Evidence
        </h3>
        <ul className="space-y-1">
          {decision.evidence.map((item) => (
            <li key={item.evidenceId} className="flex items-center gap-2">
              <Btn
                variant="ghost"
                size="sm"
                disabled={!canViewEvidence}
                onClick={() => onOpenEvidence(item)}
                className="justify-start text-left"
                aria-label={`Open evidence ${item.evidenceId}: ${item.sourceTitle}`}
              >
                {item.sourceTitle}
              </Btn>
              {item.restricted && (
                <Badge variant="secondary" className="gap-1">
                  <Lock className="h-3 w-3" aria-hidden="true" />
                  Restricted
                </Badge>
              )}
            </li>
          ))}
        </ul>
        {!canViewEvidence && (
          <p className="vf-text-caption text-muted-foreground">
            Evidence access is not granted for your role on this decision.
          </p>
        )}
      </div>

      <h3
        id={`why-flo-stopped-${decision.decisionId}`}
        className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground"
      >
        Why Flo stopped
      </h3>
      <dl
        className="space-y-1.5 vf-text-body-s"
        aria-labelledby={`why-flo-stopped-${decision.decisionId}`}
      >
        <div>
          <dt className="text-muted-foreground">Trigger</dt>
          <dd className="text-foreground">{decision.escalationDetail.trigger}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Attempted</dt>
          <dd className="text-foreground">{decision.escalationDetail.attemptedWork}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Stopping boundary</dt>
          <dd className="text-foreground">{decision.escalationDetail.stoppingBoundary}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Recommended next action</dt>
          <dd className="text-foreground">{decision.escalationDetail.recommendedNextAction}</dd>
        </div>
      </dl>

      {resolved && decision.resolution && (
        <div
          className="rounded-md border border-success/40 bg-success/5 px-3 py-2"
          aria-label="Decision resolution"
        >
          <p className="vf-text-body-s font-semibold text-foreground">
            {decision.resolution.outcomeLabel}
          </p>
          <p className="vf-text-caption text-muted-foreground">
            Resolved by {decision.resolution.resolvedByDisplayName} on{" "}
            <time dateTime={decision.resolution.resolvedAt}>
              {formatDate(decision.resolution.resolvedAt)}
            </time>
          </p>
          <p className="vf-text-body-s text-foreground mt-1">{decision.resolution.summary}</p>
        </div>
      )}

      {isOpen && (
        <div className="space-y-3 border-t border-border pt-3">
          <div className="flex flex-col gap-2">
            {canSubmit && (
              <Btn
                variant="primary"
                size="default"
                disabled={!canSubmit || submitting || mutationsPaused}
                onClick={onAccept}
              >
                {submitting ? "Submitting…" : "Accept recommendation"}
              </Btn>
            )}
            {canEdit && (
              <Btn variant="outline" size="default" disabled={mutationsPaused} onClick={onEdit}>
                Edit decision
              </Btn>
            )}
            {canDefer && (
              <Btn
                variant="ghost"
                size="default"
                disabled={mutationsPaused}
                onClick={() => setDeferOpen((open) => !open)}
                aria-label="Defer decision"
              >
                Defer decision
              </Btn>
            )}
          </div>

          {deferOpen && canDefer && (
            <div className="space-y-2 rounded-md border border-border p-3">
              <div className="space-y-1">
                <label htmlFor="defer-owner" className="vf-text-body-s font-medium text-foreground">
                  Defer to
                </label>
                <Input
                  id="defer-owner"
                  value={deferOwner}
                  onChange={(event) => setDeferOwner(event.target.value)}
                  placeholder="Owner display name"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="defer-due" className="vf-text-body-s font-medium text-foreground">
                  Due date
                </label>
                <Input
                  id="defer-due"
                  type="date"
                  value={deferDue}
                  onChange={(event) => setDeferDue(event.target.value)}
                />
              </div>
              <div className="space-y-1">
                <label htmlFor="defer-reason" className="vf-text-body-s font-medium text-foreground">
                  Reason
                </label>
                <Textarea
                  id="defer-reason"
                  rows={2}
                  value={deferReason}
                  onChange={(event) => setDeferReason(event.target.value)}
                />
              </div>
              <Button
                type="button"
                className="w-full"
                disabled={!deferReady || submitting || mutationsPaused}
                onClick={() =>
                  onDefer({
                    ownerDisplayName: deferOwner.trim(),
                    dueAt: deferDue,
                    reason: deferReason.trim(),
                  })
                }
              >
                Continue to preview
              </Button>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
