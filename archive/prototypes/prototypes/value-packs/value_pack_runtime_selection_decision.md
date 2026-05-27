# Intelligence Layer Data Model Architecture

## 1. Purpose

This document defines the underlying data model architecture for the platform’s end-to-end intelligence layer.

The goal is to make Value Packs more than static industry content. They should become runtime intelligence primitives that shape how the platform extracts signals, matches evidence, seeds opportunities, builds value trees, selects formulas, validates assumptions, and produces executive-ready business value narratives.

## 2. Recommended Scope

Choose **Signal + Opportunity + Value Tree** as the first meaningful runtime scope.

This means Value Packs should directly influence:

1. Signal extraction
2. Evidence matching
3. Impact quantification
4. Opportunity discovery
5. Value Tree construction
6. Formula selection
7. Formula governance
8. Persona-aware workspace context

Defer the broader user-facing surfaces until the core intelligence layer is stable:

- BusinessCase generation templates
- Benchmark Policy prepopulation
- Workflow template autoloading
- Admin PackManagement lifecycle UI
- Full multi-pack composition and inheritance conflict resolution

## 3. Runtime Pack Selection Model

Choose **Tenant default + account override**.

### Core Rule

Each tenant has a default Value Pack. Each account inherits the tenant default unless the account defines an override.

### Recommended Phase 1 Behavior

1. Tenant configures one default primary pack.
2. Account inherits the tenant default pack.
3. Account may override the inherited pack.
4. Account may optionally attach one supplemental pack in a later phase.
5. Every intelligence operation resolves an **Effective Pack Context** before execution.

### Resolution Precedence

```text
1. Account primary override
2. Account supplemental pack, if enabled later
3. Tenant default pack
4. Global/common pack
```

### Design Principle

Do not allow agents to guess which pack applies. Pack resolution should be deterministic, auditable, and stored with every generated artifact.

## 4. End-to-End Intelligence Workflow

The intelligence layer should support this workflow:

```text
Tenant configuration
  ↓
Account setup
  ↓
Effective Pack Context resolution
  ↓
Signal extraction
  ↓
Evidence matching
  ↓
Opportunity seeding
  ↓
Impact quantification
  ↓
Value Tree construction
  ↓
Formula selection and governance
  ↓
Assumption/evidence validation
  ↓
Executive narrative and business case outputs
  ↓
Realization tracking and expansion signals
```

The platform should treat each step as a data-producing stage, not just an agent response.

## 5. Core Domain Entities

### Tenant

Represents the customer organization using the platform.

Key fields:

```text
tenant_id
name
default_pack_id
allowed_pack_ids
pack_policy
created_at
updated_at
```

Responsibilities:

- Defines the default industry/segment intelligence context.
- Controls which packs are available to accounts.
- Provides governance boundaries for pack usage.

### Account

Represents a customer, prospect, or target company being analyzed.

Key fields:

```text
account_id
tenant_id
name
industry
segment
region
account_pack_override_id
pack_override_reason
created_at
updated_at
```

Responsibilities:

- Inherits the tenant default pack.
- May override the pack for account-specific precision.
- Acts as the primary runtime context for intelligence workflows.

### Value Pack

Represents an industry, segment, or domain-specific intelligence bundle.

Key fields:

```text
pack_id
name
industry
segment
version
status
parent_pack_id
scope
created_by
published_at
deprecated_at
```

Responsibilities:

- Provides domain-specific language, personas, KPIs, use cases, signals, formulas, benchmarks, and evidence expectations.
- Defines how the platform should interpret account data in a specific context.

### Effective Pack Context

A resolved runtime object used by agents and workflows.

Key fields:

```text
effective_pack_context_id
tenant_id
account_id
primary_pack_id
source
resolution_reason
resolved_at
resolved_by
pack_version
```

Example source values:

```text
tenant_default
account_override
system_default
manual_selection
```

Responsibilities:

- Prevents ambiguity about which pack was used.
- Captures the pack version used at execution time.
- Gives every downstream artifact a traceable intelligence context.

## 6. Value Pack Internal Model

A Value Pack should not be a single blob of markdown. It should be structured into reusable intelligence primitives.

### Pack Persona

Represents buyer, influencer, evaluator, operator, or executive personas relevant to a pack.

Key fields:

```text
persona_id
pack_id
name
role_type
seniority
pain_points
decision_criteria
preferred_metrics
common_objections
value_language
```

Used by:

- Signal extraction
- Opportunity seeding
- Narrative generation
- Stakeholder-specific ROI views

### Pack Use Case

Represents a repeatable business use case relevant to the pack.

Key fields:

```text
use_case_id
pack_id
name
description
persona_ids
related_kpis
related_formulas
trigger_signals
expected_outcomes
```

Used by:

- OpportunityFinder
- Value Tree Explorer
- Business value hypothesis generation

### Pack Signal Definition

Defines what the platform should look for in account data.

Key fields:

```text
signal_definition_id
pack_id
name
category
description
positive_patterns
negative_patterns
source_types
confidence_rules
related_use_cases
related_personas
```

Example categories:

```text
pain
initiative
risk
growth
cost_pressure
compliance
technology_change
competitive_pressure
```

Used by:

- Layer 2 signal extraction prompts
- Signal scoring
- Evidence matching

### Pack KPI

Represents a business metric that matters in the pack context.

Key fields:

```text
kpi_id
pack_id
name
category
unit
calculation_notes
benchmark_refs
owner_personas
related_formulas
```

Example categories:

```text
revenue_uplift
cost_savings
risk_reduction
productivity
cycle_time
quality
compliance
retention
```

Used by:

- Impact quantification
- Value Tree construction
- Formula governance

### Pack Formula

Represents a governed calculation pattern.

Key fields:

```text
formula_id
pack_id
name
formula_expression
input_variables
output_metric_id
confidence_level
source_notes
governance_status
version
```

Governance statuses:

```text
draft
approved
deprecated
requires_review
```

Used by:

- Value Tree Explorer
- Formula Governance
- ROI modeling
- Integrity checks

### Pack Evidence Rule

Defines how evidence should be interpreted for a pack.

Key fields:

```text
evidence_rule_id
pack_id
source_type
accepted_evidence_patterns
rejected_evidence_patterns
minimum_confidence
recency_requirement
persona_relevance
```

Used by:

- Evidence matching
- Assumption validation
- IntegrityAgent scoring

### Pack Benchmark

Represents benchmark values or expected ranges.

Key fields:

```text
benchmark_id
pack_id
kpi_id
segment
company_size_band
region
value_range
source
confidence
valid_from
valid_to
```

Used by:

- Impact quantification
- Formula input suggestions
- Business case calibration

## 7. Intelligence Layer Runtime Entities

These are generated or updated as users and agents move through the workflow.

### Signal

A discovered piece of intelligence from account data.

Key fields:

```text
signal_id
tenant_id
account_id
effective_pack_context_id
signal_definition_id
source_artifact_id
summary
category
confidence
sentiment
extracted_by_agent
created_at
```

Responsibilities:

- Captures a meaningful observation.
- Links back to pack-specific signal definitions.
- Serves as input to opportunity discovery.

### Evidence Artifact

A source item used to support signals, assumptions, or claims.

Key fields:

```text
evidence_artifact_id
tenant_id
account_id
source_type
source_uri
title
excerpt
metadata
collected_at
trust_score
```

Source examples:

```text
crm_note
call_transcript
website_page
annual_report
support_ticket
email
uploaded_document
third_party_research
```

### Evidence Match

A relationship between evidence and a platform-generated object.

Key fields:

```text
evidence_match_id
evidence_artifact_id
target_type
target_id
match_reason
confidence
matched_by_agent
created_at
```

Target types:

```text
signal
opportunity
assumption
formula_input
value_tree_node
business_case_claim
```

### Opportunity Hypothesis

A pack-informed potential value opportunity.

Key fields:

```text
opportunity_id
tenant_id
account_id
effective_pack_context_id
use_case_id
name
description
value_category
confidence
status
created_by_agent
created_at
```

Value categories:

```text
revenue_uplift
cost_savings
risk_reduction
```

Statuses:

```text
seeded
validated
rejected
promoted_to_value_tree
```

### Impact Estimate

A quantified estimate attached to an opportunity, formula, or value tree node.

Key fields:

```text
impact_estimate_id
tenant_id
account_id
opportunity_id
formula_id
kpi_id
value_low
value_mid
value_high
unit
confidence
calculation_trace
created_at
```

Responsibilities:

- Separates raw opportunity discovery from quantified financial impact.
- Stores uncertainty ranges instead of false precision.
- Links calculations back to pack formulas and evidence.

### Value Tree

A structured model of how value is created for an account.

Key fields:

```text
value_tree_id
tenant_id
account_id
effective_pack_context_id
name
status
created_at
updated_at
```

Statuses:

```text
draft
validating
approved
locked
```

### Value Tree Node

A node in the value tree.

Key fields:

```text
node_id
value_tree_id
parent_node_id
node_type
label
value_category
kpi_id
formula_id
impact_estimate_id
confidence
sort_order
```

Node types:

```text
strategic_outcome
value_driver
use_case
kpi
formula
assumption
```

### Assumption

A statement required for a value model to hold.

Key fields:

```text
assumption_id
tenant_id
account_id
value_tree_id
node_id
statement
variable_name
value
unit
confidence
status
created_at
```

Statuses:

```text
unverified
partially_supported
supported
rejected
requires_customer_input
```

### Formula Input

A specific variable value used in a formula.

Key fields:

```text
formula_input_id
formula_id
impact_estimate_id
assumption_id
name
value
unit
source_type
confidence
```

Responsibilities:

- Allows formulas to be auditable.
- Enables the IntegrityAgent to inspect each input, not just the final output.

### Reasoning Trace

A standard trace record for agent-generated outputs.

Key fields:

```text
trace_id
tenant_id
account_id
agent_name
operation_type
input_refs
output_refs
model_name
prompt_version
pack_context_id
created_at
```

Responsibilities:

- Captures lineage from inputs to outputs.
- Supports debugging, governance, and repeatability.
- Should be linked to every major generated artifact.

## 8. Agent-to-Data Mapping

### ContextExtractionAgent

Reads source material and produces:

```text
EvidenceArtifact
Signal
EvidenceMatch
ReasoningTrace
```

Pack dependency:

```text
PackSignalDefinition
PackEvidenceRule
PackPersona
```

### OpportunityFinder

Reads signals and pack use cases, then produces:

```text
OpportunityHypothesis
EvidenceMatch
ReasoningTrace
```

Pack dependency:

```text
PackUseCase
PackPersona
PackKPI
```

### FinancialModelingAgent

Reads opportunities and formulas, then produces:

```text
ImpactEstimate
FormulaInput
Assumption
ReasoningTrace
```

Pack dependency:

```text
PackFormula
PackKPI
PackBenchmark
```

### IntegrityAgent

Reads assumptions, evidence, formulas, and traces, then produces:

```text
ValidationFinding
EvidenceMatch
Assumption status updates
ReasoningTrace
```

Pack dependency:

```text
PackEvidenceRule
PackFormula governance status
PackBenchmark confidence
```

### NarrativeAgent

Reads approved value trees, evidence, and personas, then produces:

```text
ExecutiveNarrative
BusinessCaseClaim
EvidenceMatch
ReasoningTrace
```

Pack dependency:

```text
PackPersona
PackUseCase
PackKPI
Value language from pack
```

## 9. Effective Pack Context in the UI

### SignalsTab

The SignalsTab should include a pack selector that shows:

```text
Current effective pack
Whether it is inherited from tenant default
Whether it is overridden for the account
Pack version
Last resolved timestamp
```

User actions:

```text
View inherited pack
Override account pack
Re-run signal extraction with selected pack
Compare previous run against new pack context, later phase
```

### Opportunity Workspace

Should show:

```text
Pack-driven opportunity seeds
Relevant personas
Related use cases
Signal evidence backing each opportunity
Confidence and evidence coverage
```

### Value Tree Explorer

Should show:

```text
Pack-selected formulas
KPI lineage
Formula governance status
Assumption/evidence pairs
Impact ranges
```

### Formula Governance

Should show:

```text
Formula source pack
Formula version
Approval status
Input variables
Evidence coverage
Benchmark source and confidence
Where the formula is used
```

## 10. Data Relationships

Recommended high-level relationship model:

```text
Tenant
  has many Accounts
  has one default ValuePack
  allows many ValuePacks

Account
  belongs to Tenant
  may override ValuePack
  has many EffectivePackContexts
  has many Signals
  has many Opportunities
  has many ValueTrees

ValuePack
  has many PackPersonas
  has many PackUseCases
  has many PackSignalDefinitions
  has many PackKPIs
  has many PackFormulas
  has many PackEvidenceRules
  has many PackBenchmarks

EffectivePackContext
  belongs to Tenant
  belongs to Account
  references ValuePack
  is referenced by Signals, Opportunities, ValueTrees, ImpactEstimates, and ReasoningTraces

Signal
  references PackSignalDefinition
  has many EvidenceMatches
  seeds Opportunities

OpportunityHypothesis
  references PackUseCase
  has many ImpactEstimates
  may become a ValueTreeNode

ValueTree
  has many ValueTreeNodes
  has many Assumptions
  has many ImpactEstimates

Formula
  produces FormulaInputs
  contributes to ImpactEstimates
  is governed by FormulaGovernance

EvidenceArtifact
  has many EvidenceMatches
  supports Signals, Assumptions, Opportunities, FormulaInputs, and Claims
```

## 11. Persistence Strategy

### Relational Store

Use Postgres/Supabase for canonical records:

```text
Tenants
Accounts
ValuePacks
Pack primitives
EffectivePackContexts
Signals
EvidenceArtifacts
EvidenceMatches
Opportunities
ValueTrees
Assumptions
Formulas
ImpactEstimates
ReasoningTraces
```

Why:

- Tenant isolation
- RLS enforcement
- Auditable joins
- Transactional integrity
- Governance workflows

### Vector Store

Use a vector store for semantic retrieval over:

```text
Evidence artifacts
Pack descriptions
Use cases
Persona language
Formula descriptions
Benchmarks
Past business cases
```

Vector entries must include:

```text
tenant_id
account_id, where applicable
pack_id, where applicable
source_type
source_id
version
visibility_scope
```

### Graph Layer, optional but valuable

A graph layer can represent relationships among:

```text
Personas
Use cases
KPIs
Signals
Opportunities
Formulas
Evidence
Value tree nodes
```

This is especially useful for the Value Graph and explainable lineage, but should not replace the relational system of record in the first implementation.

## 12. Multi-Tenancy and Access Control

Every runtime entity should carry:

```text
tenant_id
account_id, where applicable
created_by
created_at
updated_at
```

Core rules:

1. Tenant isolation is mandatory.
2. Account-scoped data must not leak across accounts unless explicitly promoted into a tenant-level library.
3. Pack-level global content can be shared, but tenant-customized pack extensions must be isolated.
4. Generated outputs must retain the pack version and evidence references used at creation time.

## 13. Governance and Audit Requirements

Every major generated object should be auditable.

Minimum audit fields:

```text
created_by_agent
agent_version
model_name
prompt_version
input_refs
output_refs
effective_pack_context_id
reasoning_trace_id
confidence
status
```

Governed objects:

```text
PackFormula
PackBenchmark
ImpactEstimate
Assumption
BusinessCaseClaim
ExecutiveNarrative
ValueTree
```

Governance statuses should be explicit, not implied.

## 14. Pack Versioning

Packs should be versioned because generated artifacts depend on the pack content used at the time.

Recommended pattern:

```text
pack_id = stable logical identity
pack_version_id = immutable published version
```

Runtime artifacts should reference `pack_version_id`, not only `pack_id`.

This allows:

- Reproducibility
- Auditability
- Safe pack updates
- Comparison of old vs. new analysis
- Deprecation without breaking historical outputs

## 15. Event Model

The intelligence layer should emit domain events as workflows progress.

Example events:

```text
pack.context.resolved
signals.extraction.started
signals.extraction.completed
evidence.matched
opportunity.seeded
opportunity.validated
impact.estimated
value_tree.created
value_tree.node.added
assumption.created
assumption.validated
formula.selected
formula.governance.flagged
narrative.generated
business_case.claim.created
```

Each event should include:

```text
event_id
tenant_id
account_id
effective_pack_context_id
actor_type
actor_id
source_artifact_ids
target_artifact_ids
created_at
```

## 16. Minimal Phase 1 Schema Set

For the first implementation, do not build every entity at once. Start with the smallest schema that supports the medium scope.

### Required Now

```text
tenants
accounts
value_packs
value_pack_versions
pack_personas
pack_use_cases
pack_signal_definitions
pack_kpis
pack_formulas
effective_pack_contexts
signals
evidence_artifacts
evidence_matches
opportunity_hypotheses
impact_estimates
value_trees
value_tree_nodes
assumptions
reasoning_traces
```

### Can Defer

```text
pack_benchmarks
pack_evidence_rules
business_case_templates
benchmark_policies
workflow_templates
pack_lifecycle_approvals
pack_admin_audit_logs
multi_pack_resolution_rules
```

## 17. Implementation Boundaries

### Build Now

- Tenant default pack setting
- Account pack override
- Effective Pack Context resolver
- Pack-aware signal extraction
- Pack-aware evidence matching
- Pack-driven opportunity seeding
- Pack-selected formulas in Value Tree Explorer
- Formula provenance in Formula Governance
- Persona surfacing in workspace
- Reasoning trace linkage

### Defer

- Full PackManagement admin lifecycle
- Multi-pack composition
- Pack inheritance conflict resolution
- Auto-loaded workflow templates
- BusinessCase template generation
- Benchmark policy automation
- Redis/session-like runtime caches for pack context unless needed

## 18. Value Pack Package Architecture and Swarm Generation Plan

Your current 30-pack plan is a strong starting package for the intelligence layer:

```text
5 Master Packs
25 Vertical Subpacks
Cross-domain validation
OpenClaw-compatible skill packaging
Machine-readable JSON
Worked TypeScript signal examples
```

This should be treated as the platform’s initial **Domain Intelligence Corpus**, not merely documentation.

### 18.1 Package Layers

Each generated Value Pack should produce three layers of output:

```text
Human-readable layer:
  SKILL.md
  README.md
  methodology.md

Machine-readable layer:
  value-pack.json
  inheritanceManifest.json
  formulas.json
  signals.json
  personas.json
  kpis.json
  benchmarks.json
  evidence-rules.json

Executable/example layer:
  signals-examples.ts
  formula-examples.ts
  opportunity-seeding-examples.ts
  value-tree-examples.ts
  validation-fixtures.json
```

The important shift is that the JSON files should become canonical runtime inputs. Markdown should explain the pack. JSON should power the product.

### 18.2 Recommended Master/Subpack Model

The 5 Master Packs should define common reusable intelligence for each broad industry:

```text
Manufacturing Master
SaaS Master
Healthcare Master
Financial Services Master
Public Sector Master
```

The 25 Subpacks should specialize the master content without duplicating it:

```text
Manufacturing:
  Discrete
  Process
  Advanced
  Contract
  Supply Chain

SaaS:
  Horizontal
  Vertical
  AI-Native
  Infrastructure
  Go-to-Market

Healthcare:
  Providers
  Payers
  Life Sciences
  Operations
  Compliance/Data

Financial Services:
  Banking
  Capital Markets
  Insurance
  Fintech
  Risk/Compliance

Public Sector:
  Federal
  State/Local
  Education
  Public Health
  Infrastructure
```

### 18.3 Inheritance Manifest

Every Subpack should include an `inheritanceManifest` that explicitly declares what it inherits, overrides, extends, or deprecates.

Recommended structure:

```json
{
  "subpackId": "manufacturing.discrete",
  "parentPackId": "manufacturing.master",
  "parentVersion": "1.0.0",
  "inherits": {
    "personas": ["operations_leader", "plant_manager", "cfo"],
    "kpis": ["oee", "scrap_rate", "throughput", "downtime"],
    "formulas": ["downtime_cost", "yield_improvement_value"],
    "evidenceRules": ["production_variance", "maintenance_logs"]
  },
  "overrides": {
    "kpis": ["line_changeover_time"],
    "signals": ["excessive_retooling_delay"]
  },
  "extends": {
    "personas": ["quality_director"],
    "useCases": ["defect_reduction", "line_balancing"]
  },
  "deprecatedFromParent": []
}
```

Runtime rule: the product should never infer inheritance by folder path alone. It should read and validate the manifest.

### 18.4 Canonical `value-pack.json` Shape

Each `value-pack.json` should map directly to the core schema entities in this architecture.

Recommended top-level shape:

```json
{
  "packId": "manufacturing.discrete",
  "name": "Discrete Manufacturing Value Pack",
  "industry": "Manufacturing",
  "segment": "Discrete Manufacturing",
  "version": "1.0.0",
  "status": "draft",
  "parentPackId": "manufacturing.master",
  "packType": "subpack",
  "personas": [],
  "useCases": [],
  "signalDefinitions": [],
  "kpis": [],
  "formulas": [],
  "evidenceRules": [],
  "benchmarks": [],
  "regulatoryContext": [],
  "opportunitySeeds": [],
  "valueTreeTemplates": [],
  "qualityMetadata": {
    "createdBy": "Kimi K2.6 Elevated Agent Swarm",
    "validationStatus": "pending",
    "confidence": null,
    "sourceCoverage": null
  }
}
```

### 18.5 What the Swarm Should Generate Beyond the Current Plan

Your current plan is good. The main missing piece is not more prose. It is **evaluation and runtime fixture data**.

The swarm should also generate:

```text
1. Golden signal extraction examples
2. Negative signal examples
3. Evidence matching fixtures
4. Opportunity seeding examples
5. Formula input/output test cases
6. Value tree construction examples
7. Persona-specific narrative snippets
8. Benchmark source notes and confidence ratings
9. Regulatory/compliance caveats
10. Cross-pack conflict examples
```

These become training/evaluation data for the intelligence workflow.

### 18.6 Training/Evaluation Data Needed

Do not frame this as model fine-tuning data first. Frame it as **workflow evaluation data**.

For each pack, require:

```text
Signal extraction fixtures:
  input text
  expected signals
  expected category
  expected confidence range
  expected evidence span
  false positives to avoid

Evidence matching fixtures:
  evidence artifact
  target signal/opportunity/assumption
  expected match reason
  expected confidence

Opportunity fixtures:
  input signals
  expected opportunity hypotheses
  expected related use case
  expected value category

Formula fixtures:
  formula inputs
  expected output
  accepted range
  assumptions required
  evidence requirements

Value tree fixtures:
  account scenario
  expected top-level outcomes
  expected value drivers
  expected KPI nodes
  expected formula nodes
  expected assumptions
```

### 18.7 Cross-Domain Validation Agents

The 8 validation agents should produce machine-readable findings, not only narrative reports.

Recommended `validation-report.json` shape:

```json
{
  "packId": "manufacturing.discrete",
  "validator": "kpi_consistency",
  "status": "pass_with_warnings",
  "criticalFindings": [],
  "warnings": [],
  "recommendations": [],
  "qualityScores": {
    "completeness": 0.92,
    "specificity": 0.88,
    "evidenceDefensibility": 0.81,
    "runtimeUsability": 0.86
  }
}
```

### 18.8 Quality Gates for Runtime Readiness

A pack should not be published just because its files exist.

Recommended gates:

```text
Schema validity:
  value-pack.json validates against JSON Schema

Inheritance validity:
  subpack inheritanceManifest references real parent objects

No duplicate IDs:
  all persona, KPI, formula, signal, and use-case IDs are stable and unique

Formula validity:
  formulas include inputs, units, outputs, assumptions, and examples

Evidence defensibility:
  benchmarks and formulas include source notes and confidence ratings

Runtime fixture coverage:
  pack includes signal, evidence, opportunity, formula, and value-tree examples

Cross-pack consistency:
  KPI names, units, and value categories are consistent across related packs

Prompt usability:
  pack content can be injected into Layer 2/3/4 prompts without excessive context bloat
```

### 18.9 How Packs Enter the Platform

The ingestion pipeline should convert `/outputs/` into canonical database records.

```text
/outputs/{pack}/SKILL.md
  -> human-readable docs and agent instructions

/outputs/{pack}/value-pack.json
  -> ValuePack, ValuePackVersion, PackPersona, PackUseCase, PackSignalDefinition, PackKPI, PackFormula

/outputs/{pack}/signals-examples.ts
  -> evaluation fixtures and developer examples

/outputs/{pack}/validation-report.json
  -> pack quality metadata and publish gates
```

Recommended ingestion stages:

```text
1. Validate file set
2. Validate JSON schema
3. Validate inheritance
4. Normalize IDs and units
5. Create immutable ValuePackVersion
6. Insert pack primitives into Postgres
7. Embed selected pack text into vector store
8. Register evaluation fixtures
9. Mark pack as draft or publishable
```

### 18.10 Revised Swarm Objective

The swarm objective should be updated from:

```text
Create 30 complete Value Packs.
```

to:

```text
Create 30 runtime-ingestable, validated, versioned Value Packs with machine-readable intelligence primitives, inheritance manifests, quality reports, and evaluation fixtures for signal extraction, evidence matching, opportunity seeding, formula resolution, and value-tree construction.
```

This aligns the pack-generation process with the intelligence layer architecture rather than producing static content.

## 19. Acceptance Criteria

1. A tenant can define a default pack.
2. An account can inherit the tenant default pack.
3. An account can override the tenant default pack.
4. The system resolves and stores an Effective Pack Context before signal extraction.
5. Signals reference the effective pack context and pack signal definition.
6. Evidence matches reference both evidence artifacts and target objects.
7. Opportunity hypotheses can be seeded from pack use cases and signals.
8. Impact estimates can reference pack formulas and KPIs.
9. Value Tree nodes can reference opportunities, KPIs, formulas, assumptions, and impact estimates.
10. Formula Governance can show which formulas came from which pack version.
11. The UI clearly explains whether a pack was inherited or overridden.
12. Generated outputs store pack version and reasoning trace references.
13. Multi-pack composition is not required for Phase 1.
14. BusinessCase generation and admin PackManagement are not required for Phase 1.

## 19. Strategic Summary

The Value Pack should become the semantic operating system for the platform’s intelligence layer.

It should not merely influence prompts. It should govern how the platform understands an account, identifies signals, interprets evidence, proposes opportunities, selects formulas, quantifies value, validates assumptions, and explains the resulting business case.

The correct first architecture is:

```text
Tenant default pack
  + Account override
  + Effective Pack Context
  + Pack-aware signals
  + Pack-aware opportunities
  + Pack-aware value tree
  + Formula/evidence/reasoning provenance
```

This creates a strong foundation without prematurely taking on full multi-pack composition or full user-facing pack lifecycle management.

