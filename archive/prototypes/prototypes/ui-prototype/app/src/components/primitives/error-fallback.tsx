import { AlertTriangle, RotateCcw, Home } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ErrorFallbackProps {
  error?: Error;
  resetErrorBoundary?: () => void;
}

export function ErrorFallback({ error, resetErrorBoundary }: ErrorFallbackProps) {
  const navigate = useNavigate();

  return (
    <main className="min-h-screen flex items-center justify-center p-6" role="alert" aria-label="Application error">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="w-16 h-16 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto">
          <AlertTriangle className="w-8 h-8 text-destructive" />
        </div>

        <div>
          <h1 className="text-lg font-bold text-foreground mb-1">Something went wrong</h1>
          <p className="text-sm text-muted-foreground">
            An unexpected error occurred. Try refreshing the page or return home.
          </p>
        </div>

        {error && (
          <pre className="text-left text-xs bg-muted rounded-lg p-4 overflow-auto text-muted-foreground border border-border">
            <code>{error.message}</code>
          </pre>
        )}

        <div className="flex items-center justify-center gap-3">
          {resetErrorBoundary && (
            <button
              onClick={resetErrorBoundary}
              className="flex items-center gap-2 px-4 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90"
            >
              <RotateCcw className="w-4 h-4" />
              Try Again
            </button>
          )}
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-2 px-4 py-2.5 bg-card border border-border text-foreground rounded-lg text-sm font-medium hover:bg-muted"
          >
            <Home className="w-4 h-4" />
            Go Home
          </button>
        </div>
      </div>
    </main>
  );
}
