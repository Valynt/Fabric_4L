# ValuePilot — Route Map & Application Guide

## Application Architecture

| Property | Value |
|----------|-------|
| **Framework** | React 18 + TypeScript |
| **Routing** | React Router v7 (HashRouter) |
| **Styling** | Tailwind CSS 3.4 + shadcn/ui |
| **Theme** | oklch() color space, light/dark toggle |
| **Deployment** | Static (HashRouter for SPA compatibility) |

---

## Route Overview

```
/                                    ProspectSetup
  /intelligence                      ProspectIntelligence
  /ai-model                          AIGeneratedModel
  /driver-tree                       ValueDriverTree
  /evidence                          EvidenceMatch
  /calculator                        ValueCalculator
  /value-case                        GeneratedValueCase
  /personal                          PersonalScreen
  /organization                      OrganizationScreen
  /security                          SecurityScreen
  /configuration                     ConfigurationScreen
  /operations                        OperationsScreen
```

All routes are rendered inside the `Layout` component which provides the collapsible sidebar, header breadcrumb, step progress bar, and theme toggle.

---

## Workflow Routes (Value Modeling Pipeline)

### `/` — Prospect Setup
**Component**: `ProspectSetup.tsx`  
**Step**: 1 of 7

The entry point for creating a new value model. The user enters minimal prospect information (company + contact), and the system enriches the rest from connected CRM and public data sources.

**State**: Local `useState` for form fields (`company`, `contact`, `title`) and an `isAnalyzing` loading state.

**Key UI Elements**:
- Hero section with app branding and description
- Input card with Company Name (required), Main Contact (required), Contact Title
- AI enrichment signals: "Company: 12K employees, $4.2B revenue", "CRM: Opportunity found", "Stakeholders: 6 mapped"
- "Generate Value Model" CTA button with loading spinner
- "Save as draft" secondary action
- Recent Prospect Models grid (3 cards: Meridian, Continental, Magna Steyr)

**Navigation**: Clicking "Generate" sets `isAnalyzing=true`, then after 1.5s navigates to `/intelligence`.

---

### `/intelligence` — Prospect Intelligence
**Component**: `ProspectIntelligence.tsx`  
**Step**: 2 of 7

AI-enriched prospect profile auto-generated from CRM, public data, and the ontology. Displays pain signals, stakeholder mapping, and ontology-to-product matching.

**State**: `activeSection` tab ("pain" | "stakeholders" | "ontology"), local data arrays.

**Data**:
- 5 pain signals with confidence scores (72–96%) and data sources
- 6 stakeholders with influence/interest scoring mapped to a 2-axis grid
- 5 ontology matches mapping Axiom Forge X1 capabilities to Meridian's pain points

**Key UI Elements**:
- 4 summary stat cards: Company info, Headcount, Assembly Lines, CRM Opportunity
- 3 tab buttons: Pain Signals (5), Stakeholder Map (6), Ontology Match (5)
- "Generate AI Value Model" CTA
- Pain signals list with confidence progress bars
- Stakeholder table with influence/interest mini-charts
- Ontology match cards with relevance scores

**Navigation**: "Generate AI Value Model" → `/ai-model`

---

### `/ai-model` — AI Generated Model
**Component**: `AIGeneratedModel.tsx`  
**Step**: 3 of 7

The AI generates 5 value hypotheses from the prospect profile and ontology. Each hypothesis is presented as an "approve / modify / skip" card. The system calculates approved value totals in real-time.

**State**: `hypotheses` array with `status: "suggested" | "approved" | "modified" | "rejected"`, `generating` boolean for regenerate animation.

**Key UI Elements**:
- 4 stat cards: AI Hypotheses count, Approved count, Approved Value ($M), Avg Confidence (%)
- 5 hypothesis cards, each with:
  - Circular confidence gauge (SVG)
  - IF/THEN hypothesis statement
  - Expected annual value
  - Matched pain signal and evidence count
  - Approve / Modify / Skip action buttons
  - Status badges for reviewed items
- "Regenerate" and "Build Driver Tree" CTAs

**Navigation**: "Build Driver Tree" → `/driver-tree`

---

### `/driver-tree` — Value Driver Tree
**Component**: `ValueDriverTree.tsx`  
**Step**: 4 of 7

Hierarchical value decomposition: 1 Goal → 5 Drivers → 12 Levers. Each node shows its value, formula, and source. Users can expand/collapse nodes and review formula details.

**State**: `tree` (nested recursive structure with `expanded` flags), `rightPanel` ("formula" | "validation").

**Key UI Elements**:
- Tree view with drag handles, expand/collapse chevrons, type badges (G/D/L)
- AI-generated sparkle indicators on nodes
- Inline validation banner: "Tree validated — 5 drivers, 12 levers"
- Right panel: Formula Inspector or Driver Validation view
- Value Distribution bar chart (top 5 drivers as %)
- "Add Driver" / "Add Lever" buttons

**Navigation**: "Match Evidence" → `/evidence`

---

### `/evidence` — Evidence Match
**Component**: `EvidenceMatch.tsx`  
**Step**: 5 of 7

Evidence library auto-mapped to driver tree levers. 8 evidence items with tier classification (proof/supporting), confidence scores, and AI mapping indicators.

**State**: `selectedId`, `search`, `filter` ("all" | "mapped").

**Data**: 8 evidence items from BMW Annual Report, Fraunhofer IPA, Universal Robots, MIT Sloan, Axiom Pilot, NAM, JD Power, IFR.

**Key UI Elements**:
- 4 stat cards: Total Evidence, AI Mapped, Proof Points, Avg Confidence
- Search bar with filter toggle (All / AI Mapped)
- Evidence list with tier badges, mapped driver, confidence %
- Detail panel: statement text, source, circular confidence gauge, AI mapping, Verify/Re-score actions

**Navigation**: "Value Calculator" → `/calculator`

---

### `/calculator` — Value Calculator
**Component**: `ValueCalculator.tsx`  
**Step**: 6 of 7

Scenario modeling with 3 scenarios (Conservative / Expected / Optimistic) across 6 value levers. Each lever has adjustable sliders with AI-pre-filled values from the prospect profile.

**State**: `values` (per-lever A/B values), `scenario` ("A" | "B" | "C").

**Key UI Elements**:
- 3 scenario cards showing total $M with selection highlight
- 6 lever rows with: confidence indicator, name, slider (min/max), base value, scenario value, $M total
- Right panel: total value, lever breakdown bars, confidence range bar

**Navigation**: Not wired (final step before Value Case generation)

---

### `/value-case` — Generated Value Case
**Component**: `GeneratedValueCase.tsx`  
**Step**: 7 of 7

Final deliverable: auto-generated value case with 3-year projections, ROI metrics, model quality score, and recommended next steps.

**Data**: 5 ranked value areas with detailed breakdowns, 3-year projections (3 scenarios), model quality score (82/100).

**Key UI Elements**:
- 4 KPI cards: 3-Year Value ($44.6M), ROI (285%), Payback (12mo), Confidence (82%)
- Insight banner: "Labor Cost Reduction is #1 Value Driver" ($6.2M / 42%)
- 5 ranked result cards with sub-lever breakdowns and evidence citations
- 3-Year Value Projection bar chart (Conservative/Expected/Optimistic)
- Model Quality circular score with sub-dimensions
- AI-Generated Insights panel
- Recommended Next Steps with priority indicators
- "Open in Decision Studio" CTA
- Export actions: Print, PDF, PPT, Share

---

## Governance & Settings Routes

### `/personal` — Personal Settings
**Component**: `PersonalScreen.tsx`

5-tab personal settings: Profile, Preferences, Notifications, Connected Accounts, Sessions & Devices.

**Tabs**:
| Tab | Content |
|-----|---------|
| Profile | Avatar, name, title, team, email, phone, timezone |
| Preferences | Theme (light/dark), density, landing page, currency, units, AI tone |
| Notifications | Per-channel toggles: Email (5), In-App (4), Slack (2) |
| Connected Accounts | Google, Microsoft, Slack, Salesforce, HubSpot — connect/disconnect |
| Sessions | Device list with revoke, sign-out-all action |

---

### `/organization` — Organization Settings
**Component**: `OrganizationScreen.tsx`

6-tab workspace governance: Workspace Profile, Members & Teams, Roles & Permissions, Policies, Usage & Plans, Customization.

**Tabs**:
| Tab | Content |
|-----|---------|
| Workspace Profile | Logo, name, domain, business unit, region, language, timezone, defaults |
| Members & Teams | 5 members table with roles/status, 4 team cards |
| Roles & Permissions | Admin, Value Engineer, Viewer roles with descriptions and member counts |
| Policies | 5 active policies: data retention, sharing, export, AI usage, approval requirements |
| Usage & Plans | Enterprise plan quotas (seats, models, storage), API usage meters |
| Customization | 3 custom fields, 4 workflow stage labels |

---

### `/security` — Security Settings
**Component**: `SecurityScreen.tsx`

6-tab security configuration: Authentication, Identity Provisioning, Data Protection, Sharing Controls, API & Service Access, Audit & Compliance.

**Tabs**:
| Tab | Content |
|-----|---------|
| Authentication | SSO (SAML, OIDC), MFA (TOTP, SMS, WebAuthn), password policy, session timeout |
| Identity Provisioning | SCIM, JIT provisioning, group mapping, deprovisioning rules |
| Data Protection | Classification (public/internal/confidential), retention (7yr models, 3yr evidence), encryption, backups |
| Sharing Controls | Default visibility (workspace), external sharing (disabled), link expiry, watermarking |
| API & Service Access | OAuth 2.0 apps, API keys with scopes, rate limits, webhook audit |
| Audit & Compliance | Activity log table, compliance standards (SOC2, ISO 27001, GDPR), scheduled reports |

---

### `/configuration` — Configuration Settings
**Component**: `ConfigurationScreen.tsx`

8-tab system configuration: Integrations, Agents & AI, Ontology & Packs, Formulas & Models, Workflow Configuration, Reports & Delivery, Notifications & Automations, Feature Controls.

**Tabs**:
| Tab | Content |
|-----|---------|
| Integrations | 6 CRM/ERP connectors (Salesforce, HubSpot, SAP, NetSuite, Workday, Snowflake), status, sync settings |
| Agents & AI | 5 AI agents with status/toggles, model selection, temperature, max tokens |
| Ontology & Packs | 3 installed packs, 8 total, version management, custom ontology editor |
| Formulas & Models | 6 formula categories, 3 custom formulas, formula editor |
| Workflow Configuration | 7-stage pipeline, SLA timers, auto-advance rules, required approvals |
| Reports & Delivery | 4 report templates (Value Case, Executive Summary, TCO Analysis, ROI Report), scheduling |
| Notifications & Automations | 8 trigger types, 6 action types, sample automations |
| Feature Controls | 6 feature flags (Beta AI Models, Evidence Marketplace, Decision Studio, etc.) |

---

### `/operations` — Operations
**Component**: `OperationsScreen.tsx`

4-tab operational monitoring: Sync Health, Jobs & Queues, System Events, Tenant Observability.

**Tabs**:
| Tab | Content |
|-----|---------|
| Sync Health | 8 system integrations with status badges, 6 AI agent connectors with query volumes, sync preferences |
| Jobs & Queues | 7 active jobs with progress bars and filters, 4 scheduled recurring jobs |
| System Events | 10 event log entries with severity filtering, 4 summary metric cards |
| Tenant Observability | 4 KPI cards, 6 component health rows, compute usage chart, API endpoint breakdown, plan quotas |

---

## Layout & Shared Components

### `Layout.tsx` — Shell Component
The root layout wrapping all routes via `<Outlet />`.

**Responsibilities**:
- Collapsible sidebar (260px expanded → 56px collapsed, 300ms transition)
- Theme toggle (light/dark, persisted to localStorage)
- Breadcrumb navigation (workflow vs. governance context)
- Step progress bar (workflow routes only)
- Notification bell with unread indicator

**Sidebar Sections**:
| Section | Items |
|---------|-------|
| Company Header | Logo, name, "Enterprise", dropdown chevron |
| Search | Input with Command+K shortcut |
| Workflow (collapsible) | 7 step navigation items |
| Governance & Settings (collapsible) | 5 settings categories |
| Co-Pilot Card | Context-aware AI assistant prompt |
| Bottom Nav | Support, Feedback |
| User Profile | Avatar, name, email, dropdown (Profile/Settings/Sign Out) |

**Theme System**:
- CSS variables in `oklch()` color space
- `dark` class on `<html>` toggles between light/dark palettes
- Preference saved to `localStorage` key `vp-theme`
- Defaults to system `prefers-color-scheme` on first visit

---

## State Management

| Scope | Approach |
|-------|----------|
| Route-level state | `useState` (no global state library) |
| Form inputs | Controlled components with `useState` |
| Tab selection | `useState<string>` for active tab ID |
| Theme | `useState` + `localStorage` + DOM class toggle |
| Sidebar collapsed | `useState<boolean>` |
| Sidebar section open/close | `useState<boolean>` per section |
| URL/routing | React Router `useLocation`, `useNavigate` |

No external state management library is used. All state is local to components or passed via props where needed.

---

## Data Flow

```
ProspectSetup (input)
  ↓
ProspectIntelligence (AI enrichment)
  ↓
AIGeneratedModel (hypothesis generation)
  ↓
ValueDriverTree (hierarchical decomposition)
  ↓
EvidenceMatch (evidence mapping)
  ↓
ValueCalculator (scenario modeling)
  ↓
GeneratedValueCase (final deliverable)
```

Each step is **independent** — there is no shared state between routes. Data is hardcoded as mock data within each component. In a production implementation, this would be replaced with:
- API calls to a backend service
- React Query or SWR for server state
- A global store (Zustand/Redux) for cross-route state

---

## File Structure

```
src/
├── App.tsx                    # Router definition (12 routes)
├── main.tsx                   # Entry point with theme init
├── index.css                  # oklch theme variables
├── sections/
│   ├── Layout.tsx             # Root shell (sidebar + header)
│   ├── ProspectSetup.tsx      # Step 1
│   ├── ProspectIntelligence.tsx  # Step 2
│   ├── AIGeneratedModel.tsx   # Step 3
│   ├── ValueDriverTree.tsx    # Step 4
│   ├── EvidenceMatch.tsx      # Step 5
│   ├── ValueCalculator.tsx    # Step 6
│   └── GeneratedValueCase.tsx # Step 7
└── settings/
    ├── PersonalScreen.tsx     # /personal
    ├── OrganizationScreen.tsx # /organization
    ├── SecurityScreen.tsx     # /security
    ├── ConfigurationScreen.tsx # /configuration
    └── OperationsScreen.tsx   # /operations
```
