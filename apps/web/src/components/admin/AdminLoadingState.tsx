/**
 * AdminLoadingState — Admin-styled loading state wrapper.
 */
import { LoadingState } from "@/components/states/LoadingState";

export interface AdminLoadingStateProps {
  message?: string;
  className?: string;
  fullPage?: boolean;
}

export function AdminLoadingState({
  message = "Loading admin data…",
  className,
  fullPage,
}: AdminLoadingStateProps) {
  return (
    <LoadingState
      message={message}
      className={className}
      fullPage={fullPage}
    />
  );
}
