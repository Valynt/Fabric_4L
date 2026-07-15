# Fabric Harness MVP Implementation Plan

## Stage 1: Repository Discovery (Agent: Repository Cartographer)
- Inspect repo layout at `services/layer4-agents/`
- Identify canonical Layer 4 path and package/import style
- Identify existing LangGraph/workflow/checkpoint code
- Identify tenant context implementation
- Identify logging/tracing/metrics conventions
- Identify validation/L5 client patterns
- Identify DB and migration patterns
- Identify FastAPI route style
- Identify test structure
- Identify frontend governance route structure
- Output: Discovery note

## Stage 2: Architecture Integration (Agent: Architecture Integrator)
- Analyze discovery findings
- Determine how harness fits without drift
- Decide on persistence approach (in-memory vs DB)
- Decide on API route approach
- Produce implementation ADR/note if repo supports it
- Output: Architecture decision note + implementation strategy

## Stage 3: Test-First Skeleton (Agent: Test Strategist)
- Write failing tests for all modules before implementation
- State machine transitions
- Tool contracts
- Human gates
- Checkpoints
- Validation hooks
- Telemetry
- API tests (if applicable)
- Tenant isolation
- Output: Complete test suite

## Stage 4: Backend Implementation (Agents: Backend Implementer + Governance & Validation Engineer + Observability Engineer + Security Reviewer)
- models.py - typed domain models
- state_machine.py - workflow state transitions
- registry.py - tool contract registry
- tool_contracts.py - tool contract definitions
- human_gates.py - human gate lifecycle
- checkpoints.py - deterministic checkpointing
- policies.py - approval and publication policies
- telemetry.py - structured trace emission
- validation_hooks.py - L5 validation hook abstraction
- API routes (if appropriate)
- Output: All harness modules + tests passing

## Stage 5: Frontend (Agent: Frontend Engineer) - ONLY if backend complete
- Check for existing Governance UI
- Add HarnessRuns list if appropriate
- Add HarnessRunDetail if appropriate
- Use existing primitives only
- Output: Frontend changes (if applicable)

## Stage 6: Verification & Release (Agent: Release Engineer + Final Code Reviewer)
- Run targeted harness tests
- Run Layer 4 unit/integration tests
- Run type/lint checks
- Run contract tests if APIs changed
- Run frontend tests if changed
- Final code review against invariants
- Output: Final report with completion status

## Skill Loading
- Stage 1-2: vibecoding-general-swarm (for coding patterns)
- Stage 3-4: vibecoding-general-swarm + security patterns
- Stage 5: vibecoding-webapp-swarm (if frontend changes)
- Stage 6: General verification
