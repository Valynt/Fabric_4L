"""Shared CLI utilities."""

from __future__ import annotations

import json
from typing import Any

from rich.console import Console
from rich.table import Table

from ..client import ValueFabricClient
from ..errors import ConfigurationError
from .config import get_profile_config

console = Console()


def get_client() -> ValueFabricClient:
    """Build a ``ValueFabricClient`` from the active CLI profile."""
    cfg = get_profile_config()
    base_url = cfg.get("base_url")
    api_key = cfg.get("api_key")
    if not base_url:
        raise ConfigurationError(
            "No base_url configured. Run: vf config set-url <url>"
        )
    if not api_key:
        raise ConfigurationError(
            "No API key configured. Run: vf auth login or vf config set-api-key"
        )
    return ValueFabricClient(base_url=base_url, api_key=api_key)


def print_json(data: Any) -> None:
    """Print data as formatted JSON."""
    console.print(json.dumps(data, indent=2, default=str))


def print_table(
    rows: list[dict[str, Any]],
    *,
    columns: list[str],
    headers: dict[str, str] | None = None,
    json_output: bool = False,
) -> None:
    """Print rows as a Rich table or JSON."""
    if json_output:
        print_json(rows)
        return

    if not rows:
        console.print("[italic]No results.[/italic]")
        return

    table = Table(show_header=True, header_style="bold magenta")
    hdr = headers or {}
    for col in columns:
        table.add_column(hdr.get(col, col))

    for row in rows:
        table.add_row(*[str(row.get(col, "")) for col in columns])

    console.print(table)


def print_object(data: dict[str, Any], *, json_output: bool = False) -> None:
    """Print a single object as a key/value table or JSON."""
    if json_output:
        print_json(data)
        return

    table = Table(show_header=False)
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    for key, value in data.items():
        table.add_row(str(key), str(value))
    console.print(table)
