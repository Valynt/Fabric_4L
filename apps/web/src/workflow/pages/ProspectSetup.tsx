import type { ProspectPromptBuilderProps } from "@/components/workspace/ProspectPromptBuilder"
import ProspectSetupPage from "@/pages/ProspectSetup"

export default function ProspectSetup(props: ProspectPromptBuilderProps) {
  return <ProspectSetupPage mode="workflow" {...props} />
}
