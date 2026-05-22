# Changelog

All notable changes to Value Fabric are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Changed
- **ADR-027 Layer 2 migration**: Moved `alignment.py`, `coreference.py`, `validation.py`, and `api/` wrappers from `value_fabric/layer2/` to `services/layer2-extraction/src/layer2_extraction/`. Deleted empty stale directories (`coreference/`, `db/`, `extraction/`). `value_fabric/layer2/` now contains only the path-appender shim `__init__.py`.
- **ADR-027 Layer 6 migration**: Converted `value_fabric/layer6/` from active implementation namespace to path-appender shim. All implementation files (`api/`, `config.py`, `database.py`, `metrics/`, `models/`, `observability/`, `repositories/`, `settings.py`, `shared_bootstrap.py`) now live exclusively in `services/layer6-benchmarks/src/`.
- **ADR-027 Layer 1/L3 cleanup** (completed 2026-05-14): Removed legacy namespaces `value_fabric/layer1_ingestion/` and `value_fabric/layer3_knowledge/`. Deleted 20 empty stale subdirectories under `value_fabric/layer3/`.
- **`check_duplicate_source_trees.py`**: Updated `LAYER_MAP` to reflect ADR-027 service-first model (canonical = `services/`, compat = `value_fabric/`). Added path-appender shim pattern recognition alongside re-export shim pattern.
- **`check_layer3_settings_shim_drift.py`**: Updated canonical settings path from `value_fabric/layer3/config/settings.py` to `services/layer3-knowledge/src/config/settings.py` per ADR-027.
- **`check_security_regressions.py`**: Baselined 18 pre-existing Layer 3 findings (Redis KEYS usage, infra URI exposure, fake health check timing) with documented remediation tracking.
- **`tests/security/test_tenant_context_contract.py`**: Fixed hardcoded `value_fabric/shared/identity/` paths to canonical `packages/shared/src/value_fabric/shared/identity/`. Increased `dispatch` search window to 8000 chars to cover full method body.
- **`tests/ci/test_env_contract_validator_i01.py`**: Fixed contradictory assertion (`"../../.env.example" not in source` was wrong; removed duplicate check).
- **`tests/contract/test_*.py`** (8 files): Fixed stale `)` syntax errors introduced when skip markers were added.
- **`tests/contract/test_*.py`** (5 files): Added `try/except ImportError` guards for module-level service-stack imports that prevented collection without live services.
- **`tests/baselines/deprecation-budget.json`**: Removed 2 stale entries referencing deleted `value_fabric/layer1_ingestion/__init__.py` and `value_fabric/layer3_knowledge/__init__.py`.
- **`services/layer3-knowledge/src/migrations/`**: Updated docstring `python -m` invocation paths from deleted `value_fabric.layer3_knowledge` namespace to canonical service path.

### Added
- **`scripts/ci/check_stale_namespace_dirs.py`**: New guard that verifies deleted legacy namespace directories (`value_fabric/layer1_ingestion/`, `value_fabric/layer3_knowledge/`, `value_fabric/layer2_extraction/`, `value_fabric/layer6_benchmarks/`) are not reintroduced, and that shim-only directories contain only `__init__.py`.
- **`.github/workflows/k8s-validation.yml`**: New workflow validating K8s base and overlay manifests (`kubectl kustomize` dry-run) on every PR touching `k8s/`. Includes legacy namespace reference check.
- **`docs/architecture/adr-027-layer3-canonical-path.md`**: Added Production Readiness Completion section with namespace removal changelog, new CI gates table, deferred items register, and rollback plan.
- **`docs/governance/production-readiness-live-env-deferred.md`**: Track B deferred items register for live-environment validation.

### CI / Guardrails
- Extended `scripts/ci/check_layer1_imports.py` to detect stale implementation files in shim-only directories (`value_fabric/layer2/`, `value_fabric/layer6/`).
- Updated `scripts/ci/check_layer56_shims.py` to verify `value_fabric/layer6/` is shim-only (not service-tree shims).
- Added 8 new critical gates to `.github/workflows/critical-gates.yml`: `adr027-layer3-imports`, `adr027-layer4-imports`, `adr027-layer5-shim`, `adr027-deprecated-namespaces`, `adr027-duplicate-source-trees`, `alembic-head-consistency`, `env-contract-structure`, `stale-namespace-dirs`.
- Added `check_stale_namespace_dirs.py` step to `repo-hygiene.yml`; added `value_fabric/**` to path triggers.
- Fixed `critical-gates.yml` gate commands referencing non-existent test files (`test_tenant_isolation_hostile.py` → `test_tenant_isolation.py` + `test_graph_tenant_hostile_regression.py`; `test_auth_endpoint_coverage.py` → `test_sensitive_route_audit_coverage.py`).
- Canonical launch readiness source set to `docs/readiness/current.md`; roadmap launch criteria references now point to canonical readiness.

## [1.0.0] — 2026-05-12

### Deployment Target
- Environment: production
- Namespace: fabric-4l-prod
- Registry: ghcr.io/value-fabric

### Infrastructure
- Kubernetes manifests validated via `kubectl kustomize`
- Production overlay: 3,175 lines of rendered manifests
- HPA, PDB, NetworkPolicies, and monitoring configured
- ExternalSecrets configured for secret management

### Services
| Service | Replicas | Layer |
|---------|----------|-------|
| layer1-ingestion | 3 | L1 |
| layer2-extraction | 3 | L2 |
| layer3-knowledge | 3 | L3 |
| layer4-agents | 3 | L4 |
| layer5-ground-truth | 2 | L5 |
| layer6-benchmarks | 2 | L6 |
| frontend (web) | 2 | UI |

### Fixes
- Fixed K8s overlay patches: corrected container name (`frontend` → `web`)
- Fixed K8s overlay patches: corrected ConfigMap name (`global-config` → `value-fabric-config`)
- Fixed K8s overlay patches: added missing namespace metadata
- Aligned all version sources to 1.0.0

## [0.9.0] — 2026-04-12

### Added
- Layer 5 Ground Truth store (100% complete, production-ready)
- Layer 4 Agent Engine with LangGraph orchestration, pause/resume controls
- Frontend: Command Center, Graph Explorer, admin screens
- Governance middleware: JWT auth, RBAC, API key management
- Audit log (append-only, DB trigger-enforced) — `audit_events` table
- Alembic migrations for governance tables (tenants, users, api_keys) and audit_events
- Monitoring stack: Prometheus, Grafana dashboards, alerting rules
- Kubernetes manifests for all layers + external secrets (Vault integration)
- Domain packs: life-sciences, manufacturing, software

### Changed
- Shared identity library (`packages/shared/src/value_fabric/shared/identity/`) promoted to single cross-layer auth package

### Fixed
- Pagination contract consistency across all layer APIs
- Graph traversal depth limit handling in Layer 3

---

## [0.8.0] — 2026-03-15

### Added
- Layer 3 Knowledge Graph API (Neo4j + pgvector + GraphRAG hybrid retrieval)
- Layer 2 Ontology-guided extraction pipeline (LLM + RDF/OWL generation)
- Layer 1 Intelligent ingestion service (Playwright + Redis + PostgreSQL)
- Agent behavior artifacts: `layer4-agents/agents/`, `layer4-agents/skills/`, `layer4-agents/workflows/`
- Business Analyst Agent and Knowledge Navigator Agent definitions
- 12 atomic skill definitions (evaluate_formula, semantic_search, graph_traverse, etc.)
- CI pipeline: lint, type-check, 80%+ coverage gate per layer
- Docker Compose for local full-stack development
- `AGENTS.md` — contributor guide for AI agents and developers (P0 MAS best practice)
- `contracts/tool-manifests/` — versioned JSON Schema tool manifests for all agent skills
- `contracts/jsonschema/` — shared data model schemas (entities, events)
- `tests/evals/` — golden-trace agent evaluation framework with fixtures
- Root `README.md` with repo map and quickstart
- `CONTRIBUTING.md` — developer setup, coding standards, PR conventions
- `SECURITY.md` — supported versions and vulnerability reporting
- `CHANGELOG.md` — SemVer-based release history
- `Makefile` — developer ergonomics (`verify`, `test`, `lint`, `build`, `migrate`, `evals`)
- `.github/dependabot.yml` — automated dependency updates (pip, npm, GitHub Actions)
