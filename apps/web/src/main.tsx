import './lib/opentelemetry';  // Initialize RUM
import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import * as Sentry from "@sentry/react";
import {
  QueryCache,
  QueryClient,
  QueryClientProvider,
  MutationCache,
} from "@tanstack/react-query";
import App from "./App";
import "./index.css";
import { I18nProvider } from "./i18n";
import { STALE_TIME } from "./hooks/useApiShared";
import { logError } from "./lib/telemetry";
import { installAnalytics } from "./lib/analytics";
import { installWebVitals } from "./lib/web-vitals";

// P1-004: Sentry error tracking — initialized when SENTRY_DSN is configured.
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (sentryDsn) {
  try {
    Sentry.init({
      dsn: sentryDsn,
      environment: import.meta.env.MODE,
      sampleRate: 0.1,
      tracesSampleRate: 0.01,
      profilesSampleRate: 0.0,
      attachStacktrace: true,
    });
  } catch (error) {
    logError("Failed to initialize Sentry", { error: error instanceof Error ? error.message : String(error) });
  }
}
import {
  getClerkPublishableKey,
  getClerkUrls,
} from "./auth/clerkConfig";

// ReactQueryDevtools is only included in development builds.
// Vite's tree-shaking drops this import entirely in production,
// preventing the ~40 kB devtools chunk from reaching end users.
const ReactQueryDevtools = import.meta.env.DEV
  ? lazy(() =>
      import("@tanstack/react-query-devtools").then(m => ({
        default: m.ReactQueryDevtools,
      }))
    )
  : null;

const queryClient = new QueryClient({
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

installAnalytics();
installWebVitals();

const clerkUrls = getClerkUrls();
const clerkPublishableKey = getClerkPublishableKey();

const ClerkProvider = lazy(() =>
  import("@clerk/react").then((m) => ({ default: m.ClerkProvider }))
);

const AppRoot = (
  <QueryClientProvider client={queryClient}>
    <I18nProvider>
      <App />
      {import.meta.env.DEV && ReactQueryDevtools && (
        <Suspense fallback={<div className="h-8 w-32 animate-pulse rounded-md bg-accent" />}>
          <ReactQueryDevtools initialIsOpen={false} />
        </Suspense>
      )}
    </I18nProvider>
  </QueryClientProvider>
);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Suspense fallback={null}>
      <ClerkProvider
        publishableKey={clerkPublishableKey}
        signInUrl={clerkUrls.signInUrl}
        signUpUrl={clerkUrls.signUpUrl}
        signInFallbackRedirectUrl={clerkUrls.afterSignInUrl}
        signUpFallbackRedirectUrl={clerkUrls.afterSignUpUrl}
        afterSignOutUrl="/"
      >
        {AppRoot}
      </ClerkProvider>
    </Suspense>
  </StrictMode>
);

// P2-006: Register service worker for offline asset caching
if ("serviceWorker" in navigator && import.meta.env.PROD) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/sw.js")
      .catch((err) => logError("Service worker registration failed", { error: err instanceof Error ? err.message : String(err) }));
  });
}
