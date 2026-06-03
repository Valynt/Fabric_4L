---
skill_id: structured-outputs
name: structured-outputs
version: 1.0.0
description: Pydantic-based structured output validation and LLM response parsing with OpenAI/Anthropic function calling and JSON schema enforcement
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Structured Outputs with LLMs

Use this skill when implementing LLM integrations that require:
- Type-safe response parsing from LLM outputs
- Function calling with Pydantic models
- JSON schema validation for extraction tasks
- Fallback handling for malformed responses

## Core Patterns

### Pydantic Response Models
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedCapability(BaseModel):
    name: str = Field(description="The capability name")
    description: str = Field(description="What the capability does")
    confidence: float = Field(ge=0, le=1, description="Extraction confidence")
    evidence_quotes: List[str] = Field(description="Verbatim supporting text")

class ExtractionResult(BaseModel):
    capabilities: List[ExtractedCapability]
    model_config = {"extra": "forbid"}  # Strict validation
```

### OpenAI Structured Output
```python
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

response = await client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[{"role": "user", "content": prompt}],
    response_format=ExtractionResult,  # Pydantic class
)

result: ExtractionResult = response.choices[0].message.parsed
```

### Anthropic Tool Use Pattern
```python
from anthropic import AsyncAnthropic

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = await client.messages.create(
    model="claude-3-5-sonnet-20241022",
    messages=messages,
    tools=[{
        "name": "extract_capabilities",
        "description": "Extract capabilities from text",
        "input_schema": ExtractionResult.model_json_schema()
    }],
    tool_choice={"type": "tool", "name": "extract_capabilities"}
)
```

### Fallback Handling
```python
from pydantic import ValidationError

async def extract_with_fallback(text: str, client_type: str = "openai"):
    """Try structured output, fall back to manual parsing."""
    try:
        if client_type == "openai":
            return await extract_openai(text)
        else:
            return await extract_anthropic(text)
    except ValidationError as e:
        logger.warning(f"Validation failed: {e}")
        # Fall back to raw completion + manual parsing
        return await extract_raw_with_repair(text, e)
```

## Project-Specific Conventions

- **Ontology Models**: Base extraction schemas in `layer2-extraction/src/models/ontology.py`
- **Confidence Scoring**: Always include confidence field (0.0-1.0)
- **Evidence Quotes**: Require verbatim source text for all extractions
- **Location**: Implement in `layer2-extraction/src/extraction/llm_extractor.py`

## Validation Best Practices

```python
class TruthValidationResult(BaseModel):
    is_valid: bool
    violations: List[str] = []
    corrected_value: Optional[str] = None
    
    @field_validator("violations")
    @classmethod
    def check_validity_consistency(cls, v, info):
        is_valid = info.data.get("is_valid")
        if is_valid and v:
            raise ValueError("Cannot have violations if is_valid=True")
        if not is_valid and not v:
            raise ValueError("Must have violations if is_valid=False")
        return v
```

## Anti-Patterns to Avoid

- Don't use `dict` response parsing without schema validation
- Don't ignore validation errors in production code
- Don't trust LLM confidence scores without logprob analysis
- Don't return partial results without marking them incomplete
