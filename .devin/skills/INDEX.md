# Skills Index

This index catalogs all available skills in the `.devin/skills/` directory. Skills are reusable capability modules that agents can invoke programmatically.

For skill authoring specifications, see [SKILL_SCHEMA.md](./SKILL_SCHEMA.md).

---

## Authentication & Authorization

### clerk-auth
**Description:** Clerk authentication setup, configuration, and integration for React/Vite and Next.js projects
**When to Use:** Setting up Clerk auth, configuring OIDC/JWT for multi-tenancy, migrating from Auth0, adding sign-in UI components
**Side Effects:** write
**Related Workflow:** `/clerk-auth`

---

## Quality Debt & Code Hygiene

### repowise-production-readiness
**Description:** Systematic codebase transformation using repowise MCP intelligence to bring code from functional to production-ready through assessment, prioritization, and execution
**When to Use:** Preparing for production deployment, code health assessment, security audits, technical debt cleanup
**Side Effects:** read, write
**Related Workflow:** `/repowise-production-readiness`

### code-quality-improvement
**Description:** Focused production-quality pass for functional code with concrete quality gaps
**When to Use:** Code is functional but rough, fragile, or incomplete; code review identifies quality gaps; repowise reports maintainability or fragility findings
**Side Effects:** read, write
**Related Workflow:** `/code-quality-improvement`

### security-auditor
**Description:** Security auditing for CORS, API key leaks, penetration testing support, and vulnerability scanning
**When to Use:** Auditing CORS configuration, scanning for API key header leaks, checking for hardcoded secrets, validating WebSocket authentication, penetration testing support
**Side Effects:** none
**Related Workflow:** `/security-auditor`

### contract-enforcement-auditor
**Description:** Scan for contract violations and enforcement gaps across all 6 canonical contracts in contract.md
**When to Use:** Auditing compliance, checking ESLint rule status, verifying CI gate blocking, assessing gap between documented contracts and runtime enforcement
**Side Effects:** read
**Related Workflow:** `/contract-enforcement-auditor`

### dead-code-sweeper
**Description:** Identify and safely remove dead code including orphan pages, unreachable routes, unused exports, mock data blocks
**When to Use:** Cleaning up codebase, after major refactors, when FRONTEND_AUDIT_REPORT.md dead code list needs action
**Side Effects:** write
**Related Workflow:** `/dead-code-sweeper`

### deprecation-migrator
**Description:** Migrate deprecated anti-pattern instances to canonical replacements defined in contract.md
**When to Use:** Fixing tenant-id-as-parameter, direct-header-access, explicit-db-connect, inline-middleware patterns
**Side Effects:** write
**Related Workflow:** `/deprecation-migrator`

### dil-hook-scaffolder
**Description:** Scaffold TanStack Query hooks for DIL (Data Intelligence Layer) backend services with zero frontend integration
**When to Use:** Building frontend hooks for products, evidence, competitive-intel, roi, enrichment services
**Side Effects:** write
**Related Workflow:** `/dil-hook-scaffolder`

### facade-page-connector
**Description:** Rewire frontend pages from static/mock data or generic useWorkspaceTabQuery to real backend hooks
**When to Use:** Page renders hardcoded data, uses MOCK_ arrays, connects to generic workspace endpoint
**Side Effects:** write
**Related Workflow:** `/facade-page-connector`

### tool-contract-sync
**Description:** Audit and fix the three-way sync between tool implementations, skill definitions, and tool manifests
**When to Use:** Tools registered in ToolRegistry but missing skill MDs or JSON Schema manifests
**Side Effects:** write
**Related Workflow:** `/tool-contract-sync`

---

## Testing & Quality Assurance

### autonomous-test-assurance
**Description:** Level 4 autonomous agent for end-to-end test assurance with self-directed discovery and automatic recovery
**When to Use:** Comprehensive test suite transformation into production assurance without human checkpoints
**Related Workflow:** `/autonomous-test-assurance-agent`

### invariant-driven-testing
**Description:** Turn user workflows into testable business and security invariants through adversarial design, tenant isolation, full-stack automation, business-rule validation, failure injection, observability, environment engineering, and honest reporting
**When to Use:** A user workflow needs to be proven beyond the UI, including security boundaries, business rules, failure modes, and full-stack Playwright evidence
**Side Effects:** write

### test-quality-auditor
**Description:** Evaluate test suites against quality principles and safely rewrite tests for Python/pytest and TypeScript/Vitest
**When to Use:** Auditing test quality, applying targeted rewrites, resolving failures
**Related Workflow:** `/test-quality-remediation`

### pytest
**Description:** Python testing with pytest including fixtures, parametrization, markers, mocking, and async testing patterns
**When to Use:** Writing or refactoring Python tests

### playwright
**Description:** End-to-end test automation with Playwright for TypeScript, JavaScript, Python, Java, and C#
**When to Use:** E2E testing, local execution, cloud testing, POM patterns, CI/CD integration

---

## Code Review & Development

*(Note: Legacy jr-* workflow skills removed - not used in this repository)*

### pr-lifecycle
**Description:** Full PR pipeline — branch, commit, push, create PR, monitor CI, respond to review feedback, merge to main, and clean up
**When to Use:** Implementation is complete and work needs to go through the full PR pipeline to merge
**Side Effects:** exec

---

## Architecture & Governance

### pre-production-audit
**Description:** Conduct comprehensive pre-production audits of enterprise SaaS platforms
**When to Use:** Preparing for production deployment, reviewing code quality, assessing security posture
**Related Workflow:** `/pre-production-audit`

### contract-enforcement-auditor
*(See above under Quality Debt)*

### tool-contract-sync
*(See above under Quality Debt)*

### code-boundary-enforcement
**Description:** Enforce strict boundary discipline between domains, dependencies, and system layers
**When to Use:** Ensuring separation between internal domains, external dependencies, and system layers
**Related Workflow:** `/code-boundary-enforcement`

---

## SaaS & Billing

### stripe-integration
**Description:** Stripe billing integration for subscriptions, invoicing, usage metering, and customer portal
**When to Use:** Creating subscriptions, processing webhooks, metering usage, configuring customer portal, DSAR compliance
**Side Effects:** write
**Related Workflow:** `/stripe-integration`

---

## Frontend & UX

### agentic-ux
**Description:** UI patterns for agent-driven interfaces including streaming responses, tool execution visibility, confirmation flows, and progress indication
**When to Use:** Building AI-powered user interfaces

### login-signup-ux
**Description:** Best practices for designing, building, and testing login and signup flows with strong UX, accessibility, security, and OAuth integration
**When to Use:** Implementing authentication flows

### shadcn-fabric
**Description:** shadcn/ui usage guidelines for Value Fabric frontend
**When to Use:** Using shadcn/ui components

### facade-page-connector
*(See above under Quality Debt)*

### frontend-audit-refactor
**Description:** Audit a React/TypeScript frontend codebase and its backend API connections, then apply iterative refactoring loops
**When to Use:** Auditing frontend, reviewing backend connections, finding and removing stale code

### react-component-design
**Description:** Three-phase React component design workflow with chain-of-thought rigor
**When to Use:** Designing React components with agent skills

### component-self-review
**Description:** Post-generation code review workflow for enterprise-grade component validation
**When to Use:** After component generation but before merging

---

## AI & Orchestration

### orchestration
**Description:** LangGraph-based workflow orchestration for multi-step agent processes with state management, checkpointing, and human-in-the-loop integration
**When to Use:** Building multi-step AI workflows

### autonomous-test-assurance
*(See above under Testing & Quality Assurance)*

### memory-context
**Description:** Vector store and knowledge graph integration for semantic memory, conversation context management, and cross-session persistence
**When to Use:** Implementing memory systems for AI agents

### structured-outputs
**Description:** Pydantic-based structured output validation and LLM response parsing with OpenAI/Anthropic function calling and JSON schema enforcement
**When to Use:** Parsing structured outputs from LLMs

---

## Documentation

### technical-documentation
**Description:** Professional technical documentation generation and maintenance workflow
**When to Use:** Creating documentation for new systems or APIs, when docs are outdated, for handoffs
**Related Workflow:** `/technical_documentation`

### fumadocs
**Description:** Fumadocs documentation framework guidelines
**When to Use:** Working with Fumadocs documentation system
**Related Workflow:** `/fumadocs-drift-audit`

### cleanup-docs
**Description:** Monorepo documentation cleanup workflow
**When to Use:** Cleaning up scattered documentation, consolidating docs
**Related Workflow:** `/cleanup-docs`

---

## Infrastructure & DevOps

### bunnyshell
**Description:** Manage Bunnyshell cloud environments for development, staging, and production deployments
**When to Use:** Creating ephemeral dev environments, managing staging environments, automating production deployments, providing isolated environments for tenant onboarding
**Side Effects:** exec
**Related Workflow:** `/bunnyshell`

### observability-setup
**Description:** OpenTelemetry tracing, structured logging, circuit breakers, and monitoring configuration
**When to Use:** Migrating services to OTel, standardizing structured logging, implementing circuit breakers, setting up SLO tracking
**Side Effects:** write
**Related Workflow:** `/observability-setup`

### load-testing
**Description:** Load testing and performance validation for production launch readiness
**When to Use:** Running load tests at 2x traffic, validating p95 latency, verifying HPA scaling, monitoring error rates
**Side Effects:** exec
**Related Workflow:** `/load-testing`

### siem-integration
**Description:** SIEM integration for audit log streaming, security alerting, and compliance monitoring
**When to Use:** Configuring audit log streaming to SIEM, setting up security alerts, compliance monitoring for SOC 2
**Side Effects:** write
**Related Workflow:** `/siem-integration`

### gate-hardening
**Description:** Build machine-verifiable production release gate system using TDD
**When to Use:** Codebase needs ship/no-ship test gates for tenant isolation, state consistency, degraded dependencies
**Related Workflow:** `/gate-hardening`

### drift-assessment
**Description:** Multi-layer drift detection for API contracts, schemas, and behavior drift
**When to Use:** After code changes touching API routes or schemas, before releases, weekly drift reports
**Related Workflow:** `/drift-assessment`

### value-engine-e2e-validation
**Description:** Bootstrap the full development stack, seed a demo tenant and user, authenticate, execute the complete Value Engine workflow end-to-end
**When to Use:** End-to-end validation of the Value Engine

---

## Evaluation & Metrics

### evals
**Description:** Evaluation frameworks for agent performance, output quality, and extraction accuracy with metrics collection and regression testing
**When to Use:** Evaluating agent performance, measuring output quality

---

## Skill Maintenance

**Last Updated:** 2026-06-25

**Total Skills:** 43

**Skills with Full Frontmatter:** 11 (security-auditor, stripe-integration, observability-setup, load-testing, siem-integration, contract-enforcement-auditor, deprecation-migrator, dead-code-sweeper, bunnyshell, clerk-auth, invariant-driven-testing)

**Skills Needing Frontmatter Updates:** 30 remaining

**Note:** This index is generated manually. Consider automating this index generation by parsing SKILL.md frontmatter from all skill directories.
