/**
 * App bootstrap factories — extracted from main.tsx so the imperative
 * boot sequence is unit-testable.
 *
 * Kept behavior-identical to the inline logic previously embedded in the
 * entrypoint: Sentry init is guarded by DSN presence and swallows failures,
 * the QueryClient wires error handlers to the telemetry logger, and service
 * worker registration only runs in production after the `load` event.
 */

import * as Sentry from "@sentry/react";
import { MutationCache, QueryCache, QueryClient } from "@tanstack/react-query";
import { STALE_TIME } from "@/hooks/useApiShared";
import { logError } from "@/lib/telemetry";

// P1-004: Sentry error tracking — initialized when SENTRY_DSN is configured.
export function initSentry(options: {
  dsn?: string;
  mode?: string;
}): void {
  if (!options.dsn) {
    return;
  }
  try {
    Sentry.init({
      dsn: options.dsn,
      environment: options.mode,
      sampleRate: 0.1,
      tracesSampleRate: 0.01,
      profilesSampleRate: 0.0,
      attachStacktrace: true,
    });
  } catch (error) {
    logError("Failed to initialize Sentry", {
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        logError("Query failed", {
          queryKey: JSON.stringify(query.queryKey),
          error: error instanceof Error ? error.message : String(error),
        });
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _context, mutation) => {
        logError("Mutation failed", {
          mutationKey: mutation.options.mutationKey?.toString(),
          error: error instanceof Error ? error.message : String(error),
        });
      },
    }),
    defaultOptions: {
      queries: {
        // Global default — individual hooks override with a more specific STALE_TIME key
        staleTime: STALE_TIME.activity,
        retry: 2,
        refetchOnWindowFocus: false,
      },
    },
  });
}

// P2-006: Register service worker for offline asset caching.
export function registerServiceWorker(isProd: boolean = import.meta.env.PROD): void {
  if (!isProd || !("serviceWorker" in navigator)) {
    return;
  }
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .catch((err) =>
        logError("Service worker registration failed", {
          error: err instanceof Error ? err.message : String(err),
        })
      );
  });
}