import { useOnlineStatus } from "@/hooks/useOnlineStatus";
import { WifiOff } from "lucide-react";

/**
 * P2-005: Offline handling banner.
 *
 * Displays a fixed banner at the top of the viewport when the browser
 * detects it is offline. Automatically hides when connectivity resumes.
 */
export function OfflineBanner() {
  const isOnline = useOnlineStatus();

  if (isOnline) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed top-0 left-0 right-0 z-50 flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-sm font-medium text-white"
    >
      <WifiOff className="h-4 w-4" aria-hidden="true" />
      <span>You are offline. Some features may be unavailable.</span>
    </div>
  );
}
