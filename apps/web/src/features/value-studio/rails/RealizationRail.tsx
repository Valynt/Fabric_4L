import StudioAgentRail from "../components/StudioAgentRail";
import type { StudioTabRailProps } from "../types";

export default function RealizationRail(props: StudioTabRailProps) {
  return <StudioAgentRail {...props} activeTab="value-realization" />;
}
