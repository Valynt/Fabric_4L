---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Documentation Rules

This page defines the conventions for writing, structuring, and maintaining documentation in the ValuePact docs site. All durable pages must follow these rules so the documentation remains consistent, discoverable, and authoritative.

## Documentation structure (Diataxis)

The docs site follows the Diataxis framework, organizing content into four quadrants:

| Quadrant | Purpose | Example topics |
|---|---|---|
| **Tutorials** | Learning-oriented, step-by-step lessons | "Getting started with ingestion jobs" |
| **How-to guides** | Task-oriented, goal-driven procedures | "How to add a new benchmark dataset" |
| **Reference** | Information-oriented, authoritative lookup | Glossary, API specs, command reference |
| **Explanations** | Understanding-oriented, conceptual depth | "Why the six-layer architecture uses GraphRAG" |

!!! warning "Do not mix quadrants on the same page"
    A reference page should not become a tutorial. If a page starts accumulating procedural steps, split the steps into a how-to guide and link to it. This keeps each page optimized for its audience.

## Directory conventions

| Directory | Quadrant | Content |
|---|---|---|
| `docs-site/docs/tutorials/` | Tutorials | Onboarding, first-job walkthroughs |
| `docs-site/docs/how-to/` | How-to guides | Operational procedures, migration guides |
| `docs-site/docs/reference/` | Reference | API docs, glossary, command lists |
| `docs-site/docs/explanations/` | Explanations | ADRs, architecture overviews, deep dives |
| `docs-site/docs/fabric4l/behavior-contracts/` | Reference | Behavior contracts, test strategy, gates |
| `docs-site/docs/fabric4l/reference/` | Reference | Glossary, links, documentation rules |

Generated API docs live under `docs-site/docs/api/` and must not be hand-edited.

## Page template requirements

Every durable page must include the following elements in order:

1. **Front matter** — YAML metadata block (see below)
2. **H1 heading** — The page title
3. **Lead paragraph** — One or two sentences stating what the page covers and why it matters
4. **Body sections** — Organized by H2 and H3 headings
5. **Tables** — For structured data (markers, file paths, status codes)
6. **Admonitions** — For notes, warnings, tips, and dangers
7. **Related documentation** — Links to related pages at the bottom

## Front matter conventions

Every page must include the following front matter:

```yaml
---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---
```

| Field | Required | Values | Notes |
|---|---|---|---|
| `owner` | Yes | `platform-team`, `docs-team`, `security-leads`, `backend-leads`, `frontend-leads`, or a GitHub handle | The team or person accountable for accuracy |
| `status` | Yes | `draft`, `active`, `deprecated` | `draft` for new pages still in review; `active` for current truth; `deprecated` for historical preservation only |
| `last_reviewed` | Yes | `YYYY-MM-DD` | Update this date every time the page is substantively changed |

Optional fields:

| Field | Use |
|---|---|
| `review_cycle` | `quarterly`, `monthly`, `on-change` |
| `next_review` | `YYYY-MM-DD` |
| `tags` | Comma-separated list for discoverability |

## When to update docs

Update documentation in the same PR as the code change that makes it stale. Do not defer doc updates to a future sprint.

| Change type | Docs to update |
|---|---|
| Public API route added, changed, or removed | OpenAPI spec, API reference, behavior contract |
| Layer responsibility changes | Architecture explanations, layer-specific reference |
| Setup command or env var changes | Tutorials, how-to guides, `.env.example` |
| Agent behavior or output schema changes | Behavior contracts, agent workflow docs, frontend type docs |
| Contract shape changes | OpenAPI specs, JSON schemas, TypeScript types, TanStack Query hooks |
| Security or governance rule changes | Behavior contracts, security reference, runbooks |
| Production-readiness check changes | Gate registry, CI workflow docs |
| Frontend component or design system changes | `DESIGN.md`, component reference, a11y docs |

!!! tip "Docs are code"
    A PR is not complete if it changes behavior without updating the corresponding docs, contracts, and tests. This is enforced by `make verify` and the `contract-checks` CI job.

## Review process

1. **Author updates docs** in the same branch as the implementation.
2. **Peer review** includes a docs check: Are the changes accurate? Are related pages updated?
3. **CI preflight** runs `make check-conflict-markers` and link checks.
4. **Merge** only after docs and code are approved together.
5. **Post-merge**, the docs site rebuilds automatically from `main`.

### Review checklist for docs changes

- [ ] Front matter is present and correct (`owner`, `status`, `last_reviewed`)
- [ ] Lead paragraph explains the page's purpose
- [ ] Tables are used for structured data
- [ ] Admonitions are used for warnings, tips, and notes
- [ ] Code examples use the correct syntax and paths
- [ ] Links to related docs are included at the bottom
- [ ] No placeholder text ("Explain what this page documents")
- [ ] No product marketing copy
- [ ] No unverified assumptions

## Link conventions

### Internal links

Use relative Markdown links. Prefer paths that work regardless of the docs site base URL.

```markdown
[Behavior Contracts](../behavior-contracts/)
[Test Strategy](../behavior-contracts/test-strategy.md)
`AGENTS.md`
```

| Target | Link style |
|---|---|
| Another docs page | Relative path from current file |
| Repo root file | `../../../../FILENAME.md` |
| Source file | `../../../../services/layer4-agents/src/...` |

### External links

Use angle brackets for bare URLs or standard Markdown for titled links.

```markdown
<https://fastapi.tiangolo.com/>
[FastAPI docs](https://fastapi.tiangolo.com/)
```

## Code example standards

### Shell commands

Use `bash` for shell blocks. Include the working directory or service context if it matters.

```bash
# Run from repo root
make verify

# Run from a service directory
cd services/layer4-agents && pytest -m unit

# Frontend commands use pnpm
pnpm --dir apps/web run test
```

### Python code

Use `python` for Python blocks. Include imports if the snippet is meant to be copy-paste runnable.

```python
from value_fabric.shared.tenant import TenantContext

ctx = TenantContext(tenant_id="tenant-123", user_id="user-456")
repo.method(..., tenant_id=ctx.tenant_id)
```

### TypeScript / JSX

Use `tsx` or `typescript` as appropriate.

```tsx
import { PageShell } from "@/components/layout/PageShell";

export function IngestionPage() {
  return (
    <PageShell>
      <PageHeader title="Ingestion Jobs" />
    </PageShell>
  );
}
```

### File paths

Use inline code for paths. Use the canonical source-of-truth path, not a compatibility shim path.

```markdown
Canonical route file: `services/layer4-agents/src/api/routes/workflows.py`
OpenAPI spec: `contracts/openapi/layer4-agents.yaml`
```

## Admonition syntax

Use MkDocs Material admonitions to highlight important information.

| Type | Use for |
|---|---|
| `!!! note` | Neutral supplementary information |
| `!!! tip` | Best practices, shortcuts, optimization hints |
| `!!! warning` | Cautions that could lead to incorrect behavior |
| `!!! danger` | Serious risks: data loss, security breach, production outage |
| `!!! example` | Concrete examples |

Syntax:

```markdown
!!! warning "Custom title"
    Body text indented by four spaces.
```

## Tables

Use tables for structured data: markers, file paths, status codes, coverage gates, and layer responsibilities.

```markdown
| Column A | Column B |
|---|---|
| Value 1 | Value 2 |
```

Keep tables scannable. If a table exceeds six rows, consider splitting it or adding a filter description.

## Terminology and style

- Use "ValuePact" for the product and "Value Fabric" for the architecture/codebase.
- Use "tenant" (lowercase) unless it starts a sentence.
- Use "behavior contract" (two words) not "behavior-contract".
- Use "fail closed" not "fail-closed".
- Use sentence case for headings ("Test strategy" not "Test Strategy"), except for proper nouns.

## Related documentation

- [Links](links.md) — Internal and external reference directory
- [Glossary](glossary.md) — Platform terminology definitions
- `docs/development/DISCOVERY_MAP.md` — Issue-to-implementation routing
- `AGENTS.md` — Concise agent entry point
