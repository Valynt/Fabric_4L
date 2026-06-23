---
skill_id: fumadocs
name: fumadocs
version: 1.0.0
description: Fumadocs documentation framework guidelines
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Fumadocs — Documentation Framework

## Overview

**Fumadocs** (Foo-ma docs) is a documentation framework designed to be fast, flexible, and composable into React frameworks.

**Architecture**:
| Package | Purpose |
|---------|---------|
| `fumadocs-core` | Headless logic: search, content sources, Markdown extensions |
| `fumadocs-ui` | Default theme with beautiful UI components |
| `fumadocs-mdx` | Official content source for MDX files |
| `fumadocs-cli` | CLI for installing components and automation |

## Quick Start

### Automatic Installation

Requires **Node.js 22+**.

```bash
npm create fumadocs-app
```

Template options:
- **Framework**: Next.js, Waku, React Router, Tanstack Start
- **Content**: Fumadocs MDX (default)

Pre-configured features:
- LLM integration (`/llms.txt`, `/llms-full.txt`)
- Dynamic OpenGraph images
- Type-safe content layer

### Manual Installation

For existing codebases, follow the [manual installation guide](https://www.fumadocs.dev/docs/manual-installation).

## Project Structure

```
my-docs/
├── app/                 # Next.js app directory
│   ├── layout.tsx      # Root layout with Providers
│   ├── page.tsx          # Home page
│   └── docs/             # Docs routes
│       └── [[...slug]]/
├── content/              # MDX content source
│   └── docs/
├── lib/
│   └── source.ts         # Content source config
├── components/
│   └── mdx.tsx           # MDX components
└── source.config.ts      # Fumadocs MDX config
```

## Core Concepts

### Content Source

Fumadocs uses a **content source** to transform content into type-safe data. The official source is **Fumadocs MDX**.

```typescript
// lib/source.ts
import { docs } from '@/.source';
import { loader } from 'fumadocs-core/source';

export const source = loader({
  baseUrl: '/docs',
  source: docs.toFumadocsSource(),
});
```

### Collections

A **collection** is a group of related content files.

```typescript
// source.config.ts
import { defineDocs, defineConfig } from 'fumadocs-mdx/config';

export const { docs, meta } = defineDocs({
  dir: 'content/docs',
});

export default defineConfig();
```

### Page Tree

The **page tree** defines navigation structure based on:
1. File system structure
2. JSON/YAML meta files
3. Frontmatter properties

## MDX Content

### File Conventions

```mdx
---
title: Getting Started
description: Learn the basics
icon: Rocket
---

# Getting Started

Your content here...
```

### Built-in Frontmatter

| Property | Type | Description |
|----------|------|-------------|
| `title` | `string` | Page title (required) |
| `description` | `string` | Meta description |
| `icon` | `string` | Lucide icon name |
| `full` | `boolean` | Full-width layout |
| `sidebar` | `boolean` | Show/hide in sidebar |

### Customizing Components

```tsx
// components/mdx.tsx
import defaultMdxComponents from 'fumadocs-ui/mdx';

export function getMDXComponents(components?: MDXComponents) {
  return {
    ...defaultMdxComponents,
    // Custom components
    MyComponent: (props) => <div {...props} />,
    ...components,
  };
}
```

## UI Components

### Installation

```bash
npx fumadocs add <component>
```

### Available Components

| Component | Purpose |
|-----------|---------|
| `Accordion` | Collapsible content sections |
| `CodeBlock` | Syntax-highlighted code (Shiki) |
| `CodeBlockDynamic` | Interactive code highlighting |
| `Files` | File tree display |
| `GitHubInfo` | Repo stats display |
| `GraphView` | Page relationship graph |
| `ZoomableImage` | Lightbox image viewer |
| `InlineTOC` | Table of contents inline |
| `Steps` | Step-by-step guides |
| `Tabs` | Persistent tab groups |
| `TypeTable` | API documentation tables |
| `AutoTypeTable` | Auto-generated from TypeScript |
| `Banner` | Announcement banners |
| `Callout` | Info/warning/danger boxes |
| `Card` | Content cards with icons |

### Usage Example

```mdx
import { Callout } from 'fumadocs-ui/components/callout';
import { Steps, Step } from 'fumadocs-ui/components/steps';

<Callout type="warning">
  This is a warning callout.
</Callout>

<Steps>
  <Step title="Install">
    ```bash
    npm install
    ```
  </Step>
  <Step title="Configure">
    Update your config file.
  </Step>
</Steps>
```

## Layouts

### Docs Layout

```tsx
import { DocsLayout } from 'fumadocs-ui/layouts/docs';

<DocsLayout
  tree={source.pageTree}
  nav={{ title: 'My Docs' }}
>
  {children}
</DocsLayout>
```

### Home Layout

```tsx
import { HomeLayout } from 'fumadocs-ui/layouts/home';

<HomeLayout>
  <Hero />
  <Features />
</HomeLayout>
```

## Search

### Built-in Search

Fumadocs supports Orama (default) or Algolia:

```tsx
// app/layout.tsx
import { SearchProvider } from 'fumadocs-ui/components/search';

<SearchProvider>
  {children}
</SearchProvider>
```

## Internationalization (i18n)

```typescript
// lib/source.ts
import { loader } from 'fumadocs-core/source';
import { createI18n } from 'fumadocs-core/i18n';

export const i18n = createI18n({
  languages: ['en', 'zh'],
  defaultLanguage: 'en',
});

export const source = loader({
  i18n,
  // ...
});
```

## Theming

### Color Themes

Configure in `tailwind.config.ts`:

```typescript
darkMode: 'class',
theme: {
  extend: {
    colors: {
      background: 'hsl(var(--background))',
      foreground: 'hsl(var(--foreground))',
      primary: {
        DEFAULT: 'hsl(var(--primary))',
        foreground: 'hsl(var(--primary-foreground))',
      },
    },
  },
},
```

## CLI Commands

```bash
# Add UI component
npx fumadocs add <component>

# Generate types
npx fumadocs-mdx

# Development
npm run dev

# Build
npm run build
```

## Deployment

### Static Export

```typescript
// next.config.ts
const config = {
  output: 'export',
};
```

## Best Practices

1. **Use content sources** — Don't hardcode docs; use MDX with type safety
2. **Leverage page tree** — Organize content with meta files and file structure
3. **Customize MDX components** — Extend defaults for your design system
4. **Use built-in components** — Cards, Callouts, Steps for consistent UX
5. **Configure search** — Enable Orama or Algolia for discoverability
6. **Add LLM support** — Include `/llms.txt` for AI context

## Common Patterns

```tsx
// Dynamic page with params
export default async function Page({
  params,
}: { params: { slug?: string[] } }) {
  const page = source.getPage(params.slug);
  if (!page) notFound();

  const MDX = page.data.body;

  return (
    <DocsPage toc={page.data.toc}>
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <MDX components={getMDXComponents()} />
    </DocsPage>
  );
}
```

## Resources

- **Docs**: https://www.fumadocs.dev/docs
- **UI Components**: https://www.fumadocs.dev/docs/ui/components
- **GitHub**: https://github.com/fuma-nama/fumadocs


---

# Extracted Workflow Reference

### 8. Produce Remediation Pack

Deliver structured findings with actionable fixes.

**Required Deliverables:**

#### A. Executive Summary
- Total drift instances found: N
- Drift categories: [component|routing|navigation|theme|build|content]
- Risk level: [Critical|High|Medium|Low]
- Estimated effort to remediate: [hours/days]

#### B. Prioritized Findings

**Stale Commands:**
| Command | Doc Location | Current Behavior | Fix |
|---------|--------------|------------------|-----|
| | | | |

**Stale Component Names:**
| Documented Name | Actual Name | File | Fix |
|-------------------|-------------|------|-----|
| | | | |

**Stale File Paths:**
| Documented Path | Actual Path | References | Fix |
|-----------------|-------------|------------|-----|
| | | | |

**Moved Routes:**
| Old Route | New Route | Redirect Needed? | Docs Updated? |
|-----------|-----------|------------------|---------------|
| | | | |

**Hidden Prerequisites:**
| Requirement | Where Required | Currently Documented? | Action |
|-------------|----------------|----------------------|--------|
| | | | |

**Incomplete Examples:**
| Example Location | Issue | Missing | Fix |
|------------------|-------|---------|-----|
| | | | |

**Duplicate/Overlapping Docs:**
| Documents | Overlap Area | Recommendation |
|-----------|--------------|----------------|
| | | |

**Content/UI Mismatch:**
| Doc Description | Actual UI | Location | Fix |
|-----------------|-----------|----------|-----|
| | | | |

#### C. Exact Files to Update

| Priority | File | Change Type | Effort |
|----------|------|-------------|--------|
| P0 | | | |
| P1 | | | |
| P2 | | | |

#### D. Draft Markdown for Top 3 Fixes

Provide ready-to-paste markdown updates for highest-value fixes.

---

## Output Format

### Changed File Impact Table

```markdown
| File | Change Type | Impact Area | Doc Action |
|------|-------------|-------------|------------|
| `app/docs/layout.tsx` | Modified | Layout | Check layout docs, sidebar config |
| `lib/source.ts` | Modified | Source Loading | Update content source documentation |
| `components/mdx.tsx` | Added | MDX Components | Document new components |
| `content/docs/api/*.mdx` | Deleted | Content | Remove or redirect broken links |
```

### Topic-Doc Inventory

```markdown
| Topic | Docs Found | Coverage | Status |
|-------|------------|----------|--------|
| Layout customization | `docs/layouts.mdx`, `README.md` | Partial | Needs update |
| MDX components | `docs/components/*.mdx` | Complete | Current |
| API documentation | `docs/api/*.mdx` | Missing | Create |
```

### Stale/Missing/Duplicate List

```markdown
## Stale Documentation
1. `docs/components/accordion.mdx` - Props table outdated (P1)
2. `docs/quickstart.md` - Uses old CLI command (P0)

## Missing Documentation
1. New `Tabs` component usage (P1)
2. `meta.json` advanced configuration (P2)

## Duplicate Documentation
1. `docs/layout.mdx` and `docs/theme.mdx` overlap on customization (P2)
```

### Top 10 Fixes Ranked

```markdown
| Rank | Issue | User Impact | Effort | File |
|------|-------|-------------|--------|------|
| 1 | Quickstart uses deprecated command | High | 5 min | `docs/quickstart.md` |
| 2 | Component props outdated | High | 30 min | `docs/components/*.mdx` |
| 3 | Missing navigation docs | Medium | 2 hrs | `docs/navigation.mdx` |
```

### Diátaxis-Fumadocs Alignment Report

```markdown
## Alignment Status

| Diátaxis Type | Content Count | Presentation | Issues |
|---------------|---------------|--------------|--------|
| **Tutorials** | 5 | Ordered nav, next-links | ✅ Aligned |
| **How-to Guides** | 12 | Task-grouped, searchable | ⚠️ Mixed with tutorials |
| **Reference** | 8 | Dense layout, API tables | ❌ Using blog spacing |
| **Explanation** | 3 | Essay layout | ❌ Heavy sidebar chrome |

## Critical Misalignments

1. **Reference docs use tutorial layout** — Switch to dense `DocsLayout` variant
2. **Tutorials lack explicit ordering** — Add `order` frontmatter + `meta.json`
3. **How-to guides not searchable** — Add search weighting for `/how-to/` prefix
```

---