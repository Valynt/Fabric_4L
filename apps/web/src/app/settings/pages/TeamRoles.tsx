import { CapabilityGate } from "../components/CapabilityGate";
import { TeamRolesScreen } from "./TeamAccessScreens";

export function TeamRoles() {
  return (
    <CapabilityGate capability="team">
      <TeamRolesScreen />
    </CapabilityGate>
  );
}
