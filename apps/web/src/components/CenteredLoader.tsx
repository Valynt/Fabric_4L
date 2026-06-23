/**
 * CenteredLoader — Thin wrapper around LoadingState for full-container centering.
 *
 * Preserves the original `h-full w-full` flex container so callers that render
 * inside a parent with defined height continue to center correctly.
 */
import { LoadingState } from "@/components/states";

interface CenteredLoaderProps {
  message?: string;
}

export function CenteredLoader({ message = "Loading..." }: CenteredLoaderProps) {
  return (
    <div className="flex h-full w-full items-center justify-center">
      <LoadingState message={message} />
    </div>
  );
}

export default CenteredLoader;
