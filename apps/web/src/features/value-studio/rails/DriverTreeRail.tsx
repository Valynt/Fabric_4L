import StudioAgentRail from "../components/StudioAgentRail";
import type { StudioTabRailProps } from "../types";

export default function DriverTreeRail(props: StudioTabRailProps) {
  return <StudioAgentRail {...props} activeTab="driver-tree" />;
}
