---
skill_id: tool-contract-sync
name: tool-contract-sync
version: 1.0.0
description: Audit and fix the three-way sync between tool implementations, skill definitions, and tool manifests. Use when tools are registered in the ToolRegistry but missing skill MDs or JSON Schema manifests, or when evals are missing. Closes the gap between 26 registered tools and only 9 skill definitions + 9 manifests + 2 evals.
side_effects: write
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Tool-Contract Sync

Ensures every tool in ToolRegistry has a skill definition, JSON Schema manifest, and golden-trace eval. AGENTS.md P0 rule: "Do not change a tool manifest without updating the corresponding skill definition."

## When to Use

- After adding, modifying, or removing a tool
- When auditing agent/tool contract compliance
- When skill count doesn't match tool count
- Before running `make verify && make evals`

## Current State

### Registered Tools (26 in `__init__.py`)

- **Knowledge (6):** query_graph, semantic_search, get_entity, get_relationships, traverse_tree, find_paths
- **Calculation (4):** evaluate_formula, calculate_roi, compare_benchmarks, sensitivity_analysis
- **CRM (4):** get_prospect_data, update_opportunity, fetch_interaction_history, score_lead
- **Generation (5):** generate_section, create_chart, format_table, assemble_document, document_export
- **Integration (4):** send_notification, create_task, schedule_meeting, export_to_crm
- **Utility (2):** validate_input, format_currency
- **Competitive (1):** analyze_competition

### Skill Definitions (9 in `layer4-agents/skills/`)

assess_drift, audit_ai_systems, audit_compliance, audit_infrastructure, audit_performance, evaluate_formula, generate_business_case, graph_traverse, semantic_search

### Tool Manifests (9 in `contracts/tool-manifests/`)

assess_drift, audit_ai_systems, audit_compliance, audit_infrastructure, audit_performance, evaluate_formula, generate_business_case, graph_traverse, semantic_search

### Evals (2 in `tests/evals/skills/`)

test_evaluate_formula.py, test_semantic_search.py

## Workflow Steps

### Step 1: Generate Gap Report

Cross-reference all three sources:

```bash
# Tools registered
grep -oP "name = \"[^\"]+\"" services/layer4-agents/src/tools/*.py | sort

# Skills
ls services/layer4-agents/skills/*.md | xargs -I{} basename {} .md | sort

# Manifests
ls contracts/tool-manifests/*.json | xargs -I{} basename {} .json | sort

# Evals
ls tests/evals/skills/test_*.py | xargs -I{} basename {} .py | sed 's/^test_//' | sort
```

Gap matrix:

| Tool | Impl | Skill | Manifest | Eval |
|------|------|-------|----------|------|
| query_graph | ✅ | ❌ | ❌ | ❌ |
| semantic_search | ✅ | ✅ | ✅ | ✅ |
| calculate_roi | ✅ | ❌ | ❌ | ❌ |
| ... | | | | |

### Step 2: Generate Missing Skill Definitions

For each tool without skill MD, create `services/layer4-agents/skills/{tool_name}.md`:

```markdown
---
name: {tool_name}
description: {description from BaseTool.description}
---

# {Tool Title}

{Description from tool class docstring}

## Parameters

- `{param_name}`: {type} — {description} (required|optional)

## Steps

1. Validate input parameters
2. {Step from execute() logic}
3. Return structured result

## Output

Returns {output_schema description} with {key fields}.
```

Extract parameters from the tool's `input_schema` Pydantic model. Extract steps from `execute()` method.

### Step 3: Generate Missing Tool Manifests

For each tool without manifest, create `contracts/tool-manifests/{tool_name}.json`:

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

**Type mapping:**
- `str` → `"string"`
- `int` → `"integer"`
- `float` → `"number"`
- `bool` → `"boolean"`
- `list[T]` → `{"type": "array", "items": {"type": "T"}}`
- `Optional[T]` → NOT in `required` array

### Step 4: Generate Missing Eval Stubs

For each tool without eval, create `tests/evals/skills/test_{tool_name}.py`:

```python
"""Golden-trace eval for {tool_name} skill."""
import pytest
from value-fabric.layer4-agents.src.tools import {ToolClass}

@pytest.fixture
def tool():
    return {ToolClass}()

class TestGoldenTrace:
    @pytest.mark.asyncio
    async def test_basic_execution(self, tool):
        result = await tool.run({
            # Minimum valid input from input_schema
        })
        assert result is not None

    @pytest.mark.asyncio
    async def test_missing_required_field(self, tool):
        with pytest.raises(Exception):
            await tool.run({})

    @pytest.mark.asyncio
    async def test_edge_case(self, tool):
        pass
```

### Step 5: Validate Consistency

After generating all artifacts:
1. Verify skill name matches across implementation `.name`, skill MD `name:`, manifest `"name"`
2. Verify parameter names match between `input_schema` and manifest `"parameters"`
3. Verify descriptions don't contradict

```bash
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

- **Audit skills** (`assess_drift`, `audit_*`) have skill MDs and manifests but NO registered tool class — they are prompt-only skills. Don't create tool implementations.
- **Don't modify migrations** (AGENTS.md P0 rule #3).
- **Eval fixtures:** Use `tests/evals/conftest.py` for shared fixtures. Don't duplicate setup.
