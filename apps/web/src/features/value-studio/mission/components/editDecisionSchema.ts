/**
 * Value Studio (mission-led) — edit-decision validation schema (contract §9.9, FE-RAIL-006).
 *
 * Extracted from EditDecisionForm so the validation contract can be unit-tested
 * without rendering the dialog, and so the form module exports only components
 * (react-refresh/only-export-components). The schema is built around the
 * projection's recommended values: departing from the recommended working or
 * alternative target REQUIRES a rationale.
 */

import { z } from "zod";

export function buildEditDecisionSchema(
  recommendedWorkingHours: number,
  recommendedAltHours: number,
) {
  return z
    .object({
      workingHours: z
        .number({ error: "Enter the working target as a number." })
        .int("Working target must be a whole number of hours.")
        .positive("Working target must be above zero.")
        .max(100_000, "Working target is unreasonably large."),
      alternativeHours: z
        .number({ error: "Enter the alternative as a number." })
        .int("Alternative must be a whole number of hours.")
        .positive("Alternative must be above zero.")
        .max(100_000, "Alternative is unreasonably large.")
        .optional(),
      alternativeScope: z.string().trim().max(200, "Keep the scope note under 200 characters.").optional(),
      rationale: z.string().trim().max(2_000, "Keep the rationale under 2,000 characters."),
    })
    .superRefine((values, ctx) => {
      const departsFromRecommendation =
        values.workingHours !== recommendedWorkingHours ||
        (typeof values.alternativeHours === "number" &&
          values.alternativeHours !== recommendedAltHours);
      if (departsFromRecommendation && values.rationale.length === 0) {
        ctx.addIssue({
          code: "custom",
          path: ["rationale"],
          message:
            "A rationale is required when the edit departs from Flo's recommendation.",
        });
      }
    });
}

export type EditDecisionFormValues = z.infer<ReturnType<typeof buildEditDecisionSchema>>;
