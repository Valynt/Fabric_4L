# Missing Routes Implementation Plan

**Date:** 2026-05-01
**Status:** Analysis Complete — Ready for Implementation

---

## Executive Summary

| Route | Status | Frontend Hook | Backend Gap | Effort | Priority |
|-------|--------|---------------|-------------|--------|----------|
| `POST /v1/formulas` | ❌ Missing | ✅ `useCreateFormula` | No create endpoint | Medium | P1 |
| `PATCH /v1/formulas/{id}` | ❌ Missing | ✅ `useUpdateFormula` | No update endpoint | Medium | P1 |
| `DELETE /v1/formulas/{id}` | ❌ Missing | ✅ `useDeleteFormula` | No delete endpoint | Low | P1 |
| `GET /v1/roi/benchmarks` | ❌ Missing | Unknown | Lists all benchmarks | Low | P2 |

**Frontend CRUD hooks are implemented and waiting for backend endpoints.**

---

## Root Cause Analysis

### 1. Formula Routes (POST, PATCH, DELETE)

**Current State:**
- `formulas.py` — Has **read-only** endpoints: `GET /formulas`, `GET /formulas/{id}`, `POST /formulas/evaluate`, `POST /formulas/scenario`
- `formula_governance.py` — Has **lifecycle** endpoints: `/{id}/versions`, `/{id}/submit`, `/{id}/approve`, `/{id}/activate`, `/{id}/deprecate`
- **Missing:** Basic CRUD operations (Create, Update, Delete)

**Why Missing:**
1. **Architecture Gap:** Formulas were designed as immutable registry entries initially
2. **Governance-First Approach:** The team built approval workflows before basic CRUD
3. **Frontend-Hooks-First:** Frontend hooks (`useCreateFormula`, `useUpdateFormula`, `useDeleteFormula`) were scaffolded expecting backend to catch up

**Evidence from Contract Map:**
```markdown
| Formula Create | — | L3 | `/v1/formulas` | POST | — | `CreateFormulaInput` | `Formula` | missing | Backend router does not implement plain POST /formulas. Use `/v1/formulas/evaluate` or `/v1/formulas/scenario` instead. |
| Formula Update | — | L3 | `/v1/formulas/{id}` | PATCH | — | `UpdateFormulaInput` | `Formula` | missing | Backend router does not implement PATCH /formulas/{id}. |
| Formula Delete | — | L3 | `/v1/formulas/{id}` | DELETE | — | — | `{ status: string }` | missing | Backend router does not implement DELETE /formulas/{id}. |
```

### 2. ROI Benchmarks Route (GET /v1/roi/benchmarks)

**Current State:**
- `roi_calculator.py` has `GET /roi/benchmarks/{industry}` — requires industry path param
- `benchmarks.py` has `GET /benchmarks` — separate router, no tenant isolation

**Why Missing:**
1. **Path Parameter Mismatch:** Contract expects `/v1/roi/benchmarks` (no industry filter required)
2. **Router Separation:** ROI benchmarks and general benchmarks are in different files
3. **Use Case:** Frontend likely wants to list all benchmarks across industries for ROI calculations

---

## Implementation Plan

### Route 1: POST /v1/formulas (Create Formula)

**File:** `services/layer3-knowledge/src/api/routes/formulas.py`

**Implementation:**
```python
@router.post("/formulas", response_model=FormulaMetadata, status_code=201)
async def create_formula(
    request: CreateFormulaRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
) -> FormulaMetadata:
    """Create a new formula. Requires authentication."""
    # Validate expression syntax
    # Create Formula node in Neo4j
    # Create initial FormulaVersion
    # Return created formula metadata
```

**Required Models:**
```python
class CreateFormulaRequest(BaseModel):
    name: str
    description: str
    expression: str
    variables: list[VariableMetadata]
    output_unit: str
    category: str = "Custom"
    owner: str | None = None
```

**Neo4j Query:**
```cypher
CREATE (f:Formula {
    id: $formula_id,
    name: $name,
    description: $description,
    expression: $expression,
    outputUnit: $output_unit,
    category: $category,
    status: 'draft',
    version: '1.0.0',
    createdAt: $created_at,
    updatedAt: $created_at,
    owner: $owner,
    tenantId: $tenant_id
})
CREATE (fv:FormulaVersion {
    id: $version_id,
    version: '1.0.0',
    formulaId: $formula_id,
    status: 'draft',
    createdAt: $created_at,
    createdBy: $owner,
    changeSummary: 'Initial version'
})
CREATE (f)-[:HAS_VERSION]->(fv)
WITH f
UNWIND $variables as var
CREATE (v:Variable {
    name: var.name,
    displayName: var.display_name,
    type: var.type,
    unit: var.unit,
    required: var.required,
    defaultValue: var.default_value
})
CREATE (f)-[:REQUIRES]->(v)
RETURN f
```

**Acceptance Criteria:**
- [ ] Creates Formula node with tenant isolation
- [ ] Creates initial FormulaVersion (v1.0.0, status=draft)
- [ ] Creates Variable nodes linked to formula
- [ ] Validates expression syntax before creation
- [ ] Returns 201 with created FormulaMetadata
- [ ] Emits audit event for formula creation

**Effort:** 2-3 hours
**Dependencies:** None

---

### Route 2: PATCH /v1/formulas/{id} (Update Formula)

**File:** `services/layer3-knowledge/src/api/routes/formulas.py`

**Implementation:**
```python
@router.patch("/formulas/{formula_id}", response_model=FormulaMetadata)
async def update_formula(
    formula_id: str,
    request: UpdateFormulaRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
) -> FormulaMetadata:
    """Update an existing formula. Creates new version if expression changes."""
    # Check formula exists and is editable (draft/under_review only)
    # If expression changes: create new FormulaVersion
    # Update formula properties
    # Return updated metadata
```

**Required Models:**
```python
class UpdateFormulaRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    expression: str | None = None
    variables: list[VariableMetadata] | None = None
    output_unit: str | None = None
    category: str | None = None
```

**Business Logic:**
- Only formulas in `draft` or `under_review` status can be updated
- If `expression` changes → auto-create new version (bump minor version)
- If only metadata changes → update in-place

**Acceptance Criteria:**
- [ ] Validates formula is editable (not approved/active/deprecated/retired)
- [ ] Handles expression changes by creating new FormulaVersion
- [ ] Updates Variable relationships if variables change
- [ ] Returns updated FormulaMetadata
- [ ] Emits audit event for formula update

**Effort:** 3-4 hours
**Dependencies:** POST /formulas (reuse models)

---

### Route 3: DELETE /v1/formulas/{id} (Delete Formula)

**File:** `services/layer3-knowledge/src/api/routes/formulas.py`

**Implementation:**
```python
@router.delete("/formulas/{formula_id}")
async def delete_formula(
    formula_id: str,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(require_admin_role),  # Admin only
) -> dict[str, str]:
    """Delete a formula and all its versions. Admin only."""
    # Check formula exists
    # Check no active ValuePacks reference this formula
    # Delete Formula, FormulaVersions, and Variable relationships
    # Return success message
```

**Neo4j Query:**
```cypher
// Check for references
MATCH (f:Formula {id: $formula_id})
OPTIONAL MATCH (vp:ValuePack)-[:USES_FORMULA]->(f)
WITH f, count(vp) as ref_count
WHERE ref_count = 0

// Delete
MATCH (f)-[:HAS_VERSION]->(fv:FormulaVersion)
OPTIONAL MATCH (f)-[:REQUIRES]->(v:Variable)
DELETE fv, v
DELETE f
```

**Business Logic:**
- Admin-only operation (require_admin_role)
- Cannot delete if formula is referenced by ValuePacks
- Soft-delete alternative: Could set status to 'deleted' instead

**Acceptance Criteria:**
- [ ] Restricted to admin users
- [ ] Prevents deletion if formula is in use
- [ ] Cascading delete of FormulaVersions and Variables
- [ ] Returns 200 with `{ "status": "deleted" }`
- [ ] Emits audit event for formula deletion

**Effort:** 2 hours
**Dependencies:** None

---

### Route 4: GET /v1/roi/benchmarks (List All ROI Benchmarks)

**File:** `services/layer3-knowledge/src/api/routes/roi_calculator.py`

**Implementation:**
```python
@router.get("/benchmarks", response_model=list[BenchmarkSummary])
async def list_all_benchmarks(
    request: Request,
    industry: str | None = Query(None),
    category: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    tenant_id: str = Depends(get_verified_tenant_id),
):
    """List all benchmarks across industries for ROI calculations."""
    # Query Benchmark nodes with optional filters
    # Return list of benchmarks
```

**Options:**
1. **Reuse existing benchmarks.py router** — Add prefix `/roi` in main.py
2. **Add endpoint to roi_calculator.py** — Duplicate query logic
3. **Proxy/redirect** — ROI router calls benchmarks service

**Recommended: Option 1** — Register `benchmarks.router` with `/roi` prefix in main.py

**Change in main.py:**
```python
from .routes import benchmarks

app.include_router(
    benchmarks.router,
    prefix="/roi",
    tags=["ROI Calculator"],
)
```

**This provides:**
- `GET /roi/benchmarks` — All benchmarks
- `GET /roi/benchmarks/{benchmark_id}` — Single benchmark
- `GET /roi/benchmarks/policies` — Benchmark policies

**Acceptance Criteria:**
- [ ] `GET /v1/roi/benchmarks` returns list of all benchmarks
- [ ] Supports `industry` and `category` query filters
- [ ] Supports pagination (skip/limit)
- [ ] Returns same schema as `GET /v1/benchmarks`

**Effort:** 30 minutes
**Dependencies:** benchmarks.py already exists

---

## Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `formulas.py` | Add POST, PATCH, DELETE endpoints | +150 lines |
| `formulas.py` | Add CreateFormulaRequest, UpdateFormulaRequest models | +30 lines |
| `roi_calculator.py` | Add GET /benchmarks endpoint OR | +30 lines |
| `main.py` | Register benchmarks router with /roi prefix | +5 lines |
| `formula_governance.py` | Add create_formula_version helper | Optional |

---

## Testing Plan

### Backend Tests
```python
# tests/formulas/test_crud.py
def test_create_formula_success():
def test_create_formula_invalid_expression():
def test_create_formula_unauthorized():
def test_update_formula_success():
def test_update_formula_not_editable():
def test_update_formula_creates_new_version():
def test_delete_formula_success():
def test_delete_formula_in_use():
def test_delete_formula_not_admin():
```

### Contract Tests
```bash
pytest tests/contract/test_layer3_contract.py -v
# Verify new endpoints match OpenAPI spec
```

### Frontend Integration
```typescript
// useFormulas.test.ts - Unskip existing tests
it('creates formula successfully')  // Currently works with mocks
it('updates formula successfully')  // Currently works with mocks
it('deletes formula successfully') // Currently works with mocks
```

---

## Implementation Order

1. **POST /v1/formulas** — Foundation for other operations
2. **PATCH /v1/formulas/{id}** — Builds on POST models
3. **DELETE /v1/formulas/{id}** — Simplest, uses existing auth
4. **GET /v1/roi/benchmarks** — Router registration only

**Total Effort:** 8-10 hours
**Risk:** Low — Existing patterns to follow

---

## Notes

- Formula registry currently uses **in-memory static data** (`FORMULA_REGISTRY`). The new CRUD endpoints should transition to **Neo4j persistence**.
- The `formula_governance.py` router already uses Neo4j. Follow its patterns for tenant isolation and audit logging.
- The frontend hooks (`useCreateFormula`, `useUpdateFormula`, `useDeleteFormula`) are **already implemented** and tested with mocks. They will work once backend endpoints are added.
