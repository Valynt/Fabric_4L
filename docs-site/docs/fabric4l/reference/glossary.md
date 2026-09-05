---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Glossary

This glossary defines terms used across the ValuePact platform, its documentation, and its behavior contracts. Definitions are authoritative: when a contract or gate references a term, it uses the meaning given here.

## Platform terminology

| Term | Definition |
|---|---|
| **ValuePact** | The commercial platform built on the Value Fabric six-layer architecture. It provides intelligent data ingestion, ontology-guided extraction, knowledge graph analysis, agentic workflows, ground truth validation, and benchmarking. |
| **Value Fabric** | The internal engineering name for the platform architecture and monorepo. "ValuePact" is the product; "Value Fabric" is the codebase and pipeline. |
| **Six-layer architecture** | The platform pipeline: L1 Ingestion → L2 Extraction → L3 Knowledge → L4 Agents → L5 Ground Truth → L6 Benchmarks. Each layer has a dedicated service, port, and responsibility. |
| **Pack** | A domain extension that configures the platform for an industry or use case. Packs may include ontologies, formulas, variables, benchmarks, personas, and value drivers. They live in `packs/` and are loaded at runtime. |
| **Tenant** | An isolated organizational boundary. Every data read and write must be scoped to a tenant. Tenants are identified by `tenant_id` extracted from authenticated context, not from request bodies. |
| **Tenant context** | The authenticated scope (tenant_id, user_id, roles) that travels with every request through middleware, services, repositories, and graph queries. |
| **Tenant isolation** | The first-class invariant that Tenant A cannot read, write, or infer data belonging to Tenant B. Enforced by RLS, repository filters, graph query predicates, and cache key scoping. |

## Architecture terminology

| Term | Definition |
|---|---|
| **Layer** | A major stage in the six-layer pipeline. Each layer owns a service directory under `services/`, a port (8001–8006), and a distinct responsibility. |
| **Service** | A deployable backend unit. The maintained services are `layer1-ingestion`, `layer2-extraction`, `layer3-knowledge`, `layer4-agents`, `layer5-ground-truth`, `layer6-benchmarks`, and `api` (shared gateway). |
| **Source-of-truth path** | The canonical runtime path for a module. For example, Layer 4 runtime code lives in `services/layer4-agents/src/layer4_agents/`. Compatibility shims may redirect from legacy paths, but new code must use the canonical path. |
| **Compatibility shim** | A redirect or adapter that preserves imports from legacy paths (e.g., `value_fabric.layer4.*`) while the canonical path is elsewhere. Shims are tracked in `docs/governance/compatibility-debt-registry.md`. |
| **API gateway** | The shared `services/api/` entry point that enforces authentication, tenant context extraction, rate limiting, and routing to L1–L6. |
| **Middleware** | Interceptors that run before route handlers, responsible for auth validation, tenant context attachment, audit logging, and governance checks. |

## Layer-specific terminology

| Term | Definition |
|---|---|
| **Ingestion job** | A Layer 1 unit of work that crawls or receives data, places it on a Celery queue, and tracks state in PostgreSQL. Jobs are tenant-scoped and carry provenance metadata. |
| **Ontology** | A formal schema that defines entity types, relationships, and constraints used by Layer 2 to guide extraction. Ontologies are versioned and can be pack-specific. |
| **RDF / OWL** | Resource Description Framework and Web Ontology Language. Layer 2 can emit structured extraction results as RDF/OWL for downstream semantic interoperability. |
| **Provenance** | Metadata that records the origin, transformation history, and responsible actor for a piece of data. Required for audit and Layer 5 validation. |
| **Knowledge graph** | The Neo4j-hosted graph representation of entities, relationships, and semantic properties built by Layer 3. |
| **GraphRAG** | Graph Retrieval-Augmented Generation. A Layer 3 technique that combines graph traversal with vector similarity to retrieve context for agent workflows. |
| **Hybrid retrieval** | Layer 3's combination of keyword search, vector similarity (pgvector), and graph traversal to answer complex queries. |
| **Subgraph API** | A Layer 3 endpoint family that returns bounded graph views (subgraphs) scoped to a tenant and query context. |
| **LangGraph** | The framework used by Layer 4 to define agent workflows as state machines with nodes, edges, and conditional transitions. |
| **Checkpoint** | A persisted snapshot of a Layer 4 workflow state at a specific node. Checkpoints enable resume after interruption or failure. |
| **ROI calculator** | A Layer 4 business-case tool that computes return-on-investment estimates from extracted value drivers and benchmark data. |
| **TruthObject** | A Layer 5 validated claim object. It contains a proposition, supporting evidence, a maturity score, and an audit trail. |
| **Maturity ladder** | A Layer 5 framework that scores organizational capabilities across levels (e.g., ad-hoc → defined → managed → optimizing). |
| **Benchmark dataset** | A Layer 6 collection of peer data, statistical baselines, and comparison policies used to validate claims and score maturity. |
| **Dataset lineage** | The complete provenance chain for a benchmark dataset, including sources, transformations, and approval history. |

## Testing terminology

| Term | Definition |
|---|---|
| **Behavior contract** | An executable definition of intended behavior: an allowed test, a denied test, an expected failure mode, and a gate. |
| **Behavior-first testing** | The strategy of encoding intended and denied behavior as tests before claiming the behavior is production-ready. |
| **Critical behavior** | A behavior whose failure would affect tenant isolation, auth, data privacy, billing, availability, security, or compliance. |
| **Hostile test** | A test that attempts an action that must be denied and asserts the exact failure mode. Also called a denied test or negative test. |
| **Readiness ladder** | The four-stage progression from static contract resolution to production readiness: Static → Executed → Audited → Production. |
| **Readiness gate** | A Makefile target or CI job that enforces a set of invariants. Example: `make production-readiness-gate`. |
| **Drift** | Architectural divergence between components that should remain aligned: API schemas vs. frontend types, OpenAPI specs vs. route handlers, agent outputs vs. UI expectations. |
| **Contract drift** | Silent divergence between a contract (OpenAPI, JSON Schema, behavior contract) and its implementation. |
| **Schema drift** | Silent divergence between a database model and its migration, or between a Pydantic model and its JSON Schema. |
| **Tenant boundary** | The logical perimeter that separates one tenant's data and operations from another's. Tests that validate this perimeter are marked `tenant_boundary`. |
| **Fail closed** | The default security posture: if a request cannot be explicitly authorized, it is denied. Untested behavior is assumed unsafe. |
| **Behavior debt** | A coverage gap where a critical behavior lacks an allowed or denied test. Tracked with `BEHAVIOR-DEBT-*` tickets and `TODO(behavior-debt)` comments. |
| **Waiver** | A time-boxed, owned exception that permits a skip or xfail in the readiness audit without producing RED. |
| **Benign skip** | A skip that is structurally not-applicable (e.g., a read-only endpoint has no write methods to test). Does not downgrade GREEN. |

## Frontend terminology

| Term | Definition |
|---|---|
| **PageShell** | The canonical layout wrapper for application pages. Reuse it instead of creating one-off page wrappers. |
| **Right rail** | The right-side panel used for detail views, agent streams, and contextual information. Preferred over modal-heavy flows. |
| **Horizontal tabs** | The primary navigation pattern inside major workspaces. Preferred over vertical side navigation at the workspace level. |
| **TanStack Query** | The data-fetching library used for server state in the frontend. All server data should be fetched through Query hooks, not raw `fetch`. |
| **Zustand** | The lightweight state manager used for client-side state where TanStack Query is insufficient. |
| **shadcn/ui** | The component library foundation built on Radix UI and Tailwind CSS. Prefer shadcn primitives over custom components. |

## Security and compliance terminology

| Term | Definition |
|---|---|
| **RLS** | Row-Level Security. PostgreSQL feature used to enforce tenant isolation at the database layer. |
| **OWASP Top 10** | The ten most critical web application security risks. The platform maintains tests marked `security` that validate mitigations for each category. |
| **Auth bypass** | A development-only mechanism that disables authentication for local testing. Controlled by flags like `DEV_AUTH_BYPASS`. Must never be enabled in production. |
| **ProductionSafetyValidator** | A startup-time validator that checks for unsafe defaults (e.g., dev auth bypass flags) and causes the process to exit if they are present in production-like environments. |
| **Audit log** | An append-only record of sensitive actions, including actor, tenant, timestamp, and action outcome. Required for compliance and incident response. |
| **Correlation ID** | A unique identifier attached to every request that propagates across services, logs, and traces for end-to-end debugging. |

## Tooling and infrastructure terminology

| Term | Definition |
|---|---|
| **pnpm** | The mandatory package manager for the monorepo. npm and yarn are prohibited. Version is pinned at 10.18.1. |
| **Infisical** | The secrets management platform used for local development and CI/CD secret injection. |
| **Alembic** | The database migration tool used by Python services. Each service manages its own migration path. |
| **Celery** | The distributed task queue used by Layer 1 for background job processing. Backed by Redis. |
| **Playwright** | The browser automation framework used for Layer 1 crawling and frontend E2E testing. |
| **pytest** | The Python test runner. Configured in `pytest.ini` with custom markers, timeout, and test paths. |
| **MkDocs Material** | The documentation site generator and theme used for `docs-site/`. Supports admonitions, tables, code blocks, and navigation. |

## Related documentation

- [Links](links.md) — Internal and external references
- [Documentation Rules](documentation-rules.md) — Conventions for writing and maintaining docs
- `AGENTS.md` — Concise agent entry point and progressive-disclosure map
