/**
 * StudioShell — Main Value Studio workspace shell
 *
 * Composes: Header → Tabs → Tab Frame
 *
 * Route: /t/:tenantSlug/accounts/:accountId/studio/:tabId
 */
import StudioHeader from "./components/StudioHeader";
import StudioTabs from "./StudioTabs";
import StudioTabFrame from "./components/StudioTabFrame";
import StudioRightRail from "./components/StudioRightRail";
import { StudioRailProvider } from "./context/StudioRailContext";

export default function StudioShell() {
  return (
    <StudioRailProvider>
      <div className="flex flex-col h-full overflow-hidden">
        <StudioHeader />
        <StudioTabs />
        <div className="flex flex-1 min-h-0 overflow-hidden">
          <div className="flex-1 min-w-0 overflow-y-auto p-6">
            <StudioTabFrame />
          </div>
          <StudioRightRail />
        </div>
      </div>
    </StudioRailProvider>
  );
}
