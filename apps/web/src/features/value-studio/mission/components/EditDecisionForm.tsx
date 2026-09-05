/**
 * Value Studio (mission-led) — edit-decision form (contract §9.9, FE-RAIL-006).
 *
 * Validated with zod + react-hook-form (onBlur validation, onChange
 * revalidation). Departing from the recommended working or alternative target
 * REQUIRES a rationale — enforced by a schema built around the projection's
 * recommended values. The authoritative impact section is read-only: the
 * browser never recalculates it (FE-INTENT-002). Slice 1 produces a typed
 * draft; the command backend lands in Phase 2.
 */

import { useEffect, useMemo } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { FabricDialog } from "@/components/ui/fabric/FabricDialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import type { DecisionRequestProjection } from "../types";
import type { EditDecisionDraft } from "../intentPreview";
import { formatMoneyAnnual } from "../viewModel";
import {
  buildEditDecisionSchema,
  type EditDecisionFormValues,
} from "./editDecisionSchema";

export interface EditDecisionFormProps {
  readonly decision: DecisionRequestProjection;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onSubmitDraft: (draft: EditDecisionDraft) => void;
  /** Draft being continued, so an in-progress edit survives dialog close. */
  readonly initialDraft?: EditDecisionDraft | null;
}

export function EditDecisionForm({
  decision,
  open,
  onOpenChange,
  onSubmitDraft,
  initialDraft,
}: EditDecisionFormProps) {
  const recommendedWorking = decision.currentWorkingValue.value;
  const recommendedAlt = decision.alternative.value;
  const schema = useMemo(
    () => buildEditDecisionSchema(recommendedWorking, recommendedAlt),
    [recommendedWorking, recommendedAlt],
  );

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EditDecisionFormValues>({
    resolver: zodResolver(schema),
    mode: "onBlur",
    reValidateMode: "onChange",
    defaultValues: {
      workingHours: initialDraft?.workingHours ?? recommendedWorking,
      alternativeHours: initialDraft?.alternativeHours ?? recommendedAlt,
      alternativeScope: initialDraft?.alternativeScope ?? decision.alternative.proposedScope,
      rationale: initialDraft?.rationale ?? "",
    },
  });

  useEffect(() => {
    reset({
      workingHours: initialDraft?.workingHours ?? recommendedWorking,
      alternativeHours: initialDraft?.alternativeHours ?? recommendedAlt,
      alternativeScope: initialDraft?.alternativeScope ?? decision.alternative.proposedScope,
      rationale: initialDraft?.rationale ?? "",
    });
  }, [
    decision.decisionId,
    decision.decisionVersion,
    decision.modelVersion,
    initialDraft,
    recommendedAlt,
    recommendedWorking,
    reset,
  ]);

  const submit = handleSubmit((values) => {
    onSubmitDraft({
      workingHours: values.workingHours,
      alternativeHours: values.alternativeHours,
      alternativeScope: values.alternativeScope,
      rationale: values.rationale,
    });
  });

  return (
    <FabricDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`Edit decision ${decision.decisionId}`}
      description="Adjust the proposed targets. Departing from the recommendation requires a rationale."
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <label htmlFor="edit-working-hours" className="vf-text-body-s font-medium text-foreground">
            Working downtime target ({decision.currentWorkingValue.unit})
          </label>
          <Input
            id="edit-working-hours"
            type="number"
            inputMode="numeric"
            aria-invalid={errors.workingHours ? true : undefined}
            aria-describedby={errors.workingHours ? "edit-working-hours-error" : undefined}
            {...register("workingHours", { valueAsNumber: true })}
          />
          {errors.workingHours && (
            <p id="edit-working-hours-error" role="alert" className="vf-text-caption text-destructive">
              {errors.workingHours.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <label htmlFor="edit-alt-hours" className="vf-text-body-s font-medium text-foreground">
            Alternative target ({decision.alternative.unit})
          </label>
          <Input
            id="edit-alt-hours"
            type="number"
            inputMode="numeric"
            aria-invalid={errors.alternativeHours ? true : undefined}
            aria-describedby={errors.alternativeHours ? "edit-alt-hours-error" : undefined}
            {...register("alternativeHours", { valueAsNumber: true })}
          />
          {errors.alternativeHours && (
            <p id="edit-alt-hours-error" role="alert" className="vf-text-caption text-destructive">
              {errors.alternativeHours.message}
            </p>
          )}
        </div>

        <div className="space-y-1.5">
          <label htmlFor="edit-alt-scope" className="vf-text-body-s font-medium text-foreground">
            Alternative scope note
          </label>
          <Input id="edit-alt-scope" {...register("alternativeScope")} />
        </div>

        <div className="space-y-1.5">
          <label htmlFor="edit-rationale" className="vf-text-body-s font-medium text-foreground">
            Rationale
          </label>
          <Textarea
            id="edit-rationale"
            rows={3}
            aria-invalid={errors.rationale ? true : undefined}
            aria-describedby={errors.rationale ? "edit-rationale-error" : "edit-rationale-hint"}
            {...register("rationale")}
          />
          {errors.rationale ? (
            <p id="edit-rationale-error" role="alert" className="vf-text-caption text-destructive">
              {errors.rationale.message}
            </p>
          ) : (
            <p id="edit-rationale-hint" className="vf-text-caption text-muted-foreground">
              Required only when departing from the recommendation.
            </p>
          )}
        </div>

        <div
          aria-label="Authoritative impact (read-only)"
          className="rounded-md border border-border bg-muted/40 px-3 py-2"
        >
          <p className="vf-text-caption font-medium uppercase tracking-wider text-muted-foreground">
            Authoritative impact — read-only
          </p>
          <p className="vf-text-body-s text-foreground mt-1">
            Working {formatMoneyAnnual(decision.calculatedImpact.workingAnnualBenefit)} ·
            Alternative {formatMoneyAnnual(decision.calculatedImpact.alternativeAnnualBenefit)}
          </p>
          <p className="vf-text-caption text-muted-foreground mt-0.5">
            Impact is recalculated by the deterministic calculation service after submission;
            it is never edited here.
          </p>
        </div>

        <div className="flex flex-col-reverse gap-2 pt-2 sm:flex-row sm:justify-end sm:gap-3">
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button type="submit">Continue to preview</Button>
        </div>
      </form>
    </FabricDialog>
  );
}
