import { lazy, Suspense } from "react";
import { createBrowserRouter, Navigate, useLocation, useParams } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthContext } from "@/contexts/AuthContext";
import { useAccountContextStore } from "@/stores/accountContextStore";
import { GlobalLayout } from "@/components/layout/GlobalLayout";
import { UnifiedRouteGuard } from "@/components/routing/UnifiedRouteGuard";
import { RequireClerkAuth } from "@/components/routing/RequireClerkAuth";
import { AuthorizationProvider } from "@/auth/AuthorizationProvider";
import { RootAuthStateAdapter } from "@/auth/rootAuthStateAdapter";
import { isClerkAuthEnabled } from "@/auth/clerkConfig";
import { SettingsLayout } from "@/app/settings/SettingsLayout";
import { EmptyState } from "@/components/states/EmptyState";
import { PublicLandingPage } from "@/features/public-landing";
import CommandCenter from "@/pages/CommandCenter";
import { IntelligenceWorkspace } from "@/features/intelligence-workspace";
import StudioShell from "@/features/value-studio/StudioShell";

// Settings pages — Personal
const PersonalProfile = lazy(() => import("@/app/settings/pages/PersonalProfile").then(m => ({ default: m.PersonalProfile })));
const PersonalSecurity = lazy(() => import("@/app/settings/pages/PersonalSecurity").then(m => ({ default: m.PersonalSecurity })));
const PersonalPreferences = lazy(() => import("@/app/settings/pages/PersonalPreferences").then(m => ({ default: m.PersonalPreferences })));
const PersonalNotifications = lazy(() => import("@/app/settings/pages/PersonalNotifications").then(m => ({ default: m.PersonalNotifications })));
const PersonalSessions = lazy(() => import("@/app/settings/pages/PersonalSessions").then(m => ({ default: m.PersonalSessions })));
const PersonalActivity = lazy(() => import("@/app/settings/pages/PersonalActivity").then(m => ({ default: m.PersonalActivity })));

// Settings pages — Account & Billing
const BillingWorkspace = lazy(() => import("@/app/settings/pages/BillingWorkspace").then(m => ({ default: m.BillingWorkspace })));
const BillingSubscription = lazy(() => import("@/app/settings/pages/BillingSubscription").then(m => ({ default: m.BillingSubscription })));
const BillingUsage = lazy(() => import("@/app/settings/pages/BillingUsage").then(m => ({ default: m.BillingUsage })));
const BillingPaymentMethods = lazy(() => import("@/app/settings/pages/BillingPaymentMethods").then(m => ({ default: m.BillingPaymentMethods })));
const BillingInvoices = lazy(() => import("@/app/settings/pages/BillingInvoices").then(m => ({ default: m.BillingInvoices })));

// Settings pages — Team & Access
const TeamMembers = lazy(() => import("@/app/settings/pages/TeamMembers").then(m => ({ default: m.TeamMembers })));
const TeamInvitations = lazy(() => import("@/app/settings/pages/TeamInvitations").then(m => ({ default: m.TeamInvitations })));
const TeamRoles = lazy(() => import("@/app/settings/pages/TeamRoles").then(m => ({ default: m.TeamRoles })));
const TeamPermissions = lazy(() => import("@/app/settings/pages/TeamPermissions").then(m => ({ default: m.TeamPermissions })));
const TeamApiKeys = lazy(() => import("@/app/settings/pages/TeamApiKeys").then(m => ({ default: m.TeamApiKeys })));

// Settings pages — Data & Integrations
const DataSources = lazy(() => import("@/app/settings/pages/DataSources").then(m => ({ default: m.DataSources })));
const DataIntegrations = lazy(() => import("@/app/settings/pages/DataIntegrations").then(m => ({ default: m.DataIntegrations })));
const DataVariables = lazy(() => import("@/app/settings/pages/DataVariables").then(m => ({ default: m.DataVariables })));
const DataValuePacks = lazy(() => import("@/app/settings/pages/DataValuePacks").then(m => ({ default: m.DataValuePacks })));
const DataIngestionRules = lazy(() => import("@/app/settings/pages/DataIngestionRules").then(m => ({ default: m.DataIngestionRules })));

// Settings pages — Governance
const GovernancePolicies = lazy(() => import("@/app/settings/pages/GovernancePolicies").then(m => ({ default: m.GovernancePolicies })));
const GovernanceCompliance = lazy(() => import("@/app/settings/pages/GovernanceCompliance").then(m => ({ default: m.GovernanceCompliance })));
const GovernanceHealth = lazy(() => import("@/app/settings/pages/GovernanceHealth").then(m => ({ default: m.GovernanceHealth })));
const GovernanceAuditTrail = lazy(() => import("@/app/settings/pages/GovernanceAuditTrail").then(m => ({ default: m.GovernanceAuditTrail })));
const GovernanceAdminControls = lazy(() => import("@/app/settings/pages/GovernanceAdminControls").then(m => ({ default: m.GovernanceAdminControls })));

const ClerkSignInPage = lazy(() => import("@/pages/ClerkSignIn"));
const ClerkSignUpPage = lazy(() => import("@/pages/ClerkSignUp"));
const ClerkSsoCallbackPage = lazy(() => import("@/pages/ClerkSsoCallback"));
const AcceptInvitePage = lazy(() => import("@/pages/AcceptInvite"));
const SelectOrganizationPage = lazy(() => import("@/pages/SelectOrganization"));
const OnboardingPage = lazy(() => import("@/pages/Onboarding"));
const ValueNarrativeHome = lazy(() => import("@/pages/ValueNarrativeHome"));
const Accounts = lazy(() => import("@/pages/Accounts"));
const TasksPage = lazy(() => import("@/pages/TasksPage"));
const CollaborationCommentsPage = lazy(() => import("@/pages/CollaborationCommentsPage"));
const NotificationsPage = lazy(() => import("@/pages/NotificationsPage"));

// ── Context Engine ──
const ValuePacks = lazy(() => import("@/pages/ValuePacks"));
const MyModels = lazy(() => import("@/pages/MyModels"));
const FormulaList = lazy(() => import("@/pages/FormulaList"));
const FormulaBuilder = lazy(() => import("@/pages/FormulaBuilder"));
const ValueTreeExplorer = lazy(() => import("@/pages/ValueTreeExplorer"));
const AgentWorkflows = lazy(() => import("@/pages/AgentWorkflows"));
const OntologyEditor = lazy(() => import("@/pages/OntologyEditor"));
const EntityBrowser = lazy(() => import("@/pages/EntityBrowser"));
const EntityDetail = lazy(() => import("@/pages/EntityDetail"));
const GraphExplorer = lazy(() => import("@/pages/GraphExplorer"));
const IngestionJobs = lazy(() => import("@/pages/IngestionJobs"));
const ExtractionEngine = lazy(() => import("@/pages/ExtractionEngine"));
const Integrations = lazy(() => import("@/pages/Integrations"));
const SourceConfiguration = lazy(() => import("@/pages/SourceConfiguration"));
const TargetsAdmin = lazy(() => import("@/pages/TargetsAdmin"));

// ── Deliverables ──
const BusinessCaseList = lazy(() => import("@/pages/BusinessCaseList"));
const BusinessCase = lazy(() => import("@/pages/BusinessCase"));
const InteractiveBusinessCase = lazy(() => import("@/pages/InteractiveBusinessCase"));
const CFOView = lazy(() => import("@/pages/deliverables/CFOView"));
const ExecutiveView = lazy(() => import("@/pages/deliverables/ExecutiveView"));
const TechnicalView = lazy(() => import("@/pages/deliverables/TechnicalView"));

// ── Governance ──
const DecisionTracePage = lazy(() => import("@/pages/DecisionTrace"));
const GovernanceEvidencePage = lazy(() => import("@/pages/GovernanceEvidence"));
const GovernanceCompliancePage = lazy(() => import("@/pages/GovernanceCompliance"));
const GovernanceAuditLogPage = lazy(() => import("@/pages/GovernanceAuditLog"));
const GovernanceChangeHistoryPage = lazy(() => import("@/pages/GovernanceChangeHistory"));
const ReviewQueuePage = lazy(() => import("@/pages/ReviewQueuePage"));
const VersionHistoryPage = lazy(() => import("@/pages/VersionHistoryPage"));
const BenchmarkPoliciesPage = lazy(() => import("@/pages/admin/BenchmarkPolicies"));
const HealthMonitorPage = lazy(() => import("@/pages/admin/HealthMonitor"));
const BillingAdminPage = lazy(() => import("@/pages/admin/BillingAdmin"));

// ── Dev Tools ──
const IntegrationDashboard = lazy(() => import("@/pages/dev/IntegrationDashboard"));
const NotFound = lazy(() => import("@/pages/NotFound"));
const ForbiddenPage = lazy(() => import("@/pages/ForbiddenPage"));

// ── Academy ──
const AcademyPage = lazy(() => import("@/pages/Academy"));
const AcademyQuizPage = lazy(() => import("@/pages/AcademyQuiz"));

// ── Account / Prospect Creation ──
const ProspectSetupPage = lazy(() => import("@/pages/ProspectSetup"));

function AcademyFollowUpState({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-6">
      <EmptyState title={title} description={description} />
    </div>
  );
}

export function RootRedirect() {
  return (
    <RootAuthStateAdapter>
      {({ isLoading, isAuthenticated }) => {
        if (isLoading) {
          return (
            <div className="flex h-full min-h-[200px] items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
            </div>
          );
        }

        return isAuthenticated ? (
          <Navigate to="/home" replace />
        ) : (
          <PublicLandingPage />
        );
      }}
    </RootAuthStateAdapter>
  );
}

// ═══════════════════════════════════════════════════════════════
// Legacy flat-route redirects (Phase 1 launch-blocker remediation)
// ═══════════════════════════════════════════════════════════════

/** Map of legacy flat paths to canonical tenant-scoped paths. */
export const LEGACY_FLAT_ROUTE_MAP: Record<string, string> = {
  "/discover/accounts": "/t/{tenantSlug}/accounts",
  "/accounts": "/t/{tenantSlug}/accounts",
  "/discover/jobs": "/t/{tenantSlug}/context/ingestion/jobs",
  "/discover/extraction": "/t/{tenantSlug}/context/extraction",
  "/discover/knowledge": "/t/{tenantSlug}/context/ontology",
  "/discover/integrations": "/t/{tenantSlug}/context/integrations",
  "/discover/sources": "/t/{tenantSlug}/context/sources",
  "/library": "/t/{tenantSlug}/context",
  "/library/models": "/t/{tenantSlug}/context/models",
  "/library/packs": "/t/{tenantSlug}/context/packs",
  "/library/authoring": "/t/{tenantSlug}/context/formulas",
  "/context": "/t/{tenantSlug}/context",
  "/context/packs": "/t/{tenantSlug}/context/packs",
  "/context/models": "/t/{tenantSlug}/context/models",
  "/context/formulas": "/t/{tenantSlug}/context/formulas",
  "/context/value-trees/explorer": "/t/{tenantSlug}/context/value-trees/explorer",
  "/context/agents": "/t/{tenantSlug}/context/agents",
  "/context/ontology": "/t/{tenantSlug}/context/ontology",
  "/context/ontology/entities": "/t/{tenantSlug}/context/ontology/entities",
  "/context/ontology/graph": "/t/{tenantSlug}/context/ontology/graph",
  "/context/ingestion/jobs": "/t/{tenantSlug}/context/ingestion/jobs",
  "/context/extraction": "/t/{tenantSlug}/context/extraction",
  "/context/integrations": "/t/{tenantSlug}/context/integrations",
  "/context/sources": "/t/{tenantSlug}/context/sources",
  "/context/targets": "/t/{tenantSlug}/context/targets",
  "/model": "/t/{tenantSlug}/context/models",
  "/model/value-studio": "/t/{tenantSlug}/context/models",
  "/governance/traces": "/t/{tenantSlug}/governance/traces",
  "/governance/audit/log": "/t/{tenantSlug}/governance/audit-log",
  "/governance/audit-log": "/t/{tenantSlug}/governance/audit-log",
  "/governance/evidence": "/t/{tenantSlug}/governance/evidence",
  "/governance/provenance": "/t/{tenantSlug}/governance/provenance",
  "/governance/compliance": "/t/{tenantSlug}/governance/compliance",
  "/governance/benchmarks": "/t/{tenantSlug}/governance/benchmarks",
  "/settings/governance/health": "/t/{tenantSlug}/settings/governance/health",
  "/settings/governance/benchmarks": "/t/{tenantSlug}/governance/benchmarks",
};

const LEGACY_FLAT_ROUTE_REGISTRATIONS = [
  "/discover/*",
  "/accounts",
  "/library/*",
  "/context/*",
  "/model/*",
  "/governance/*",
  "/settings/governance/*",
] as const;

export function LegacyFlatRedirect() {
  const { currentTenantSlug, isLoading } = useAuthContext();
  const { pathname } = useLocation();
  const normalized = pathname.replace(/\/$/, "") || "/";

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  if (!currentTenantSlug) {
    if (isClerkAuthEnabled()) {
      return <Navigate to="/workspaces" replace />;
    }
    return <Navigate to="/home" replace />;
  }

  const targetTemplate = LEGACY_FLAT_ROUTE_MAP[normalized];
  if (!targetTemplate) {
    return <Navigate to="/home" replace />;
  }

  return <Navigate to={targetTemplate.replace("{tenantSlug}", currentTenantSlug)} replace />;
}

export function LegacyIntelligenceRedirect() {
  const { currentTenantSlug, isLoading } = useAuthContext();
  const { accountId, tabId } = useParams<{ accountId: string; tabId: string }>();

  if (isLoading) {
    return (
      <div className="flex h-full min-h-[200px] items-center justify-center">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-border border-t-primary" />
      </div>
    );
  }

  if (!currentTenantSlug || !accountId) {
    return <Navigate to="/home" replace />;
  }

  const target = `/t/${currentTenantSlug}/accounts/${accountId}/intelligence/${tabId ?? "signals"}`;
  return <Navigate to={target} replace />;
}

function AccountOverviewRedirect() {
  const { tenantSlug, accountId } = useParams<{ tenantSlug: string; accountId: string }>();
  return <Navigate to={`/t/${tenantSlug}/accounts/${accountId}/overview`} replace />;
}

// ── Route metadata helpers ───────────────────────────────────────────────────

const authPolicy = { requiresAuth: false, tenantScoped: false, fallbackRoute: "/sign-in", analyticsRouteId: "auth" } as const;
const homePolicy = { requiresAuth: true, tenantScoped: false, fallbackRoute: "/sign-in", analyticsRouteId: "home" } as const;
const tenantStdPolicy = (id: string) => ({ requiresAuth: true, tenantScoped: true, requiredTier: "standard" as const, fallbackRoute: "/home", analyticsRouteId: id });
const tenantAdvPolicy = (id: string) => ({ requiresAuth: true, tenantScoped: true, requiredTier: "advanced" as const, fallbackRoute: "/home", analyticsRouteId: id });
const tenantAdminPolicy = (id: string) => ({ requiresAuth: true, tenantScoped: true, requiredTier: "admin" as const, fallbackRoute: "/home", analyticsRouteId: id });
const accountStdPolicy = (id: string) => ({ requiresAuth: true, tenantScoped: true, accountScoped: true, requiredTier: "standard" as const, fallbackRoute: "/home", analyticsRouteId: id });
// TODO(VF-FE-ROUTER-DEBT-001): accountAdvPolicy is reserved for future advanced account-scoped gating.
// No routes currently use it. When advanced account access is implemented,
// update affected routes (e.g. studio build, value-model detail) to use this policy.
const accountAdvPolicy = (id: string) => ({ requiresAuth: true, tenantScoped: true, accountScoped: true, requiredTier: "advanced" as const, fallbackRoute: "/home", analyticsRouteId: id });

export const router = createBrowserRouter([
  {
    path: "/",
    element: <RootRedirect />,
  },
  {
    path: "/sign-in/*",
    element: <ClerkSignInPage />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/signin",
    element: <Navigate to="/sign-in" replace />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/login",
    element: <Navigate to="/sign-in" replace />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/sign-up/*",
    element: <ClerkSignUpPage />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/accept-invite",
    element: <AcceptInvitePage />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/sso-callback/*",
    element: <ClerkSsoCallbackPage />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/signup",
    element: <Navigate to="/sign-up" replace />,
    handle: { accessPolicy: authPolicy },
  },
  {
    path: "/workspaces",
    element: (
      <RequireClerkAuth requireOrganization={false}>
        <SelectOrganizationPage />
      </RequireClerkAuth>
    ),
    handle: { accessPolicy: { ...authPolicy, requiresAuth: true } },
  },
  {
    path: "/onboarding",
    element: (
      <RequireClerkAuth requireOrganization={false}>
        <OnboardingPage />
      </RequireClerkAuth>
    ),
    handle: { accessPolicy: { ...authPolicy, requiresAuth: true } },
  },
  {
    path: "/forbidden",
    element: (
      <RequireClerkAuth requireOrganization={false}>
        <ForbiddenPage />
      </RequireClerkAuth>
    ),
    handle: { accessPolicy: { ...authPolicy, requiresAuth: true } },
  },
  {
    element: (
      <RequireClerkAuth requireOrganization={false}>
        <AuthorizationProvider>
          <GlobalLayout />
        </AuthorizationProvider>
      </RequireClerkAuth>
    ),
    children: [
      {
        path: "/dashboard",
        element: <Navigate to="/home" replace />,
        handle: { accessPolicy: homePolicy },
      },
      {
        path: "/blog",
        element: <Navigate to="/home" replace />,
        handle: { accessPolicy: homePolicy },
      },
      // Legacy flat-route redirects (see Phase 1 launch-blocker remediation)
      {
        path: "/intelligence/:accountId/:tabId",
        element: <LegacyIntelligenceRedirect />,
      },
      ...LEGACY_FLAT_ROUTE_REGISTRATIONS.map((path) => ({
        path,
        element: <LegacyFlatRedirect />,
      })),
      {
        path: "/home",
        element: (
          <UnifiedRouteGuard>
            <ValueNarrativeHome />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: homePolicy },
      },
      {
        path: "/command-center",
        element: (
          <UnifiedRouteGuard>
            <CommandCenter />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: homePolicy },
      },
      {
        path: "/tasks",
        element: (
          <UnifiedRouteGuard>
            <TasksPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: homePolicy },
      },
      {
        path: "/collaboration/comments",
        element: (
          <UnifiedRouteGuard>
            <CollaborationCommentsPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: homePolicy },
      },
      {
        path: "/notifications",
        element: (
          <UnifiedRouteGuard>
            <NotificationsPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: homePolicy },
      },

      // ═══════════════════════════════════════════════════════════════
      // ACCOUNT CREATION
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/accounts/new",
        element: (
          <UnifiedRouteGuard>
            <Suspense fallback={<div className="flex h-full min-h-[200px] items-center justify-center gap-2"><Skeleton className="h-8 w-48" /></div>}>
              <ProspectSetupPage />
            </Suspense>
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: homePolicy },
      },

      // ═══════════════════════════════════════════════════════════════
      // ACCOUNTS
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/accounts",
        element: (
          <UnifiedRouteGuard>
            <Accounts />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("accounts.list") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId",
        element: <AccountOverviewRedirect />,
        handle: { accessPolicy: accountStdPolicy("accounts.overview-redirect") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/overview",
        element: (
          <UnifiedRouteGuard>
            <Accounts />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("accounts.overview") },
      },

      // ═══════════════════════════════════════════════════════════════
      // INTELLIGENCE WORKSPACE
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/accounts/:accountId/intelligence",
        element: (
          <UnifiedRouteGuard>
            <Navigate to="signals" replace />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("intelligence.workspace") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/intelligence/:tabId",
        element: (
          <UnifiedRouteGuard>
            <Suspense fallback={<div className="flex h-full items-center justify-center gap-2"><Skeleton className="h-8 w-48" /></div>}>
              <IntelligenceWorkspace />
            </Suspense>
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("intelligence.workspace") },
      },

      // ═══════════════════════════════════════════════════════════════
      // VALUE STUDIO WORKSPACE
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/accounts/:accountId/studio",
        element: (
          <UnifiedRouteGuard>
            <Navigate to="action-plan" replace />
          </UnifiedRouteGuard>
        ),
        handle: {
          accessPolicy: accountStdPolicy("studio.workspace"),
          title: "Value Studio",
          category: "Workspace",
        },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/studio/:tabId",
        element: (
          <UnifiedRouteGuard>
            <Suspense fallback={<div className="flex h-full items-center justify-center gap-2"><Skeleton className="h-8 w-48" /></div>}>
              <StudioShell />
            </Suspense>
          </UnifiedRouteGuard>
        ),
        handle: {
          accessPolicy: accountStdPolicy("studio.workspace"),
          title: "Value Studio",
          category: "Workspace",
        },
      },

      // ═══════════════════════════════════════════════════════════════
      // DELIVERABLES
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables",
        element: (
          <UnifiedRouteGuard>
            <Navigate to="business-cases" replace />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("deliverables.workspace") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases",
        element: (
          <UnifiedRouteGuard>
            <BusinessCaseList />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("deliverables.business-cases") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/business-cases/:caseId",
        element: (
          <UnifiedRouteGuard>
            <BusinessCase />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("deliverables.business-case-detail") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/proposals",
        element: (
          <UnifiedRouteGuard>
            <BusinessCaseList />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("deliverables.proposals") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/exports",
        element: (
          <UnifiedRouteGuard>
            <BusinessCaseList />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("deliverables.exports") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/cfo",
        element: (
          <UnifiedRouteGuard>
            <CFOView />
          </UnifiedRouteGuard>
        ),
        handle: {
          accessPolicy: accountStdPolicy("deliverables.cfo-view"),
          title: "CFO View",
          category: "Deliverables",
        },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/executive",
        element: (
          <UnifiedRouteGuard>
            <ExecutiveView />
          </UnifiedRouteGuard>
        ),
        handle: {
          accessPolicy: accountStdPolicy("deliverables.executive-view"),
          title: "Executive View",
          category: "Deliverables",
        },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/deliverables/views/technical",
        element: (
          <UnifiedRouteGuard>
            <TechnicalView />
          </UnifiedRouteGuard>
        ),
        handle: {
          accessPolicy: accountStdPolicy("deliverables.technical-view"),
          title: "Technical View",
          category: "Deliverables",
        },
      },

      // ═══════════════════════════════════════════════════════════════
      // AGENTS & WORKFLOWS
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/accounts/:accountId/agents",
        element: (
          <UnifiedRouteGuard>
            <AgentWorkflows />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("agents.console") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/agents/threads/:threadId",
        element: (
          <UnifiedRouteGuard>
            <AgentWorkflows />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("agents.thread") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/workflows",
        element: (
          <UnifiedRouteGuard>
            <AgentWorkflows />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("agents.workflows") },
      },
      {
        path: "/t/:tenantSlug/accounts/:accountId/workflows/:workflowRunId",
        element: (
          <UnifiedRouteGuard>
            <AgentWorkflows />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: accountStdPolicy("agents.workflow-run") },
      },

      // ═══════════════════════════════════════════════════════════════
      // CONTEXT ENGINE
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/context",
        element: <Navigate to="sources" replace />,
        handle: { accessPolicy: tenantStdPolicy("context.workspace") },
      },
      {
        path: "/t/:tenantSlug/context/packs",
        element: (
          <UnifiedRouteGuard>
            <ValuePacks />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("context.packs") },
      },
      {
        path: "/t/:tenantSlug/context/models",
        element: (
          <UnifiedRouteGuard>
            <MyModels />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("context.models") },
      },
      {
        path: "/t/:tenantSlug/context/formulas",
        element: (
          <UnifiedRouteGuard>
            <FormulaList />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.formulas") },
      },
      {
        path: "/t/:tenantSlug/context/formulas/new",
        element: (
          <UnifiedRouteGuard>
            <FormulaBuilder isNew />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.formulas-new") },
      },
      {
        path: "/t/:tenantSlug/context/formulas/:formulaId",
        element: (
          <UnifiedRouteGuard>
            <FormulaBuilder />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.formula-detail") },
      },
      {
        path: "/t/:tenantSlug/context/value-trees/explorer",
        element: (
          <UnifiedRouteGuard>
            <ValueTreeExplorer />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.value-trees") },
      },
      {
        path: "/t/:tenantSlug/context/agents",
        element: (
          <UnifiedRouteGuard>
            <AgentWorkflows />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.agents") },
      },
      {
        path: "/t/:tenantSlug/context/ontology",
        element: (
          <UnifiedRouteGuard>
            <OntologyEditor />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.ontology") },
      },
      {
        path: "/t/:tenantSlug/context/ontology/entities",
        element: (
          <UnifiedRouteGuard>
            <EntityBrowser />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.entities") },
      },
      {
        path: "/t/:tenantSlug/context/ontology/entities/:entityId",
        element: (
          <UnifiedRouteGuard>
            <EntityDetail />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.entity-detail") },
      },
      {
        path: "/t/:tenantSlug/context/ontology/graph",
        element: (
          <UnifiedRouteGuard>
            <GraphExplorer />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.graph") },
      },
      {
        path: "/t/:tenantSlug/context/ingestion/jobs",
        element: (
          <UnifiedRouteGuard>
            <IngestionJobs />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("context.ingestion-jobs") },
      },
      {
        path: "/t/:tenantSlug/context/extraction",
        element: (
          <UnifiedRouteGuard>
            <ExtractionEngine />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("context.extraction") },
      },
      {
        path: "/t/:tenantSlug/context/integrations",
        element: (
          <UnifiedRouteGuard>
            <Integrations />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("context.integrations") },
      },
      {
        path: "/t/:tenantSlug/context/sources",
        element: (
          <UnifiedRouteGuard>
            <SourceConfiguration />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("context.sources") },
      },
      {
        path: "/t/:tenantSlug/context/targets",
        element: (
          <UnifiedRouteGuard>
            <TargetsAdmin />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("context.targets") },
      },

      // ═══════════════════════════════════════════════════════════════
      // GOVERNANCE
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/governance",
        element: <Navigate to="traces" replace />,
        handle: { accessPolicy: tenantStdPolicy("governance.workspace") },
      },
      {
        path: "/t/:tenantSlug/governance/traces",
        element: (
          <UnifiedRouteGuard>
            <DecisionTracePage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("governance.traces") },
      },
      {
        path: "/t/:tenantSlug/governance/evidence",
        element: (
          <UnifiedRouteGuard>
            <GovernanceEvidencePage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("governance.evidence") },
      },
      {
        path: "/t/:tenantSlug/governance/provenance",
        element: (
          <UnifiedRouteGuard>
            <DecisionTracePage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("governance.provenance") },
      },
      {
        path: "/t/:tenantSlug/governance/compliance",
        element: (
          <UnifiedRouteGuard>
            <GovernanceCompliancePage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("governance.compliance") },
      },
      {
        path: "/t/:tenantSlug/governance/formulas",
        element: (
          <UnifiedRouteGuard>
            <FormulaList />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("governance.formulas") },
      },
      {
        path: "/t/:tenantSlug/governance/formulas/:formulaId",
        element: (
          <UnifiedRouteGuard>
            <FormulaBuilder />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdvPolicy("governance.formula-detail") },
      },
      {
        path: "/t/:tenantSlug/governance/benchmarks",
        element: (
          <UnifiedRouteGuard>
            <BenchmarkPoliciesPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("governance.benchmarks") },
      },
      {
        path: "/t/:tenantSlug/governance/benchmarks/:benchmarkId",
        element: (
          <UnifiedRouteGuard>
            <BenchmarkPoliciesPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("governance.benchmark-detail") },
      },
      {
        path: "/t/:tenantSlug/governance/value-packs",
        element: (
          <UnifiedRouteGuard>
            <ValuePacks />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("governance.value-packs") },
      },
      {
        path: "/t/:tenantSlug/governance/value-packs/:packId",
        element: (
          <UnifiedRouteGuard>
            <ValuePacks />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("governance.value-pack-detail") },
      },
      {
        path: "/t/:tenantSlug/governance/policies",
        element: (
          <UnifiedRouteGuard>
            <GovernancePolicies />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("governance.policies") },
      },
      {
        path: "/t/:tenantSlug/governance/audit-log",
        element: (
          <UnifiedRouteGuard>
            <GovernanceAuditLogPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("governance.audit-log") },
      },
      {
        path: "/t/:tenantSlug/governance/health",
        element: (
          <UnifiedRouteGuard>
            <HealthMonitorPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("governance.health") },
      },
      {
        path: "/t/:tenantSlug/governance/billing",
        element: (
          <UnifiedRouteGuard>
            <BillingAdminPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("governance.billing") },
      },

      // ═══════════════════════════════════════════════════════════════
      // ACADEMY
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/t/:tenantSlug/academy",
        element: (
          <UnifiedRouteGuard>
            <AcademyPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("academy") },
      },
      {
        path: "/t/:tenantSlug/academy/pillars/:pillarId",
        element: (
          <UnifiedRouteGuard>
            <AcademyFollowUpState
              title="Pillar detail is not enabled for this release"
              description="Use the academy overview and quizzes while pillar-level content is being prepared for a later release."
            />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("academy.pillar") },
      },
      {
        path: "/t/:tenantSlug/academy/pillars/:pillarId/quiz",
        element: (
          <UnifiedRouteGuard>
            <AcademyQuizPage />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("academy.quiz") },
      },
      {
        path: "/t/:tenantSlug/academy/resources",
        element: (
          <UnifiedRouteGuard>
            <AcademyFollowUpState
              title="Resource library is not enabled for this release"
              description="Use the academy overview for published guidance. Resource downloads will remain out of the release gate until the library is productized."
            />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("academy.resources") },
      },
      {
        path: "/t/:tenantSlug/academy/profile",
        element: (
          <UnifiedRouteGuard>
            <AcademyFollowUpState
              title="Academy profile is not enabled for this release"
              description="Quiz progress remains available inside the academy flow. Profile-level reporting is tracked as a follow-up surface."
            />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantStdPolicy("academy.profile") },
      },

      // ═══════════════════════════════════════════════════════════════
      // SETTINGS — Personal (global)
      // ═══════════════════════════════════════════════════════════════
      {
        handle: { accessPolicy: homePolicy },
        element: (
          <UnifiedRouteGuard>
            <SettingsLayout />
          </UnifiedRouteGuard>
        ),
        children: [
          { path: "/personal", element: <Navigate to="/personal/profile" replace /> },
          { path: "/personal/profile", element: <PersonalProfile />, handle: { title: "Profile", category: "Personal Settings" } },
          { path: "/personal/security", element: <PersonalSecurity />, handle: { title: "Security", category: "Personal Settings" } },
          { path: "/personal/preferences", element: <PersonalPreferences />, handle: { title: "Preferences", category: "Personal Settings" } },
          { path: "/personal/notifications", element: <PersonalNotifications />, handle: { title: "Notifications", category: "Personal Settings" } },
          { path: "/personal/sessions", element: <PersonalSessions />, handle: { title: "Active Sessions", category: "Personal Settings" } },
          { path: "/personal/activity", element: <PersonalActivity />, handle: { title: "My Activity", category: "Personal Settings", accessPolicy: homePolicy } },
          { path: "/settings", element: <Navigate to="/settings/profile" replace />, handle: { accessPolicy: homePolicy } },
          { path: "/settings/profile", element: <PersonalProfile />, handle: { title: "Profile", category: "Personal Settings", accessPolicy: homePolicy } },
          { path: "/settings/security", element: <PersonalSecurity />, handle: { title: "Security", category: "Personal Settings", accessPolicy: homePolicy } },
          { path: "/settings/preferences", element: <PersonalPreferences />, handle: { title: "Preferences", category: "Personal Settings" } },
          { path: "/settings/notifications", element: <PersonalNotifications />, handle: { title: "Notifications", category: "Personal Settings" } },
          { path: "/settings/sessions", element: <PersonalSessions />, handle: { title: "Active Sessions", category: "Personal Settings" } },
          { path: "/settings/activity", element: <PersonalActivity />, handle: { title: "My Activity", category: "Personal Settings" } },
        ],
      },

      // ═══════════════════════════════════════════════════════════════
      // SETTINGS — Tenant / Workspace / Admin
      // ═══════════════════════════════════════════════════════════════
      {
        handle: { accessPolicy: tenantAdminPolicy("tenant-settings.workspace") },
        element: (
          <UnifiedRouteGuard>
            <SettingsLayout />
          </UnifiedRouteGuard>
        ),
        children: [
          { path: "/t/:tenantSlug/settings", element: <Navigate to="workspace" replace /> },

          // Account & Billing
          { path: "/t/:tenantSlug/settings/workspace", element: <BillingWorkspace />, handle: { title: "Workspace", category: "Account & Billing" } },
          { path: "/t/:tenantSlug/settings/billing", element: <BillingSubscription />, handle: { title: "Subscription", category: "Account & Billing" } },
          { path: "/t/:tenantSlug/settings/billing/subscription", element: <BillingSubscription />, handle: { title: "Subscription", category: "Account & Billing" } },
          { path: "/t/:tenantSlug/settings/billing/usage", element: <BillingUsage />, handle: { title: "Usage", category: "Account & Billing" } },
          { path: "/t/:tenantSlug/settings/billing/payment-methods", element: <BillingPaymentMethods />, handle: { title: "Payment Methods", category: "Account & Billing" } },
          { path: "/t/:tenantSlug/settings/billing/invoices", element: <BillingInvoices />, handle: { title: "Invoices", category: "Account & Billing" } },

          // Team & Access
          { path: "/t/:tenantSlug/settings/users", element: <TeamMembers />, handle: { title: "Team Members", category: "Team & Access" } },
          { path: "/t/:tenantSlug/settings/roles", element: <TeamRoles />, handle: { title: "Roles", category: "Team & Access" } },
          { path: "/t/:tenantSlug/settings/permissions", element: <TeamPermissions />, handle: { title: "Permissions", category: "Team & Access" } },
          { path: "/t/:tenantSlug/settings/api-keys", element: <TeamApiKeys />, handle: { title: "API Keys", category: "Team & Access" } },

          // Data & Integrations
          { path: "/t/:tenantSlug/settings/data-sources", element: <DataSources />, handle: { title: "Data Sources", category: "Data & Integrations" } },
          { path: "/t/:tenantSlug/settings/integrations", element: <DataIntegrations />, handle: { title: "Integrations", category: "Data & Integrations" } },
          { path: "/t/:tenantSlug/settings/variables", element: <DataVariables />, handle: { title: "Variables", category: "Data & Integrations" } },
          { path: "/t/:tenantSlug/settings/value-packs", element: <DataValuePacks />, handle: { title: "Value Packs", category: "Data & Integrations" } },
          { path: "/t/:tenantSlug/settings/ingestion-rules", element: <DataIngestionRules />, handle: { title: "Ingestion Rules", category: "Data & Integrations" } },

          // Governance
          { path: "/t/:tenantSlug/settings/governance", element: <Navigate to="policies" replace /> },
          { path: "/t/:tenantSlug/settings/governance/policies", element: <GovernancePolicies />, handle: { title: "Policies", category: "Governance" } },
          { path: "/t/:tenantSlug/settings/governance/compliance", element: <GovernanceCompliance />, handle: { title: "Compliance", category: "Governance" } },
          { path: "/t/:tenantSlug/settings/governance/health", element: <GovernanceHealth />, handle: { title: "Health", category: "Governance" } },
          { path: "/t/:tenantSlug/settings/governance/audit", element: <GovernanceAuditTrail />, handle: { title: "Audit Trail", category: "Governance" } },
          { path: "/t/:tenantSlug/settings/governance/admin", element: <GovernanceAdminControls />, handle: { title: "Admin Controls", category: "Governance" } },
        ],
      },

      // ═══════════════════════════════════════════════════════════════
      // DEVELOPER TOOLS
      // ═══════════════════════════════════════════════════════════════
      {
        path: "/dev/integration",
        element: (
          <UnifiedRouteGuard>
            <IntegrationDashboard />
          </UnifiedRouteGuard>
        ),
        handle: { accessPolicy: tenantAdminPolicy("dev.integration") },
      },
    ],
  },
  { path: "*", element: <NotFound /> },
]);
