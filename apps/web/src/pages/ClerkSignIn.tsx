/**
 * Custom Clerk sign-in page using the app's shadcn/ui primitives.
 *
 * This page uses Clerk's real custom-flow APIs. It does not issue local tokens,
 * call a fake backend login, or bypass the existing tenant/org route guards.
 */
import { useAuth, useClerk } from "@clerk/react";
import { AlertCircle, Apple, Layers3, Loader2 } from "lucide-react";
import { useEffect, useId, useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";

import { getClerkUrls } from "@/auth/clerkConfig";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Field, FieldError, FieldGroup, FieldLabel, FieldSeparator } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useNavigation } from "@/hooks/useNavigation";

type OAuthStrategy = "oauth_google" | "oauth_apple" | "oauth_microsoft";

type ClerkSignInResult = {
  status?: string | null;
  createdSessionId?: string | null;
};

type ClerkApiError = {
  errors?: Array<{
    message?: string;
    longMessage?: string;
  }>;
};

function getSafeAuthError(error: unknown): string {
  if (typeof error === "object" && error !== null && "errors" in error) {
    const clerkError = error as ClerkApiError;
    const message = clerkError.errors?.[0]?.message ?? clerkError.errors?.[0]?.longMessage;
    if (message) {
      return message;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return "We could not sign you in. Check your details and try again.";
}

function getClerkSignIn(clerk: ReturnType<typeof useClerk>) {
  return clerk.client.signIn;
}

/**
 * Returns a safe, app-internal redirect target from the `redirect_url` query
 * param, or null when absent/unsafe. Only same-origin absolute paths starting
 * with a single "/" are allowed to prevent open redirects.
 */
function safeRedirectTarget(search: string): string | null {
  const param = new URLSearchParams(search).get("redirect_url");
  if (!param) {
    return null;
  }
  if (!param.startsWith("/") || param.startsWith("//")) {
    return null;
  }

  const url = new URL(param, "http://fabric.local");
  const keysToDelete: string[] = [];
  url.searchParams.forEach((_value, key) => {
    if (key.toLowerCase().startsWith("__clerk_")) {
      keysToDelete.push(key);
    }
  });
  keysToDelete.forEach((key) => url.searchParams.delete(key));

  if (url.pathname.startsWith("/sign-in") || url.pathname.startsWith("/sso-callback")) {
    return null;
  }

  const normalizedSearch = url.searchParams.toString();
  return normalizedSearch ? `${url.pathname}?${normalizedSearch}` : url.pathname;
}

function GoogleIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
      <path
        d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
        fill="#4285F4"
      />
      <path
        d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
        fill="#34A853"
      />
      <path
        d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
        fill="#FBBC05"
      />
      <path
        d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
        fill="#EA4335"
      />
    </svg>
  );
}

function MicrosoftIcon() {
  return (
    <svg viewBox="0 0 24 24" className="size-4" aria-hidden="true">
      <path d="M3 3h8v8H3V3z" fill="#f25022" />
      <path d="M13 3h8v8h-8V3z" fill="#7fba00" />
      <path d="M3 13h8v8H3v-8z" fill="#00a4ef" />
      <path d="M13 13h8v8h-8v-8z" fill="#ffb900" />
    </svg>
  );
}

function CustomClerkSignInScreen({ redirectTarget }: { redirectTarget: string }) {
  const urls = getClerkUrls();
  const clerk = useClerk();
  const { navigateTo } = useNavigation();
  const emailId = useId();
  const passwordId = useId();
  const errorId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<"email" | OAuthStrategy | null>(null);
  const isBusy = pendingAction !== null;

  async function handleEmailSignIn(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    const identifier = email.trim();
    if (!identifier || !password) {
      setError("Enter your email and password to continue.");
      return;
    }

    setPendingAction("email");
    try {
      const result = await getClerkSignIn(clerk).create({
        identifier,
        password,
      }) as ClerkSignInResult;

      if (result.status === "complete" && result.createdSessionId) {
        await clerk.setActive({ session: result.createdSessionId });
        navigateTo(redirectTarget, { replace: true });
        return;
      }

      setError("Additional verification is required to complete sign-in.");
    } catch (authError) {
      setError(getSafeAuthError(authError));
    } finally {
      setPendingAction(null);
    }
  }

  async function handleOAuthSignIn(strategy: OAuthStrategy) {
    setError(null);
    setPendingAction(strategy);
    try {
      await getClerkSignIn(clerk).authenticateWithRedirect({
        strategy,
        redirectUrl: "/sso-callback",
        redirectUrlComplete: redirectTarget,
      });
    } catch (authError) {
      setError(getSafeAuthError(authError));
      setPendingAction(null);
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <div className="grid min-h-screen lg:grid-cols-2">
        <section className="flex items-center justify-center px-6 py-10 lg:px-10">
          <div className="flex w-full max-w-md flex-col gap-6">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                <Layers3 className="size-5" aria-hidden="true" />
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground">Value Fabric</p>
                <p className="text-xs text-muted-foreground">Enterprise value intelligence</p>
              </div>
            </div>

            <Card>
              <CardHeader className="text-center">
                <CardTitle className="text-2xl">
                  <h1>Welcome back</h1>
                </CardTitle>
                <CardDescription>Sign in to continue to your governed value workspace.</CardDescription>
              </CardHeader>
              <CardContent>
                <form className="flex flex-col gap-6" onSubmit={handleEmailSignIn} noValidate>
                  {error && (
                    <Alert variant="destructive" id={errorId} data-testid="custom-login-error">
                      <AlertCircle className="size-4" aria-hidden="true" />
                      <AlertDescription>{error}</AlertDescription>
                    </Alert>
                  )}

                  <FieldGroup className="gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      disabled={isBusy}
                      data-testid="oauth-google"
                      onClick={() => void handleOAuthSignIn("oauth_google")}
                    >
                      {pendingAction === "oauth_google" ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <GoogleIcon />}
                      Continue with Google
                    </Button>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        disabled={isBusy}
                        data-testid="oauth-apple"
                        onClick={() => void handleOAuthSignIn("oauth_apple")}
                      >
                        {pendingAction === "oauth_apple" ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <Apple className="size-4" aria-hidden="true" />}
                        Apple
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        className="w-full"
                        disabled={isBusy}
                        data-testid="oauth-microsoft"
                        onClick={() => void handleOAuthSignIn("oauth_microsoft")}
                      >
                        {pendingAction === "oauth_microsoft" ? <Loader2 className="size-4 animate-spin" aria-hidden="true" /> : <MicrosoftIcon />}
                        Microsoft
                      </Button>
                    </div>
                  </FieldGroup>

                  <FieldSeparator>Or continue with email</FieldSeparator>

                  <FieldGroup className="gap-4">
                    <Field data-invalid={Boolean(error)}>
                      <FieldLabel htmlFor={emailId}>Email</FieldLabel>
                      <Input
                        id={emailId}
                        data-testid="login-email"
                        type="email"
                        autoComplete="username"
                        placeholder="name@company.com"
                        value={email}
                        disabled={isBusy}
                        aria-describedby={error ? errorId : undefined}
                        aria-invalid={Boolean(error)}
                        onChange={(event) => setEmail(event.target.value)}
                      />
                    </Field>

                    <Field data-invalid={Boolean(error)}>
                      <div className="flex items-center justify-between gap-3">
                        <FieldLabel htmlFor={passwordId}>Password</FieldLabel>
                        <Link
                          to={`${urls.signInUrl}/forgot-password`}
                          className="text-sm text-primary underline-offset-4 hover:underline"
                          data-testid="forgot-password-link"
                        >
                          Forgot password?
                        </Link>
                      </div>
                      <Input
                        id={passwordId}
                        data-testid="login-password"
                        type="password"
                        autoComplete="current-password"
                        value={password}
                        disabled={isBusy}
                        aria-describedby={error ? errorId : undefined}
                        aria-invalid={Boolean(error)}
                        onChange={(event) => setPassword(event.target.value)}
                      />
                      <FieldError>{error}</FieldError>
                    </Field>
                  </FieldGroup>

                  <Button type="submit" className="w-full" disabled={isBusy} data-testid="login-submit">
                    {pendingAction === "email" ? (
                      <>
                        <Loader2 className="size-4 animate-spin" aria-hidden="true" />
                        Signing in...
                      </>
                    ) : (
                      "Sign in"
                    )}
                  </Button>

                  <p className="text-center text-sm text-muted-foreground">
                    No account yet?{" "}
                    <Link to={urls.signUpUrl} className="font-medium text-primary underline-offset-4 hover:underline" data-testid="signup-link">
                      Create one
                    </Link>
                  </p>
                </form>
              </CardContent>
            </Card>
          </div>
        </section>

        <section className="hidden bg-muted lg:block">
          <div className="flex h-full flex-col justify-between p-10">
            <div className="flex flex-col gap-4">
              <div className="w-fit rounded-lg border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground">
                Ontology-guided revenue operations
              </div>
              <h2 className="max-w-xl text-3xl font-semibold tracking-normal text-foreground">
                Turn evidence, workflows, and benchmarks into auditable value cases.
              </h2>
              <p className="max-w-lg text-sm leading-6 text-muted-foreground">
                Secure access protects tenant-scoped intelligence, agent workflows, and governed business-case evidence.
              </p>
            </div>
            <Card>
              <CardContent className="flex flex-col gap-3 p-4">
                {["Tenant-aware workspaces", "Evidence-backed claims", "Provider-agnostic agents"].map((item) => (
                  <div key={item} className="flex items-center gap-3 text-sm text-foreground">
                    <span className="size-2 rounded-full bg-primary" aria-hidden="true" />
                    {item}
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}

function ClerkSignInInner() {
  const urls = getClerkUrls();
  const location = useLocation();
  const { isLoaded, isSignedIn, getToken } = useAuth();
  const { signOut } = useClerk();
  const [sessionCheck, setSessionCheck] = useState<"idle" | "checking" | "valid" | "invalid">("idle");

  useEffect(() => {
    let cancelled = false;

    if (!isLoaded || !isSignedIn) {
      setSessionCheck("idle");
      return () => {
        cancelled = true;
      };
    }

    setSessionCheck("checking");
    void getToken({ skipCache: true })
      .then((token) => {
        if (!cancelled) {
          setSessionCheck(token ? "valid" : "invalid");
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSessionCheck("invalid");
        }
      });

    return () => {
      cancelled = true;
    };
  }, [getToken, isLoaded, isSignedIn]);

  useEffect(() => {
    if (sessionCheck !== "invalid") {
      return;
    }

    void signOut({ redirectUrl: urls.signInUrl }).catch(() => undefined);
  }, [sessionCheck, signOut, urls.signInUrl]);

  if (!isLoaded) {
    return null;
  }

  if (isSignedIn) {
    if (sessionCheck !== "valid") {
      return null;
    }

    const target = safeRedirectTarget(location.search) ?? urls.afterSignInUrl;
    return <Navigate to={target} replace />;
  }

  const redirectTarget = safeRedirectTarget(location.search) ?? urls.afterSignInUrl;
  return <CustomClerkSignInScreen redirectTarget={redirectTarget} />;
}

export default function ClerkSignInPage() {
  return <ClerkSignInInner />;
}
