# Value Fabric Roadmap

> **Audit note (2026-07-18):** The duplicate redirect at `docs/roadmap.md` was archived to `archive/planning-audit-2026-07-18/docs/roadmap.md` because it only pointed back to this file.

This root roadmap is the canonical product roadmap for the platform.

- Canonical launch readiness: [docs/readiness/current.md](docs/readiness/current.md)
- Launch blocker register: [docs/launch/launch-blocker-register.md](docs/launch/launch-blocker-register.md)

Do not declare an independent launch readiness percentage in this file. The
canonical readiness percentage, when present, belongs in
`docs/readiness/current.md` and must remain aligned with the readiness
consistency gate.

## v1.0 — Launched (2026-05-12)

- React + TypeScript frontend with full workspace workflows
- FastAPI multi-layer backend with PostgreSQL + Neo4j persistence
- Deterministic ROI calculations and business case generation
- Multi-tenant isolation via PostgreSQL RLS and GovernanceMiddleware
- Governance review queues and append-only audit log
- LangGraph agent orchestration (Layer 4)
- Value pack integration (life-sciences, manufacturing, software)
- Kubernetes production deployment (6-layer microservices)
- Clerk authentication + Keycloak/OIDC enterprise SSO
- Prometheus + Grafana observability stack

## v1.1 — Released (2026-05-14)

- ADR-027 canonical path migration (Layers 2, 3, 4, 6)
- OIDC/JWT validation hardening
- Layer 4 contract fixes and import topology enforcement
- 24 frontend security vulnerability patches

## v1.2 — Released (2026-06-25)

- Official launch polish: branding, metadata, and documentation cleanup
- Version alignment across all service packages
- Removal of stale scratch files and placeholder content

## Q3 2026

- Advanced evidence provenance and ground-truth validation
- Real-time collaboration and notifications
- Mobile-responsive optimizations
- Enhanced CRM webhook integrations (Salesforce, HubSpot)

## Q4 2026

- Advanced analytics and reporting dashboards
- Custom formula builder UI enhancements
- Value realization tracking and dashboards
- Expansion revenue signals and churn prediction

## Future

- Industry marketplace for Value Packs
- Partner ecosystem integrations
- White-label capabilities
- Advanced AI reasoning and planning
