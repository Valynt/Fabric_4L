/**
 * Value Studio (mission-led) — evidence drawer (contract §9.10, FE-EV-*).
 *
 * Shows the safe, server-cleared summary/excerpt for one evidence reference.
 * Restricted evidence renders a notice and NO excerpt (FE-EV-003): the front
 * end never reveals content the backend flagged as restricted.
 */

import { Lock } from "lucide-react";
import { SidePanel } from "@/components/ui/fabric/SidePanel";
import { formatDate } from "@/lib/formatters";
import type { EvidenceReference } from "../types";

export interface EvidenceDrawerProps {
  readonly evidence: EvidenceReference | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
}

export function EvidenceDrawer({ evidence, open, onOpenChange }: EvidenceDrawerProps) {
  return (
    <SidePanel
      open={open}
      onOpenChange={onOpenChange}
      title={evidence ? evidence.sourceTitle : "Evidence"}
      description={evidence ? `${evidence.sourceType} · ${evidence.evidenceId}` : undefined}
      width="lg"
    >
      {evidence && (
        <div className="space-y-4">
          {evidence.restricted ? (
            <div
              role="note"
              className="flex items-start gap-2 rounded-md border border-warning/40 bg-warning/10 px-3 py-2"
            >
              <Lock className="h-4 w-4 mt-0.5 shrink-0 text-warning" aria-hidden="true" />
              <p className="vf-text-body-s text-foreground">
                This source is restricted. Only governance metadata is shown; the excerpt is
                withheld pending access approval.
              </p>
            </div>
          ) : (
            <p className="vf-text-body-m text-foreground">{evidence.excerpt}</p>
          )}
          <dl className="space-y-2 vf-text-body-s">
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Captured</dt>
              <dd className="text-foreground">
                <time dateTime={evidence.capturedAt}>{formatDate(evidence.capturedAt)}</time>
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Traceability</dt>
              <dd className="text-foreground">{evidence.traceabilityState}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Validation</dt>
              <dd className="text-foreground">{evidence.validationState}</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted-foreground">Approval</dt>
              <dd className="text-foreground">{evidence.approvalState}</dd>
            </div>
            {evidence.affectedObjectIds.length > 0 && (
              <div className="flex justify-between gap-3">
                <dt className="text-muted-foreground">Affects</dt>
                <dd className="text-foreground text-right">
                  {evidence.affectedObjectIds.join(", ")}
                </dd>
              </div>
            )}
          </dl>
        </div>
      )}
    </SidePanel>
  );
}
