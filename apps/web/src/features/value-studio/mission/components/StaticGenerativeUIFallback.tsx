/**
 * Value Studio (mission-led) — static generative-UI fallback notice
 * (contract §11.4, FE-SUC-010).
 *
 * When a tailored (generative) surface fails — or the server projection flags
 * `generativeUiFallback` — the affected lens renders the approved static
 * component plus this non-blocking notice. The notice never replaces
 * authoritative data and never blocks the rest of the page.
 */

import { Info } from "lucide-react";

export interface StaticGenerativeUIFallbackProps {
  /** Server-reported component name (e.g. "BranchComparison"). */
  readonly componentName: string;
  /** Server-reported failure class, when known. */
  readonly failureClass?: string;
}

export function StaticGenerativeUIFallback({
  componentName,
  failureClass,
}: StaticGenerativeUIFallbackProps) {
  return (
    <div
      role="status"
      data-testid="generative-ui-fallback"
      className="flex items-start gap-2 rounded-md border border-border bg-muted/40 px-3 py-2"
    >
      <Info className="h-4 w-4 mt-0.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      <p className="vf-text-body-s text-muted-foreground">
        The tailored view for {componentName} is temporarily unavailable. You are seeing the
        approved static version — no data was lost.
        {failureClass ? ` (Reference: ${failureClass})` : ""}
      </p>
    </div>
  );
}
