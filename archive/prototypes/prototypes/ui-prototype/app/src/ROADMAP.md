# ValuePilot — Refactor Roadmap

## Architecture Map

### Routes (11)
| # | Route | Component | Status |
|---|-------|-----------|--------|
| 1 | `/` | ProspectSetup | ✅ Refactored |
| 2 | `/intelligence` | ProspectIntelligence | ✅ Refactored |
| 3 | `/ai-model` | AIGeneratedModel | ✅ Refactored |
| 4 | `/driver-tree` | ValueDriverTree | ✅ Refactored |
| 5 | `/evidence` | EvidenceMatch | ✅ Refactored |
| 6 | `/calculator` | ValueCalculator | ✅ Refactored |
| 7 | `/value-case` | GeneratedValueCase | ✅ Refactored |
| 8 | `/setup` | SetupScreen | ✅ Refactored |
| 9 | `/settings` | SettingsScreen | ✅ Refactored |
| 10 | `/operations` | OperationsScreen | ✅ Refactored |
| 11 | `*` | NotFound | ✅ Created |
| — | Layout | Layout | ✅ Refactored |

### Components
| Directory | Count | Purpose |
|-----------|-------|---------|
| `components/ui/` | 60+ | Raw shadcn primitives (untouched) |
| `components/primitives/` | 2 | ErrorBoundary, ErrorFallback |
| `components/blocks/` | 5 | StatCard, StatusBadge, ProgressBar, SectionCard, TabNav |

### Dead Code Removed
- [x] `src/App.css`
- [x] `src/pages/Home.tsx`
- [x] `src/settings/ConfigurationScreen.tsx`
- [x] `src/settings/OrganizationScreen.tsx`
- [x] `src/settings/PersonalScreen.tsx`
- [x] `src/settings/SecurityScreen.tsx`

## Refactor Plan

### Phase 1: Infrastructure ✅
- [x] Create STANDARDS.md
- [x] Create ROADMAP.md
- [x] Create components/primitives/ (design system wrappers)
- [x] Create components/blocks/ (product compositions)
- [x] Remove dead code files

### Phase 2: Extract Shared Blocks ✅
- [x] StatCard — used across 7+ pages (icon + label + value + sublabel)
- [x] ProgressBar — used in AI Model, Calculator, Operations
- [x] StatusBadge — used in Setup, Operations (Connected/Active/Warning/Error)
- [x] TabNav — used in Setup, Settings, Operations
- [x] SectionCard — consistent card wrapper with header

### Phase 3: Page Refactors ✅
- [x] Layout.tsx — semantic HTML, collapsible sidebar
- [x] ProspectSetup — semantic HTML, use blocks
- [x] ProspectIntelligence — semantic HTML, use blocks
- [x] AIGeneratedModel — semantic HTML, use blocks
- [x] ValueDriverTree — semantic HTML, use blocks
- [x] EvidenceMatch — semantic HTML, use blocks
- [x] ValueCalculator — semantic HTML, use blocks
- [x] GeneratedValueCase — semantic HTML, use blocks
- [x] SetupScreen — extract tab content, use blocks
- [x] SettingsScreen — extract tab content, use blocks
- [x] OperationsScreen — extract tab content, use blocks

### Phase 4: Component API Standardization ✅
- [x] All blocks accept `className` prop via `cn()`
- [x] Consistent sizing variants (`sm` | `md`)
- [x] SectionCard supports `icon` prop for header icons
- [x] StatusBadge supports `size` and custom `label`
- [x] Barrel exports in `components/blocks/index.ts`

### Phase 5: Cross-Cutting Concerns ✅
- [x] Error boundary wrapper (class component)
- [x] 404 page with navigation
- [x] Build verification (clean, zero errors)
- [x] CHANGELOG.md
