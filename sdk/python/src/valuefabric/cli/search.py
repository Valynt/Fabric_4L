"""Search CLI commands for hybrid entity search."""

from __future__ import annotations

from typing import Optional

import typer
from rich import print as rich_print
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from ..generated.l3 import EntityType, SearchRequest, SearchType
from ..generated.l3_client import L3Client
from .config import get_profile_config


def _get_l3_client() -> L3Client:
    """Create L3 client from profile config."""
    config = get_profile_config()
    base_url = config.get("base_url", "http://localhost:8001")
    api_key = config.get("api_key")
    jwt_token = config.get("jwt_token")
    return L3Client(base_url=base_url, api_key=api_key, jwt_token=jwt_token)


def _execute_search(
    query: str,
    entity_type: Optional[str],
    top_k: int,
    search_type: str,
    json_output: bool,
) -> None:
    """Execute the search and display results."""
    client = _get_l3_client()

    # Build request
    try:
        search_type_enum = SearchType(search_type.lower())
    except ValueError:
        rich_print(f"[red]Invalid search type: {search_type}[/red]")
        rich_print("[yellow]Valid types: hybrid, vector, bm25, graph[/yellow]")
        raise typer.Exit(1)

    request_kwargs: dict = {
        "query": query,
        "top_k": top_k,
        "search_type": search_type_enum,
    }

    if entity_type:
        try:
            request_kwargs["entity_type"] = EntityType(entity_type)
        except ValueError:
            rich_print(f"[red]Invalid entity type: {entity_type}[/red]")
            rich_print("[yellow]Valid types: " + ", ".join(e.value for e in EntityType) + "[/yellow]")
            raise typer.Exit(1)

    request = SearchRequest(**request_kwargs)

    # Execute search with progress indicator
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description=f"Searching for '{query}'...", total=None)
        try:
            response = client.search(request)
        except Exception as e:
            rich_print(f"[red]Search failed: {e}[/red]")
            raise typer.Exit(1)

    # Output results
    if json_output:
        import json
        print(json.dumps(response.model_dump(mode="json"), indent=2))
        return

    if not response.results:
        rich_print(f"[yellow]No results found for '{query}'[/yellow]")
        return

    # Build table
    table = Table(title=f"Search Results for '{query}' ({response.total_results} total)")
    table.add_column("Entity ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Type", style="magenta")
    table.add_column("Score", justify="right", style="yellow")
    table.add_column("Confidence", justify="right", style="blue")

    for result in response.results:
        table.add_row(
            result.entity_id[:20] + "..." if len(result.entity_id) > 20 else result.entity_id,
            result.name[:50] + "..." if len(result.name) > 50 else result.name,
            result.entity_type.value if result.entity_type else "N/A",
            f"{result.combined_score:.3f}",
            f"{result.confidence:.3f}",
        )

    rich_print(table)
    rich_print(f"[dim]Search type: {response.search_type.value} | "
               f"Processing time: {response.processing_time_ms}ms[/dim]")


def search_command(
    query: str = typer.Argument(..., help="Search query string"),
    entity_type: Optional[str] = typer.Option(
        None, "--type", "-t", help="Filter by entity type (e.g., Capability, UseCase)"
    ),
    top_k: int = typer.Option(10, "--limit", "-l", help="Number of results to return", min=1, max=100),
    search_type: str = typer.Option(
        "hybrid", "--search-type", help="Search algorithm (hybrid, vector, bm25, graph)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Execute hybrid search combining BM25, vector, and graph signals."""
    _execute_search(query, entity_type, top_k, search_type, json_output)
