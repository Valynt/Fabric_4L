# ValuePilot — Refactor Changelog

## Phase 8: ProspectSetup Simplified — Launchpad Intake (Corrected Direction)
Radical simplification following the principle: **minimal intake + smart confirmation**, not governance dashboard.

### What changed
- **Removed right rail entirely** — Model Readiness meter, Improvement Opportunities, Auto-Enriched Data tiles, Model Construction Status panel all gone
- **Removed heavy "Value Model Inputs" card** — Replaced with compact inline Setup Status Strip (lightweight pills, not a card)
- **No "Model Readiness" language** — No percentages, no scoring, no evaluation framing on step 1
- **No full-width top progress bar** — Removed from Layout.tsx
- **No header step dots** — Removed the circle indicators from the header right area
- **Future sidebar steps muted** — Steps beyond the current one are visually dimmed (opacity-40)

### New structure (single-threaded flow)
1. **Step Label** — "STEP 1 OF 7" with subtle underline accent
2. **Hero** — "Construct a Value Model" (42px) with calm, confident subtitle
3. **Setup Status Strip** — Compact pills: ✓ Company, ✓ Primary Contact, ~ Buyer Role (inferred), ⚠ Primary Objective (needed)
4. **Prospect Context Card** (20px radius, 28px padding):
   - Company Name (single, full-width, 56px height)
   - Main Contact + Contact Title (2-column split)
   - Primary Objective (required, 5 selectable radio tiles: Reduce costs, Increase revenue, Improve efficiency, Mitigate risk, Custom…)
   - Inline validation: "Choose the main outcome so we can shape the model correctly."
5. **Inline Intelligence Cards** (lightweight, assistive, NOT dashboard tiles):
   - Buyer Role Detected — inferred role with Confirm/Adjust actions
   - Company Profile Found — enrichment data with Confirm/Edit actions
   - CRM Opportunity Found — Salesforce record with Review/Ignore actions
6. **Action Row** — "Continue to Intelligence →" (primary) + "Save draft" (secondary)
7. **Optional missing-inputs cue** — Subtle inline list only when required fields are empty

### Tone shift
- Before: "Each input directly affects model credibility" (clinical, system-centric)
- After: "Start with the company and primary contact. ValuePilot will enrich the rest and highlight anything that needs confirmation." (guided, co-pilot feel)

## Phase 6: Model Construction Completeness (New Block Components)
- **`ModelInputsTracker`** — Persistent summary panel showing 5 critical inputs (Company, Contact, Buyer Role, Primary Objective, Financial Baseline) with 3 status states: Complete (green ✓), Inferred (blue ~), Missing (amber ⚠). Collapsible, always-visible, click-to-jump.
- **`ModelReadinessMeter`** — Progressive gating meter (0-100%) with color-coded states: red (<50), amber (50-79), green (80+). Shows contextual message + improvement opportunities with point values (e.g., "Define primary objective +15%"). Compact and full variants.

## Phase 7: ProspectSetup Redesign — Completeness-First UX
Complete rewrite of the Prospect Setup screen with 6 UX principles:

1. **"Model Inputs" Layer** — `ModelInputsTracker` sits directly below the header, always visible. Shows 2 Complete, 2 Inferred, 1 Missing at initial state. Never feels like a form — feels like system state.

2. **Progressive Gating** — Readiness flows 70% → 90% → 100%:
   - 70%: "Model will be usable but has gaps" (amber)
   - 90%: "Model is well-supported. Generate when ready." (green)
   - 100%: Generate button fully enabled

3. **Inline Intelligence Prompts** —
   - **Buyer Role Detected**: Brain circuit icon, shows inferred "Economic Buyer" with likely priorities, Confirm/Adjust actions
   - **Primary Objective**: Expandable picker with 5 AI-suggested objectives based on company + role context ("Reduce production downtime", "Improve plant throughput", etc.)

4. **Model Integrity Feedback** — Readiness meter with specific improvement opportunities: "Confirm buyer role +10%", "Define primary objective +15%"

5. **Smart Defaults + Explicit Overrides** — Auto-Enriched Data panel with actionable chips: "12K employees, $4.2B revenue" with **Confirm?** action, "MAC-2026-0417 found" with **Review?** action

6. **Communication Shift** — No "Required" labels. Instead: "Affects model accuracy", "Strongly recommended", "Each input directly affects model credibility"

7. **Model Construction Status** — Three-section panel: What we know / What we're assuming / What's missing

## Phase 1: Infrastructure
- Created `STANDARDS.md` — global standards for component architecture, naming, design tokens, accessibility, and code quality
- Created `ROADMAP.md` — complete inventory of all 10 routes, 60+ UI components, dead code, and phased refactor plan
- Established three-tier component hierarchy:
  - `components/ui/` — raw shadcn primitives (untouched)
  - `components/primitives/` — design system defaults (ErrorBoundary, ErrorFallback)
  - `components/blocks/` — product compositions (StatCard, StatusBadge, ProgressBar, SectionCard, TabNav)
- Removed 6 dead code files: `App.css`, `Home.tsx`, `ConfigurationScreen.tsx`, `OrganizationScreen.tsx`, `PersonalScreen.tsx`, `SecurityScreen.tsx`

## Phase 2: Shared Block Components
- **`StatCard`** — icon + label + value + sublabel, used across all 7 workflow pages
- **`StatusBadge`** — 11 states (connected, active, warning, error, paused, completed, queued, running, failed, degraded, healthy), used in Setup and Operations
- **`ProgressBar`** — SVG-free, configurable size/color, used in Intelligence, AI Model, Calculator, Operations
- **`SectionCard`** — consistent card wrapper with optional header, description, icon, and action slot, used everywhere
- **`TabNav`** — accessible vertical/horizontal tab navigation with ARIA roles, used in Setup, Settings, Operations
- Barrel exports via `components/blocks/index.ts`

## Phase 3: Page Refactors
All 10 pages updated with:
- Semantic HTML (`<main>`, `<section>`, `<header>`, `<aside>`, `<article>`)
- Proper heading hierarchy (h1 → h2 → h3)
- Shared block components replacing ad-hoc markup
- Named exports consistently used

### Specific changes:
- **Layout.tsx** — collapsible sidebar (260px ↔ 56px rail, 300ms transition), semantic HTML, company header, search, user profile dropdown, theme toggle
- **ProspectSetup** — uses SectionCard
- **ProspectIntelligence** — uses StatCard, SectionCard, ProgressBar
- **AIGeneratedModel** — uses StatCard
- **ValueDriverTree** — uses SectionCard
- **EvidenceMatch** — uses StatCard, SectionCard, StatusBadge
- **ValueCalculator** — uses SectionCard, ProgressBar
- **GeneratedValueCase** — uses StatCard, SectionCard, ProgressBar
- **SetupScreen** — uses SectionCard, StatusBadge, TabNav
- **SettingsScreen** — uses TabNav
- **OperationsScreen** — uses SectionCard, StatusBadge, ProgressBar, TabNav

## Phase 4: Component API Standardization
- All blocks accept `className` prop via `cn()` for style extensions
- Consistent sizing variants (`sm` | `md`) on ProgressBar, StatusBadge
- SectionCard enhanced with `icon` prop for header icons
- StatusBadge supports custom `label` override
- Added `components/primitives/index.ts` barrel exports

## Phase 5: Cross-Cutting Concerns
- **`ErrorBoundary`** — class component wrapper catching render errors, shows fallback UI with error message, Try Again, and Go Home actions
- **`NotFound`** — 404 page with 404 code, back navigation, and dashboard link
- **Catch-all route** — `*` route in App.tsx renders NotFound within Layout
- **Build** — zero TypeScript errors, zero warnings, clean Vite production build

## Deployment
- Deployed to production (static hosting via HashRouter)
- All routes tested and functional
