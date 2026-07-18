# Three-Tier UX Model Specification

## Overview

The Three-Tier UX Model implements **progressive disclosure** in the Value Fabric Platform, ensuring users see only the complexity appropriate to their role and expertise level.

**Design Philosophy:**
- **Tier 1 (Standard):** Simplified flows for business users who need quick insights
- **Tier 2 (Advanced):** Power-user tools for analysts and modelers who need granular control
- **Tier 3 (Admin):** Governance controls for administrators who manage tenant configuration

---

## Tier Structure

### Tier 1: Standard Users

**Target Audience:**
- Business executives
- Sales representatives
- Customer success managers
- General business users

**Available Features:**
| Feature | Description |
|---------|-------------|
| **Command Center** | Overview dashboard with key metrics and quick actions |
| **Value Packs** | Pre-built value models and templates |
| **Business Cases** | ROI analysis workflows and case management |
| **Research** | Account management and data source overview |
| **Evidence** | Decision traces and audit trails (read-only) |
| **Settings** | User preferences and profile management |

**UI Characteristics:**
- Simplified navigation with 5-7 top-level items
- Pre-configured workflows with minimal customization
- Visual summaries over detailed data tables
- Guided wizards for complex tasks
- Hide internal mechanics (formulas, graph queries, etc.)

### Tier 2: Advanced Users

**Target Audience:**
- Business analysts
- Value engineers
- Solution architects
- Data scientists

**Available Features:**
| Feature | Description | Progressive Disclosure |
|---------|-------------|----------------------|
| **Extraction Engine** | Data extraction and processing pipelines | Hidden from Tier 1 |
| **Value Tree Explorer** | Interactive value tree visualization | Toggle-enabled |
| **Formula Studio** | Formula authoring and testing | Toggle-enabled |
| **Graph Explorer** | Knowledge graph visualization | Hidden from Tier 1 |
| **Ontology Browser** | Entity types and relationship definitions | Hidden from Tier 1 |
| **Agent Workflows** | AI agent orchestration (full access) | Enhanced controls |
| **Audit & Provenance** | Full audit trails with lineage | Enhanced details |

**UI Characteristics:**
- Expanded navigation with 8-10 items
- Direct access to underlying models
- Raw data tables alongside visualizations
- Query builders and custom filters
- Formula editing capabilities

**Advanced Mode Toggle:**
- Standard users can temporarily enable Advanced Mode
- Persists across sessions (stored in localStorage)
- Can be disabled to return to simplified view
- Visual indicator shows when Advanced Mode is active

### Tier 3: Admin Users

**Target Audience:**
- Tenant administrators
- Governance officers
- System integrators
- Pack authors

**Available Features:**
| Feature | Description | Governance Purpose |
|---------|-------------|-------------------|
| **Formula Governance** | Formula lifecycle management (registry, versions, approvals) | Quality control |
| **Benchmark Policies** | Industry benchmark and policy configuration | Standardization |
| **Variable Registry** | Variable definitions and source bindings | Data integrity |
| **Data Sources** | Full data source configuration | System integration |
| **Pack Management** | Value pack authoring and distribution | Content management |
| **Permissions** | Role-based access control and teams | Security |
| **Audit / Change Log** | System-wide audit and change tracking | Compliance |
| **System Settings** | Tenant-wide configuration | Platform management |

**UI Characteristics:**
- Comprehensive navigation with all system features
- Bulk operations and batch editing
- Configuration wizards for complex setups
- Health monitoring and diagnostic tools
- Governance workflows with approval queues

---

## Implementation Architecture

### Component Structure

```
frontend/client/src/
├── components/
│   └── navigation/
│       └── TieredNav.tsx          # Three-tier navigation component
├── pages/
│   └── admin/
│       ├── FormulaGovernance.tsx  # Tier 3: Formula management
│       ├── BenchmarkPolicies.tsx  # Tier 3: Benchmark configuration
│       └── VariableRegistry.tsx   # Tier 3: Variable catalog
├── stores/
│   └── userTierStore.ts           # Role and tier state management
└── App.tsx                        # Tier-based routing with RouteGuard
```

### State Management

**User Tier Store (`userTierStore.ts`):**
```typescript
interface UserTierState {
  currentTier: "standard" | "advanced" | "admin";
  isAdvancedModeEnabled: boolean;
  userRole: string | null;
  permissions: UserPermissions;
  
  // Actions
  setTier: (tier: UserTier) => void;
  toggleAdvancedMode: () => void;
  canAccessRoute: (routeTier: UserTier) => boolean;
  canAccessFeature: (feature: keyof UserPermissions) => boolean;
  
  // Computed
  effectiveTier: UserTier;
  isPrivileged: boolean;
}
```

**Persistence:**
- User tier and role stored in localStorage via Zustand persist
- Advanced Mode toggle persists across sessions
- Server-side role validation on API calls

### Route Protection

**RouteGuard Component:**
```typescript
function RouteGuard({ 
  children, 
  requiredTier = "standard" 
}: { 
  children: React.ReactNode; 
  requiredTier?: UserTier;
}) {
  const canAccessRoute = useUserTierStore(state => state.canAccessRoute);
  const routeTier = getRouteTier(location);
  
  if (!canAccessRoute(routeTier)) {
    return <Redirect to="/command-center" />;
  }
  
  return <>{children}</>;
}
```

**Route Tier Mapping:**
| Route Pattern | Required Tier |
|--------------|---------------|
| `/command-center` | standard |
| `/value-packs` | standard |
| `/extraction-engine` | advanced |
| `/value-trees/*` | advanced |
| `/graph/*` | advanced |
| `/ontology/*` | advanced |
| `/admin/*` | admin |

### Progressive Disclosure Patterns

**1. Navigation Collapse:**
- Advanced/Tier 3 items completely hidden in Tier 1
- Child routes filtered based on parent tier
- Breadcrumb navigation adapts to visible hierarchy

**2. Feature Hiding:**
```typescript
// In component code
const { effectiveTier } = useUserTierStore();

{effectiveTier !== "standard" && (
  <AdvancedFeaturePanel />
)}
```

**3. Simplified Alternatives:**
- Complex data tables → Visual summary cards
- Raw formula editing → Guided formula wizard
- Query builder → Pre-built filter sets

**4. Contextual Help:**
- Tier 1: Inline tooltips and guided tours
- Tier 2: Technical documentation links
- Tier 3: API reference and configuration guides

---

## Navigation Structure

### Tier 1 (Standard) Navigation

```
Command Center
Value Packs
Business Cases
├── All Cases
└── Workflow Dashboard
Research
├── Accounts
└── Ingestion Jobs
Evidence
├── Decision Traces
└── Lineage Explorer
Settings
```

### Tier 2 (Advanced) Navigation

```
Command Center
Extraction Engine
Value Models
├── Tree Explorer
├── Normalization
└── Formula Studio
Graph Explorer
├── Graph Explorer
├── Query Builder
└── Communities
Ontology
├── Entity Browser
├── Extraction Jobs
└── Validation
Agent Workflows
├── Workflow Dashboard
└── Business Cases
Audit & Provenance
├── Decision Traces
├── Lineage Explorer
└── Compliance Reports
```

### Tier 3 (Admin) Navigation

```
Command Center
Formula Governance
├── Formula Registry
├── Version History
└── Approval Queue
Benchmark Policies
├── Benchmark Library
└── Policy Config
Variable Registry
├── Variable Catalog
└── Source Bindings
Data Sources
├── Scraping Targets
└── Ingestion Jobs
Pack Management
Permissions
├── Roles & Access
└── Teams
Audit / Change Log
├── Decision Traces
└── Compliance Reports
System Settings
```

---

## Visual Design

### Tier Indicators

**Mode Pills:**
- Standard: Blue (`bg-blue-50 text-blue-700`)
- Advanced: Violet (`bg-violet-50 text-violet-700`)
- Admin: Amber (`bg-amber-50 text-amber-700`)

**Navigation Icons:**
- Standard items: Neutral grays
- Advanced items: Violet accents
- Admin items: Amber accents with "Admin" badge

**Advanced Mode Toggle:**
- Positioned in navigation footer
- Visual toggle switch with clear on/off states
- Persistent indicator in header when active

### Responsive Behavior

**Desktop (>1024px):**
- Fixed sidebar (240px) with full navigation
- Mode switcher visible at bottom
- All tiers use consistent layout

**Tablet (768-1024px):**
- Collapsible sidebar
- Tier indicator in compact header
- Touch-friendly mode toggle

**Mobile (<768px):**
- Bottom sheet navigation
- Tier switcher in settings menu
- Progressive disclosure via accordion

---

## Security Considerations

### Client-Side Protection
- Route guards prevent UI access to unauthorized tiers
- Navigation items filtered based on user tier
- Feature flags disable restricted functionality

### Server-Side Validation
- **CRITICAL:** All tier checks must be validated server-side
- API endpoints verify user role for admin operations
- Formula governance workflows require approval permissions
- Audit logs capture tier escalation attempts

### Role Mapping
| User Role | Assigned Tier | Advanced Mode |
|-----------|---------------|---------------|
| viewer | standard | Toggle-able |
| user | standard | Toggle-able |
| analyst | advanced | Always on |
| editor | advanced | Always on |
| admin | admin | Always on |

---

## Acceptance Criteria

- [x] **Navigation Reorganization:** All routes organized by tier
- [x] **Advanced Mode Toggle:** Standard users can enable/disable advanced features
- [x] **Admin Control Plane:** `/admin/*` routes with full governance controls
- [x] **Progressive Disclosure:** Complexity hidden from Tier 1 users
- [x] **Route Protection:** Tier-based access control with automatic redirects
- [x] **Visual Indicators:** Clear tier identification throughout UI
- [x] **Persistence:** User preferences survive page reloads
- [x] **Responsive Design:** Works across desktop, tablet, and mobile

---

## Future Enhancements

1. **Custom Tier Definitions:** Allow tenants to define custom role tiers
2. **Feature-Level Permissions:** Granular control beyond tier boundaries
3. **Contextual Tier Switching:** Auto-promote tier based on task context
4. **Training Mode:** Guided tours that temporarily elevate tier for learning
5. **Analytics:** Track feature usage by tier for UX optimization
