# Prompt: Fumadocs Documentation Drift Audit

When reviewing docs drift around Fumadocs:

## 1. Identify the Baseline

Find the last commit where Fumadocs packages or docs-framework wiring last materially changed.

**Look for:**
- Changes to `fumadocs-core`, `fumadocs-ui`, `fumadocs-mdx`, `fumadocs-cli` in `package.json`
- Modifications to content source configuration (`source.config.ts`, `lib/source.ts`)
- Layout changes (`app/layout.tsx`, `app/docs/layout.tsx`)
- Route handler updates (`app/docs/[[...slug]]/page.tsx`)
- MDX component changes (`components/mdx.tsx`)
- Navigation structure changes (`meta.json`, `_meta.tsx`)
- OpenAPI generation changes
- Theme/style modifications

## 2. Diff BASELINE..HEAD

Review all code changes that affect:
- **Routes** - Added/removed/renamed page routes
- **Layouts** - Layout component structure, providers, wrappers
- **Page Generation** - Dynamic routes, params handling, data fetching
- **Source Loading** - Content discovery, parsing, frontmatter handling
- **MDX Components** - Component availability, props, exports
- **OpenAPI Generation** - Schema changes, endpoint documentation
- **Navigation** - Sidebar, breadcrumbs, page tree structure
- **Examples Embedded in Code** - Component demos, usage patterns

Do not only review docs files. Review all code changes with documentation impact.

## 3. Map Impact Areas

Sort changes into categories:
- **Layout** - Page structure, navigation appearance
- **Navigation** - Sidebar, breadcrumbs, page tree
- **MDX Components** - Component availability, props, usage patterns
- **Source Loading** - Content discovery, frontmatter handling
- **OpenAPI** - API documentation accuracy
- **Theme** - Visual appearance, color schemes
- **Search** - Search functionality, indexing
- **Build** - Build process, output structure
- **Authoring Flow** - Content creation workflow

## 4. Check Diátaxis-Fumadocs Alignment

**Post-migration maintenance:** Ensure Fumadocs presentation matches Diátaxis content semantics.

**Mental model:**
```
Diátaxis (WHAT) → Fumadocs (HOW)
/tutorials/      → Ordered nav, next-links, linear flow
/how-to/         → Task-grouped, searchable, minimal noise
/reference/      → Dense layout, API tables, completeness
/explanation/    → Essay layout, minimal interruptions
```

**Drift indicators:**
| Diátaxis Type | Expected Presentation | Drift |
|---------------|----------------------|-------|
| **Tutorials** | Sequential nav, "next" buttons | Flat nav breaks flow |
| **How-to** | Prominent search, task titles | Buried in mixed nav |
| **Reference** | Dense, tabbed, scannable | Blog-style spacing |
| **Explanation** | Essay layout, light chrome | Heavy sidebar/nav |

## 5. Collect Topic Documentation

Gather every doc related to the requested TOPIC:
- MDX pages in `content/docs/` or `docs/`
- README files
- Internal notes and specs
- Code comments that are effectively authoritative

## 6. Cross-Check Docs Against Code

**Prefer the code as the source of truth** when docs conflict.

**Check for:**
- Renamed props (documented vs actual component props)
- Moved routes (documented URLs vs actual routes)
- Changed examples (code in docs vs current usage)
- Broken screenshots (UI appearance vs screenshots)
- Outdated assumptions (file paths, commands, requirements)

## 7. Cross-Check Against Fumadocs Patterns

Not to force upgrades, but to spot where your docs or implementation are now fighting the framework.

**Fumadocs emphasizes:**
- Layouts (`DocsLayout`, `HomeLayout`)
- OpenAPI integration
- Access control patterns
- i18n configuration
- Content source adapters
- Search integration

**Look for conflicts:**
- Custom implementations of Fumadocs-provided features
- Non-standard MDX patterns
- Manual navigation when file-based would work

## 8. Flag Issues

| Issue Type | What to Flag |
|------------|--------------|
| **Stale commands** | CLI commands that no longer work |
| **Stale component names** | Renamed or removed components |
| **Stale file paths** | Moved or reorganized content |
| **Moved routes** | URL changes without redirects |
| **Hidden prerequisites** | Requirements not documented |
| **Incomplete examples** | Code that won't run as written |
| **Duplicate/overlapping docs** | Same topic covered multiple times |
| **Content/UI mismatch** | Docs describe different UI than exists |
| **Diátaxis presentation drift** | Tutorials without ordering, reference using blog layout, etc. |

## 9. Deliver Remediation Pack

**Required deliverables:**

### Executive Summary
- What changed (high-level)
- What is stale
- What is missing
- What to update first

### Prioritized Findings
Rank by **user impact × effort**:
- P0: Broken/misleading — fix immediately
- P1: Outdated but functional — schedule soon
- P2: Missing coverage — backlog

### Exact Files to Update
List with specific paths and change types.

### Draft Markdown Updates
Ready-to-paste fixes for top 3 highest-value issues.

## Constraints

> Do not treat package version changes alone as meaningful. The review is only complete after checking route structure, source loading, navigation tree generation, MDX components, and API/OpenAPI generation.

This prevents shallow audits.
