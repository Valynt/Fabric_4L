import * as React from "react"
import { useContext } from "react"
import { useNavigation } from "@/hooks/useNavigation"
import { AuthContext } from "@/contexts/AuthContext"
import { ProspectPromptBuilder } from "@/components/workspace/ProspectPromptBuilder"
import type {
  ProspectPromptBuilderProps,
  ProspectSetupPromptPayload,
} from "@/components/workspace/ProspectPromptBuilder"

function useTenantSlug(): string | null {
  const ctx = useContext(AuthContext)
  return ctx?.currentTenantSlug ?? null
}

/**
 * Canonical account/prospect creation page.
 * Route: /accounts/new
 * After creation, navigates to /t/:tenantSlug/accounts/:accountId/intelligence/signals
 */
export default function ProspectSetupPage({ ...props }: ProspectPromptBuilderProps) {
  const { navigateTo } = useNavigation()
  const tenantSlug = useTenantSlug() ?? "default"

  const handleCreateSetup = React.useCallback(
    async (payload: ProspectSetupPromptPayload) => {
      return props.onCreateSetup ? await props.onCreateSetup(payload) : undefined
    },
    [props.onCreateSetup]
  )

  const handleNavigateToWorkspace = React.useCallback(
    (path: string, accountId: string) => {
      if (props.onNavigateToWorkspace) {
        props.onNavigateToWorkspace(path, accountId)
        return
      }
      navigateTo(path)
    },
    [props.onNavigateToWorkspace, navigateTo]
  )

  const handleFallbackNavigation = React.useCallback(() => {
    navigateTo("/home")
  }, [navigateTo])

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <ProspectPromptBuilder
        {...props}
        onCreateSetup={handleCreateSetup}
        onNavigateToWorkspace={handleNavigateToWorkspace}
        onFallbackNavigation={handleFallbackNavigation}
        getWorkspacePath={(accountId) =>
          `/t/${tenantSlug}/accounts/${accountId}/intelligence/signals`
        }
      />
    </main>
  )
}

