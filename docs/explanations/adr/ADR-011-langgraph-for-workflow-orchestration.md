<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-011: LangGraph for Workflow Orchestration

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** AI/ML Architecture Committee

---

## Context

Layer 4 (Agentic Workflow Engine) needs to orchestrate:
- Multi-step AI workflows (whitespace analysis, ROI calculation, business case generation)
- Human-in-the-loop approval gates
- Long-running processes (5+ minutes end-to-end)
- Complex state management across tool calls
- Checkpoint/resume for fault tolerance

We evaluated:
1. **LangGraph** (LangChain's graph-based workflow framework)
2. **Temporal** (Durable execution platform)
3. **Celery + State Machine** (Traditional task queue)
4. **Custom Orchestrator** (Build from scratch)

## Decision

We chose **LangGraph** with PostgreSQL checkpoint persistence:

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import AsyncPostgresSaver

# Build workflow graph
workflow = StateGraph(AgentState)
workflow.add_node("extract", extract_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("generate", generate_node)
workflow.add_node("human_approval", human_approval_node)

workflow.add_edge("extract", "analyze")
workflow.add_edge("analyze", "generate")
workflow.add_conditional_edges(
    "generate",
    route_based_on_confidence,
    {"approved": END, "needs_review": "human_approval"}
)
```

## Rationale

### Comparison Matrix

| Criteria | LangGraph | Temporal | Celery + SM | Custom |
|----------|-----------|----------|-------------|--------|
| LLM Integration | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| State Management | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Human-in-the-Loop | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ |
| Checkpoint/Resume | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| Observability | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| Learning Curve | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐ |
| Vendor Lock-in | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

### Why LangGraph?

1. **Native LLM Support**: Built for AI agent workflows
   - Streaming support for real-time updates
   - Token usage tracking
   - Structured output parsing
   - Prompt management

2. **Stateful Execution**: Persistent state across nodes
   ```python
   class AgentState(TypedDict):
       messages: Annotated[list, add_messages]
       extracted_entities: list[Entity]
       analysis_result: AnalysisResult
       confidence_score: float
       requires_approval: bool
   ```

3. **Human-in-the-Loop**: Built-in interrupt/resume
   ```python
   # Workflow pauses for human approval
   workflow.add_node("human_approval", human_approval_node)
   workflow.add_interrupt("human_approval")
   
   # Resume after approval
   await workflow.resume(thread_id, human_input={"approved": True})
   ```

4. **Checkpoint Persistence**: Fault-tolerant execution
   ```python
   # PostgreSQL-backed checkpointing
   saver = AsyncPostgresSaver(pool)
   workflow.compile(checkpointer=saver)
   
   # Automatic resume on failure
   await workflow.ainvoke(
       initial_state,
       config={"configurable": {"thread_id": workflow_id}}
   )
   ```

5. **Streaming**: Real-time progress updates
   ```python
   async for event in workflow.astream(initial_state):
       if event["type"] == "tool_call":
           await websocket.send({
               "status": "tool_executing",
               "tool": event["tool"],
           })
   ```

### Why Not Temporal?

- Learning curve for complex workflows
- Less native LLM integration
- Additional infrastructure (Temporal server)
- Heavier weight for our use case

### Why Not Celery + State Machine?

- Manual state management complexity
- No built-in checkpoint/resume
- Limited observability
- Task chaining becomes unwieldy

### Why Not Custom?

- Significant development effort
- Maintenance burden
- Missing battle-tested patterns
- Opportunity cost

## Trade-offs

### Positive
- Purpose-built for AI agent workflows
- Stateful execution with persistence
- Human-in-the-loop support
- Strong observability integration
- Active ecosystem and community

### Negative
- Newer framework (rapid evolution)
- Dependency on LangChain ecosystem
- Limited workflow visualization
- Learning curve for graph concepts

## Mitigations

| Risk | Mitigation |
|------|-----------|
| Framework evolution | Pin versions, thorough testing, abstraction layer |
| Vendor lock-in | Abstract workflow interface, no deep coupling |
| Debugging | OpenTelemetry tracing, structured logging |
| Complexity | Documentation, code reviews, patterns library |

## Implementation

### Workflow Definition Pattern

```python
class WhitespaceAnalysisWorkflow:
    """Production workflow with checkpointing and error handling."""
    
    def __init__(self, tool_registry: ToolRegistry, checkpoint_saver: AsyncPostgresSaver):
        self.tool_registry = tool_registry
        self.saver = checkpoint_saver
        self.graph = self._build_graph()
    
    def _build_graph(self) -> CompiledStateGraph:
        """Build workflow graph with error handling."""
        workflow = StateGraph(AnalysisState)
        
        # Add nodes
        workflow.add_node("ingest", self._ingest_node)
        workflow.add_node("extract", self._extract_node)
        workflow.add_node("analyze", self._analyze_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("error_handler", self._error_handler_node)
        
        # Add edges
        workflow.add_edge("ingest", "extract")
        workflow.add_edge("extract", "analyze")
        workflow.add_conditional_edges(
            "analyze",
            self._route_based_on_confidence,
            {
                "generate": "generate",
                "needs_review": "human_review",
            }
        )
        workflow.add_edge("generate", END)
        
        # Error handling
        workflow.add_node("error_handler", self._handle_error)
        
        # Compile with checkpointing
        return workflow.compile(
            checkpointer=self.saver,
            interrupt_before=["human_review"],
        )
    
    async def execute(
        self,
        inputs: AnalysisInputs,
        tenant_id: UUID,
        user_id: str,
    ) -> AnalysisResult:
        """Execute workflow with full observability."""
        
        workflow_id = str(uuid4())
        
        # Initialize state
        initial_state = AnalysisState(
            tenant_id=tenant_id,
            user_id=user_id,
            inputs=inputs,
            step="ingest",
            started_at=datetime.utcnow(),
        )
        
        # Execute with streaming
        final_state = None
        async for event in self.graph.astream(
            initial_state,
            config={
                "configurable": {"thread_id": workflow_id},
                "metadata": {
                    "tenant_id": str(tenant_id),
                    "user_id": user_id,
                    "workflow_type": "whitespace_analysis",
                },
            },
        ):
            # Stream progress to WebSocket
            await self._emit_progress(tenant_id, workflow_id, event)
            
            if event["type"] == "state":
                final_state = event["data"]
        
        return AnalysisResult(
            workflow_id=workflow_id,
            result=final_state["result"],
            completed_at=datetime.utcnow(),
        )
```

### Error Handling and Recovery

```python
class ResilientWorkflowNode:
    """Base class for resilient workflow nodes."""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    
    async def execute_with_retry(
        self,
        state: AgentState,
    ) -> AgentState:
        """Execute node with exponential backoff retry."""
        
        for attempt in range(self.MAX_RETRIES):
            try:
                return await self._execute(state)
            except TransientError as e:
                if attempt == self.MAX_RETRIES - 1:
                    raise
                
                delay = self.RETRY_DELAY * (2 ** attempt)
                logger.warning(
                    "Node retry",
                    node=self.__class__.__name__,
                    attempt=attempt + 1,
                    delay=delay,
                    error=str(e),
                )
                await asyncio.sleep(delay)
            except PermanentError:
                # Don't retry permanent errors
                raise
    
    @abstractmethod
    async def _execute(self, state: AgentState) -> AgentState:
        """Implement node logic."""
        pass
```

### Observability Integration

```python
class TracedWorkflow:
    """Workflow with OpenTelemetry tracing."""
    
    def __init__(self):
        self.tracer = trace.get_tracer("layer4-agents")
    
    async def _ingest_node(self, state: AgentState) -> AgentState:
        """Ingest node with full tracing."""
        
        with self.tracer.start_as_current_span("workflow.ingest") as span:
            span.set_attribute("workflow_id", state["workflow_id"])
            span.set_attribute("tenant_id", str(state["tenant_id"]))
            
            try:
                # Execute ingestion
                documents = await self.ingestion_service.ingest(
                    state["inputs"]["urls"]
                )
                
                span.set_attribute("documents_ingested", len(documents))
                
                return {
                    **state,
                    "documents": documents,
                    "step": "extract",
                }
            
            except Exception as e:
                span.record_exception(e)
                span.set_status(StatusCode.ERROR)
                raise
```

## Consequences

### Accepted
- Dependency on LangChain/LangGraph ecosystem
- Learning curve for graph-based workflows
- Limited workflow visualization tools

### Mitigated
- Ecosystem evolution via abstraction layer
- Learning curve via documentation and patterns
- Visualization via custom tooling

## Related Decisions

- ADR-001: Multi-layer architecture
- ADR-007: OpenTelemetry for observability

---

**Last Updated:** April 21, 2026
