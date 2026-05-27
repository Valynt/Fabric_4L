# ValuePilot — Frontend Standards

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 18 + TypeScript |
| Build | Vite |
| Styling | Tailwind CSS 3.4 + shadcn/ui |
| Color Space | oklch() |
| Routing | React Router v7 (HashRouter) |
| State | Local useState (no global store) |
| Components | Radix UI primitives via shadcn |
| Icons | Lucide React |

## Component Architecture (Three-Tier)

```
components/ui/        — Raw shadcn primitives (CLI-managed, never import directly)
components/primitives/ — Design-system defaults (wraps ui/, product-specific extensions)
components/blocks/    — Product compositions (PricingCard, StatCard, ValueModelCard)
```

**Import Rule**: Application code imports only from `primitives/` or `blocks/`. Never from `ui/`.

## Naming Conventions

| Aspect | Convention | Example |
|--------|-----------|---------|
| Filename | lowercase kebab-case | `value-model-card.tsx` |
| Export | PascalCase named export | `export function ValueModelCard` |
| Props interface | `{Name}Props` | `interface ValueModelCardProps` |
| Variant names | Semantic (not visual) | `primary`, `destructive` not `blue`, `red` |

## Design Tokens

All styling flows through CSS variables in oklch(). No hardcoded colors. No inline styles except dynamic calculations.

Key tokens: `--background`, `--foreground`, `--primary`, `--muted`, `--border`, `--radius`, `--sidebar-*`

## Accessibility (WCAG 2.1 AA)

- Semantic HTML: `<main>`, `<section>`, `<nav>`, proper heading hierarchy (h1→h2→h3)
- Keyboard navigation: all interactive elements focusable
- ARIA labels where semantic HTML is insufficient
- Color contrast 4.5:1 minimum
- Focus indicators visible

## Code Quality

- Named exports only (no `export default`)
- `cn()` utility for all className merging
- Single Responsibility: components do one thing
- No prop drilling: use composition or context
- No unused imports or variables
