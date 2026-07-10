# Storybook Setup Guide — Fabric_4L Frontend

## Quick Start

```bash
cd apps/web
npx storybook@latest init --yes
```

This will detect Vite + React + TypeScript and scaffold the correct configuration.

## Manual Configuration

If the automatic setup fails, follow these steps:

### 1. Install Dependencies

```bash
cd apps/web
pnpm add -D storybook @storybook/react @storybook/react-vite @storybook/addon-essentials @storybook/addon-interactions @storybook/test @storybook/addon-a11y
```

### 2. Initialize Storybook Config

```bash
npx storybook@latest init --yes --package-manager pnpm
```

### 3. Apply Custom Configuration

Replace the generated `.storybook/main.ts` with the version from this repo (see `.storybook/main.ts`).
Replace the generated `.storybook/preview.tsx` with the version from this repo (see `.storybook/preview.tsx`).

### 4. Verify Setup

```bash
# Start Storybook dev server
pnpm storybook

# Build Storybook for static hosting
pnpm run storybook:build
```

## Story File Conventions

| Directory | Contents |
|---|---|
| `stories/ui/` | shadcn/ui primitive stories (Button, Card, Dialog, etc.) |
| `stories/domain/` | Product-specific domain component stories |
| `stories/pages/` | Full page layout / composition stories |

### Naming Convention

- Stories: `ComponentName.stories.tsx`
- Co-located tests: `ComponentName.test.tsx` (in `src/`)

### Meta Export Pattern

```tsx
import type { Meta, StoryObj } from "@storybook/react";
import { MyComponent } from "@/components/MyComponent";

const meta: Meta<typeof MyComponent> = {
  title: "Domain/MyComponent",
  component: MyComponent,
  tags: ["autodocs"],
  argTypes: {
    status: {
      control: "select",
      options: ["idle", "loading", "success", "error"],
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    status: "idle",
  },
};
```

## Running Storybook

```bash
# Dev server (port 6006)
make storybook

# Static build
make storybook-build

# Test stories with test-runner
make storybook-test
```

## CI Integration

Storybook is built and tested in CI via `.github/workflows/storybook.yml`.

## Accessibility Testing

Storybook includes `@storybook/addon-a11y` for automated accessibility checks.

Open the **Accessibility** panel in Storybook to view axe-core audit results for each story.

## Design Token Integration

Storybook automatically loads Tailwind CSS classes and the Inter / JetBrains Mono font stack defined in DESIGN.md.

Theme switching (light / dark) is available via the **Backgrounds** toolbar.
