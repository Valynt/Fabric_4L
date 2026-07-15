# AI Rules — Value Fabric (Fabric_4L)

> **This file extracts non-negotiable rules from existing documentation.**
> Sources: `AGENTS.md`, `SECURITY.md`, `DESIGN.md`, `packages/platform-contract/CONTRACT.md`.
> If any rule here conflicts with those sources, the source file wins.

---

## Package Manager

- **Always:** `pnpm install --frozen-lockfile`
- **Never:** `npm install`, `yarn`, or any npm/yarn command
- Lockfile changes require explicit justification

---

## Tenant Isolation (Security-Critical)

- Every data read/write must be scoped by `tenant_id`
- Use `RequestContext` from `GovernanceMiddleware` — never extract `tenant_id` from raw request payloads
- PostgreSQL RLS is the enforcement layer; the application layer must also enforce
- Missing tenant context → reject the request (fail-safe default)

```python
# Correct pattern
from shared.identity.dependencies import get_request_context
from shared.identity.context import RequestContext

@router.get('/items')
async def list_items(ctx: RequestContext = Depends(get_request_context)):
    tenant_id = ctx.tenant_id  # Guaranteed to be set; never from request body
```

---

## Contract-First Development

- Declare tool schemas, agent outputs, and API response shapes in `contracts/` **before** implementing
- Update OpenAPI spec, JSON schema, TypeScript types, TanStack hooks, and tests together
- Contract tests must pass before merging any API change
- Never silently change API response shapes

---

## Security Rules

- No secrets in commits — use Infisical or local uncommitted `.env` files
- Dev auth bypass (`DISABLE_AUTH=true`) must never be committed to non-dev configs
- JWT tokens must be validated; never trust unsigned or self-signed tokens in production
- Exposed tokens must be revoked immediately (see `SECURITY.md`)
- SSRF protection: validate all outbound URLs against allowlists
- Rate limiting: enforce at the API gateway and per-service

---

## Code Quality

- Python: mypy strict mode, ruff linting, bandit security scanning
- TypeScript: strict mode, no `any` without documented rationale
- No `# noqa` or `type: ignore` without a comment explaining why
- No broad rewrites — make the smallest safe change
- No deleted tests — if a test is wrong, fix the test or the code, not both

---

## Frontend Rules (apps/web)

- Read `DESIGN.md` and `apps/web/DESIGN.md` before any frontend change
- Use existing shadcn/ui components — do not introduce new UI libraries
- Preserve horizontal tabs / right-rail layout conventions
- Server state lives in React Query; client state in Zustand
- Test behavior, not implementation details

---

## Git and PR Rules

- Conventional commits: `feat|fix|docs|test|chore|refactor|perf|ci(scope): message`
- AI co-authoring trailer: `Co-authored-by: <agent-name> <no-reply@...>`
- Never push directly to `main`
- Never perform destructive git operations (`--force`, `reset --hard` on shared branches)
- Every PR must include: summary, validation commands run, risks, rollback plan

---

## Stop Conditions (Human Approval Required)

Stop and request human approval before:
- Rotating or revoking live secrets
- Changing GitHub branch protection rules
- Changing required CI check names
- Modifying auth, RBAC, tenant isolation, or production bypass logic
- Updating `CODEOWNERS` with real team names
- Changing public API contracts
- Changing database migrations
- Broad refactors of Layer 4 agents or tenant-sensitive code
