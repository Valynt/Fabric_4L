"""API key CLI commands."""

from __future__ import annotations

import typer

from ._utils import get_client, print_object, print_table

app = typer.Typer(help="API key management")


@app.command("list")
def list_api_keys(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    enabled_only: bool = typer.Option(True, "--enabled-only/--all", help="Filter enabled keys"),
) -> None:
    """List API keys for the current tenant."""
    client = get_client()
    keys = client.list_api_keys(enabled_only=enabled_only)
    rows = [k.model_dump(mode="json") for k in keys]
    print_table(
        rows,
        columns=["key_id", "name", "role", "enabled", "created_at"],
        json_output=json_output,
    )


@app.command("create")
def create_api_key(
    name: str,
    role: str = typer.Option("analyst", "--role", "-r", help="Role for the key"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Create a new API key."""
    client = get_client()
    result = client.create_api_key(name, role)
    data = result.model_dump(mode="json")
    print_object(data, json_output=json_output)
