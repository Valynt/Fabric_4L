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

export default function StudioShell() {
  return (
    <div className="flex flex-col h-full overflow-hidden">
      <StudioHeader />
      <StudioTabs />
      <div className="flex-1 min-h-0 overflow-y-auto p-6">
        <StudioTabFrame />
      </div>
    </div>
  );
}
