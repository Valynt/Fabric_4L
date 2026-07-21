/**
 * SearchErrorState Component
 *
 * Error state UI when search fails.
 */

import { AlertCircle } from "lucide-react";

interface SearchErrorStateProps {
  error?: Error | null;
  onRetry?: () => void;
}

export function SearchErrorState({ error, onRetry }: SearchErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
      <div className="w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
        <AlertCircle className="h-6 w-6 text-destructive" />
      </div>
      <h3 className="text-sm font-medium mb-2">Search failed</h3>
      <p className="text-xs text-muted-foreground max-w-sm mb-4">
        {error?.message || "An error occurred while searching. Please try again."}
      </p>
      {onRetry && (
        <button type="button"
          onClick={onRetry}
          className="text-xs px-3 py-1.5 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          Try again
        </button>
      )}
    </div>
  );
}
