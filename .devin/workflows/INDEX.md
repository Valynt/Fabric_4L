# Workflows Index

This index catalogs all available workflows in the `.devin/workflows/` directory. Workflows are orchestration patterns with explicit state machines for human-driven processes.

For workflow authoring specifications, see [WORKFLOW.md](./WORKFLOW.md).

---

## Agent Infrastructure & Meta Workflows

### value-fabric-harness
**Description:** Value Fabric coding harness — layer-scoped context assembly and pre-edit boundary guards for safe, contract-aligned development.
**When to Use:** See workflow file for activation criteria

---

## Quality Debt & Code Hygiene

### code-boundary-enforcement
**Description:** Enforce strict boundary discipline between domains, dependencies, and system layers
**When to Use:** See workflow file for activation criteria

### contract-enforcement-auditor
**Description:** Scan for contract violations and enforcement gaps across all 6 canonical contracts in contract.md. Use when auditing compliance, checking if ESLint rules are actually running, verifying CI gates are blocking, or assessing the gap between documented contracts and runtime enforcement. Reports on the 58% enforcement rate identified in CONTRACT_ENFORCEMENT_ASSESSMENT.md.
**When to Use:** See workflow file for activation criteria

### dead-code-sweeper
**Description:** Identify and safely remove dead code including orphan pages, unreachable routes, unused exports, mock data blocks, and duplicate workspace systems. Use when cleaning up the codebase, after major refactors, or when the FRONTEND_AUDIT_REPORT.md dead code list needs action. Targets 2,500+ confirmed dead lines plus uncatalogued backend dead code.
**When to Use:** See workflow file for activation criteria

### deprecation-migrator
**Description:** Migrate deprecated anti-pattern instances to canonical replacements defined in contract.md. Use when fixing tenant-id-as-parameter, direct-header-access, explicit-db-connect, inline-middleware, inline-tool-definition, tools-throwing-exceptions, json-parse-llm, imperative-navigation, url-concatenation, or raw-sql-tenant patterns. Targets ~280 instances tracked in DEPRECATIONS.md.
**When to Use:** See workflow file for activation criteria

### dil-hook-scaffolder
**Description:** Scaffold TanStack Query hooks for DIL (Data Intelligence Layer) backend services that have zero frontend integration. Use when building frontend hooks for products, evidence, competitive-intel, roi, enrichment, value-hypotheses, narratives, or intelligence endpoints. Addresses 52 unintegrated backend endpoints identified in FRONTEND_AUDIT_REPORT.md.
**When to Use:** See workflow file for activation criteria

### facade-page-connector
**Description:** Rewire frontend pages from static/mock data or generic useWorkspaceTabQuery to real backend hooks. Use when a page renders hardcoded data, uses MOCK_ arrays, or connects to the generic workspace endpoint instead of its dedicated DIL service. Fixes the 74% of pages with zero API calls identified in FRONTEND_AUDIT_REPORT.md.
**When to Use:** See workflow file for activation criteria

### tool-contract-sync
**Description:** Audit and fix the three-way sync between tool implementations, skill definitions, and tool manifests. Use when tools are registered in the ToolRegistry but missing skill MDs or JSON Schema manifests, or when evals are missing. Closes the gap between 26 registered tools and only 9 skill definitions + 9 manifests + 2 evals.
**When to Use:** See workflow file for activation criteria

---

## Testing & Quality Assurance

### autonomous-test-assurance-agent
**Description:** Autonomous Level 4 agent for end-to-end test assurance with self-directed discovery, automatic remediation, and PR-ready delivery without human checkpoints
**When to Use:** See workflow file for activation criteria

### test-quality-remediation
**Description:** Step-by-step operational workflow for auditing tests, applying targeted rewrites, executing suites, diagnosing failures, and resolving them safely
**When to Use:** See workflow file for activation criteria

---

## Code Review & Development

### code-quality-improvement
**Description:** Systematic code quality improvement workflow for transforming functional code into production-grade output through inspection, analysis, and targeted fixes
**When to Use:** See workflow file for activation criteria

### repowise-production-readiness
**Description:** Systematic codebase transformation using repowise MCP intelligence to bring code from functional to production-ready through assessment, prioritization, and execution
**When to Use:** See workflow file for activation criteria

---

## Architecture & Governance

### drift-assessment
**Description:** Multi-layer drift detection for API contracts, schemas, and behavior drift
**When to Use:** See workflow file for activation criteria

---

## Frontend & UX

### fabric-ui-drift-agent
**Description:** Fabric System Hardening + UI Consistency Deployment with autonomous multi-agent enforcement loop
**When to Use:** See workflow file for activation criteria

### palette-ux-agent
**Description:** UX-focused agent for small interface improvements and accessibility enhancements
**When to Use:** See workflow file for activation criteria

### react-component-design
**Description:** Three-phase React component design workflow with chain-of-thought rigor
**When to Use:** See workflow file for activation criteria

---

## Documentation

### cleanup-docs
**Description:** Monorepo documentation cleanup
**When to Use:** See workflow file for activation criteria

### fumadocs-drift-audit
**Description:** Audit Fumadocs documentation drift for ongoing maintenance and migration
**When to Use:** See workflow file for activation criteria

### technical-documentation
**Description:** Professional technical documentation generation and maintenance workflow
**When to Use:** See workflow file for activation criteria

---

## Infrastructure & DevOps

### bunnyshell
**Description:** Set up and manage Bunnyshell Environments as a Service for Value Fabric. Use when creating development, staging, or production environments, configuring environment templates, integrating Bunnyshell with existing infrastructure, or automating environment lifecycle management.
**When to Use:** See workflow file for activation criteria

### dependency-update
**Description:** Systematic dependency update workflow for security patches, bug fixes, and feature updates with testing and rollback planning
**When to Use:** See workflow file for activation criteria

### feature-flag-rollout
**Description:** Systematic feature flag rollout workflow for safe, gradual feature deployment with monitoring and rollback capabilities
**When to Use:** See workflow file for activation criteria

### performance-investigation
**Description:** Systematic performance investigation workflow for identifying bottlenecks, analyzing metrics, and implementing optimizations
**When to Use:** See workflow file for activation criteria

---

## Planning & Roadmap

### launch-readiness-assessment
**Description:** Assess launch readiness using dual-track claimed-versus-verified evidence and generate a refreshed 5-sprint plan without creating artifacts until explicitly approved
**When to Use:** See workflow file for activation criteria

### roadmap-management
**Description:** Comprehensive roadmap management workflow for auditing task status, identifying gaps, proposing additions, and generating work packages
**When to Use:** See workflow file for activation criteria

---

## Operations & Incident Response

### incident-response
**Description:** Structured incident response workflow for production incidents with severity triage, communication, and post-mortem
**When to Use:** See workflow file for activation criteria

---

## Workflow Templates

### WORKFLOW.md
**Description:** Workflow authoring specification for structured orchestration patterns
**When to Use:** Creating new workflows with proper state management and circuit breakers

---

## Workflow Maintenance

**Last Updated:** 2026-07-13

**Total Workflows:** 26

**Workflows with Frontmatter:** 26/26 (100%)

**Note:** This index is auto-generated. Run `python scripts/ci/generate_workflow_index.py` to regenerate.
