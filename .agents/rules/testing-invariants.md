# Testing Invariants & Behavior-First Governance

No critical behavior exists unless it is tested.

## Testing Standards
1. **Behavior First**: Tests assert what behavior is allowed and what behavior is denied.
2. **Readiness Ladder**:
   - Stage 1: Static contract resolved (`make check-behavior-contract`)
   - Stage 2: Behavior tests executed (`pnpm run test:critical-behaviors`)
   - Stage 3: Readiness audit passed (`make check-behavior-readiness-audit`)
   - Stage 4: Production ready (`make production-readiness-gate`)
3. **Naming**: Name tests after behaviors (e.g. `test_tenant_a_cannot_access_tenant_b_data`), not function names.
4. **Pytest Markers**:
   - `unit`: Fast pure logic without I/O
   - `integration`: Service boundaries with DB/cache
   - `contract_static`: OpenAPI/schema compliance
   - `tenant_boundary`: Cross-tenant security assertions
