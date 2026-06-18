# Sub-plan F: Simplify Docker Compose Stack (#8)

**Goal:** Replace 17 standalone compose files and multiple env variants with a base compose plus small environment-specific overlays.

**Canonical structure**
- `docker-compose.base.yml` — shared services: postgres, redis, neo4j, minio, keycloak.
- `docker-compose.override.<env>.yml` — environment-specific layer services and hardening.
- `.env.example` remains the committed reference; `.env.generated` flow is documented or removed if Infisical is canonical.

**Files to inspect / modify**
- `docker-compose.dev.yml`
- `docker-compose.full.yml`
- `docker-compose.live.yml`
- `docker-compose.backend-integrated.yml`
- `docker-compose.contract.yml`
- `docker-compose.e2e.yml`
- `docker-compose.release-smoke.yml`
- Other `docker-compose*.yml` files at root
- `.env.example`, `.env.generated`, `.env.dev.example`, `.env.smoke.template`, `.env.production-compose.template`
- `package.json` scripts that reference compose files
- `docs/development/COMMANDS.md`, `docs/getting-started/environment.md`

**Approach**
1. Extract shared infrastructure services into `docker-compose.base.yml`.
2. For each environment, create a minimal override file containing only the differences (layer services, env vars, volumes, ports).
3. Delete the standalone compose files once overrides are validated.
4. Update `package.json` scripts to use the new `-f docker-compose.base.yml -f docker-compose.override.<env>.yml` pattern.
5. Document the single command: `docker compose -f docker-compose.base.yml -f docker-compose.override.dev.yml up`.

**Validation**
- `docker compose -f docker-compose.base.yml -f docker-compose.override.dev.yml config` renders without errors.
- `docker compose -f docker-compose.base.yml -f docker-compose.override.full.yml config` renders without errors.
- `pnpm env:dev && docker compose ... up -d` boots the local stack.
- `make migrate` still runs against the dev stack.

**Rollback**
Restore any deleted compose file from git history if an environment is broken.

**Risks**
- Environment-specific networking, secrets, or volume mounts may be lost during extraction.
- Developers relying on old compose filenames need updated commands.
