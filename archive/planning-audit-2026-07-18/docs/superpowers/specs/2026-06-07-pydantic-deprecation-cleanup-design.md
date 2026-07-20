# Pydantic Deprecation Cleanup

## Summary
Migrate remaining Pydantic V1-style `class Config` inner classes to the V2 `model_config = ConfigDict(...)` pattern. This removes `PydanticDeprecatedSince20` warnings and ensures compatibility with Pydantic V3.

## Affected Files
| File | Current Pattern | New Pattern |
|---|---|---|
| `packages/shared/src/value_fabric/shared/security/config.py` | `class Config: extra = "allow"` | `model_config = ConfigDict(extra="allow")` |
| `packages/shared/src/value_fabric/shared/rate_limiting/admin_api.py` | `class Config: json_schema_extra = {...}` | `model_config = ConfigDict(json_schema_extra={...})` |
| `packages/shared/src/value_fabric/shared/audit/models.py` | `class Config: from_attributes = True` | `model_config = ConfigDict(from_attributes=True)` |
| `services/layer4-agents/src/layer4_agents/api/tenants.py` | `class Config: json_schema_extra = {...}` | `model_config = ConfigDict(json_schema_extra={...})` |
| `services/layer3-knowledge/src/models/valuepack.py` (×2) | `class Config: from_attributes = True` | `model_config = ConfigDict(from_attributes=True)` |
| `tests/security/test_input_validation.py` (×2) | `class Config: extra = "forbid"` / `extra = "ignore"` | `model_config = ConfigDict(extra="...")` |

## Migration Rules
1. Replace the inner `class Config:` block with a class-level `model_config = ConfigDict(...)` assignment.
2. Preserve the exact setting values (`extra`, `from_attributes`, `json_schema_extra`).
3. Add `ConfigDict` to the existing `pydantic` import line in each file.

## Validation
- Import each affected module under `warnings.filterwarnings('error', category=PydanticDeprecatedSince20)` and confirm no exception.
- Run targeted tests for the touched services/packages.
- Confirm `ruff check` passes on modified files.

## Risks
- **Low.** This is a purely mechanical, behavior-preserving migration recommended by Pydantic's own migration guide. No model semantics change.
