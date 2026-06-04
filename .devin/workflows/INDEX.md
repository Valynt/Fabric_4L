# Workflows Index

This index catalogs all available workflows in the `.windsurf/workflows/` directory. Workflows are orchestration patterns with explicit state machines for human-driven processes.

For workflow authoring specifications, see [WORKFLOW.md](./WORKFLOW.md).

---

## Agent Infrastructure & Meta Workflows

### value-fabric-harness
**Description:** Layer-scoped context assembly and pre-edit boundary guards for safe, contract-aligned development
**When to Use:** At the start of every coding task in the Fabric_4L monorepo to inject governance context and catch drift before editing
**Related Skill:** `skills/jr-plan/SKILL.md` (plan decomposition)

---

## Quality Debt & Code Hygiene

### contract-enforcement-auditor
**Description:** Scans for contract violations and enforcement gaps across all 6 canonical contracts in contract.md
**When to Use:** Auditing compliance, checking ESLint rule status, verifying CI gate blocking, assessing gap between documented contracts and runtime enforcement
**Related Skill:** `skills/contract-enforcement-auditor/SKILL.md`

### dead-code-sweeper
**Description:** Identifies and safely removes dead code including orphan pages, unreachable routes, unused exports, mock data blocks
**When to Use:** Cleaning up codebase, after major refactors, when FRONTEND_AUDIT_REPORT.md dead code list needs action
**Related Skill:** `skills/dead-code-sweeper/SKILL.md`

### deprecation-migrator
**Description:** Migrate deprecated anti-pattern instances to canonical replacements defined in contract.md
**When to Use:** Fixing tenant-id-as-parameter, direct-header-access, explicit-db-connect, inline-middleware patterns
**Related Skill:** `skills/deprecation-migrator/SKILL.md`

### dil-hook-scaffolder
**Description:** Scaffolds TanStack Query hooks for DIL (Data Intelligence Layer) backend services with zero frontend integration
**When to Use:** Building frontend hooks for products, evidence, competitive-intel, roi, enrichment services
**Related Skill:** `skills/dil-hook-scaffolder/SKILL.md`

### facade-page-connector
**Description:** Rewires frontend pages from static/mock data or generic useWorkspaceTabQuery to real backend hooks
**When to Use:** Page renders hardcoded data, uses MOCK_ arrays, connects to generic workspace endpoint
**Related Skill:** `skills/facade-page-connector/SKILL.md`

### tool-contract-sync
**Description:** Audit and fix the three-way sync between tool implementations, skill definitions, and tool manifests
**When to Use:** Tools registered in ToolRegistry but missing skill MDs or JSON Schema manifests
**Related Skill:** `skills/tool-contract-sync/SKILL.md`

### code-boundary-enforcement
**Description:** Enforce strict boundary discipline between domains, dependencies, and system layers
**When to Use:** Ensuring separation between internal domains, external dependencies, and system layers

---

## Testing & Quality Assurance

### autonomous-test-assurance-agent
**Description:** Level 4 autonomous agent for end-to-end test assurance with self-directed discovery and automatic recovery
**When to Use:** Comprehensive test suite transformation into production assurance without human checkpoints

### test-quality-remediation
**Description:** Systematic test quality improvement across the repository with discovery, audit, rewrite, and validation phases
**When to Use:** Auditing test quality, applying targeted rewrites, resolving failures

---

## Code Review & Development

### code-quality-improvement
**Description:** Systematic code quality improvement workflow for transforming functional code into production-grade output through inspection, analysis, and targeted fixes
**When to Use:** Improving code quality after implementation, React component self-review, periodic technical debt cleanup

---

## Architecture & Governance

### drift-assessment
**Description:** Multi-layer drift detection for API contracts, schemas, and behavior drift
**When to Use:** After code changes touching API routes or schemas, before releases, weekly drift reports

---

## Frontend & UX

### palette-ux-agent
**Description:** UX-focused agent for small interface improvements and accessibility enhancements
**When to Use:** Adding micro-UX improvements, fixing accessibility issues, improving keyboard navigation, adding ARIA labels

### fabric_ui_drift_agent.md
**Description:** Fabric System Hardening + UI Consistency Deployment with autonomous multi-agent enforcement loop
**When to Use:** Auditing or remediating UI governance drift across `apps/web/src/`

### react-component-design
**File:** `react_component_design.md`
**Description:** Three-phase React component design workflow with chain-of-thought rigor
**When to Use:** Designing React components with agent skills

---

## Documentation

### technical_documentation
**Description:** Professional technical documentation generation and maintenance workflow
**When to Use:** Creating documentation for new systems or APIs, when docs are outdated, for handoffs

### fumadocs-drift-audit
**Description:** Audit Fumadocs documentation drift for ongoing maintenance and migration
**When to Use:** Post-release, periodic maintenance, pre-migration, when docs appear out of sync

### cleanup-docs
**Description:** Monorepo documentation cleanup workflow
**When to Use:** Cleaning up scattered documentation, consolidating docs

---

## Infrastructure & DevOps

### dependency-update
**Description:** Systematic dependency update workflow for security patches, bug fixes, and feature updates with testing and rollback planning
**When to Use:** Monthly dependency updates, security vulnerabilities, critical bug fixes

### bunnyshell.md
**Description:** Bunnyshell Environment Management for repeatable Value Fabric environments
**When to Use:** Creating or managing development, staging, or production-like Bunnyshell environments

### performance-investigation
**Description:** Systematic performance investigation workflow for identifying bottlenecks, analyzing metrics, and implementing optimizations
**When to Use:** Slow response times, high latency, resource utilization issues

### feature-flag-rollout
**Description:** Systematic feature flag rollout workflow for safe, gradual feature deployment with monitoring and rollback capabilities
**When to Use:** Deploying new features, A/B testing, gradual migration to new implementations

---

## Planning & Roadmap

### roadmap-management
**Description:** Comprehensive roadmap management workflow for auditing task status, identifying gaps, proposing additions, and generating work packages
**When to Use:** Daily/weekly execution sync, sprint planning, quarterly roadmap updates

### launch-readiness-assessment
**Description:** Fabric_4L Dual-Track Launch Readiness Assessment & Sprint Plan using claimed-versus-verified evidence
**When to Use:** Pre-release readiness reviews, quarterly roadmap updates

---

## Orchestration Patterns (Templates)

### _templates/human-in-the-loop
**Pattern:** Human-in-the-Loop
**Description:** Agent generates diff, stops, notifies human, resumes only after approval
**Use Cases:** Auth/billing changes, database schema migrations, API contract breaking changes, security policy modifications

### _templates/manager-worker
**Pattern:** Manager-Worker
**Description:** Decompose large refactoring by project graph; workers execute in parallel; manager validates
**Use Cases:** Large refactoring tasks, parallel code transformations

### _templates/pipeline-dag
**Pattern:** Pipeline (DAG)
**Description:** Multi-stage pipeline where each stage is an agent with explicit input/output contracts
**Use Cases:** Multi-stage processes with dependencies between stages

---

## Operations & Incident Response

### incident-response
**Description:** Structured incident response workflow for production incidents with severity triage, communication, and post-mortem
**When to Use:** Production outages, security incidents, data integrity issues, critical bugs

---

## Workflow Templates

### WORKFLOW.md
**Description:** Workflow authoring specification for structured orchestration patterns
**When to Use:** Creating new workflows with proper state management and circuit breakers

---

## Workflow Maintenance

**Last Updated:** 2026-05-27

**Total Workflows:** 27 (24 main workflows + 3 templates)

**Workflows with Frontmatter:** 27/27 (100%)

**Moved to Governance:** production-only-delivery.md → docs/governance/

**Note:** This index is generated manually. Consider automating this index generation by parsing workflow frontmatter from all workflow files.
