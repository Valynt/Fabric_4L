import { cn } from "@/lib/utils";
import { captureException } from "@/lib/telemetry";
import { AlertTriangle, RotateCcw, Copy, Check } from "lucide-react";
import { Component, ReactNode, useState } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  traceId: string | null;
  errorCode: string | null;
}

/**
 * ApiError interface matching the error class from client.ts
 */
interface ApiError extends Error {
  traceId: string | null;
  statusCode: number;
  errorCode: string;
}

/**
 * Copy button component for trace ID
 */
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API not available, ignore
    }
  };

  return (
    <button
      onClick={handleCopy}
      className="ml-2 p-1 rounded hover:bg-muted transition-colors"
      title="Copy trace ID"
    >
      {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
    </button>
  );
}

/**
 * Error boundary with production-safe error display.
 *
 * Task 60: Error Response Hardening
 * - In production: Shows generic error message + trace_id for support
 * - In development: Shows full stack trace for debugging
 */
class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null, traceId: null, errorCode: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Extract trace_id and error_code from ApiError if available
    const apiError = error as ApiError;
    const traceId = apiError.traceId || null;
    const errorCode = apiError.errorCode || null;
    return { hasError: true, error, traceId, errorCode };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    captureException(error, {
      traceId: this.state.traceId,
      componentStack: errorInfo.componentStack,
    });

    this.setState({ errorInfo });
  }

  private getSupportMessage(): string {
    if (this.state.traceId) {
      return `Please contact support and reference trace ID: ${this.state.traceId}`;
    }
    return "Please try again or contact support if the problem persists.";
  }

  render() {
    if (this.state.hasError) {
      const isDev = import.meta.env.DEV;
      const { error, traceId, errorCode } = this.state;

      return (
        <div className="flex items-center justify-center min-h-screen p-8 bg-background">
          <div className="flex flex-col items-center w-full max-w-2xl p-8">
            <AlertTriangle
              size={48}
              className="text-destructive mb-6 flex-shrink-0"
            />

            <h2 className="text-xl font-semibold mb-2">Something went wrong</h2>
            <p className="text-muted-foreground mb-6 text-center">
              {this.getSupportMessage()}
            </p>

            {/* Error code display */}
            {errorCode && (
              <div className="mb-4 px-3 py-1 bg-destructive/10 rounded-full">
                <span className="text-xs font-medium text-destructive">Error: {errorCode}</span>
              </div>
            )}

            {/* Trace ID display for support correlation */}
            {traceId && (
              <div className="flex items-center mb-6 p-3 bg-muted rounded-lg">
                <span className="text-sm text-muted-foreground">Trace ID:</span>
                <code className="ml-2 text-sm font-mono bg-background px-2 py-1 rounded">
                  {traceId}
                </code>
                <CopyButton text={traceId} />
              </div>
            )}

            {/* Debug info - only shown in development */}
            {isDev && error && (
              <div className="p-4 w-full rounded bg-muted overflow-auto mb-6">
                <div className="text-xs text-muted-foreground mb-2">
                  Development Mode - Full error details:
                </div>
                <pre className="text-sm text-muted-foreground whitespace-pre-wrap break-all">
                  {error.stack || error.message}
                </pre>
              </div>
            )}

            <button
              onClick={() => window.location.reload()}
              className={cn(
                "flex items-center gap-2 px-4 py-2 rounded-lg",
                "bg-primary text-primary-foreground",
                "hover:opacity-90 cursor-pointer transition-opacity"
              )}
            >
              <RotateCcw size={16} />
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
