/**
 * Value Studio (mission-led) — proposed model patch (contract §9.5, FE-PATCH-*).
 *
 * Ordered list of patch items exactly as the artifact projects them: status
 * with icon + text (never color-only), affected objects, and linked evidence
 * identifiers. The UI does not reorder, infer, or complete patch items.
 */

import { CheckCircle2, CircleDashed, Circle, OctagonAlert } from "lucide-react";
import { FabricCard } from "@/components/ui/fabric/FabricCard";
import { cn } from "@/lib/utils";
import type { ModelPatchItemStatus, ModelPatchProjection } from "../types";

export interface ModelPatchCardProps {
  readonly patch: ModelPatchProjection;
}

const ITEM_STATUS: Record<
  ModelPatchItemStatus,
  { icon: typeof Circle; label: string; classes: string }
> = {
  proposed: { icon: CircleDashed, label: "Proposed", classes: "text-primary" },
  pending: { icon: Circle, label: "Pending", classes: "text-warning" },
  completed: { icon: CheckCircle2, label: "Completed", classes: "text-success" },
  blocked: { icon: OctagonAlert, label: "Blocked", classes: "text-destructive" },
};

export function ModelPatchCard({ patch }: ModelPatchCardProps) {
  const ordered = [...patch.items].sort((a, b) => a.order - b.order);
  return (
    <FabricCard
      title={patch.title}
      description={`Model ${patch.modelVersion} · artifact ${patch.artifactId}`}
      padding="normal"
    >
      <ol className="space-y-3" aria-label="Patch items">
        {ordered.map((item) => {
          const status = ITEM_STATUS[item.status];
          const Icon = status.icon;
          return (
            <li key={item.patchItemId} className="flex gap-3">
              <span className="vf-text-body-s font-semibold text-muted-foreground mt-0.5 w-5 text-right">
                {item.order}.
              </span>
              <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", status.classes)} aria-hidden="true" />
              <div className="min-w-0">
                <p className="vf-text-body-s text-foreground">{item.summary}</p>
                <p className="vf-text-caption text-muted-foreground mt-0.5">
                  <span className={cn("font-medium", status.classes)}>{status.label}</span>
                  {item.affectedObjectIds.length > 0 && (
                    <> · touches {item.affectedObjectIds.join(", ")}</>
                  )}
                  {item.evidenceIds.length > 0 && <> · evidence {item.evidenceIds.join(", ")}</>}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </FabricCard>
  );
}
