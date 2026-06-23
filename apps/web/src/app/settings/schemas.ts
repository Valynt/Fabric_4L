/**
 * Settings & Configuration Center — Schemas
 *
 * Route schema, RBAC rules, screen definitions, and navigation model
 * for the unified Settings / Configuration Center.
 */

// ── Route Schema ──────────────────────────────────────────────────────────────

export const settingsRoutes = {
  personal: {
    label: "Personal Settings",
    basePath: "/personal",
    scope: "user" as const,
    routes: {
      profile: "/personal/profile",
      security: "/personal/security",
      preferences: "/personal/preferences",
      notifications: "/personal/notifications",
      sessions: "/personal/sessions",
    },
  },

  billing: {
    label: "Account & Billing",
    basePath: "/settings/billing",
    scope: "tenant" as const,
    routes: {
      workspace: "/settings/workspace",
      subscription: "/settings/billing/subscription",
      usage: "/settings/billing/usage",
      paymentMethods: "/settings/billing/payment-methods",
      invoices: "/settings/billing/invoices",
    },
  },

  teamAccess: {
    label: "Team & Access",
    basePath: "/settings/users",
    scope: "workspace" as const,
    routes: {
      members: "/settings/users",
      roles: "/settings/roles",
      permissions: "/settings/permissions",
      apiKeys: "/settings/api-keys",
    },
  },

  dataIntegrations: {
    label: "Data & Integrations",
    basePath: "/settings/data-sources",
    scope: "workspace" as const,
    routes: {
      dataSources: "/settings/data-sources",
      integrations: "/settings/integrations",
      variables: "/settings/variables",
      valuePacks: "/settings/value-packs",
      ingestionRules: "/settings/ingestion-rules",
    },
  },

  governance: {
    label: "Governance",
    basePath: "/settings/governance",
    scope: "admin" as const,
    routes: {
      policies: "/settings/governance/policies",
      compliance: "/settings/governance/compliance",
      health: "/settings/governance/health",
      auditTrail: "/settings/governance/audit",
      adminControls: "/settings/governance/admin",
    },
  },
} as const;

// ── RBAC Schema ───────────────────────────────────────────────────────────────

export const settingsAccessRules = {
  personal: {
    scope: "user" as const,
    capability: "personal" as const,
    allowedRoles: ["super_admin", "tenant_admin", "content_admin", "analyst", "read_only", "admin", "advanced", "standard", "viewer", "user"],
    rule: "All authenticated users can manage their own personal settings.",
    restrictions: [
      "Tenant admins cannot edit another user's personal preferences.",
      "Impersonation requires a dedicated audit workflow.",
    ],
  },

  billing: {
    scope: "tenant" as const,
    capability: "billing" as const,
    allowedRoles: ["super_admin", "tenant_admin", "admin"],
    rule: "Tenant admins and super admins can access billing and workspace controls.",
    restrictions: [
      "Standard users should not see payment methods.",
      "Editors and viewers should not see subscription controls.",
    ],
  },

  teamAccess: {
    scope: "workspace" as const,
    capability: "team" as const,
    allowedRoles: ["super_admin", "tenant_admin", "admin"],
    partialAccess: {
      editor: ["members:view"],
      viewer: [],
    },
    rule: "Admins manage members, roles, permissions, and API keys.",
    restrictions: [
      "Read-only and viewer roles may inspect team membership, role, and policy matrices but cannot mutate.",
      "Editors may view members but cannot grant roles or assign policy controls.",
      "Only admins can create tenant-wide API keys.",
    ],
  },

  dataIntegrations: {
    scope: "workspace" as const,
    capability: "integrations" as const,
    allowedRoles: ["super_admin", "tenant_admin", "admin"],
    partialAccess: {
      editor: ["sources:view", "variables:view", "value_packs:view"],
      viewer: [],
    },
    rule: "Admins configure data sources, integrations, variables, ingestion rules, and value packs.",
    restrictions: [],
  },

  governance: {
    scope: "admin" as const,
    capability: "governance" as const,
    allowedRoles: ["super_admin", "tenant_admin", "content_admin", "admin"],
    rule: "Governance controls are restricted to tenant admins, content admins, and super admins.",
    restrictions: [
      "Audit trail is read-only for most admins.",
      "Policy edits require elevated permissions.",
    ],
  },

  superAdmin: {
    scope: "admin" as const,
    capability: "super_admin" as const,
    allowedRoles: ["super_admin"],
    rule: "Platform-level super-admin operations are restricted to the super admin role.",
    restrictions: [],
  },
} as const;

// ── Screen Schema ─────────────────────────────────────────────────────────────

export interface SettingsScreenCard {
  title: string;
  description?: string;
  fields?: string[];
  type?: "table" | "form" | "cards";
  columns?: string[];
  roles?: string[];
  integrations?: string[];
  packs?: string[];
}

export interface SettingsScreen {
  id: string;
  title: string;
  category: string;
  route: string;
  scope: string;
  subnav: string[];
  primaryActions?: string[];
  summaryMetrics?: string[];
  cards: SettingsScreenCard[];
}

export const settingsScreens: SettingsScreen[] = [
  {
    id: "personal-profile",
    title: "User Profile & Personal Preferences",
    category: "Personal Settings",
    route: "/personal/profile",
    scope: "user",
    subnav: [
      "Profile Information",
      "Security & Authentication",
      "Preferences",
      "Notifications",
      "Active Sessions",
    ],
    primaryActions: ["Save profile", "Change avatar"],
    cards: [
      {
        title: "Profile Information",
        description: "Name, avatar, email, and account identity.",
        fields: ["Full name", "Email", "Title", "Default workspace"],
      },
      {
        title: "Security & Authentication",
        description: "SSO, password, MFA, and linked accounts.",
        fields: ["MFA", "Google SSO", "Password", "Authenticator app"],
      },
      {
        title: "Preferences",
        description: "Theme, localization, and notifications.",
        fields: ["Theme", "Language", "Email alerts", "In-app alerts"],
      },
    ],
  },

  {
    id: "account-billing",
    title: "Account & Billing Configuration",
    category: "Account & Billing",
    route: "/settings/billing",
    scope: "tenant",
    subnav: [
      "Workspace",
      "Subscription",
      "Usage",
      "Payment Methods",
      "Invoices",
    ],
    summaryMetrics: ["Current Plan", "LLM Usage", "Next Invoice"],
    cards: [
      {
        title: "Workspace Management",
        description:
          "Name, domain, account picker behavior, and workspace switching.",
        fields: [
          "Workspace name",
          "Verified domain",
          "Default industry pack",
          "Tenant ID",
        ],
      },
      {
        title: "Usage Dashboard",
        fields: ["API calls", "LLM tokens", "Ingestion jobs"],
      },
      {
        title: "Billing Management",
        fields: ["Payment method", "Invoice history", "Billing contact"],
      },
    ],
  },

  {
    id: "team-access",
    title: "Team & Access Configuration",
    category: "Team & Access",
    route: "/settings/users",
    scope: "workspace",
    subnav: ["Members", "Invitations", "Roles", "Permissions", "API Keys"],
    primaryActions: ["Invite user", "Assign role", "Assign policy", "Create API key"],
    cards: [
      {
        title: "Team Members",
        description: "Member lifecycle management: invite, deactivate, reactivate, and inspect status.",
        type: "table",
        columns: ["User", "Role", "Status", "Action"],
      },
      {
        title: "Role Definition & Assignment",
        description: "Define workspace roles and assign them to members.",
        roles: ["Admin", "Editor", "Viewer"],
      },
      {
        title: "Permission Matrix & Policy Assignment",
        description: "Inspect capability matrix and assign policy controls per surface.",
        fields: ["Members policy", "Role policy", "API key policy"],
      },
    ],
  },

  {
    id: "data-integrations",
    title: "Data & Integration Setup",
    category: "Data & Integrations",
    route: "/settings/data-sources",
    scope: "workspace",
    subnav: [
      "Data Sources",
      "Integrations",
      "Variables",
      "Value Packs",
      "Ingestion Rules",
    ],
    summaryMetrics: ["Sources", "Integrations", "Variables", "Value Packs"],
    primaryActions: ["Add source"],
    cards: [
      {
        title: "Connection Hub",
        description: "Data sources and external business systems.",
        integrations: [
          "Salesforce CRM",
          "ERP / Cost Data",
          "Google Drive",
          "Layer 1 Web Ingestion",
        ],
      },
      {
        title: "Variable Registry",
        description:
          "Reusable variables and custom fields used across formulas.",
        fields: [
          "Loaded_Annual_Cost",
          "Plant_Cycle_Time",
          "Defect_Rate",
        ],
      },
      {
        title: "Value Packs",
        description:
          "Enable industry capabilities, formulas, templates, and benchmarks.",
        packs: ["Manufacturing", "AI / Data Platform", "Financial Services"],
      },
    ],
  },
];

// ── Navigation Model ──────────────────────────────────────────────────────────

export interface SettingsNavItem {
  label: string;
  icon: string;
  path: string;
  scope: string;
  children: SettingsNavChild[];
}

export interface SettingsNavChild {
  label: string;
  path: string;
}

export const settingsNavigation: SettingsNavItem[] = [
  {
    label: "Personal Settings",
    icon: "User",
    path: "/personal/profile",
    scope: "user",
    children: [
      { label: "Profile", path: "/personal/profile" },
      { label: "Security", path: "/personal/security" },
      { label: "Preferences", path: "/personal/preferences" },
      { label: "Notifications", path: "/personal/notifications" },
      { label: "Active Sessions", path: "/personal/sessions" },
      { label: "My Activity", path: "/personal/activity" },
    ],
  },
  {
    label: "Account & Billing",
    icon: "CreditCard",
    path: "/settings/billing",
    scope: "tenant",
    children: [
      { label: "Workspace", path: "/settings/workspace" },
      { label: "Subscription", path: "/settings/billing/subscription" },
      { label: "Usage", path: "/settings/billing/usage" },
      { label: "Payment Methods", path: "/settings/billing/payment-methods" },
      { label: "Invoices", path: "/settings/billing/invoices" },
    ],
  },
  {
    label: "Team & Access",
    icon: "Users",
    path: "/settings/users",
    scope: "workspace",
    children: [
      { label: "Members", path: "/settings/users" },
      { label: "Roles", path: "/settings/roles" },
      { label: "Permissions", path: "/settings/permissions" },
      { label: "API Keys", path: "/settings/api-keys" },
    ],
  },
  {
    label: "Data & Integrations",
    icon: "Database",
    path: "/settings/data-sources",
    scope: "workspace",
    children: [
      { label: "Data Sources", path: "/settings/data-sources" },
      { label: "Integrations", path: "/settings/integrations" },
      { label: "Variables", path: "/settings/variables" },
      { label: "Value Packs", path: "/settings/value-packs" },
      { label: "Ingestion Rules", path: "/settings/ingestion-rules" },
    ],
  },
  {
    label: "Governance",
    icon: "Shield",
    path: "/settings/governance/policies",
    scope: "admin",
    children: [
      { label: "Policies", path: "/settings/governance/policies" },
      { label: "Compliance", path: "/settings/governance/compliance" },
      { label: "Health", path: "/settings/governance/health" },
      { label: "Audit Trail", path: "/settings/governance/audit" },
      { label: "Admin Controls", path: "/settings/governance/admin" },
    ],
  },
];

// ── Category Tabs (horizontal) ────────────────────────────────────────────────

export const settingsCategories = [
  { key: "personal", label: "Personal", basePath: "/personal", scope: "user" },
  {
    key: "billing",
    label: "Account & Billing",
    basePath: "/settings/billing",
    scope: "tenant",
  },
  {
    key: "teamAccess",
    label: "Team & Access",
    basePath: "/settings/users",
    scope: "workspace",
  },
  {
    key: "dataIntegrations",
    label: "Data & Integrations",
    basePath: "/settings/data-sources",
    scope: "workspace",
  },
  {
    key: "governance",
    label: "Governance",
    basePath: "/settings/governance",
    scope: "admin",
  },
] as const;

export type SettingsCategoryKey = (typeof settingsCategories)[number]["key"];

export type SettingsCapabilityKey =
  (typeof settingsAccessRules)[keyof typeof settingsAccessRules]["capability"];

export type SettingsCapability = SettingsCapabilityKey;

export const orderedCapabilities: SettingsCapability[] = [
  "personal",
  "billing",
  "team",
  "integrations",
  "governance",
  "super_admin",
];

export const settingsCapabilityRoutePrefixes: Array<{
  capability: SettingsCapabilityKey;
  prefixes: readonly string[];
}> = [
  { capability: "personal", prefixes: ["/personal"] },
  {
    capability: "billing",
    prefixes: ["/settings/workspace", "/settings/billing"],
  },
  {
    capability: "team",
    prefixes: [
      "/settings/users",
      "/settings/roles",
      "/settings/permissions",
      "/settings/api-keys",
    ],
  },
  {
    capability: "integrations",
    prefixes: [
      "/settings/data-sources",
      "/settings/integrations",
      "/settings/variables",
      "/settings/value-packs",
      "/settings/ingestion-rules",
    ],
  },
  { capability: "governance", prefixes: ["/settings/governance"] },
] as const;

export function getSettingsCapabilityForPath(
  path: string
): SettingsCapabilityKey | undefined {
  return settingsCapabilityRoutePrefixes.find((group) =>
    group.prefixes.some((prefix) => path.startsWith(prefix))
  )?.capability;
}

export function getCapabilitiesForRole(role: string | null | undefined): Set<SettingsCapability> {
  const normalized = (role ?? "").trim().toLowerCase();
  const capabilities = new Set<SettingsCapability>();
  for (const rule of Object.values(settingsAccessRules)) {
    if ((rule.allowedRoles as readonly string[]).includes(normalized)) {
      capabilities.add(rule.capability);
    }
  }
  return capabilities.size > 0 ? capabilities : new Set<SettingsCapability>(["personal"]);
}

export const governanceAdminControlMetrics = [
  { key: "tenantStatus", label: "Tenant status" },
  { key: "mfaRequirement", label: "MFA requirement" },
  { key: "sessionTimeout", label: "Session timeout" },
  { key: "auditTrail", label: "Audit trail feature" },
] as const;
