# Fabric 4L Documentation Site Configuration Guide

## Overview

This guide specifies the complete configuration for the Fabric 4L documentation site (`docs-site/`). The site uses [VitePress](https://vitepress.dev/) as the static site generator with custom theming, search integration, and multi-version support.

**Site URL:** https://docs.fabric4l.io  
**Repository:** https://github.com/bmsull560/Fabric_4L/tree/main/docs-site  
**Build Output:** `docs-site/.vitepress/dist`

---

## 1. Dark/Light Mode Toggle

### Implementation

VitePress provides built-in dark mode support via CSS variables. The toggle is rendered in the top-right navigation bar.

### Configuration

```typescript
// docs-site/.vitepress/config.ts
import { defineConfig } from 'vitepress'

export default defineConfig({
  // Appearance: 'dark' forces dark mode, 'light' forces light mode
  // Default uses system preference with manual toggle
  appearance: true, // Enables dark/light toggle with system preference as default

  themeConfig: {
    // Customizable label for accessibility
    darkModeSwitchLabel: 'Toggle dark mode',
    lightModeSwitchTitle: 'Switch to light theme',
    darkModeSwitchTitle: 'Switch to dark theme',
  }
})
```

### CSS Variable Overrides

```css
/* docs-site/.vitepress/theme/custom.css */
:root {
  /* Light mode — Fabric 4L brand palette */
  --vp-c-brand-1: #6366f1;
  --vp-c-brand-2: #818cf8;
  --vp-c-brand-3: #4f46e5;
  --vp-c-brand-soft: rgba(99, 102, 241, 0.14);

  /* Custom background accents */
  --vp-c-bg: #ffffff;
  --vp-c-bg-alt: #f8fafc;
  --vp-c-bg-elv: #ffffff;

  /* Typography */
  --vp-font-family-base: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --vp-font-family-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;
}

.dark {
  /* Dark mode — Fabric 4L dark palette */
  --vp-c-bg: #0f172a;
  --vp-c-bg-alt: #1e293b;
  --vp-c-bg-elv: #1e293b;
  --vp-c-text-1: #f1f5f9;
  --vp-c-text-2: #94a3b8;
  --vp-c-divider: #334155;
}

/* Layer-specific accent colors used in diagrams */
:root {
  --l1-color: #3b82f6; /* Ingestion — blue */
  --l2-color: #10b981; /* Extraction — emerald */
  --l3-color: #f59e0b; /* Knowledge — amber */
  --l4-color: #8b5cf6; /* Agents — violet */
  --l5-color: #ef4444; /* Ground Truth — red */
  --l6-color: #06b6d4; /* Benchmarks — cyan */
}
```

### Toggle Persistence

The selected theme is persisted in `localStorage` under the key `vitepress-theme-appearance`. The value is either `"dark"` or `"light"`. On first visit, the system preference (`prefers-color-scheme`) is respected.

---

## 2. Search Functionality (Algolia DocSearch)

### Algolia DocSearch Configuration

Fabric 4L uses [Algolia DocSearch](https://docsearch.algolia.com/) for full-text search across all documentation.

### Application

Apply at https://docsearch.algolia.com/apply/ with the following details:
- **Website URL:** https://docs.fabric4l.io
- **Email:** docs@fabric4l.io
- **Repository:** https://github.com/bmsull560/Fabric_4L

### VitePress Config

```typescript
// docs-site/.vitepress/config.ts
export default defineConfig({
  themeConfig: {
    search: {
      provider: 'algolia',
      options: {
        appId: process.env.ALGOLIA_APP_ID || 'YOUR_APP_ID',
        apiKey: process.env.ALGOLIA_SEARCH_API_KEY || 'YOUR_SEARCH_API_KEY',
        indexName: 'fabric4l',

        // Search across all versions
        algoliaOptions: {
          facetFilters: ['version:v1.2.0'],
        },

        // Custom placeholder
        placeholder: 'Search documentation...',

        // Translations for UI strings
        translations: {
          button: {
            buttonText: 'Search',
            buttonAriaLabel: 'Search documentation',
          },
          modal: {
            searchBox: {
              resetButtonTitle: 'Clear search',
              resetButtonAriaLabel: 'Clear search',
              cancelButtonText: 'Cancel',
              cancelButtonAriaLabel: 'Cancel',
            },
            startScreen: {
              recentSearchesTitle: 'Recent',
              noRecentSearchesText: 'No recent searches',
              saveRecentSearchButtonTitle: 'Save this search',
              removeRecentSearchButtonTitle: 'Remove this search from history',
              favoriteSearchesTitle: 'Favorite',
              removeFavoriteSearchButtonTitle: 'Remove this search from favorites',
            },
            errorScreen: {
              titleText: 'Unable to fetch results',
              helpText: 'Check your network connection.',
            },
            footer: {
              selectText: 'to select',
              navigateText: 'to navigate',
              closeText: 'to close',
              searchByText: 'Search by',
            },
            noResultsScreen: {
              noResultsText: 'No results for',
              suggestedQueryText: 'Try searching for',
              reportMissingResultsText: 'Believe this query should return results?',
              reportMissingResultsLinkText: 'Let us know.',
            },
          },
        },
      },
    },
  },
})
```

### Environment Variables

```bash
# .env (not committed — add to CI/CD secrets)
ALGOLIA_APP_ID=your_app_id
ALGOLIA_SEARCH_API_KEY=your_search_api_key  # Public search-only key
ALGOLIA_ADMIN_API_KEY=your_admin_api_key    # For crawler indexing (CI only)
```

### Crawler Configuration

```javascript
// algolia-crawler.config.js (for Algolia Crawler dashboard)
new Crawler({
  appId: 'YOUR_APP_ID',
  apiKey: 'YOUR_ADMIN_API_KEY',
  rateLimit: 8,
  startUrls: ['https://docs.fabric4l.io/'],
  sitemaps: ['https://docs.fabric4l.io/sitemap.xml'],
  ignoreCanonicalTo: true,
  discoveryPatterns: ['https://docs.fabric4l.io/**'],
  actions: [
    {
      indexName: 'fabric4l',
      pathsToMatch: ['https://docs.fabric4l.io/**'],
      recordExtractor: ({ $, helpers }) => {
        return helpers.docsearch({
          recordProps: {
            lvl0: {
              selectors: '.VPDoc h1',
              defaultValue: 'Documentation',
            },
            lvl1: '.VPDoc h2',
            lvl2: '.VPDoc h3',
            lvl3: '.VPDoc h4',
            lvl4: '.VPDoc h5',
            lvl5: '.VPDoc h6',
            content: '.VPDoc p, .VPDoc li',
            version: {
              selectors: '.version-badge',
              defaultValue: 'v1.2.0',
            },
          },
          aggregateContent: true,
          recordVersion: 'v3',
        })
      },
    },
  ],
  initialIndexSettings: {
    fabric4l: {
      attributesForFaceting: ['version', 'type'],
      attributesToRetrieve: [
        'hierarchy',
        'content',
        'anchor',
        'url',
        'url_without_anchor',
        'type',
        'version',
      ],
      attributesToHighlight: ['hierarchy', 'content'],
      attributesToSnippet: ['content:10'],
      camelCaseAttributes: ['hierarchy', 'content'],
      searchableAttributes: [
        'unordered(hierarchy.lvl0)',
        'unordered(hierarchy.lvl1)',
        'unordered(hierarchy.lvl2)',
        'unordered(hierarchy.lvl3)',
        'unordered(hierarchy.lvl4)',
        'unordered(hierarchy.lvl5)',
        'unordered(hierarchy.lvl6)',
        'content',
      ],
      distinct: true,
      attributeForDistinct: 'url',
      customRanking: [
        'desc(weight.pageRank)',
        'desc(weight.level)',
        'asc(weight.position)',
      ],
      ranking: [
        'words',
        'filters',
        'typo',
        'attribute',
        'proximity',
        'exact',
        'custom',
      ],
    },
  },
})
```

### Fallback: Local Search (for offline/self-hosted)

```typescript
// Use local search for development or air-gapped deployments
search: {
  provider: 'local',
  options: {
    translations: {
      button: {
        buttonText: 'Search',
        buttonAriaLabel: 'Search documentation',
      },
      modal: {
        noResultsText: 'No results for',
        resetButtonTitle: 'Clear search',
        footer: {
          navigateText: 'to navigate',
          selectText: 'to select',
          closeText: 'to close',
        },
      },
    },
  },
}
```

---

## 3. Version Selector

### Supported Versions

| Version | Status | Branch | Docs Path |
|---------|--------|--------|-----------|
| v1.2.0 | Current (stable) | `main` | `/` |
| v1.1.x | Maintenance | `release/v1.1` | `/v1.1/` |
| v1.0.x | End of Life | `release/v1.0` | `/v1.0/` |

### VitePress Config — Versioning

```typescript
// docs-site/.vitepress/config.ts
export default defineConfig({
  themeConfig: {
    // Version dropdown in nav
    nav: [
      {
        text: 'v1.2.0',
        items: [
          {
            text: 'v1.2.0 (Current)',
            link: '/',
            activeMatch: '^/$|^/((?!v1\.|v1\.).)*$',
          },
          {
            text: 'v1.1.x',
            link: 'https://v1-1.docs.fabric4l.io',
          },
          {
            text: 'v1.0.x',
            link: 'https://v1-0.docs.fabric4l.io',
          },
        ],
      },
    ],

    // Banner for non-current versions
    // (Handled by custom VersionBanner component)
  },
})
```

### Version Banner Component

```vue
<!-- docs-site/.vitepress/theme/components/VersionBanner.vue -->
<template>
  <div v-if="showBanner" class="version-banner" :class="bannerType">
    <p>
      <strong>{{ bannerTitle }}</strong> —
      You're viewing {{ currentVersion }} documentation.
      <a :href="latestUrl">View latest (v1.2.0)</a>
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useData } from 'vitepress'

const { site, page } = useData()

const currentVersion = ref('v1.2.0') // Detected from URL or config
const latestVersion = 'v1.2.0'

const showBanner = computed(() => currentVersion.value !== latestVersion)

const bannerType = computed(() => {
  if (currentVersion.value.startsWith('v1.1')) return 'maintenance'
  return 'eol' // End of life
})

const bannerTitle = computed(() => {
  if (bannerType.value === 'maintenance') return 'Maintenance Mode'
  return 'End of Life'
})

const latestUrl = 'https://docs.fabric4l.io' + page.value.relativePath
</script>

<style scoped>
.version-banner {
  padding: 12px 24px;
  text-align: center;
  font-size: 14px;
}
.version-banner.maintenance {
  background: #fef3c7;
  color: #92400e;
  border-bottom: 1px solid #f59e0b;
}
.version-banner.eol {
  background: #fee2e2;
  color: #991b1b;
  border-bottom: 1px solid #ef4444;
}
.version-banner a {
  text-decoration: underline;
  font-weight: 600;
}
.dark .version-banner.maintenance {
  background: #451a03;
  color: #fcd34d;
}
.dark .version-banner.eol {
  background: #450a0a;
  color: #fca5a5;
}
</style>
```

### Multi-Version Build Script

```bash
#!/bin/bash
# docs-site/scripts/build-versions.sh

set -euo pipefail

VERSIONS=("v1.2.0" "v1.1" "v1.0")
BRANCHES=("main" "release/v1.1" "release/v1.0")
BASE_DIR=$(pwd)
BUILD_DIR="$BASE_DIR/.vitepress/dist"

# Clean and create build directory
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

for i in "${!VERSIONS[@]}"; do
  version="${VERSIONS[$i]}"
  branch="${BRANCHES[$i]}"
  
  echo "Building documentation for $version (branch: $branch)..."
  
  if [ "$version" = "v1.2.0" ]; then
    # Current version builds at root
    git checkout "$branch"
    npm run docs:build
    # dist is already at root
  else
    # Older versions build in subdirectories
    git checkout "$branch"
    npm run docs:build
    mkdir -p "$BUILD_DIR/$version"
    cp -r .vitepress/dist/* "$BUILD_DIR/$version/"
  fi
done

# Generate version index
cat > "$BUILD_DIR/versions.json" << 'EOF'
{
  "versions": [
    { "version": "v1.2.0", "path": "/", "status": "current" },
    { "version": "v1.1", "path": "/v1.1/", "status": "maintenance" },
    { "version": "v1.0", "path": "/v1.0/", "status": "eol" }
  ]
}
EOF

echo "Multi-version build complete. Output: $BUILD_DIR"
```

---

## 4. "Edit This Page" Links

### Configuration

```typescript
// docs-site/.vitepress/config.ts
export default defineConfig({
  themeConfig: {
    // Enable edit links — points to GitHub edit interface
    editLink: {
      pattern: 'https://github.com/bmsull560/Fabric_4L/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },
  },
})
```

### Path Mapping

The `:path` placeholder is replaced with the relative path from the docs root:

| Docs Page | Edit Link |
|-----------|-----------|
| `docs/tutorials/getting-started.md` | `https://github.com/bmsull560/Fabric_4L/edit/main/docs/tutorials/getting-started.md` |
| `docs/reference/faq.md` | `https://github.com/bmsull560/Fabric_4L/edit/main/docs/reference/faq.md` |
| `docs/explanations/architecture-decisions.md` | `https://github.com/bmsull560/Fabric_4L/edit/main/docs/explanations/architecture-decisions.md` |

### Branch-Aware Edit Links

For versioned documentation, edit links should target the correct branch:

```typescript
// docs-site/.vitepress/config.ts — version-aware edit links
const versionBranchMap: Record<string, string> = {
  'v1.2.0': 'main',
  'v1.1': 'release/v1.1',
  'v1.0': 'release/v1.0',
}

function getEditLinkPattern(path: string): string {
  const version = detectVersionFromPath(path)
  const branch = versionBranchMap[version] || 'main'
  return `https://github.com/bmsull560/Fabric_4L/edit/${branch}/docs/:path`
}

export default defineConfig({
  themeConfig: {
    editLink: {
      pattern: ({ filePath }) => {
        return getEditLinkPattern(filePath)
      },
      text: 'Edit this page on GitHub',
    },
  },
})
```

---

## 5. Responsive Design Breakpoints

### Breakpoint Definitions

The documentation site uses the following responsive breakpoints aligned with VitePress defaults and Fabric 4L design system:

```css
/* docs-site/.vitepress/theme/custom.css */

/* Mobile first — base styles for < 768px */
:root {
  --vp-screen-max-width: 1376px;
  --vp-layout-max-width: 1440px;
}

/* Small tablets and large phones: 768px - 959px */
@media (min-width: 768px) {
  .VPNav {
    --vp-nav-height: 64px;
  }
}

/* Tablets and small desktops: 960px - 1279px */
@media (min-width: 960px) {
  .VPContent {
    --vp-sidebar-width: 272px;
  }
  
  .VPDoc {
    padding: 32px 24px 96px;
  }
}

/* Desktops: 1280px - 1440px */
@media (min-width: 1280px) {
  .VPContent.has-sidebar {
    --vp-sidebar-left-width: 272px;
  }
  
  .VPDoc {
    padding: 48px 32px 128px;
  }
  
  .VPDoc.has-aside .content-container {
    max-width: 688px;
  }
}

/* Large desktops: > 1440px */
@media (min-width: 1440px) {
  .VPDoc.has-aside .content-container {
    max-width: 784px;
  }
  
  .VPDoc.has-aside .aside {
    max-width: 256px;
  }
}
```

### Mobile-Specific Adjustments

```css
/* Mobile navigation hamburger */
@media (max-width: 767px) {
  .VPNavScreen {
    --vp-nav-screen-bg: var(--vp-c-bg);
  }
  
  /* Stack sidebar above content */
  .VPContent.has-sidebar {
    flex-direction: column;
  }
  
  /* Full-width code blocks */
  .vp-doc div[class*='language-'] {
    border-radius: 8px;
    margin: 16px -24px;
  }
  
  /* Hide table of contents on mobile */
  .VPDoc .aside {
    display: none;
  }
  
  /* Simplify hero section */
  .VPHero .container {
    flex-direction: column;
    text-align: center;
  }
  
  .VPHero .image {
    order: -1;
    margin-bottom: 24px;
  }
}

/* Touch-friendly tap targets */
@media (pointer: coarse) {
  .VPNavBarMenuLink,
  .VPSidebarItem .item,
  .edit-link-button {
    min-height: 44px;
    padding: 12px 16px;
  }
}
```

### Sidebar Behavior by Breakpoint

| Breakpoint | Sidebar Behavior |
|------------|-----------------|
| < 960px | Hidden by default, toggled via hamburger menu. Overlay on mobile. |
| 960px - 1279px | Fixed left sidebar, collapsible. |
| >= 1280px | Fixed left sidebar + right TOC (aside). Both visible by default. |

---

## 6. OG Image Generation for Social Sharing

### Architecture

OG images are generated at build time using `@vercel/og` (or Satori + Resvg) and cached.

```typescript
// docs-site/scripts/generate-og-images.ts
import { writeFileSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

interface OGImageParams {
  title: string
  description?: string
  section?: string
}

function generateOGImageHTML({ title, description, section }: OGImageParams): string {
  const sectionColors: Record<string, string> = {
    tutorials: '#3b82f6',
    'how-to': '#10b981',
    reference: '#f59e0b',
    explanations: '#8b5cf6',
    migrations: '#ef4444',
    default: '#6366f1',
  }

  const accentColor = sectionColors[section || 'default']

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    * { margin: 0; padding: 0; box-sizing: border-box; }
    
    body {
      width: 1200px;
      height: 630px;
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
      display: flex;
      flex-direction: column;
      padding: 60px;
      position: relative;
      overflow: hidden;
    }
    
    .accent-bar {
      position: absolute;
      top: 0;
      left: 0;
      width: 100%;
      height: 8px;
      background: ${accentColor};
    }
    
    .grid-pattern {
      position: absolute;
      inset: 0;
      background-image: 
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
      background-size: 40px 40px;
    }
    
    .logo {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 40px;
    }
    
    .logo-icon {
      width: 48px;
      height: 48px;
      background: ${accentColor};
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 24px;
      color: white;
    }
    
    .logo-text {
      font-size: 28px;
      font-weight: 700;
      color: #f8fafc;
      letter-spacing: -0.5px;
    }
    
    .logo-version {
      font-size: 16px;
      font-weight: 500;
      color: ${accentColor};
      background: rgba(99, 102, 241, 0.15);
      padding: 4px 12px;
      border-radius: 6px;
      margin-left: 8px;
    }
    
    .section-badge {
      display: inline-block;
      font-size: 16px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 1.5px;
      color: ${accentColor};
      margin-bottom: 20px;
      padding: 8px 16px;
      border: 2px solid ${accentColor};
      border-radius: 8px;
      align-self: flex-start;
    }
    
    .title {
      font-size: 56px;
      font-weight: 800;
      color: #f8fafc;
      line-height: 1.15;
      letter-spacing: -1.5px;
      margin-bottom: 24px;
      max-width: 900px;
    }
    
    .description {
      font-size: 28px;
      font-weight: 400;
      color: #94a3b8;
      line-height: 1.4;
      max-width: 800px;
    }
    
    .footer {
      margin-top: auto;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    
    .url {
      font-size: 20px;
      color: #64748b;
      font-weight: 500;
    }
    
    .layers {
      display: flex;
      gap: 8px;
    }
    
    .layer-dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
    }
    
    .layer-dot:nth-child(1) { background: #3b82f6; }
    .layer-dot:nth-child(2) { background: #10b981; }
    .layer-dot:nth-child(3) { background: #f59e0b; }
    .layer-dot:nth-child(4) { background: #8b5cf6; }
    .layer-dot:nth-child(5) { background: #ef4444; }
    .layer-dot:nth-child(6) { background: #06b6d4; }
  </style>
</head>
<body>
  <div class="accent-bar"></div>
  <div class="grid-pattern"></div>
  
  <div class="logo">
    <div class="logo-icon">4L</div>
    <div class="logo-text">Fabric 4L</div>
    <div class="logo-version">v1.2.0</div>
  </div>
  
  ${section ? `<div class="section-badge">${section}</div>` : ''}
  <h1 class="title">${title}</h1>
  ${description ? `<p class="description">${description}</p>` : ''}
  
  <div class="footer">
    <span class="url">docs.fabric4l.io</span>
    <div class="layers">
      <div class="layer-dot"></div>
      <div class="layer-dot"></div>
      <div class="layer-dot"></div>
      <div class="layer-dot"></div>
      <div class="layer-dot"></div>
      <div class="layer-dot"></div>
    </div>
  </div>
</body>
</html>
  `.trim()
}

// Generate OG images for each documentation section
const sections = [
  { title: 'Getting Started', description: 'Launch your Fabric 4L environment in minutes', section: 'tutorials', output: 'og-tutorials.png' },
  { title: 'API Reference', description: 'Complete API documentation for all 6 layers', section: 'reference', output: 'og-reference.png' },
  { title: 'Architecture Decisions', description: 'Transparent ADR index with rationale', section: 'explanations', output: 'og-explanations.png' },
  { title: 'Migration Guides', description: 'Step-by-step upgrade instructions', section: 'migrations', output: 'og-migrations.png' },
  { title: 'FAQ & Troubleshooting', description: 'Answers to common questions', section: 'reference', output: 'og-faq.png' },
  { title: 'Fabric 4L Documentation', description: 'Enterprise agentic SaaS platform documentation', section: '', output: 'og-home.png' },
]

// In production, use Satori + Resvg to convert HTML to PNG
// For this script, we output the HTML templates for the build pipeline
const outputDir = join(__dirname, '../public/og')
mkdirSync(outputDir, { recursive: true })

for (const section of sections) {
  const html = generateOGImageHTML(section)
  writeFileSync(join(outputDir, `${section.output}.html`), html)
  console.log(`Generated OG template: ${section.output}.html`)
}

console.log('\nOG image templates generated. Run `npm run docs:build:og` to render PNGs.')
```

### Build Pipeline Integration

```json
// docs-site/package.json
{
  "scripts": {
    "docs:dev": "vitepress dev",
    "docs:build": "vitepress build",
    "docs:build:og": "tsx scripts/generate-og-images.ts && tsx scripts/render-og-images.ts",
    "docs:preview": "vitepress preview"
  },
  "devDependencies": {
    "@vercel/og": "^0.6.0",
    "satori": "^0.10.0",
    "resvg-js": "^2.6.0",
    "tsx": "^4.7.0",
    "vitepress": "^1.1.0"
  }
}
```

---

## 7. Meta Tags and SEO Optimization

### Global Head Configuration

```typescript
// docs-site/.vitepress/config.ts
export default defineConfig({
  // Site-level metadata
  lang: 'en-US',
  title: 'Fabric 4L Documentation',
  titleTemplate: ':title | Fabric 4L Docs',
  description: 'Enterprise agentic SaaS platform documentation. Six layers from ingestion to benchmarks.',

  // Head tags injected on every page
  head: [
    // Charset and viewport
    ['meta', { charset: 'utf-8' }],
    ['meta', { name: 'viewport', content: 'width=device-width, initial-scale=1.0' }],

    // Favicon
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    ['link', { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' }],

    // Color scheme
    ['meta', { name: 'color-scheme', content: 'dark light' }],
    ['meta', { name: 'theme-color', content: '#6366f1', media: '(prefers-color-scheme: light)' }],
    ['meta', { name: 'theme-color', content: '#0f172a', media: '(prefers-color-scheme: dark)' }],

    // Open Graph — global defaults
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'Fabric 4L Documentation' }],
    ['meta', { property: 'og:image', content: 'https://docs.fabric4l.io/og/og-home.png' }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { property: 'og:locale', content: 'en_US' }],

    // Twitter Card
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:site', content: '@fabric4l' }],
    ['meta', { name: 'twitter:creator', content: '@fabric4l' }],
    ['meta', { name: 'twitter:image', content: 'https://docs.fabric4l.io/og/og-home.png' }],

    // Canonical URL base
    ['link', { rel: 'canonical', href: 'https://docs.fabric4l.io' }],

    // Preconnect to external resources
    ['link', { rel: 'preconnect', href: 'https://fonts.googleapis.com' }],
    ['link', { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' }],
  ],

  // Sitemap generation
  sitemap: {
    hostname: 'https://docs.fabric4l.io',
    lastmodDateOnly: true,
    transformItems: (items) => {
      // Prioritize important pages in sitemap
      const priorityMap: Record<string, number> = {
        '/': 1.0,
        '/tutorials/getting-started': 0.9,
        '/reference/faq': 0.9,
        '/reference/api': 0.8,
        '/explanations/architecture': 0.7,
        '/explanations/architecture-decisions': 0.7,
      }

      return items.map((item) => ({
        ...item,
        changefreq: item.url === '/' ? 'weekly' : 'monthly',
        priority: priorityMap[item.url] || 0.5,
      }))
    },
  },

  // robots.txt
  robots: {
    host: 'https://docs.fabric4l.io',
    sitemap: 'https://docs.fabric4l.io/sitemap.xml',
  },
})
```

### Page-Level Frontmatter

```yaml
---
# docs/tutorials/getting-started.md

title: Getting Started with Fabric 4L
description: Step-by-step tutorial to launch your Fabric 4L environment in under 15 minutes.

# Override OG for this page
head:
  - - meta
    - property: og:title
      content: Getting Started with Fabric 4L
  - - meta
    - property: og:description
      content: Launch your environment, upload your first document, and run an agent workflow in 15 minutes.
  - - meta
    - property: og:image
      content: https://docs.fabric4l.io/og/og-tutorials.png
  - - meta
    - name: twitter:title
      content: Getting Started with Fabric 4L
  - - meta
    - name: twitter:description
      content: Launch your environment, upload your first document, and run an agent workflow in 15 minutes.
  - - meta
    - name: twitter:image
      content: https://docs.fabric4l.io/og/og-tutorials.png

# Additional metadata
keywords:
  - fabric 4l
  - getting started
  - tutorial
  - quickstart
  - docker
  - agent workflow

# Page-level configuration
editLink: true
lastUpdated: true
outline: deep
---
```

### Structured Data (JSON-LD)

```typescript
// docs-site/.vitepress/theme/components/JsonLdSchema.vue
<template>
  <component :is="'script'" type="application/ld+json" v-html="jsonLd" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useData } from 'vitepress'

const { page, frontmatter, site } = useData()

const jsonLd = computed(() => {
  const schema = {
    '@context': 'https://schema.org',
    '@graph': [
      // Organization
      {
        '@type': 'Organization',
        '@id': 'https://fabric4l.io/#organization',
        name: 'Fabric 4L',
        url: 'https://fabric4l.io',
        logo: {
          '@type': 'ImageObject',
          url: 'https://docs.fabric4l.io/logo.png',
        },
        sameAs: [
          'https://github.com/bmsull560/Fabric_4L',
        ],
      },
      // WebSite
      {
        '@type': 'WebSite',
        '@id': 'https://docs.fabric4l.io/#website',
        url: 'https://docs.fabric4l.io',
        name: 'Fabric 4L Documentation',
        publisher: {
          '@id': 'https://fabric4l.io/#organization',
        },
        potentialAction: {
          '@type': 'SearchAction',
          target: {
            '@type': 'EntryPoint',
            urlTemplate: 'https://docs.fabric4l.io/search?q={search_term_string}',
          },
          'query-input': 'required name=search_term_string',
        },
      },
      // WebPage (current page)
      {
        '@type': 'WebPage',
        '@id': `https://docs.fabric4l.io${page.value.relativePath.replace(/\.md$/, '')}#webpage`,
        url: `https://docs.fabric4l.io${page.value.relativePath.replace(/\.md$/, '')}`,
        name: frontmatter.value.title || page.value.title,
        description: frontmatter.value.description || site.value.description,
        isPartOf: {
          '@id': 'https://docs.fabric4l.io/#website',
        },
        datePublished: frontmatter.value.date || '2026-07-14T00:00:00Z',
        dateModified: frontmatter.value.lastUpdated || new Date().toISOString(),
        breadcrumb: {
          '@id': `https://docs.fabric4l.io${page.value.relativePath.replace(/\.md$/, '')}#breadcrumb`,
        },
      },
      // BreadcrumbList
      {
        '@type': 'BreadcrumbList',
        '@id': `https://docs.fabric4l.io${page.value.relativePath.replace(/\.md$/, '')}#breadcrumb`,
        itemListElement: generateBreadcrumbs(page.value.relativePath),
      },
      // TechArticle (for documentation pages)
      {
        '@type': 'TechArticle',
        '@id': `https://docs.fabric4l.io${page.value.relativePath.replace(/\.md$/, '')}#article`,
        headline: frontmatter.value.title || page.value.title,
        description: frontmatter.value.description,
        author: {
          '@type': 'Organization',
          '@id': 'https://fabric4l.io/#organization',
        },
        publisher: {
          '@id': 'https://fabric4l.io/#organization',
        },
        isPartOf: {
          '@id': `https://docs.fabric4l.io${page.value.relativePath.replace(/\.md$/, '')}#webpage`,
        },
      },
    ],
  }

  return JSON.stringify(schema, null, 2)
})

function generateBreadcrumbs(relativePath: string) {
  const parts = relativePath.replace(/\.md$/, '').split('/').filter(Boolean)
  const items = [
    {
      '@type': 'ListItem',
      position: 1,
      name: 'Home',
      item: 'https://docs.fabric4l.io/',
    },
  ]

  let currentPath = ''
  for (let i = 0; i < parts.length; i++) {
    currentPath += `/${parts[i]}`
    items.push({
      '@type': 'ListItem',
      position: i + 2,
      name: parts[i].replace(/-/g, ' ').replace(/^\w/, (c) => c.toUpperCase()),
      item: `https://docs.fabric4l.io${currentPath}`,
    })
  }

  return items
}
</script>
```

### Last Updated and Git History

```typescript
// docs-site/.vitepress/config.ts
export default defineConfig({
  lastUpdated: {
    text: 'Last updated',
    formatOptions: {
      dateStyle: 'long',
      timeStyle: 'short',
    },
  },

  themeConfig: {
    // Show "Last updated" footer on every page
    lastUpdatedText: 'Last updated',

    // Contributor information from git history
    contributors: true,
    contributorsText: 'Contributors',
  },
})
```

### robots.txt

```
# docs-site/public/robots.txt
User-agent: *
Allow: /

# Disallow versioned docs from being indexed as duplicates
Disallow: /v1.0/
Disallow: /v1.1/

# Sitemap
Sitemap: https://docs.fabric4l.io/sitemap.xml
```

---

## 8. Complete VitePress Configuration

```typescript
// docs-site/.vitepress/config.ts (complete)
import { defineConfig } from 'vitepress'
import { fileURLToPath } from 'url'
import { dirname, resolve } from 'path'

const __dirname = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
  // Site metadata
  lang: 'en-US',
  title: 'Fabric 4L Documentation',
  titleTemplate: ':title | Fabric 4L Docs',
  description: 'Enterprise agentic SaaS platform documentation. Six layers from ingestion to benchmarks.',

  // Source directory
  srcDir: '../docs',

  // Enable clean URLs (no .html suffix)
  cleanUrls: true,

  // Markdown configuration
  markdown: {
    theme: {
      light: 'github-light',
      dark: 'github-dark',
    },
    lineNumbers: true,
    config: (md) => {
      // Custom containers
      md.use(require('markdown-it-container'), 'tip')
      md.use(require('markdown-it-container'), 'warning')
      md.use(require('markdown-it-container'), 'danger')
      md.use(require('markdown-it-container'), 'details')
    },
  },

  // Theme configuration
  appearance: true,

  // Head tags
  head: [
    ['meta', { charset: 'utf-8' }],
    ['meta', { name: 'viewport', content: 'width=device-width, initial-scale=1.0' }],
    ['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }],
    ['link', { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' }],
    ['meta', { name: 'color-scheme', content: 'dark light' }],
    ['meta', { property: 'og:type', content: 'website' }],
    ['meta', { property: 'og:site_name', content: 'Fabric 4L Documentation' }],
    ['meta', { property: 'og:image', content: 'https://docs.fabric4l.io/og/og-home.png' }],
    ['meta', { property: 'og:image:width', content: '1200' }],
    ['meta', { property: 'og:image:height', content: '630' }],
    ['meta', { property: 'og:locale', content: 'en_US' }],
    ['meta', { name: 'twitter:card', content: 'summary_large_image' }],
    ['meta', { name: 'twitter:site', content: '@fabric4l' }],
    ['link', { rel: 'canonical', href: 'https://docs.fabric4l.io' }],
  ],

  // Last updated
  lastUpdated: {
    text: 'Last updated',
    formatOptions: {
      dateStyle: 'long',
      timeStyle: 'short',
    },
  },

  // Sitemap
  sitemap: {
    hostname: 'https://docs.fabric4l.io',
  },

  themeConfig: {
    // Logo
    logo: { src: '/logo.svg', width: 24, height: 24 },
    siteTitle: 'Fabric 4L',

    // Navigation
    nav: [
      { text: 'Tutorials', link: '/tutorials/getting-started', activeMatch: '/tutorials/' },
      { text: 'How-To', link: '/how-to/', activeMatch: '/how-to/' },
      { text: 'Reference', link: '/reference/faq', activeMatch: '/reference/' },
      { text: 'Explanations', link: '/explanations/architecture-decisions', activeMatch: '/explanations/' },
      { text: 'Migrations', link: '/migrations/v1.0-to-v1.1', activeMatch: '/migrations/' },
      {
        text: 'v1.2.0',
        items: [
          { text: 'v1.2.0 (Current)', link: '/' },
          { text: 'v1.1.x', link: 'https://v1-1.docs.fabric4l.io' },
          { text: 'v1.0.x', link: 'https://v1-0.docs.fabric4l.io' },
        ],
      },
    ],

    // Sidebar
    sidebar: {
      '/tutorials/': [
        {
          text: 'Tutorials',
          items: [
            { text: 'Getting Started', link: '/tutorials/getting-started' },
            { text: 'Custom Workflows', link: '/tutorials/custom-workflows' },
            { text: 'Knowledge Graph Querying', link: '/tutorials/knowledge-graph' },
            { text: 'Agent Configuration', link: '/tutorials/agent-config' },
          ],
        },
      ],
      '/how-to/': [
        {
          text: 'How-To Guides',
          items: [
            { text: 'Deploy to Kubernetes', link: '/how-to/deploy-kubernetes' },
            { text: 'Configure Feature Flags', link: '/how-to/feature-flags' },
            { text: 'Handle GDPR Requests', link: '/how-to/gdpr-requests' },
            { text: 'Run Chaos Experiments', link: '/how-to/chaos-engineering' },
            { text: 'Set Up Monitoring', link: '/how-to/monitoring-setup' },
          ],
        },
      ],
      '/reference/': [
        {
          text: 'Reference',
          items: [
            { text: 'FAQ & Troubleshooting', link: '/reference/faq' },
            { text: 'API Documentation', link: '/reference/api' },
            { text: 'Environment Variables', link: '/reference/environment-variables' },
            { text: 'CLI Reference', link: '/reference/cli' },
            { text: 'Configuration Schema', link: '/reference/configuration' },
          ],
        },
      ],
      '/explanations/': [
        {
          text: 'Explanations',
          items: [
            { text: 'Architecture Overview', link: '/explanations/architecture' },
            { text: 'Architecture Decisions', link: '/explanations/architecture-decisions' },
            { text: 'Six-Layer Model', link: '/explanations/six-layer-model' },
            { text: 'Security Model', link: '/explanations/security-model' },
          ],
        },
      ],
      '/migrations/': [
        {
          text: 'Migration Guides',
          items: [
            { text: 'v1.0 to v1.1', link: '/migrations/v1.0-to-v1.1' },
            { text: 'v1.1 to v1.2', link: '/migrations/v1.1-to-v1.2' },
            { text: 'Migration Template', link: '/migrations/template' },
          ],
        },
      ],
    },

    // Edit link
    editLink: {
      pattern: 'https://github.com/bmsull560/Fabric_4L/edit/main/docs/:path',
      text: 'Edit this page on GitHub',
    },

    // Social links
    socialLinks: [
      { icon: 'github', link: 'https://github.com/bmsull560/Fabric_4L' },
    ],

    // Search
    search: {
      provider: 'algolia',
      options: {
        appId: process.env.ALGOLIA_APP_ID || 'YOUR_APP_ID',
        apiKey: process.env.ALGOLIA_SEARCH_API_KEY || 'YOUR_SEARCH_API_KEY',
        indexName: 'fabric4l',
      },
    },

    // Footer
    footer: {
      message: 'Released under the MIT License.',
      copyright: `Copyright © ${new Date().getFullYear()} Fabric 4L Contributors`,
    },

    // Outline (right sidebar TOC)
    outline: {
      label: 'On this page',
      level: 'deep',
    },

    // Last updated
    lastUpdatedText: 'Last updated',

    // Contributors
    contributorsText: 'Contributors',

    // Return to top
    returnToTopLabel: 'Return to top',

    // Sidebar menu label
    sidebarMenuLabel: 'Menu',

    // Dark mode toggle labels
    darkModeSwitchLabel: 'Appearance',
    lightModeSwitchTitle: 'Switch to light theme',
    darkModeSwitchTitle: 'Switch to dark theme',
  },
})
```

---

## 9. Deployment Configuration

### GitHub Pages (Default)

```yaml
# .github/workflows/docs-deploy.yml
name: Deploy Documentation

on:
  push:
    branches: [main]
    paths:
      - 'docs/**'
      - 'docs-site/**'
      - '.github/workflows/docs-deploy.yml'

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Required for git-based lastUpdated

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: npm
          cache-dependency-path: docs-site/package-lock.json

      - name: Install dependencies
        working-directory: docs-site
        run: npm ci

      - name: Generate OG images
        working-directory: docs-site
        run: npm run docs:build:og
        env:
          ALGOLIA_APP_ID: ${{ secrets.ALGOLIA_APP_ID }}

      - name: Build documentation
        working-directory: docs-site
        run: npm run docs:build
        env:
          ALGOLIA_APP_ID: ${{ secrets.ALGOLIA_APP_ID }}
          ALGOLIA_SEARCH_API_KEY: ${{ secrets.ALGOLIA_SEARCH_API_KEY }}

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs-site/.vitepress/dist

  deploy:
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    runs-on: ubuntu-latest
    needs: build
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### Vercel (Alternative)

```json
// docs-site/vercel.json
{
  "buildCommand": "npm run docs:build && npm run docs:build:og",
  "outputDirectory": ".vitepress/dist",
  "installCommand": "npm ci",
  "framework": "vitepress",
  "rewrites": [
    {
      "source": "/og/:path*",
      "destination": "/og/:path*"
    }
  ],
  "headers": [
    {
      "source": "/og/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=86400, immutable"
        }
      ]
    },
    {
      "source": "/assets/(.*)",
      "headers": [
        {
          "key": "Cache-Control",
          "value": "public, max-age=31536000, immutable"
        }
      ]
    }
  ]
}
```

---

## 10. Environment Variables Reference

| Variable | Required | Description | Used In |
|----------|----------|-------------|---------|
| `ALGOLIA_APP_ID` | Yes (search) | Algolia application ID | `config.ts`, build scripts |
| `ALGOLIA_SEARCH_API_KEY` | Yes (search) | Algolia search-only API key | `config.ts` |
| `ALGOLIA_ADMIN_API_KEY` | CI only | Algolia admin key for crawler | CI/CD pipeline |
| `DOCS_BASE_URL` | No | Override base URL (default: `/`) | `config.ts` |
| `DOCS_VERSION` | No | Override displayed version | Version badge |
| `VITE_EXTRA_HEAD` | No | JSON string of extra head tags | `config.ts` |

---

## 11. File Structure

```
docs-site/
├── .vitepress/
│   ├── config.ts              # Main VitePress configuration
│   ├── theme/
│   │   ├── index.ts           # Theme entry point
│   │   ├── custom.css         # Custom styles and CSS variables
│   │   ├── Layout.vue         # Custom layout (wraps default)
│   │   └── components/
│   │       ├── VersionBanner.vue    # Version warning banner
│   │       ├── JsonLdSchema.vue     # Structured data
│   │       ├── LayerDiagram.vue     # Interactive 6-layer diagram
│   │       └── StatusBadge.vue      # Component status badges
│   └── dist/                  # Build output (generated)
├── scripts/
│   ├── generate-og-images.ts  # OG image HTML template generator
│   ├── render-og-images.ts    # HTML → PNG renderer (Satori)
│   └── build-versions.sh      # Multi-version build script
├── public/
│   ├── favicon.svg
│   ├── logo.svg
│   ├── apple-touch-icon.png
│   ├── og/                    # Generated OG images
│   └── robots.txt
├── package.json
├── vercel.json                # Vercel deployment config
└── README.md                  # Docs site development guide
```

---

## 12. Quick Start (Docs Development)

```bash
# Navigate to docs site
cd docs-site

# Install dependencies
npm install

# Start development server
npm run docs:dev

# Build for production
npm run docs:build

# Preview production build
npm run docs:preview

# Generate OG images
npm run docs:build:og
```

The development server starts at `http://localhost:5173` with hot module replacement for both content and configuration changes.
