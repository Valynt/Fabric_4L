# Layer 4 Agent Runtime

Layer 4 uses LangGraph as the workflow runtime. This is an explicit runtime dependency, not an inferred architecture claim: `services/layer4-agents/pyproject.toml` declares `langgraph` and `langgraph-checkpoint-postgres`, and the canonical runtime imports live under `services/layer4-agents/src/layer4_agents/`.

## Runtime Initialization

The FastAPI entrypoint is `layer4_agents.api.main:app`. Startup delegates to `layer4_agents.api.startup.build_lifespan()`, which initializes the runtime in this order:

1. Configure settings, telemetry, database, Redis-backed state, feature flags, and rate limiting.
2. Create the default tool registry with `create_default_registry()`.
3. Create `StateManager` for workflow state and event publishing.
4. Create a LangGraph Postgres checkpointer with `CheckpointConfig.create_saver()`.
5. Construct `OrchestrationController(tool_registry, state_manager, checkpoint_saver=...)`.
6. Start the controller and call `recover_workflows()` before accepting traffic.

The checkpointer is mandatory during service startup. If `CheckpointConfig.create_saver()` cannot create an `AsyncPostgresSaver`, startup fails rather than running without workflow resume support.

## Workflow Execution Path

Workflow requests enter Layer 4 through the workflow API routes and resolve the singleton controller from startup state. `OrchestrationController.execute_workflow()` validates the workflow type against `WORKFLOW_TYPES`, creates a workflow instance with `create_workflow(workflow_type, tool_registry, checkpoint_saver)`, builds the initial tenant-scoped state, and schedules a `workflow_execution` task.

The scheduled task path calls `workflow.run(initial_state, thread_id=workflow_id)`. Resume paths re-create the same workflow type with the configured checkpoint saver and call `workflow.run(...)` with LangGraph resume data or checkpoint configuration.

## LangGraph Integration

All runtime workflow classes inherit from `BaseWorkflow` in `layer4_agents.workflows.base`.

- `BaseWorkflow._build_graph()` builds a LangGraph `StateGraph` from `WorkflowConfig` nodes, edges, routers, and entry point.
- `BaseWorkflow.compile()` compiles the `StateGraph` and injects `checkpointer`, `interrupt_before`, and `interrupt_after` when configured.
- `BaseWorkflow.run()` executes the compiled graph through `compiled.ainvoke(...)`.
- Native LangGraph interruptions (`GraphInterrupt`, `NodeInterrupt`, and `Command(resume=...)`) are handled as workflow interruption/resume semantics, not generic failures.

Registered workflow implementations include ROI calculation, whitespace analysis, and business case generation. The registry in `layer4_agents.workflows.__init__` keeps workflow construction pack-extensible through `register_workflow_type()` without hardcoding pack-specific behavior into the orchestration core.

## Checkpointing

Durable checkpointing is provided by LangGraph's Postgres saver:

- `CHECKPOINT_DATABASE_URL` is the canonical checkpoint database URL.
- `CheckpointConfig.create_saver()` creates `langgraph.checkpoint.postgres.aio.AsyncPostgresSaver`.
- The saver is passed into `OrchestrationController`, then into every workflow created through `create_workflow()`.
- `BaseWorkflow.compile()` passes the saver to LangGraph as `checkpointer`.

Tests that do not require Postgres use `langgraph.checkpoint.memory.InMemorySaver` to exercise real LangGraph graph execution and checkpoint isolation without external services.

## Observability

Agent runs carry stable identifiers through state, logs, metrics, and API responses:

- `workflow_id` identifies the workflow instance.
- `run_id` identifies a distinct execution attempt.
- `trace_id` links cross-layer audit and request traces.
- `tenant_id` scopes state, tools, checkpoints, and audit context.

`Layer4LifecycleLogger` emits structured lifecycle events with `Layer4EventContext`, including `request_id`, `trace_id`, `tenant_id`, `workflow_id`, `run_id`, `provider_name`, and optional `checkpoint_id`. The controller emits lifecycle stages such as workflow start, validation failure, completion, interruption, and failure. Tool execution also emits tool-call and tool-result events with the same context shape.

Prometheus workflow metrics live in `layer4_agents.metrics.prometheus_metrics`:

- `workflow_executions_total`
- `workflow_duration_seconds`
- `stuck_workflows_total`
- `repeated_workflow_failures_total`
- `checkpoint_corruption_detected_total`

Startup also schedules stuck-workflow detection through `detect_and_record_stuck_workflows()`. Checkpoint replay and conflict handling record checkpoint corruption through `record_checkpoint_corruption()` and `increment_checkpoint_corruption()`.

## Verification

Use the narrow agent runtime checks first:

```bash
pnpm test:agents
pytest tests/agents/
pytest tests/layer4/
```

`services/layer4-agents/tests/test_workflows_real_execution.py` verifies real LangGraph `StateGraph` execution with `InMemorySaver`, checkpoint persistence, thread isolation, and recursion limits. `services/layer4-agents/tests/unit/test_workflow_state_machine.py` verifies `BaseWorkflow` state-machine behavior.
