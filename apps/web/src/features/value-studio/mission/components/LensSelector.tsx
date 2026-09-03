/**
 * Value Studio (mission-led) — audience lens selector (contract §9.2, FE-LENS-*).
 *
 * Lenses change presentation depth and ordering only; they never alter
 * economic content. Selection is reflected in `?lens=` so it survives refresh
 * (FE-LENS-004). Active lens is exposed with aria-pressed and a visible
 * check plus underline so state is never color-only (FE-A11Y-004).
 */

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { AUDIENCE_LENSES, type AudienceLens } from "../types";
import { LENS_DISPLAY } from "../viewModel";

export interface LensSelectorProps {
  readonly activeLens: AudienceLens;
  readonly onSelect: (lens: AudienceLens) => void;
}

export function LensSelector({ activeLens, onSelect }: LensSelectorProps) {
  return (
    <div role="group" aria-label="Audience lens" className="flex flex-wrap items-center gap-1">
      {AUDIENCE_LENSES.map((lens) => {
        const active = lens === activeLens;
        return (
          <button
            key={lens}
            type="button"
            aria-pressed={active}
            onClick={() => onSelect(lens)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 vf-text-body-s font-medium",
              "text-muted-foreground hover:text-foreground transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
              active && "text-foreground underline underline-offset-8 decoration-2 decoration-primary",
            )}
          >
            {active && <Check className="h-3.5 w-3.5" aria-hidden="true" />}
            {LENS_DISPLAY[lens]}
          </button>
        );
      })}
    </div>
  );
}
