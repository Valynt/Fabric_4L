import { Suspense, useCallback, useState } from "react";
import { Outlet, useLocation, useMatch } from "react-router-dom";
import { Spinner } from "@/components/ui/spinner";
import { SkipLink } from "@/components/ui/skip-link";
import { LeftNavigation } from "./LeftNavigation";
import { AppHeader } from "./AppHeader";
import { AgentChat } from "./AgentChat";
import { AgentSidePanel } from "./AgentSidePanel";
import { MobileNavigation } from "./MobileNavigation";
import {
  ACCOUNT_WORKFLOW_STEPS,
  WorkflowStepIndicator,
  type WorkflowStep,
} from "@/workflow/components/WorkflowStepIndicator";
import { useUserTierStore } from "@/stores/userTierStore";
import type { AgentChatMode } from "@/types/layout";
import type { UserTier } from "@/navigation/navigationService";
import { RouteTelemetry } from "@/lib/route-telemetry";
import { useAuthContext } from "@/contexts/AuthContext";

interface WorkflowIndicatorState {
  activeStepId: string;
  completedStepIds: string[];
  steps: WorkflowStep[];
}

function getWorkflowIndicatorState(
  pathname: string
): WorkflowIndicatorState | null {
  if (!pathname.includes("/accounts/")) {
    return null;
  }

  if (pathname.includes("/deliverables/")) {
    return {
      steps: ACCOUNT_WORKFLOW_STEPS,
      activeStepId: "deliverables",
      completedStepIds: ["scope", "intelligence", "studio"],
    };
  }

  if (pathname.includes("/studio/")) {
    return {
      steps: ACCOUNT_WORKFLOW_STEPS,
      activeStepId: "studio",
      completedStepIds: ["scope", "intelligence"],
    };
  }

  if (pathname.includes("/intelligence/")) {
    return {
      steps: ACCOUNT_WORKFLOW_STEPS,
      activeStepId: "intelligence",
      completedStepIds: ["scope"],
    };
  }

  return {
    steps: ACCOUNT_WORKFLOW_STEPS,
    activeStepId: "scope",
    completedStepIds: [],
  };
}

// ── Workspace Layout Wrapper ──────────────────────────────────────────────────
// Workspace routes (intelligence, hypothesis, drivers, calculator, etc.) need
// full-bleed layout without padding/max-width constraints so their internal
// shells (account header + tab bar + scrollable canvas + right rail) fill the
// entire content area. Regular pages keep the padded container.

export function WorkspaceLayoutWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  // Hooks must be called unconditionally on every render — do not use ||
  // short-circuiting because it changes the hook count between renders.
  const matchIntelligence = useMatch(
    "/t/:tenantSlug/accounts/:accountId/intelligence/*"
  );
  const matchStudio = useMatch("/t/:tenantSlug/accounts/:accountId/studio/*");
  const matchDeliverables = useMatch(
    "/t/:tenantSlug/accounts/:accountId/deliverables/*"
  );
  const matchAccounts = useMatch("/t/:tenantSlug/accounts/*");
  const matchSettings = useMatch("/settings/*");

  const isWorkspace = Boolean(
    matchIntelligence || matchStudio || matchDeliverables || matchAccounts
  );

  const isSettings = Boolean(matchSettings);

  const noPadding = isWorkspace || isSettings;

  return (
    <>
      {noPadding ? (
        <div className="h-full">
          <Suspense
            fallback={
              <div className="flex h-full min-h-[200px] items-center justify-center">
                <Spinner className="h-6 w-6" />
              </div>
            }
          >
            {children}
          </Suspense>
        </div>
      ) : (
        <div className="mx-auto w-full max-w-screen-2xl p-4 sm:p-6 lg:p-8">
          <Suspense
            fallback={
              <div className="flex h-full min-h-[200px] items-center justify-center">
                <Spinner className="h-6 w-6" />
              </div>
            }
          >
            {children}
          </Suspense>
        </div>
      )}
    </>
  );
}

export function GlobalLayout() {
  const [leftNavCollapsed, setLeftNavCollapsed] = useState(false);
  const { pathname } = useLocation();
  // Mobile navigation uses persistent icon rail (MobilePersistentSidebar).
  // Hamburger menu drawer is not implemented; no open/close state needed.
  const rawTier = useUserTierStore(state => state.currentTier);
  const { currentTenantSlug } = useAuthContext();
  const currentTier: UserTier = rawTier === "unknown" ? "standard" : rawTier;
  const isAdvancedModeEnabled = useUserTierStore(
    state => state.isAdvancedModeEnabled
  );
  const toggleAdvancedMode = useUserTierStore(
    state => state.toggleAdvancedMode
  );
  const [agentMode, setAgentMode] = useState<AgentChatMode>("closed");

  const toggleLeftNav = useCallback(() => {
    setLeftNavCollapsed(current => !current);
  }, []);

  const openAgentModal = useCallback(() => {
    setAgentMode("modal");
  }, []);

  const closeAgent = useCallback(() => {
    setAgentMode("closed");
  }, []);

  const expandAgentPanel = useCallback(() => {
    setAgentMode("panel");
    setLeftNavCollapsed(true);
  }, []);

  const minimizeAgentPanel = useCallback(() => {
    setAgentMode("modal");
  }, []);

  const agentPanelOpen = agentMode === "panel";
  const workflowIndicatorState = getWorkflowIndicatorState(pathname);

  return (
    <div
      className={[
        "grid h-screen grid-rows-[1fr] overflow-hidden bg-background text-foreground",
        agentPanelOpen
          ? "grid-cols-[auto_minmax(0,1fr)] lg:grid-cols-[auto_minmax(0,1fr)_minmax(360px,420px)]"
          : "grid-cols-[auto_minmax(0,1fr)]",
      ].join(" ")}
    >
      <RouteTelemetry />
      <SkipLink targetId="main-content" />

      <LeftNavigation
        collapsed={leftNavCollapsed}
        onToggle={toggleLeftNav}
        currentTier={currentTier}
        currentTenantSlug={currentTenantSlug}
      />

      <MobileNavigation
        currentTier={currentTier}
        isAdvancedModeEnabled={isAdvancedModeEnabled}
        onAdvancedModeToggle={toggleAdvancedMode}
      />

      <div className="flex min-w-0 flex-col overflow-hidden">
        <AppHeader
          onToggleLeftNav={toggleLeftNav}
          // Mobile nav is persistent icon rail; no hamburger toggle needed.
          leftNavCollapsed={leftNavCollapsed}
        />

        <main
          id="main-content"
          tabIndex={-1}
          className="min-h-0 flex-1 overflow-auto outline-none"
        >
          {workflowIndicatorState && (
            <WorkflowStepIndicator
              steps={workflowIndicatorState.steps}
              activeStepId={workflowIndicatorState.activeStepId}
              completedStepIds={workflowIndicatorState.completedStepIds}
            />
          )}
          <WorkspaceLayoutWrapper>
            <Outlet />
          </WorkspaceLayoutWrapper>
        </main>
      </div>

      {agentPanelOpen && (
        <AgentSidePanel onClose={closeAgent} onMinimize={minimizeAgentPanel} />
      )}

      {/* On smaller screens, show agent as modal instead of panel */}
      {agentMode !== "panel" && (
        <AgentChat
          mode={agentMode}
          onOpen={openAgentModal}
          onClose={closeAgent}
          onExpand={expandAgentPanel}
        />
      )}
    </div>
  );
}
