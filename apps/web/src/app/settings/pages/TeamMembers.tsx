import { CapabilityGate } from "../components/CapabilityGate";
import { TeamMembersScreen } from "./TeamAccessScreens";

export function TeamMembers() {
  return (
    <CapabilityGate capability="team">
      <TeamMembersScreen />
    </CapabilityGate>
  );
}
