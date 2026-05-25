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
        <Suspense fallback={null}>
          <ReactQueryDevtools initialIsOpen={false} />
        </Suspense>
      )}
    </I18nProvider>
  </QueryClientProvider>
);

createRoot(document.getElementById("root")!).render(
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
);
