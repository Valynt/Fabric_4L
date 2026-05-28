/**
 * SSO Buttons Component — Enterprise Identity Provider Selection
 *
 * Renders SSO provider buttons for:
 * - Okta
 * - Azure AD (Microsoft Entra ID)
 * - Google Workspace
 *
 * Enabled after Task 69 (SSO/OIDC Backend) completion.
 */

import { useMemo } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface SSOProvider {
  id: string;
  name: string;
  icon: React.ReactNode;
  disabled?: boolean;
}

// SVG icons for SSO providers
const OktaIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm0 4.8a7.2 7.2 0 110 14.4 7.2 7.2 0 010-14.4z" />
  </svg>
);

const AzureIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
    <path d="M5.483 0v11.617L0 18.174V3.518L5.483 0zm13.518 0v10.583L12 23.935V12.294l7.001-12.294zm-7 19.835l-5.834-3.258L12 11.192l5.834 5.285-5.833 3.358z" />
  </svg>
);

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" className="h-5 w-5" fill="currentColor" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
  </svg>
);

interface SSOButtonsProps {
  className?: string;
  /** Enable SSO provider buttons (defaults to true after Task 69 completion) */
  enabled?: boolean;
  onProviderSelect?: (providerId: string) => void;
}

/**
 * SSO Provider Selection Buttons
 *
 * @example
 * ```tsx
 * // Default enabled after Task 69
 * <SSOButtons />
 *
 * // With custom handler
 * <SSOButtons onProviderSelect={handleSSO} />
 * ```
 */
export function SSOButtons({
  className,
  enabled = true,
  onProviderSelect,
}: SSOButtonsProps) {
  // Memoize providers to prevent recreation on every render
  const providers = useMemo<SSOProvider[]>(
    () => [
      {
        id: "okta",
        name: "Okta",
        icon: <OktaIcon />,
        disabled: !enabled,
      },
      {
        id: "azure",
        name: "Microsoft Entra ID",
        icon: <AzureIcon />,
        disabled: !enabled,
      },
      {
        id: "google",
        name: "Google",
        icon: <GoogleIcon />,
        disabled: !enabled,
      },
    ],
    [enabled]
  );

  const handleClick = (providerId: string) => {
    if (!enabled) {
      // Gated: Do nothing in preview mode
      return;
    }
    onProviderSelect?.(providerId);
  };

  return (
    <div className={cn("space-y-3", className)}>
      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">
            {enabled ? "Or continue with" : "SSO (Coming Soon)"}
          </span>
        </div>
      </div>

      <div className="grid gap-2">
        {providers.map((provider) => (
          <Button
            key={provider.id}
            variant="outline"
            type="button"
            disabled={provider.disabled}
            onClick={() => handleClick(provider.id)}
            className={cn(
              "w-full justify-start gap-3",
              !enabled && "opacity-60 cursor-not-allowed"
            )}
            title={
              enabled
                ? `Sign in with ${provider.name}`
                : `${provider.name} SSO — Coming Soon (Task 69)`
            }
          >
            {provider.icon}
            <span className="flex-1 text-center">
              {enabled ? provider.name : `${provider.name} — Coming Soon`}
            </span>
          </Button>
        ))}
      </div>

      {!enabled && (
        <p className="text-center text-xs text-muted-foreground">
          Enterprise SSO providers will be available after backend configuration.
        </p>
      )}
    </div>
  );
}

export default SSOButtons;
