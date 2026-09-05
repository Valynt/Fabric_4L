/**
 * Value Studio (mission-led) — decision intent preview (contract §9.9, FE-INTENT-*).
 *
 * Before a decision command is submitted, the user reviews a typed preview:
 * exactly what the command WILL do and WILL NOT do, plus the expected model
 * and decision versions. The Proceed control latches after the first click so
 * a command can never be double-submitted (FE-INTENT-003). In Slice 1 the
 * command backend is not connected; the page-level handler surfaces that
 * honestly instead of simulating success.
 */

import { useEffect, useState } from "react";
import { FabricDialog } from "@/components/ui/fabric/FabricDialog";
import { Button } from "@/components/ui/button";
import type { DecisionIntentPreviewContent } from "../types";

export interface DecisionIntentPreviewProps {
  readonly preview: DecisionIntentPreviewContent | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onProceed: (preview: DecisionIntentPreviewContent) => void;
}

export function DecisionIntentPreview({
  preview,
  open,
  onOpenChange,
  onProceed,
}: DecisionIntentPreviewProps) {
  const [proceedClicked, setProceedClicked] = useState(false);

  // Reset the latch whenever a different preview is shown or the dialog closes.
  useEffect(() => {
    if (!open) setProceedClicked(false);
  }, [open, preview]);

  if (!preview) return null;

  return (
    <FabricDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Review what this will do"
      description={`Command ${preview.commandType} · expects model ${preview.expectedModelVersion}, decision version ${preview.expectedDecisionVersion}`}
      footer={
        <>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            type="button"
            disabled={proceedClicked}
            onClick={() => {
              if (proceedClicked) return;
              setProceedClicked(true);
              onProceed(preview);
            }}
          >
            {proceedClicked ? "Submitting…" : "Proceed"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <div>
          <h3 className="vf-text-body-s font-semibold text-foreground">This will:</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 vf-text-body-s text-foreground">
            {preview.will.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div>
          <h3 className="vf-text-body-s font-semibold text-foreground">This will not:</h3>
          <ul className="mt-1 list-disc space-y-1 pl-5 vf-text-body-s text-muted-foreground">
            {preview.willNot.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </FabricDialog>
  );
}
