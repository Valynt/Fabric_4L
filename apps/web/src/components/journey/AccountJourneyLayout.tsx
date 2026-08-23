import { Outlet, useMatches, useParams } from "react-router-dom";
import { JourneyTimelineRightRail } from "./JourneyTimelineRightRail";

export function AccountJourneyLayout() {
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  const matches = useMatches();

  // Check if any active route match requests the journey timeline via handle
  const showTimeline = matches.some((match) => {
    const handle = match.handle as { journeyTimeline?: boolean } | undefined;
    return handle?.journeyTimeline === true;
  });

  return (
    <div className="flex h-full w-full overflow-hidden">
      <div className="flex-1 min-w-0 h-full overflow-y-auto">
        <Outlet />
      </div>

      {showTimeline && (
        <aside
          aria-label="Journey Timeline"
          className="hidden lg:block w-[320px] shrink-0 h-full overflow-hidden"
        >
          <JourneyTimelineRightRail tenantSlug={tenantSlug} accountId={accountId} />
        </aside>
      )}
    </div>
  );
}

export default AccountJourneyLayout;
