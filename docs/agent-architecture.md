# Agent Architecture (Layer 4)

> **Scope:** This document covers **Layer 4** agent orchestration only. For the
> end-to-end platform architecture (all six layers, deployment topology, data
> flow), see [`core-concepts/architecture.md`](core-concepts/architecture.md).
> For repository-wide AI agent contributor rules, see the root
> [`AGENTS.md`](../AGENTS.md).

## Overview

Fabric_4L uses a mockable agent orchestration layer for MVP. Real LLM providers can be plugged in later.

## Agents

- Account Research Agent
- Signal Extraction Agent
- Stakeholder Mapping Agent
- Ontology Match Agent
- Hypothesis Generation Agent
- Driver Tree Agent
- Evidence Matching Agent
- ROI Modeling Agent
- Business Case Agent
- Value Realization Agent
- Governance Review Agent

## LLM Provider Interface

```python
class LLMProvider:
    def generateStructured(self, prompt: str, schema: dict) -> dict
    def summarize(self, text: str) -> str
    def extract(self, text: str, fields: list) -> dict
    def classify(self, text: str, labels: list) -> str
    def reason(self, premise: str, question: str) -> str
```

## MockLLMProvider

Returns deterministic seeded outputs for all methods. Used in MVP to avoid requiring real API keys.

## AgentOrchestrator

Manages the agent lifecycle:
- `create_run()` - Initialize an agent run
- `execute_step()` - Run a step with optional tool execution
- `resume_run()` - Resume a paused run
- `cancel_run()` - Cancel a run

## Workflow States

- `pending`
- `running`
- `paused`
- `completed`
- `failed`
- `cancelled`

## Review Gates

Agent runs can set `review_required=True` to pause for human approval before continuing.

## Production Integration

Replace `MockLLMProvider` with:
- OpenAI GPT-4/4o
- Together.ai Llama 3
- Anthropic Claude

Add LangGraph for complex multi-step workflows with checkpointing.
