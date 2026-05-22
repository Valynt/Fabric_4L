# Agent Architecture (Layer 4)

> **Scope:** This document covers **Layer 4** agent orchestration only. For the
> end-to-end platform architecture (all six layers, deployment topology, data
> flow), see [`core-concepts/architecture.md`](core-concepts/architecture.md).
> For repository-wide AI agent contributor rules, see the root
> [`AGENTS.md`](../AGENTS.md).

## Overview

Fabric_4L delegates runtime LLM operations through the Layer 4 agent service contract. The services/api orchestrator must not execute local/mock LLM providers.

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

## Runtime Delegation Contract

`services/api` calls Layer 4 contracted endpoints for workflow-step execution.

- No in-process mock provider fallback in production runtime paths.
- Layer 4 unavailability maps to service-unavailable/dependency-failure API responses.
- Provider selection remains inside Layer 4 adapters, preserving provider-agnostic orchestration boundaries.

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

Layer 4 remains the only runtime boundary that selects concrete LLM providers (OpenAI, Together, Anthropic, etc.) through adapters.

Services/API must delegate and fail closed when Layer 4 is unavailable.
