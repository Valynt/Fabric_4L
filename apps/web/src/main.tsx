import { ClerkProvider } from "@clerk/react";
import { lazy, Suspense } from "react";
import { createRoot } from "react-dom/client";
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
import {
  getClerkPublishableKey,
  getClerkUrls,
  isClerkAuthEnabled,
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

// Phase 2: ClerkProvider is configured from env so the same bundle works for
// both legacy and Clerk-driven deployments. The publishable key is required
// at build time when AUTH_PROVIDER=clerk; we surface a clear error otherwise.
const clerkUrls = getClerkUrls();
const clerkPublishableKey = isClerkAuthEnabled()
  ? getClerkPublishableKey()
  : (import.meta.env.VITE_CLERK_PUBLISHABLE_KEY ?? "").toString().trim();

if (!clerkPublishableKey) {
  // Legacy mode: ClerkProvider needs *some* key to mount. We fall back to a
  // placeholder so the provider does not crash; with AUTH_PROVIDER=legacy
  // the API client never asks Clerk for a token, so the provider is inert.
  // This keeps existing deployments green while Clerk is rolled out.
  // eslint-disable-next-line no-console
  console.warn(
    "[clerk] VITE_CLERK_PUBLISHABLE_KEY not set; ClerkProvider mounted with " +
      "an inert placeholder. Set the key when AUTH_PROVIDER=clerk."
  );
}

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <I18nProvider>
      <ClerkProvider
        publishableKey={clerkPublishableKey || "pk_test_placeholder"}
        signInUrl={clerkUrls.signInUrl}
        signUpUrl={clerkUrls.signUpUrl}
        signInFallbackRedirectUrl={clerkUrls.afterSignInUrl}
        signUpFallbackRedirectUrl={clerkUrls.afterSignUpUrl}
        afterSignOutUrl="/"
      >
        <App />
      </ClerkProvider>
      {import.meta.env.DEV && ReactQueryDevtools && (
        <Suspense fallback={null}>
          <ReactQueryDevtools initialIsOpen={false} />
        </Suspense>
      )}
    </I18nProvider>
  </QueryClientProvider>
);
