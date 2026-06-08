/**
 * AdminErrorState — Admin-styled error state wrapper with retry.
 */
import { ErrorState } from "@/components/states/ErrorState";

export interface AdminErrorStateProps {
  title: string;
  description?: string;
  error?: Error | unknown;
  onRetry?: () => void;
  retryLabel?: string;
  className?: string;
}

export function AdminErrorState({
  title,
  description,
  error,
  onRetry,
  retryLabel = "Retry",
  className,
}: AdminErrorStateProps) {
  return (
    <ErrorState
      title={title}
      description={description}
      error={error}
      onRetry={onRetry}
      retryLabel={retryLabel}
      className={className}
    />
  );
}
