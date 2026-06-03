---
skill_id: evals
name: evals
version: 1.0.0
description: Evaluation frameworks for agent performance, output quality, and extraction accuracy with metrics collection and regression testing
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# Evaluation Framework

Use this skill when building:
- Agent output quality assessment
- Extraction accuracy measurement
- Regression test suites for LLM pipelines
- A/B testing for prompt variations
- Benchmark datasets for continuous validation

## Core Patterns

### Extraction Evaluation
```python
from dataclasses import dataclass
from typing import List, Optional
from difflib import SequenceMatcher

@dataclass
class ExtractionScore:
    precision: float
    recall: float
    f1: float
    semantic_similarity: float
    entity_matches: List[tuple]  # (predicted, ground_truth)

def evaluate_extraction(
    predicted: List[ExtractedEntity],
    ground_truth: List[ExtractedEntity],
    similarity_threshold: float = 0.85
) -> ExtractionScore:
    """Compare predicted entities against ground truth."""
    matches = []
    for pred in predicted:
        best_match = None
        best_score = 0
        for gt in ground_truth:
            score = entity_similarity(pred, gt)
            if score > best_score and score >= similarity_threshold:
                best_score = score
                best_match = gt
        if best_match:
            matches.append((pred, best_match))
    
    precision = len(matches) / len(predicted) if predicted else 0
    recall = len(matches) / len(ground_truth) if ground_truth else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) else 0
    
    return ExtractionScore(
        precision=precision,
        recall=recall,
        f1=f1,
        semantic_similarity=avg_semantic_score(matches),
        entity_matches=matches
    )

def entity_similarity(a: ExtractedEntity, b: ExtractedEntity) -> float:
    """Compute weighted similarity across entity fields."""
    name_sim = SequenceMatcher(None, a.name, b.name).ratio()
    desc_sim = embedding_similarity(a.description, b.description)
    return 0.6 * name_sim + 0.4 * desc_sim
```

### Agent Trajectory Evaluation
```python
from layer4_agents.src.workflows.base import WorkflowResult

@dataclass
class TrajectoryMetrics:
    steps_to_completion: int
    tool_calls_used: List[str]
    human_interventions: int
    cost_estimate: float
    success: bool
    error_type: Optional[str]

def evaluate_workflow(
    result: WorkflowResult,
    expected_output: dict,
    max_acceptable_cost: float = 2.00
) -> TrajectoryMetrics:
    """Assess workflow execution quality."""
    metrics = TrajectoryMetrics(
        steps_to_completion=len(result.state_history),
        tool_calls_used=[s.get("tool") for s in result.state_history if "tool" in s],
        human_interventions=count_interrupts(result),
        cost_estimate=estimate_cost(result.llm_calls),
        success=result.success,
        error_type=result.error_type if not result.success else None
    )
    
    # Assert quality thresholds
    assert metrics.cost_estimate <= max_acceptable_cost, \
        f"Cost {metrics.cost_estimate} exceeded budget {max_acceptable_cost}"
    
    return metrics
```

### Regression Test Suite
```python
import pytest
from pathlib import Path
import json

BENCHMARK_DIR = Path(__file__).parent / "benchmarks"

@pytest.mark.parametrize("test_case", load_test_cases(BENCHMARK_DIR / "extraction"))
async def test_extraction_regression(test_case: dict):
    """Run extraction against golden dataset."""
    result = await llm_extractor.extract(
        content=test_case["input"],
        output_schema=test_case["schema"]
    )
    
    score = evaluate_extraction(
        predicted=result.entities,
        ground_truth=test_case["expected_entities"]
    )
    
    # Fail if F1 drops below historical baseline
    baseline = test_case["baseline_f1"]
    assert score.f1 >= baseline * 0.95, \
        f"F1 {score.f1:.3f} dropped below 95% of baseline {baseline:.3f}"
```

### Prompt A/B Testing
```python
async def compare_prompt_variants(
    variants: List[str],
    test_cases: List[dict],
    n_trials: int = 3
) -> dict:
    """Compare prompt performance across variants."""
    results = {v: [] for v in variants}
    
    for variant in variants:
        for case in test_cases:
            scores = []
            for _ in range(n_trials):
                result = await run_with_prompt(variant, case)
                scores.append(evaluate(result, case["expected"]))
            results[variant].append(sum(scores) / len(scores))
    
    return {
        variant: {
            "mean": sum(scores) / len(scores),
            "variance": variance(scores)
        }
        for variant, scores in results.items()
    }
```

## Project-Specific Conventions

- **Benchmark Location**: Store in `layer2-extraction/tests/benchmarks/` or `layer4-agents/tests/benchmarks/`
- **Metrics Storage**: Log to Prometheus via `layer3-knowledge/src/middleware/metrics.py`
- **Baseline Tracking**: Store in `.eval_baselines/` with commit hash
- **CI Integration**: Run on PR with `pytest --eval-only`

## Integration Points

```python
# Ground truth validation
from layer5_ground_truth.src.services.truth_service import get_truth_objects

# Cost tracking
from layer4_agents.src.engine.cost_tracker import CostTracker

# Metrics export
from layer3_knowledge.src.middleware.metrics import record_eval_metric
```

## Anti-Patterns to Avoid

- Don't evaluate on training data (maintain train/test split)
- Don't ignore variance in LLM outputs (run multiple trials)
- Don't use exact string matching for semantic content
- Don't let baselines drift without explicit approval
