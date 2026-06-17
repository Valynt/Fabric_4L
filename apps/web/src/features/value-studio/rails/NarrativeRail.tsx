import StudioAgentRail from "../components/StudioAgentRail";
import type { StudioTabRailProps } from "../types";

export default function NarrativeRail(props: StudioTabRailProps) {
  return <StudioAgentRail {...props} activeTab="narrative" />;
}
