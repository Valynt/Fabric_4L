import StudioAgentRail from "../components/StudioAgentRail";
import type { StudioTabRailProps } from "../types";

export default function ValueModelRail(props: StudioTabRailProps) {
  return <StudioAgentRail {...props} activeTab="value-model" />;
}
