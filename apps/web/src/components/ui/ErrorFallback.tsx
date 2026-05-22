/**
 * ErrorFallback — Production-Grade Error UI
 *
 * Provides graceful degradation when components fail.
 * Follows Apple-level quality standards for error messaging.
 */

import { AlertTriangle, RefreshCw, Home, ArrowLeft } from 'lucide-react';
import { Button } from './button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './card';
import { cn } from '@/lib/utils';
import { useNavigation } from '@/hooks/useNavigation';
import { normalizeError } from '@/lib/errors';

interface ErrorFallbackProps {
  error?: Error | null;
  title?: string;
  description?: string;
  onRetry?: () => void;
  onReset?: () => void;
  showHomeButton?: boolean;
  showBackButton?: boolean;
  className?: string;
}

export function ErrorFallback({
  error,
  title = 'Something went wrong',
  description,
  onRetry,
  onReset,
  showHomeButton = true,
  showBackButton = true,
  className,
}: ErrorFallbackProps) {
  const normalizedError = error ? normalizeError(error) : undefined;
  const errorMessage = normalizedError?.message ?? description ?? 'An unexpected error occurred';
  const errorCode = normalizedError?.code;

  const handleBack = () => {
    window.history.back();
  };

  const { navigateTo } = useNavigation();

  const handleHome = () => {
    navigateTo('home');
  };

  return (
    <Card className={cn('max-w-md mx-auto', className)}>
      <CardHeader className="text-center">
        <div className="mx-auto w-12 h-12 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
          <AlertTriangle className="w-6 h-6 text-destructive" />
        </div>
        <CardTitle className="text-lg">{title}</CardTitle>
        <CardDescription className="text-sm text-muted-foreground">
          {errorMessage}
        </CardDescription>
        {errorCode && process.env.NODE_ENV === 'development' && (
          <p className="text-xs text-muted-foreground mt-2 font-mono">
            Error code: {errorCode}
          </p>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {onRetry && (
          <Button onClick={onRetry} className="w-full" variant="default">
            <RefreshCw className="w-4 h-4 mr-2" />
            Try Again
          </Button>
        )}
        {onReset && (
          <Button onClick={onReset} className="w-full" variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Reset
          </Button>
        )}
        <div className="flex gap-3">
          {showBackButton && (
            <Button onClick={handleBack} variant="outline" className="flex-1">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Go Back
            </Button>
          )}
          {showHomeButton && (
            <Button onClick={handleHome} variant="outline" className="flex-1">
              <Home className="w-4 h-4 mr-2" />
              Home
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Inline error message for forms and small components
 */
export function InlineError({
  message,
  onRetry,
  className,
}: {
  message: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div className={cn('flex items-center gap-2 text-sm text-destructive', className)}>
      <AlertTriangle className="w-4 h-4" />
      <span>{message}</span>
      {onRetry && (
        <button
          onClick={onRetry}
          className="ml-2 text-primary hover:underline font-medium"
        >
          Retry
        </button>
      )}
    </div>
  );
}

/**
 * Section-level error with skeleton fallback
 */
export function SectionError({
  title,
  message,
  onRetry,
}: {
  title: string;
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="p-6 border border-dashed border-border rounded-lg bg-muted/30">
      <h3 className="font-medium text-foreground mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground mb-3">{message}</p>
      {onRetry && (
        <Button onClick={onRetry} size="sm" variant="outline">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      )}
    </div>
  );
}
