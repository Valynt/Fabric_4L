import StudioAgentRail from "../components/StudioAgentRail";
import type { StudioTabRailProps } from "../types";

export default function ActionPlanRail(props: StudioTabRailProps) {
  return <StudioAgentRail {...props} activeTab="action-plan" />;
}
