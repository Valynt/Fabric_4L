/**
 * Value Studio (mission-led) — offline banner (contract §10, FE-OFF-*).
 *
 * Renders when the projection is cached and the browser is offline: the data
 * is clearly labeled as of its last server sync (authoritative timestamp from
 * the projection, never browser-invented), with an explicit Reconnect action.
 * Mutations stay paused while offline — enforced by the decision rail guard.
 */

import { WifiOff, RefreshCw } from "lucide-react";
import { Btn } from "@/components/ui/fabric/Btn";
import { formatDate } from "@/lib/formatters";
import type { IsoDateTime } from "../types";

export interface OfflineBannerProps {
  readonly lastSyncedAt: IsoDateTime;
  readonly onReconnect: () => void;
}

export function OfflineBanner({ lastSyncedAt, onReconnect }: OfflineBannerProps) {
  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-md border border-warning/40 bg-warning/10 px-4 py-3"
    >
      <div className="flex items-center gap-2">
        <WifiOff className="h-4 w-4 shrink-0 text-warning" aria-hidden="true" />
        <p className="vf-text-body-s text-foreground">
          You are offline. Showing data as of{" "}
          <time dateTime={lastSyncedAt}>{formatDate(lastSyncedAt)}</time>. Changes are paused
          until the connection returns.
        </p>
      </div>
      <Btn variant="outline" size="sm" onClick={onReconnect}>
        <RefreshCw className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
        Reconnect
      </Btn>
    </div>
  );
}
