import { useState, useMemo, useId } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Alert, AlertDescription } from "@/components/ui/alert"
import {
  Loader2, AlertCircle,
  Eye, EyeOff, CheckCircle,
} from "lucide-react"

// ── SVG Icons ────────────────────────────────────────────────────────────────

function AppleIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
      <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
    </svg>
  )
}

function GoogleIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" className="h-5 w-5" aria-hidden="true">
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
  )
}

// ── Platform Logo ────────────────────────────────────────────────────────────

function PlatformLogo() {
  return (
    <div className="flex items-center justify-center gap-2">
      <div className="w-8 h-8 bg-foreground rounded-lg flex items-center justify-center">
        <svg viewBox="0 0 24 24" className="w-5 h-5 text-background" fill="currentColor" aria-hidden="true">
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </div>
      <span className="font-semibold text-lg tracking-tight">Value Fabric</span>
    </div>
  )
}

// ── Password toggle hook ─────────────────────────────────────────────────────
function usePasswordToggle() {
  const [visible, setVisible] = useState(false)
  const toggle = () => setVisible(v => !v)
  const inputType = visible ? "text" : "password"
  const Icon = visible ? EyeOff : Eye
  const label = visible ? "Hide password" : "Show password"
  return { visible, toggle, inputType, Icon, label } as const
}

// ── Password strength meter ──────────────────────────────────────────────────
function getPasswordStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0
  if (pw.length >= 8) score++
  if (pw.length >= 12) score++
  if (/[a-z]/.test(pw) && /[A-Z]/.test(pw)) score++
  if (/\d/.test(pw)) score++
  if (/[^a-zA-Z0-9]/.test(pw)) score++

  if (score <= 1) return { score, label: "Weak", color: "bg-destructive" }
  if (score <= 2) return { score, label: "Fair", color: "bg-amber-500" }
  if (score <= 3) return { score, label: "Good", color: "bg-yellow-500" }
  return { score, label: "Strong", color: "bg-emerald-500" }
}

function PasswordStrength({ password }: { password: string }) {
  const strength = getPasswordStrength(password)
  if (!password) return null
  return (
    <div className="space-y-1" aria-live="polite">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map(i => (
          <div
            key={i}
            className={cn(
              "h-1 flex-1 rounded-full transition-colors",
              i <= Math.ceil(strength.score * 4 / 5) ? strength.color : "bg-muted"
            )}
          />
        ))}
      </div>
      <p className="text-xs text-muted-foreground">{strength.label}</p>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// LoginForm — Centered single-column card with Apple/Google SSO
// ═══════════════════════════════════════════════════════════════════════════════

/** Props for LoginForm. SSO buttons trigger `onSSOProvider` with a provider key. */
interface LoginFormProps extends React.ComponentProps<"div"> {
  /** Email + password submit handler */
  onLogin?: (email: string, password: string) => Promise<void>
  /** SSO provider button handler — receives "apple" | "google" */
  onSSOProvider?: (provider: string) => void
  /** Dev-only bypass button */
  onDevBypass?: () => void
  isLoading?: boolean
  error?: string | null
  successMessage?: string | null
}

export function LoginForm({
  className,
  onLogin,
  onSSOProvider,
  onDevBypass,
  isLoading = false,
  error: externalError = null,
  successMessage = null,
  ...props
}: LoginFormProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [localError, setLocalError] = useState<string | null>(null)
  const pwToggle = usePasswordToggle()
  const errorId = useId()

  const error = externalError || localError

  // Email/password form is only available in development builds.
  // Production uses SSO-only (Apple / Google).
  const showEmailPasswordForm = import.meta.env.DEV

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (!email.trim()) {
      setLocalError("Please enter your email address")
      return
    }
    if (!password.trim()) {
      setLocalError("Please enter your password")
      return
    }

    try {
      await onLogin?.(email.trim(), password)
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Incorrect password. Please try again or reset it below.")
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      {/* Platform Logo */}
      <PlatformLogo />

      {/* Login Card */}
      <Card className="overflow-hidden border border-border/50">
        <CardContent className="p-6 md:p-8">
          <form onSubmit={showEmailPasswordForm ? handleSubmit : (e) => e.preventDefault()} noValidate>
            <div className="flex flex-col gap-6">
              {/* Header */}
              <div className="flex flex-col items-center text-center">
                <h1 className="text-2xl font-bold" data-testid="login-heading">Welcome back</h1>
                <p className="text-muted-foreground">
                  Login with your Apple or Google account
                </p>
              </div>

              {/* Success message */}
              {successMessage && (
                <Alert variant="default" className="bg-emerald-500/10 text-emerald-700 border-emerald-500/20" role="status">
                  <CheckCircle className="h-4 w-4 text-emerald-500" aria-hidden="true" />
                  <AlertDescription>{successMessage}</AlertDescription>
                </Alert>
              )}

              {/* Error message */}
              {error && (
                <Alert variant="destructive" role="alert" id={errorId}>
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* SSO Buttons — Full width, stacked */}
              <div className="flex flex-col gap-3">
                <Button
                  variant="outline"
                  data-testid="sso-apple"
                  className="w-full h-11 justify-center gap-2 font-medium"
                  type="button"
                  disabled={isLoading}
                  onClick={() => onSSOProvider?.("apple")}
                >
                  <AppleIcon />
                  Login with Apple
                </Button>
                <Button
                  variant="outline"
                  data-testid="sso-google"
                  className="w-full h-11 justify-center gap-2 font-medium"
                  type="button"
                  disabled={isLoading}
                  onClick={() => onSSOProvider?.("google")}
                >
                  <GoogleIcon />
                  Login with Google
                </Button>
              </div>

              {/* Email/password — development only */}
              {showEmailPasswordForm && (
                <>
                  {/* Divider */}
                  <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border">
                    <span className="relative z-10 bg-card px-2 text-muted-foreground">
                      Or continue with
                    </span>
                  </div>

                  {/* Email field */}
                  <div className="grid gap-2">
                    <Label htmlFor="login-email" className="font-semibold">Email</Label>
                    <Input
                      id="login-email"
                      data-testid="login-email"
                      type="email"
                      placeholder="m@example.com"
                      autoComplete="username"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      disabled={isLoading}
                      required
                      autoFocus
                      aria-describedby={error ? errorId : undefined}
                    />
                  </div>

                  {/* Password field */}
                  <div className="grid gap-2">
                    <div className="flex items-center">
                      <Label htmlFor="login-password" className="font-semibold">Password</Label>
                      <a
                        href="#"
                        className="ml-auto text-sm underline-offset-2 hover:underline text-muted-foreground"
                        aria-label="Forgot your password?"
                      >
                        Forgot your password?
                      </a>
                    </div>
                    <div className="relative">
                      <Input
                        id="login-password"
                        data-testid="login-password"
                        type={pwToggle.inputType}
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        disabled={isLoading}
                        required
                        className="pr-10"
                        aria-describedby={error ? errorId : undefined}
                      />
                      <button
                        type="button"
                        data-testid="password-toggle"
                        onClick={pwToggle.toggle}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                        aria-label={pwToggle.label}
                        tabIndex={-1}
                      >
                        <pwToggle.Icon className="h-4 w-4" />
                      </button>
                    </div>
                  </div>

                  {/* Login button */}
                  <Button
                    type="submit"
                    data-testid="login-submit"
                    className="w-full h-11 bg-foreground text-background hover:bg-foreground/90 font-semibold"
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                        Signing in...
                      </>
                    ) : (
                      "Login"
                    )}
                  </Button>
                </>
              )}

              {/* Dev bypass */}
              {import.meta.env.DEV && onDevBypass && (
                <Button
                  variant="ghost"
                  type="button"
                  size="sm"
                  className="w-full text-xs text-muted-foreground hover:text-primary"
                  onClick={onDevBypass}
                >
                  Development Bypass
                </Button>
              )}

              {/* Sign up link */}
              <div className="text-center text-sm">
                Don&apos;t have an account?{" "}
                <a href="/signup" data-testid="link-to-signup" className="underline underline-offset-4" aria-label="Sign up">
                  Sign up
                </a>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-balance text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4 hover:[&_a]:text-primary">
        By clicking continue, you agree to our <a href="#" aria-label="Terms of Service">Terms of Service</a>{" "}
        and <a href="#" aria-label="Privacy Policy">Privacy Policy</a>.
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// SignupForm — Centered single-column card with Apple/Google SSO
// ═══════════════════════════════════════════════════════════════════════════════

/** Props for SignupForm. SSO buttons trigger `onSSOProvider`. */
interface SignupFormProps extends React.ComponentProps<"div"> {
  onSignup?: (data: { email: string; password: string }) => Promise<void>
  onSSOProvider?: (provider: string) => void
  isLoading?: boolean
  error?: string | null
}

export function SignupForm({
  className,
  onSignup,
  onSSOProvider,
  isLoading = false,
  error: externalError = null,
  ...props
}: SignupFormProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [localError, setLocalError] = useState<string | null>(null)
  const pwToggle = usePasswordToggle()
  const errorId = useId()
  const strengthId = useId()

  const error = externalError || localError
  const strength = useMemo(() => getPasswordStrength(password), [password])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLocalError(null)

    if (!email.trim()) {
      setLocalError("Please enter your email address")
      return
    }
    if (!password.trim()) {
      setLocalError("Please enter a password")
      return
    }
    if (password.length < 8) {
      setLocalError("Password must be at least 8 characters")
      return
    }
    if (strength.score <= 1) {
      setLocalError("Password is too weak. Add uppercase letters, numbers, or symbols.")
      return
    }

    try {
      await onSignup?.({ email: email.trim(), password })
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : "Registration failed. Please try again.")
    }
  }

  return (
    <div className={cn("flex flex-col gap-6", className)} {...props}>
      {/* Platform Logo */}
      <PlatformLogo />

      {/* Signup Card */}
      <Card className="overflow-hidden border border-border/50">
        <CardContent className="p-6 md:p-8">
          <form onSubmit={handleSubmit} noValidate>
            <div className="flex flex-col gap-6">
              {/* Header */}
              <div className="flex flex-col items-center text-center">
                <h1 className="text-2xl font-bold" data-testid="signup-heading">Create your account</h1>
                <p className="text-muted-foreground">
                  Get started with Value Fabric — it&apos;s free
                </p>
              </div>

              {/* Error message */}
              {error && (
                <Alert variant="destructive" role="alert" id={errorId}>
                  <AlertCircle className="h-4 w-4" aria-hidden="true" />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {/* SSO Buttons */}
              <div className="flex flex-col gap-3">
                <Button
                  variant="outline"
                  className="w-full h-11 justify-center gap-2 font-medium"
                  type="button"
                  disabled={isLoading}
                  onClick={() => onSSOProvider?.("apple")}
                >
                  <AppleIcon />
                  Sign up with Apple
                </Button>
                <Button
                  variant="outline"
                  className="w-full h-11 justify-center gap-2 font-medium"
                  type="button"
                  disabled={isLoading}
                  onClick={() => onSSOProvider?.("google")}
                >
                  <GoogleIcon />
                  Sign up with Google
                </Button>
              </div>

              {/* Divider */}
              <div className="relative text-center text-sm after:absolute after:inset-0 after:top-1/2 after:z-0 after:flex after:items-center after:border-t after:border-border">
                <span className="relative z-10 bg-card px-2 text-muted-foreground">
                  Or continue with
                </span>
              </div>

              {/* Email */}
              <div className="grid gap-2">
                <Label htmlFor="signup-email" className="font-semibold">Email</Label>
                <Input
                  id="signup-email"
                  data-testid="signup-email"
                  type="email"
                  placeholder="m@example.com"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  required
                  autoFocus
                  aria-describedby={error ? errorId : undefined}
                />
              </div>

              {/* Password */}
              <div className="grid gap-2">
                <Label htmlFor="signup-password" className="font-semibold">Password</Label>
                <div className="relative">
                  <Input
                    id="signup-password"
                    data-testid="signup-password"
                    type={pwToggle.inputType}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                    required
                    className="pr-10"
                    aria-describedby={cn(strengthId, error ? errorId : "")}
                  />
                  <button
                    type="button"
                    data-testid="signup-password-toggle"
                    onClick={pwToggle.toggle}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    aria-label={pwToggle.label}
                    tabIndex={-1}
                  >
                    <pwToggle.Icon className="h-4 w-4" />
                  </button>
                </div>
                <div id={strengthId}>
                  <PasswordStrength password={password} />
                  {!password && (
                    <p className="text-xs text-muted-foreground">Must be at least 8 characters.</p>
                  )}
                </div>
              </div>

              {/* Create Account button */}
              <Button
                type="submit"
                data-testid="signup-submit"
                className="w-full h-11 bg-foreground text-background hover:bg-foreground/90 font-semibold"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                    Creating account...
                  </>
                ) : (
                  "Create Account"
                )}
              </Button>

              {/* Sign in link */}
              <div className="text-center text-sm">
                Already have an account?{" "}
                <a href="/login" className="underline underline-offset-4" aria-label="Sign in">
                  Sign in
                </a>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-balance text-center text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-4 hover:[&_a]:text-primary">
        By clicking continue, you agree to our <a href="#">Terms of Service</a>{" "}
        and <a href="#">Privacy Policy</a>.
      </div>
    </div>
  )
}
