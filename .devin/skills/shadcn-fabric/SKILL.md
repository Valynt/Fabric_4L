---
skill_id: shadcn-fabric
name: shadcn-fabric
version: 1.0.0
description: shadcn/ui usage guidelines for Value Fabric frontend
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# shadcn/ui — Value Fabric

## Current Project Context

**Project**: Value Fabric — 6-layer enterprise SaaS platform  
**Framework**: React + Vite (SPA, not RSC)  
**Base**: Radix UI  
**Style**: New York  
**Tailwind**: v4 with CSS variables  
**Registry**: `@shadcnuikit` (premium blocks)

**Installed Components** (50+):
- Layout: Card, Separator, ScrollArea, Resizable, Sidebar
- Forms: Input, Textarea, Select, Checkbox, RadioGroup, Switch, Slider, Combobox
- Feedback: Alert, Badge, Progress, Skeleton, Spinner, sonner (toast)
- Overlays: Dialog, Sheet, Drawer, AlertDialog, Popover, Tooltip, HoverCard
- Navigation: Tabs, Breadcrumb, NavigationMenu, Pagination, Command
- Data: Table, Chart, Calendar, DataTable (custom Fabric component)
- Domain: FabricCard, FabricDialog, FilterBar, LoadingSkeleton, StatusBadge

**Import Aliases**:
- `@/components` → UI components
- `@/components/ui` → shadcn primitives
- `@/components/ui/fabric` → Fabric custom components
- `@/hooks` → React hooks
- `@/lib/utils` → Utilities (cn, etc.)

**Icons**: `lucide-react`

## Principles

1. **Use existing components first.** Check `@/components/ui` and `@/components/ui/fabric` before creating new UI.
2. **Compose, don't reinvent.** Settings page = Tabs + Card + Form. Dashboard = Sidebar + Card + Chart + Table.
3. **Use built-in variants before custom styles.** `variant="outline"`, `size="sm"`, etc.
4. **Use semantic colors.** `bg-primary`, `text-muted-foreground` — never raw values like `bg-blue-500`.
5. **Prefer Fabric components for domain patterns.** Use `FabricCard`, `FabricDialog`, `DataTable` for consistent product UX.

## Critical Rules

### Styling & Tailwind → [rules/styling.md](./rules/styling.md)
- **`className` for layout, not styling.** Never override component colors or typography.
- **No `space-x-*` or `space-y-*`.** Use `flex` with `gap-*`. For vertical stacks, `flex flex-col gap-*`.
- **Use `size-*` when width and height are equal.** `size-10` not `w-10 h-10`.
- **Use `truncate` shorthand.** Not `overflow-hidden text-ellipsis whitespace-nowrap`.
- **No manual `dark:` color overrides.** Use semantic tokens (`bg-background`, `text-muted-foreground`).
- **Use `cn()` for conditional classes.** Import from `@/lib/utils`.
- **No manual `z-index` on overlay components.** Dialog, Sheet, Popover handle their own stacking.

### Forms & Inputs → [rules/forms.md](./rules/forms.md)
- **Forms use `Form` + `FormField` from `@/components/ui/form`.** Built on react-hook-form + zod.
- **Use `Control` components for all inputs.** `FormControl` wraps inputs with proper binding.
- **Validation messages use `FormMessage`.** Don't write custom error display.
- **Option sets (2–7 choices) use `ToggleGroup`.** Don't loop `Button` with manual active state.
- **Field-level loading states use `Skeleton` inside `FormControl`.**

### Component Structure → [rules/composition.md](./rules/composition.md)
- **Items always inside their Group.** `SelectItem` → `SelectContent` → `Select`.
- **Use `asChild` for custom triggers.** Check component docs before overriding.
- **Dialog, Sheet, and Drawer always need a Title.** `DialogTitle`, `SheetTitle` required for accessibility.
- **Use full Card composition.** `CardHeader`/`CardTitle`/`CardDescription`/`CardContent`/`CardFooter`.
- **Button has no `isPending`/`isLoading`.** Compose with `Spinner` + `disabled`.
- **`TabsTrigger` must be inside `TabsList`.**
- **`Avatar` always needs `AvatarFallback`.**

### Fabric Domain Components → [rules/fabric.md](./rules/fabric.md)
- **Use `FabricCard` for entity displays.** Consistent header/content/footer layout with actions.
- **Use `FabricDialog` for confirmations.** Wraps AlertDialog with Fabric styling.
- **Use `DataTable` for all tabular data.** Sorting, filtering, pagination built-in.
- **Use `StatusBadge` for state indicators.** Standardized colors for success/warning/error/pending.
- **Use `FilterBar` for list filters.** Standardized layout with search + filters + actions.
- **Use `PageHeader` for page titles.** Breadcrumb + title + actions + description pattern.

### Icons → [rules/icons.md](./rules/icons.md)
- **Icons from `lucide-react` only.** Never other icon libraries.
- **Icon sizing via component CSS.** No manual `size-4` or `w-4 h-4` on icons inside buttons.
- **Pass icons as components.** `icon={SearchIcon}`, not string keys.

### CLI & Registry
- **Install via `npx shadcn@latest add`.**
- **Use `@shadcnuikit` registry for blocks.** `npx shadcn add @shadcnuikit/hero-section`
- **Always check existing components before adding.** Run `npx shadcn@latest info` to list installed.

## Key Patterns

```tsx
// Form with react-hook-form
<Form {...form}>
  <form onSubmit={form.handleSubmit(onSubmit)}>
    <FormField
      control={form.control}
      name="email"
      render={({ field }) => (
        <FormItem>
          <FormLabel>Email</FormLabel>
          <FormControl>
            <Input {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
    <Button type="submit">Submit</Button>
  </form>
</Form>

// Spacing: gap-*, not space-y-*
<div className="flex flex-col gap-4">  // correct
<div className="space-y-4">           // wrong

// Equal dimensions: size-*
<Avatar className="size-10">

// Status colors: StatusBadge or semantic tokens
<StatusBadge status="success">Active</StatusBadge>  // correct
<span className="text-emerald-600">Active</span>      // wrong

// Loading state with Button
<Button disabled={isPending}>
  {isPending && <Spinner className="mr-2" />}
  Save
</Button>

// Toast notification
import { toast } from "sonner"
toast.success("Changes saved")
```

## Component Selection

| Need | Use |
|------|-----|
| Button/action | `Button` with variant |
| Form inputs | `Input`, `Select`, `Combobox`, `Switch`, `Checkbox`, `RadioGroup`, `Textarea`, `Slider` |
| Toggle 2–5 options | `ToggleGroup` |
| Data display | `DataTable`, `Card`, `Badge`, `Avatar` |
| Navigation | `Sidebar`, `NavigationMenu`, `Breadcrumb`, `Tabs`, `Pagination` |
| Overlays | `Dialog`, `Sheet`, `Drawer`, `AlertDialog` |
| Feedback | `sonner`, `Alert`, `Progress`, `Skeleton`, `Spinner` |
| Command palette | `Command` inside `Dialog` |
| Charts | `Chart` (Recharts wrapper) |
| Layout | `Card`, `Separator`, `Resizable`, `ScrollArea`, `Accordion` |
| Empty states | Custom `Empty` component |
| Menus | `DropdownMenu`, `ContextMenu` |
| Tooltips | `Tooltip`, `HoverCard`, `Popover` |
| Entity cards | `FabricCard` |
| Status indicators | `StatusBadge` |
| List filters | `FilterBar` |
| Page structure | `PageHeader`, `AppShell` |

## Workflow

1. **Check existing components first** — Look in `@/components/ui` and `@/components/ui/fabric`
2. **Find components** — `npx shadcn@latest search` or browse `@shadcnuikit`
3. **Install** — `npx shadcn@latest add <component>` or `npx shadcn add @shadcnuikit/<block>`
4. **Fix imports** — Ensure third-party components use `@/components/ui/*` paths
5. **Review** — Check added files for correctness, missing sub-components, icon library

## Registry Commands

```bash
# List installed components
npx shadcn@latest info

# Search all registries
npx shadcn@latest search

# Add from shadcn/ui
npx shadcn@latest add button

# Add from shadcnui kit registry
npx shadcn add @shadcnuikit/hero-section

# View component docs
npx shadcn@latest docs button
```
