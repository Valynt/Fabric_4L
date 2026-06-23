---
workflow_id: production-only-delivery
name: Production-Only Delivery
version: 1.0.0
description: Ensure all implementation work results in real, production-grade code with no mock, stub, placeholder, simulated, or shortcut behavior in production paths.
pattern: human-in-the-loop
risk_level: high
---

# Production-Only Delivery Standard

## STEP 1: Restate the real production objective
- Identify the exact production behavior that must work end to end.
- Name the real runtime path, real inputs, real outputs, real persistence, and real integrations involved.
- Do not redefine the task into a prototype, scaffold, or partial simulation.

## STEP 2: Identify production dependencies and contracts
- Enumerate required APIs, services, schemas, interfaces, data models, queues, storage, auth, config, and external dependencies.
- Confirm the real contract for each dependency before coding.
- If a contract is missing, implement or define the real contract cleanly.
- Do not invent fake data or substitute mock behavior in production code.

## STEP 3: Design the minimal real implementation
- Choose the smallest implementation that is still fully real and production-viable.
- Prefer narrow, complete, working slices over broad but shallow scaffolding.
- Keep architecture clean, typed, validated, observable, and maintainable.
- No temporary shims, no hardcoded outputs, no no-op handlers.

## STEP 4: Implement only real production paths
- Wire actual request handling, actual business logic, actual validation, actual persistence, and actual integration calls.
- Use real error handling, retry behavior, logging, and metrics where appropriate.
- Do not simulate downstream services or expected responses in production code.
- If a real integration cannot yet be completed, stop and mark it blocked. Do not fake it.

## STEP 5: Enforce no-shortcut rules during coding
Reject any code that includes:
- mocks or stubs in production code
- placeholder return values
- hardcoded demo data
- fake success responses
- partial implementations presented as complete
- TODO-based core logic gaps
- silent fallbacks that hide incomplete behavior
- simulated backend behavior behind a "temporary" label

## STEP 6: Validate the full runtime path
- Verify the feature works through the real execution path.
- Validate real input handling, real side effects, real persistence, and real outputs.
- Confirm failures are surfaced honestly and observably.
- Confirm no core behavior depends on fake logic.

## STEP 7: Test appropriately
- Production code must stay real.
- Tests may use mocks only where appropriate for isolation in test code.
- Prefer integration or end-to-end verification for critical runtime paths.
- Ensure tests validate actual behavior, not implementation theater.

## STEP 8: Review against production-quality gates
Before declaring completion, confirm:
- code is typed and structured
- contracts are explicit
- validation is real
- error handling is robust
- observability is present
- architecture remains maintainable
- no simulated behavior exists in production paths
- no core logic is deferred behind TODOs

## STEP 9: Report status honestly
Allowed statuses:
- **Complete**: only if the real production path works end to end
- **Partial**: some real parts implemented, with explicit remaining gaps
- **Blocked**: real dependency or contract prevents proper completion

Never claim "done" if:
- behavior is mocked
- output is hardcoded
- integration is simulated
- persistence is skipped
- a placeholder stands in for core logic

## Definition of Done
The feature is done only when the production path operates with real logic, real contracts, real integrations, real data handling, and production-grade quality standards.
