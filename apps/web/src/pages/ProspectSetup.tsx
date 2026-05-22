import * as React from "react"
import { useNavigation } from "@/hooks/useNavigation"
import { ProspectPromptBuilder } from "@/components/workspace/ProspectPromptBuilder"
import type {
  ProspectPromptBuilderProps,
  ProspectSetupPromptPayload,
} from "@/components/workspace/ProspectPromptBuilder"
import { WorkflowLayout } from "@/workflow/components/WorkflowLayout"
import { useWorkflowStore } from "@/workflow/store/workflowStore"
import { STEPS } from "@/workflow/constants"

export type ProspectSetupMode = "workflow" | "value-pilot"

type ProspectSetupPageProps = ProspectPromptBuilderProps & {
  mode: ProspectSetupMode
}

type ModeConfig = {
  workspacePath: (accountId: string) => string
  fallbackRoute: string
}

const MODE_CONFIG: Record<ProspectSetupMode, ModeConfig> = {
  workflow: {
    workspacePath: (accountId) => `/accounts/${accountId}/intelligence/signals`,
    fallbackRoute: "workflow-intelligence",
  },
  "value-pilot": {
    workspacePath: (accountId) => `/accounts/${accountId}/workspace/action-plan`,
    fallbackRoute: "workflow-intelligence",
  },
}

export default function ProspectSetupPage({ mode, ...props }: ProspectSetupPageProps) {
  const { navigateTo } = useNavigation()
  const { setProspect, setCurrentStep } = useWorkflowStore()
  const modeConfig = MODE_CONFIG[mode]

  const handleBeforeSubmit = React.useCallback(
    (state: { draft: { companyName: string; stakeholders: { economicBuyer: string; champion: string } } }) => {
      const tempId = `temp_${Date.now()}`
      setProspect({
        companyId: tempId,
        companyName: state.draft.companyName || "",
        contactName: state.draft.stakeholders.economicBuyer || state.draft.stakeholders.champion || "",
        contactTitle: "",
      })
    },
    [setProspect]
  )

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
    setCurrentStep(STEPS.INTELLIGENCE)
    navigateTo(modeConfig.fallbackRoute)
  }, [modeConfig.fallbackRoute, navigateTo, setCurrentStep])

  return (
    <WorkflowLayout>
      <ProspectPromptBuilder
        {...props}
        onCreateSetup={handleCreateSetup}
        onNavigateToWorkspace={handleNavigateToWorkspace}
        onBeforeSubmit={handleBeforeSubmit}
        onFallbackNavigation={handleFallbackNavigation}
        getWorkspacePath={modeConfig.workspacePath}
      />
    </WorkflowLayout>
  )
}
