/**
 * Value Studio (mission-led) — inline error surface (contract §10, FE-ERR-001).
 *
 * Full-page error state: assertive announcement (role="alert"), the server
 * correlation ID for support traceability, and an explicit Retry action when
 * the failure is retryable. No auto-retry loops; retry is always user-initiated.
 */

import { AlertTriangle, RotateCcw } from "lucide-react";
import { Btn } from "@/components/ui/fabric/Btn";

export interface InlineErrorProps {
  readonly title?: string;
  readonly message: string;
  /** Server correlation ID — always shown, never invented. */
  readonly correlationId: string;
  readonly onRetry?: () => void;
}

export function InlineError({ title, message, correlationId, onRetry }: InlineErrorProps) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-destructive/40 bg-destructive/5 p-6 space-y-3"
    >
      <div className="flex items-start gap-3">
        <AlertTriangle className="h-5 w-5 mt-0.5 shrink-0 text-destructive" aria-hidden="true" />
        <div className="space-y-1">
          <h2 className="vf-heading-m font-semibold text-foreground">
            {title ?? "Value Studio couldn't load"}
          </h2>
          <p className="vf-text-body-m text-muted-foreground">{message}</p>
        </div>
      </div>
      <p className="vf-text-caption text-muted-foreground">
        Correlation ID: <span className="font-mono">{correlationId}</span>
      </p>
      {onRetry && (
        <Btn variant="outline" size="default" onClick={onRetry}>
          <RotateCcw className="mr-1.5 h-4 w-4" aria-hidden="true" />
          Retry
        </Btn>
      )}
    </div>
  );
}
