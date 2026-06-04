---
workflow_id: code-boundary-enforcement
name: Code Boundary Enforcement
version: 1.0.0
description: Enforce strict boundary discipline between domains, dependencies, and system layers
pattern: circuit-breaker
risk_level: medium
---

# Code Boundary Enforcement Workflow

This workflow ensures the codebase maintains clear separation between internal domains, external dependencies, and system layers to maximize maintainability, testability, and security.

## The Seven Boundary Types

This workflow enforces **seven distinct boundary types** that protect system integrity at different scopes:

| Boundary | Scope | Violation Symptom | Healthy Signal |
|----------|-------|-------------------|----------------|
| **Module** | Code organization | Build pulls in internal paths from sibling modules | Module builds independently; imports are internal or from shared, stable packages |
| **Build** | Build process | Docker context = entire repo; language A build breaks due to language B errors | Each service has its own build; no cross-service dependencies in build step |
| **Runtime** | Execution | One service crash cascades to downstream failures | Services depend on network contracts only; graceful degradation on dependency failure |
| **Deployment** | Infrastructure | Cannot roll one layer without rolling others | Each layer is its own Deployment/image; independently rollable |
| **Data** | Information flow | Shared internal objects between layers; implicit schema assumptions | Well-defined schemas; versioned contracts; explicit data transformation at boundaries |
| **Dependency** | Package/imports | One service's dependencies pollute another's build | Dependencies limited to declared runtime requirements |
| **Interface** | API/contracts | Other layers rely on implementation details | Clean HTTP API/message contract; swappable implementations; testable in isolation |

## When to Use

- Creating new modules, functions, or classes
- Reviewing code for architectural integrity
- Refactoring to improve separation of concerns
- Integrating external APIs or databases
- **Before fixing build issues (check Build/Dependency boundaries first)**
- **When a service fails due to unrelated code changes (boundary breach)**
- **When a build breaks due to errors in a different language stack or module**
- Before marking a task as complete
- When code review reveals boundary violations
- Periodic boundary hardening audits

## When to Stop

- All boundary definitions documented and validated
- No boundary smells remain (P0/P1 issues resolved)
- Test doubles replace all external dependencies in unit tests
- Static analysis passes with no boundary violations
- Time budget exhausted (can be refined in follow-up)

## Steps

1. **Define the Boundaries**
   // turbo
   For every module, function, or class, explicitly document:
   - **The Contract**: What inputs are accepted (validated at boundary) and what outputs are guaranteed
   - **The Ownership**: Which layer owns this logic (Domain, Application, Infrastructure, Interface)
   - **The Dependencies**: What external systems or modules this code interacts with (and how interactions are isolated)

2. **Audit External Boundaries**
   Check each boundary type against these protocols:

   **Database Boundaries:**
   - [ ] All queries isolated in Repository/DAO classes (never in domain logic)
   - [ ] Use DTOs or Entities to cross boundary—never pass raw database rows upstream
   - [ ] Transaction boundaries managed at application service layer
   - [ ] Database exceptions translated to domain exceptions at boundary

   **Third-Party API Boundaries:**
   - [ ] Adapter pattern implemented: Interface with concrete adapter (e.g., `ExternalPaymentGateway` → `StripePaymentAdapter`)
   - [ ] HTTP clients wrapped in dedicated gateway classes (no raw fetch/axios in business logic)
   - [ ] External responses validated and sanitized immediately upon entry
   - [ ] Circuit breakers and timeouts configured at adapter level
   - [ ] External data formats mapped to internal domain models within adapter (anti-corruption layer)

   **File System/OS Boundaries:**
   - [ ] File I/O abstracted behind interfaces (`FileStorage` with `LocalFileSystem` and `S3Storage` implementations)
   - [ ] Path traversal prevention: Validate file paths at entry points using `^` and `$` regex anchors
   - [ ] Resource cleanup guaranteed via try-with-resources or equivalent patterns

   **Input Validation Boundaries (Security Critical):**
   - [ ] Validate at outermost layer using strict patterns:
     - Regex anchors: Use `^pattern$` not `pattern`
     - Type coercion: Reject unexpected types immediately
     - Length limits: Enforce maximums to prevent DoS
   - [ ] Sanitize on entry, encode on exit (HTML, SQL, shell context-aware)
   - [ ] Never pass raw user input to system calls, SQL concatenation, or eval

3. **Audit System Boundaries (Layer/Service Level)**
   // turbo
   Verify the seven architectural boundaries for each layer/service:

   **Build Boundary:**
   - [ ] Can build service from its own directory without unrelated code
   - [ ] Docker context narrowed to service directory (not entire monorepo)
   - [ ] Build steps isolated per service (no cross-service compilation)
   - [ ] CI pipeline builds layers independently in parallel

   **Module Boundary:**
   - [ ] Layer is self-contained; no imports from sibling layers' internal paths
   - [ ] Shared code lives in `shared/` or published packages only
   - [ ] No references to sibling module internal paths (e.g., importing UI components into API services)

   **Dependency Boundary:**
   - [ ] Runtime dependencies match declared requirements (no surprise imports)
   - [ ] Cross-stack packages absent (e.g., UI packages in backend, server packages in frontend)
   - [ ] Test utilities from other modules not imported in production code

   **Runtime Boundary:**
   - [ ] Service communicates via network contracts (HTTP/API/messages) only
   - [ ] No assumptions about other services' process models or threading
   - [ ] Graceful degradation when dependencies unavailable

   **Deployment Boundary:**
   - [ ] Each layer is its own Kubernetes Deployment with independent image
   - [ ] Can roll one layer without affecting others
   - [ ] Health checks isolated per service

   **Data Boundary:**
   - [ ] Layer-to-layer communication uses versioned schemas (OpenAPI, JSON Schema)
   - [ ] Data transformations happen at boundary, not leaked into business logic
   - [ ] Pipeline stages (L2→L3→L4) have explicit contract definitions

   **Interface Boundary:**
   - [ ] HTTP API or message contract is the only dependency other layers rely on
   - [ ] Implementation can be swapped without consumer changes
   - [ ] Testable with contract tests/mocks in isolation

4. **Audit Internal Boundaries (Code Level)**
   Verify layer and module boundaries:

   **Layer Boundaries (Clean Architecture/Hexagonal):**
   - [ ] Dependencies point inward only: Domain knows nothing of Application
   - [ ] Dependency Inversion: Domain defines interfaces, Infrastructure implements them
   - [ ] No domain logic in controllers or data access layers

   **Module/Namespace Boundaries:**
   - [ ] Explicit exports (whitelist approach): Only expose intended public APIs
   - [ ] Cross-module communication via published interfaces only
   - [ ] Event-driven boundaries: Use domain events for loose coupling between bounded contexts

   **Function/Method Boundaries (Single Responsibility):
   - [ ] One Reason to Change: Function does one thing; if "and" appears in name, split it
   - [ ] Limit Side Effects: Pure functions preferred; side effects explicit in naming
   - [ ] Parameter Count: Max 3-4 parameters (use parameter objects beyond this)
   - [ ] Return Consistency: Return same types (don't mix `User`, `null`, `false`)

4. **Fix Boundary Violations (P0/P1 Priority)**
   // turbo
   Transform violations into proper boundaries:

   **P0 - Critical (Fix Immediately):**
   - **Build boundary breach**: Service build fails due to unrelated code (cross-language/cross-module errors) → Narrow Docker context, isolate build
   - **Dependency boundary breach**: Packages from one stack in another service's build (e.g., frontend packages in backend) → Clean up dependencies, remove cross-module imports
   - **Module boundary breach**: Importing from sibling module's internal paths → Move to shared/ or use public interface only
   - SQL injection or raw queries in business logic → Extract Repository class
   - Raw HTTP calls in domain code → Implement Adapter pattern
   - Input validation after business logic → Move validation to boundary entry
   - Regex without anchors → Add `^` and `$` anchors
   - Secrets/credentials in logs → Sanitize at boundary

   **P1 - High Priority:**
   - **Runtime boundary fragile**: Service assumes other service's implementation details → Add circuit breaker, use contract testing
   - **Data boundary implicit**: Shared internal objects between layers → Define explicit schema, add transformation layer
   - Hardcoded strings/numbers in boundary code → Extract constants
   - No retry logic on external calls → Add circuit breaker at adapter
   - Direct dependency instantiation → Inject via constructor
   - Missing type coercion at validation → Add strict type checks

   **Example Transformation:**
   ```javascript
   // ❌ Boundary Violation:
   function processOrder(orderData) {
     const user = db.query(`SELECT * FROM users WHERE id = ${orderData.userId}`);
     const payment = await fetch('https://api.stripe.com/v1/charges', {...});
     fs.writeFileSync('receipts/' + orderData.id + '.txt', ...);
   }

   // ✅ Boundary Respecting:
   class OrderProcessor {
     constructor(userRepo, paymentGateway, receiptStore) {
       this.userRepo = userRepo;
       this.paymentGateway = paymentGateway;
       this.receiptStore = receiptStore;
     }
     async process(orderData) {
       const validatedOrder = OrderValidator.validate(orderData);
       const user = await this.userRepo.findById(validatedOrder.userId);
       const payment = await this.paymentGateway.charge(user, validatedOrder.amount);
       if (payment.isSuccessful()) {
         await this.receiptStore.save(payment.receipt);
         return Result.success(payment);
       }
       return Result.failure(payment.error);
     }
   }
   ```

5. **Verify Testability**
   // turbo
   Ensure boundaries support proper testing:

   - [ ] **Mockability**: External dependencies replaceable with test doubles without code changes
   - [ ] **Interface-Based Testing**: Unit tests target interfaces, not concrete implementations
   - [ ] **Boundary Testing**: Verify code handles external contract violations (timeouts, malformed data, nulls)
   - [ ] **No Real Services in Unit Tests**: Database, HTTP calls, file system faked/isolated

   **Test Double Strategy:**
   - [ ] **Stubs**: For providing fixed data to drive code under test
   - [ ] **Mocks**: For verifying interactions across boundaries
   - [ ] **Fakes**: Lightweight in-memory implementations for integration testing
   - [ ] **Spies**: For capturing boundary-crossing data for verification

6. **Detect and Fix Boundary Smells**
   Scan for red flags and refactor:

   **Immediate Red Flags:**
   - [ ] **Leaky Abstractions**: Internal data structures exposed in public method signatures
   - [ ] **Temporal Coupling**: Method B must be called immediately after Method A
   - [ ] **Feature Envy**: Method in Class A reaching into private state of Class B
   - [ ] **Shotgun Surgery**: One change requires edits in 5+ files
   - [ ] **Global State**: Static variables bypassing explicit boundaries

   **Security Smells:**
   - [ ] Input validation after business logic processing
   - [ ] Regex without anchors allowing substring bypasses
   - [ ] Type juggling at security boundaries

7. **Document Boundaries**
   // turbo
   For each boundary crossing, document:
   ```markdown
   ## Boundary: [Module A] ↔ [Module B]
   - **Contract**: [Interface definition or API spec]
   - **Data Format**: [JSON Schema, Protobuf, or Type definitions]
   - **Error Handling**: [How failures are propagated/retried]
   - **Ownership**: [Team/Module responsible for maintenance]
   - **SLA**: [Performance expectations at this seam]
   ```

8. **Final Review**
   // turbo
   - Run all tests to ensure nothing broke
   - Verify unit tests use mocks, not real services
   - Check that external dependencies are injectable
   - Confirm no boundary violations remain in static analysis
   - Commit with descriptive message: "Boundary: [specific enforcement made]"

## Success Criteria (Definition of Done)

### System Boundaries (Layer/Service Level)
- [ ] Each layer builds independently from its own directory
- [ ] Docker context narrowed; no cross-service build dependencies
- [ ] No P0 boundary breaches (build/dependency/module/runtime)
- [ ] Layers deploy independently; failure in one doesn't cascade
- [ ] Data contracts (OpenAPI/JSON Schema) defined for inter-layer pipelines

### Code Boundaries (Module/Function Level)
- [ ] All external dependencies isolated behind interfaces/adapters
- [ ] Input validation occurs at outermost layer with strict patterns
- [ ] Unit tests use test doubles (no real database/HTTP/file system)
- [ ] No P0 or P1 boundary violations remain
- [ ] Boundary documentation complete for all major seams
- [ ] Static analysis passes with no import/boundary violations
- [ ] Code is now swappable (can change DB/API without touching domain logic)

## Concrete Actions Checklist

Use this to ensure direct improvements:

- [ ] Defined contract, ownership, and dependencies for all new modules
- [ ] Extracted at least one boundary violation into proper adapter/repository
- [ ] Added input validation with anchored regex or strict type checking
- [ ] Implemented at least one test double for external dependency
- [ ] Documented at least one boundary crossing with contract/data format/error handling
- [ ] Fixed at least one boundary smell (leaky abstraction, temporal coupling, feature envy)
- [ ] Moved validation to outermost layer (controller/gateway)
- [ ] Verified no real services in unit tests
- [ ] Committed with descriptive message explaining boundary enforcement

## Anti-Patterns to Avoid

### System Boundary Anti-Patterns
- **Don't**: Build a service from the entire monorepo context (violates Build boundary)
- **Don't**: Allow errors in one language stack to break builds in another (violates Dependency boundary)
- **Don't**: Import from sibling module internal paths like `../other-module/src/` (violates Module boundary)
- **Don't**: Assume other service's process model or threading (violates Runtime boundary)
- **Don't**: Roll all layers together as one unit (violates Deployment boundary)
- **Don't**: Pass raw internal objects between layers without schema (violates Data boundary)
- **Don't**: Rely on implementation details of other services (violates Interface boundary)

### Code Boundary Anti-Patterns
- **Don't**: Mix business logic with database queries or HTTP calls
- **Don't**: Pass raw user input to system calls or SQL concatenation
- **Don't**: Use regex without anchors (`/admin/i` instead of `/^admin$/i`)
- **Don't**: Expose internal data structures (HashMaps, database rows) in public APIs
- **Don't**: Allow global state to bypass explicit boundaries
- **Don't**: Validate input after business logic processing
- **Don't**: Use real services in unit tests (database, HTTP, file system)
- **Don't**: Leave TODOs for "future boundary cleanup"

## Example Commands

"Enforce boundaries on the payment processing module"
"Audit the extraction pipeline for boundary violations"
"Apply adapter pattern to the third-party API integration"
"Document the database boundary contracts for the knowledge layer"
"Refactor the file system access to use proper abstraction"
"Harden input validation boundaries on all entry points"
"Verify testability of the agent orchestration boundaries"
"Fix build boundary: narrow Docker context to service directory"
"Audit data boundaries between pipeline stages for schema contract drift"
"Restore dependency boundary: remove cross-stack imports from service"
## Required State JSON

Every workflow MUST maintain and update an explicit state object. Agents read this state at the start of every turn.

```json
{
  "stage": "inspection|analysis|execution|validation|reporting",
  "agent_id": "code-boundary-enforcement-001",
  "files_touched": [],
  "tests_run": [],
  "decisions_made": [],
  "blocked_by": null,
  "retry_count": 0,
  "circuit_breaker": {
    "tripped": false,
    "reason": null,
    "escalation_path": null
  }
}
```

## Circuit Breaker Configuration

```yaml
circuit_breaker:
  max_tool_errors: 3
  max_self_correction_loops: 2
  action_on_trip: halt_and_escalate
  escalation_path: "log_and_notify"
```

## Completion Checklist

- [ ] State JSON updated with current stage, touched files, tests, and decisions.
- [ ] Circuit breaker evaluated before retrying after tool errors or self-correction loops.
- [ ] Relevant validation commands run and recorded in the workflow state.
- [ ] No security, tenant-isolation, contract, governance, or frontend-design assertions weakened.
