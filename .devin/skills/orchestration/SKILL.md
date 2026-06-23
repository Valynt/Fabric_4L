---
skill_id: orchestration
name: orchestration
version: 1.0.0
description: LangGraph-based workflow orchestration for multi-step agent processes with state management, checkpointing, and human-in-the-loop integration
side_effects: none
timeout_ms: 30000
required_context:
  - project_graph
allowed_agents:
  - "*"
---

# LangGraph Workflow Orchestration

Use this skill when building or modifying agent workflows in Layer 4 that require:
- Multi-step state machines with persistence
- Tool registry execution patterns
- Human-in-the-loop checkpoints
- Workflow resumption and error recovery

## Core Patterns

### State Graph Definition
```python
from langgraph.graph import StateGraph, END
from layer4_agents.src.models.agent_state import AgentState

builder = StateGraph(AgentState)
builder.add_node("analyze", analyze_node)
builder.add_node("tools", tool_node)
builder.add_node("human_review", human_review_node)
builder.add_conditional_edges("analyze", route_decision)
builder.add_edge("tools", "analyze")
builder.add_edge("human_review", END)
```

### Checkpoint Persistence
```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.postgres import PostgresStore

# For testing
memory = MemorySaver()

# For production
store = PostgresStore(conn_string=os.getenv("DATABASE_URL"))
```

### Human-in-the-Loop Pattern
```python
def human_review_node(state: AgentState) -> AgentState:
    """Pause for human approval before critical actions."""
    if state.get("requires_approval"):
        raise NodeInterrupt("Approval required for: " + state["proposed_action"])
    return state
```

## Project-Specific Conventions

- **State Schema**: Use `layer4-agents/src/models/agent_state.py` as canonical state definition
- **Tool Registry**: Import tools from `layer4-agents/src/tools/registry.py`
- **State Manager**: Redis-backed persistence at `layer4-agents/src/engine/state_manager.py`
- **Workflow Location**: All workflow definitions in `layer4-agents/src/workflows/`

## Testing Approach

```python
def test_workflow_resumption():
    graph = build_workflow_graph()
    config = {"configurable": {"thread_id": "test-1"}}
    
    # Run to interruption
    result = graph.invoke({"input": "test"}, config, stream_mode="values")
    
    # Resume from checkpoint
    result = graph.invoke(Command(resume=True), config)
```

## Anti-Patterns to Avoid

- Don't create stateful classes in nodes (use pure functions)
- Don't access database directly from nodes (use state updates)
- Don't hardcode thread IDs (require them in config)
- Don't ignore checkpoint serialization errors
