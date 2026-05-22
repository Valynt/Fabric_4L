import { CapabilityGate } from "../components/CapabilityGate";
import { TeamPermissionsScreen } from "./TeamAccessScreens";

export function TeamPermissions() {
  return (
    <CapabilityGate capability="team">
      <TeamPermissionsScreen />
    </CapabilityGate>
  );
}
