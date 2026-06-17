/**
 * ErrorState — Structured error state with retry and fallback actions
 *
 * Use when queries fail. Never show raw error text directly on canvas.
 */
import { AlertCircle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { ReactNode } from "react";
import { Btn } from "@/components/ui/fabric";

interface ErrorStateProps {
  title: string;
  description?: string;
  error?: Error | unknown;
  onRetry?: () => void;
  retryLabel?: string;
  fallbackAction?: ReactNode;
  className?: string;
  fullPage?: boolean;
}

export function ErrorState({ 
  title, 
  description,
  error,
  onRetry,
  retryLabel = "Retry",
  fallbackAction,
  className,
  fullPage = false
}: ErrorStateProps) {
  const [showDetails, setShowDetails] = useState(false);
  
  const errorMessage = error instanceof Error 
    ? error.message 
    : typeof error === 'string' 
      ? error 
      : JSON.stringify(error) ?? 'Unknown error';

  return (
    <div 
      role="alert"
      aria-live="assertive"
      className={cn(
        "flex flex-col items-center justify-center gap-4 text-center",
        fullPage ? "min-h-[60vh]" : "py-16",
        className
      )}
    >
      <AlertCircle size={32} className="text-destructive/70" aria-hidden="true" />
      <div className="space-y-1">
        <h3 className="text-sm font-medium text-foreground">{title}</h3>
        {description && (
          <p className="text-xs text-muted-foreground max-w-sm">{description}</p>
        )}
      </div>
      
      <div className="flex items-center gap-2 pt-1">
        {onRetry && (
          <Btn variant="outline" onClick={onRetry}>
            {retryLabel}
          </Btn>
        )}
        {fallbackAction}
      </div>

      {!!error && (
        <div className="pt-2">
          <button
            onClick={() => setShowDetails(!showDetails)}
            aria-expanded={showDetails}
            className="flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          >
            {showDetails ? <ChevronUp size={12} aria-hidden="true" /> : <ChevronDown size={12} aria-hidden="true" />}
            {showDetails ? "Hide details" : "Show details"}
          </button>
          {showDetails && (
            <div className="mt-2 max-w-sm overflow-auto rounded bg-muted/50 p-2 text-left font-mono vf-text-micro text-muted-foreground">
              {String(errorMessage)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default ErrorState;
