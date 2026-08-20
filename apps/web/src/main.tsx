import './lib/opentelemetry';  // Initialize RUM
import "./lib/zod-config";
import { lazy, StrictMode, Suspense } from "react";
import { createRoot } from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import App from "./App";
import "./index.css";
import { I18nProvider } from "./i18n";
import { installAnalytics } from "./lib/analytics";
import { initWebVitals } from "./lib/web-vitals";
import { createQueryClient, initSentry, registerServiceWorker } from "./app/bootstrapFactory";

initSentry({ dsn: import.meta.env.VITE_SENTRY_DSN, mode: import.meta.env.MODE });

import {
  getClerkPublishableKey,
  getClerkUrls,
  isClerkAuthEnabled,
} from "./auth/clerkConfig";
import { shadcn } from "@clerk/ui/themes";

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

const queryClient = createQueryClient();

installAnalytics();
initWebVitals();
registerServiceWorker();

const clerkUrls = getClerkUrls();
const clerkAuthEnabled = isClerkAuthEnabled();
const clerkPublishableKey = clerkAuthEnabled ? getClerkPublishableKey() : "";

// Brand Clerk's components with the official shadcn theme. The theme maps
// Clerk's internal UI to the same shadcn CSS tokens the app already defines
// (--primary, --background, --border, ...). Because those tokens flip under
// the `.dark` class managed by ThemeProvider, Clerk automatically follows the
// app's light/dark mode without needing the React theme context — which
// matters here because <ClerkProvider> is mounted above <ThemeProvider>.
//
// We intentionally do NOT hardcode colorPrimary (it previously drifted from
// the app brand token); the shadcn theme derives it from --primary. Only the
// app font is carried over so the widget matches the surrounding typography.
const clerkAppearance = clerkAuthEnabled
  ? {
      theme: shadcn,
      variables: {
        fontFamily: "var(--font-sans)",
      },
    }
  : {};

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
    {clerkAuthEnabled ? (
      <Suspense fallback={null}>
        <ClerkProvider
          publishableKey={clerkPublishableKey}
          appearance={clerkAppearance}
          signInUrl={clerkUrls.signInUrl}
          signUpUrl={clerkUrls.signUpUrl}
          signInFallbackRedirectUrl={clerkUrls.afterSignInUrl}
          signUpFallbackRedirectUrl={clerkUrls.afterSignUpUrl}
          afterSignOutUrl="/"
        >
          {AppRoot}
        </ClerkProvider>
      </Suspense>
    ) : (
      AppRoot
    )}
  </StrictMode>
);
