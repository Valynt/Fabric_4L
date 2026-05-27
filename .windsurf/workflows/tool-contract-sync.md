---
workflow_id: tool-contract-sync
name: Tool Contract Sync
version: 1.0.0
description: Audit and fix the three-way sync between tool implementations, skill definitions, and tool manifests. Use when tools are registered in the ToolRegistry but missing skill MDs or JSON Schema manifests, or when evals are missing. Closes the gap between 26 registered tools and only 9 skill definitions + 9 manifests + 2 evals.
pattern: circuit-breaker
risk_level: medium
---

# Tool-Contract Sync

Ensures every tool registered in the ToolRegistry has a corresponding skill definition in `layer4-agents/skills/`, a JSON Schema manifest in `contracts/tool-manifests/`, and a golden-trace eval in `tests/evals/skills/`. This is a P0 rule from AGENTS.md: "Do not change a tool manifest without updating the corresponding skill definition."

## When to Use

- After adding, modifying, or removing a tool
- When auditing agent/tool contract compliance
- When the skill count doesn't match the tool count
- Before running `make verify && make evals`

## Current State (as audited)

### Registered Tools (26 in `__init__.py`)

**Knowledge (6):** `query_graph`, `semantic_search`, `get_entity`, `get_relationships`, `traverse_tree`, `find_paths`
**Calculation (4):** `evaluate_formula`, `calculate_roi`, `compare_benchmarks`, `sensitivity_analysis`
**CRM (4):** `get_prospect_data`, `update_opportunity`, `fetch_interaction_history`, `score_lead`
**Generation (5):** `generate_section`, `create_chart`, `format_table`, `assemble_document`, `document_export`
**Integration (4):** `send_notification`, `create_task`, `schedule_meeting`, `export_to_crm`
**Utility (2):** `validate_input`, `format_currency`
**Competitive (1):** `analyze_competition`

### Skill Definitions (9 in `layer4-agents/skills/`)

`assess_drift`, `audit_ai_systems`, `audit_compliance`, `audit_infrastructure`, `audit_performance`, `evaluate_formula`, `generate_business_case`, `graph_traverse`, `semantic_search`

### Tool Manifests (9 in `contracts/tool-manifests/`)

`assess_drift`, `audit_ai_systems`, `audit_compliance`, `audit_infrastructure`, `audit_performance`, `evaluate_formula`, `generate_business_case`, `graph_traverse`, `semantic_search`

### Evals (2 in `tests/evals/skills/`)

`test_evaluate_formula.py`, `test_semantic_search.py`

## Workflow Steps

### Step 1: Generate Gap Report

Read all three sources and cross-reference:

```bash
# Tools registered in code
grep -oP "name = \"[^\"]+\"" services/layer4-agents/src/tools/*.py | sort

# Skill definitions
ls services/layer4-agents/skills/*.md | xargs -I{} basename {} .md | sort

# Tool manifests
ls contracts/tool-manifests/*.json | xargs -I{} basename {} .json | sort

# Evals
ls tests/evals/skills/test_*.py | xargs -I{} basename {} .py | sed 's/^test_//' | sort
```

Produce a gap matrix:

| Tool Name | Implementation | Skill MD | Manifest JSON | Eval Test |
|-----------|---------------|----------|---------------|-----------|
| query_graph | ✅ | ❌ | ❌ | ❌ |
| semantic_search | ✅ | ✅ | ✅ | ✅ |
| evaluate_formula | ✅ | ✅ | ✅ | ✅ |
| calculate_roi | ✅ | ❌ | ❌ | ❌ |
| ... | | | | |

### Step 2: Generate Missing Skill Definitions

For each tool without a skill MD, create `services/layer4-agents/skills/{tool_name}.md`:

```markdown
---
name: {tool_name}
description: {description from BaseTool.description}
---

# {Tool Title}

{Description from the tool class docstring}

## Parameters

- `{param_name}`: {type} — {description} (required|optional)

## Steps

1. Validate input parameters
2. {Step from execute() logic}
3. Return structured result

## Output

Returns {output_schema description} with {key fields}.
```

**To extract parameters:** Read the tool's `input_schema` Pydantic model from the implementation file. Each field becomes a parameter entry.

**To extract steps:** Read the tool's `execute()` method and summarize its logic steps.

### Step 3: Generate Missing Tool Manifests

For each tool without a manifest JSON, create `contracts/tool-manifests/{tool_name}.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://valuefabric.ai/contracts/tool-manifests/{tool_name}.json",
  "name": "{tool_name}",
  "version": "1.0.0",
  "description": "{description from BaseTool.description}",
  "parameters": {
    "type": "object",
    "properties": {
      "{param_name}": {
        "type": "{json_schema_type}",
        "description": "{param_description}"
      }
    },
    "required": ["{required_params}"],
    "additionalProperties": false
  },
  "returns": {
    "type": "object",
    "properties": {
      "{field_name}": {
        "type": "{json_schema_type}",
        "description": "{field_description}"
      }
    },
    "required": ["{required_fields}"]
  }
}
```

**Type mapping (Python → JSON Schema):**
- `str` → `"string"`
- `int` → `"integer"`
- `float` → `"number"`
- `bool` → `"boolean"`
- `list[T]` → `{"type": "array", "items": {"type": "T"}}`
- `dict[str, T]` → `{"type": "object", "additionalProperties": {"type": "T"}}`
- `Optional[T]` → field is NOT in `required` array

### Step 4: Generate Missing Eval Stubs

For each tool without an eval, create `tests/evals/skills/test_{tool_name}.py`:

```python
"""Golden-trace eval for {tool_name} skill."""
import pytest
from value-fabric.layer4-agents.src.tools import {ToolClass}


@pytest.fixture
def tool():
    return {ToolClass}()


class TestGoldenTrace:
    """Golden trace tests for {tool_name}."""

    @pytest.mark.asyncio
    async def test_basic_execution(self, tool):
        """Test basic tool execution with valid input."""
        result = await tool.run({
            # Minimum valid input from input_schema
        })
        assert result is not None
        # Assert on expected output fields

    @pytest.mark.asyncio
    async def test_missing_required_field(self, tool):
        """Test that missing required fields raise ToolValidationError."""
        with pytest.raises(Exception):
            await tool.run({})

    @pytest.mark.asyncio
    async def test_edge_case(self, tool):
        """Test edge case behavior."""
        # Tool-specific edge case
        pass
```

### Step 5: Validate Consistency

After generating all missing artifacts:

1. Verify skill name matches across all three: implementation `.name`, skill MD `name:` frontmatter, manifest `"name"` field
2. Verify parameter names match between implementation `input_schema` and manifest `"parameters"`
3. Verify description is consistent (doesn't need to be identical, but shouldn't contradict)

```bash
# Quick consistency check
python scripts/ci/check_tool_contracts.py
```

### Step 6: Run Verification

```bash
# Collect all evals
python -m pytest tests/evals/ --collect-only -q

# Run evals
python -m pytest tests/evals/ -v --tb=short

# Full verify
make verify && make evals
```

## Edge Cases

- **Audit skills** (`assess_drift`, `audit_*`) have skill MDs and manifests but NO registered tool class — they may be prompt-only skills. Don't create tool implementations for these; they are legitimate skill-only definitions.
- **`document_export`** has a tool implementation but overlaps with `generate_business_case` skill — verify they serve different purposes before creating duplicates.
- **Don't modify migrations** (AGENTS.md P0 rule #3).
- **Eval fixtures:** Use `tests/evals/conftest.py` for shared fixtures. Don't duplicate fixture setup across eval files.
