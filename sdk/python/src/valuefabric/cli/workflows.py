"""Workflow CLI commands."""

from __future__ import annotations

import json
from typing import Any

import typer

from ._utils import get_client, print_object, print_table

app = typer.Typer(help="Workflow management")


@app.command("list")
def list_workflows(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    active: bool = typer.Option(False, "--active", help="List active workflows"),
) -> None:
    """List workflow types or active workflows."""
    client = get_client()
    if active:
        workflows = client.list_active_workflows()
        rows = [w.model_dump(mode="json") for w in workflows]
        cols = ["workflow_instance_id", "workflow_type", "status", "progress_percentage"]
    else:
        workflows = client.list_workflows()
        rows = [w.model_dump(mode="json") for w in workflows]
        cols = ["type", "name", "description"]
    print_table(rows, columns=cols, json_output=json_output)


@app.command("execute")
def execute_workflow(
    workflow_type: str,
    tenant_id: str = typer.Option(..., "--tenant-id", help="Tenant ID"),
    user_id: str = typer.Option(..., "--user-id", help="User ID"),
    inputs: str | None = typer.Option(None, "--inputs", help="JSON inputs string"),
    priority: str = typer.Option("NORMAL", "--priority", "-p", help="Execution priority"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Execute a workflow."""
    parsed_inputs: dict[str, Any] = {}
    if inputs:
        parsed_inputs = json.loads(inputs)
    client = get_client()
    result = client.execute_workflow(
        workflow_type=workflow_type,
        tenant_id=tenant_id,
        user_id=user_id,
        inputs=parsed_inputs,
        priority=priority,
    )
    print_object(result, json_output=json_output)


@app.command("get")
def get_workflow(
    workflow_id: str,
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Get workflow status."""
    client = get_client()
    wf = client.get_workflow(workflow_id)
    print_object(wf.model_dump(mode="json"), json_output=json_output)
