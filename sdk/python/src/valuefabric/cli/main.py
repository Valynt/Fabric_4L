"""Entrypoint for the ``vf`` CLI."""

from __future__ import annotations

import sys

import typer
from rich import print as rich_print

from ..__version__ import __version__
from ..errors import ConfigurationError
from .api_keys import app as api_keys_app
from .auth import app as auth_app
from .config import app as config_app
from .flags import app as flags_app
from .health import health as health_command
from .models import app as models_app
from .search import search_command
from .tenants import app as tenants_app
from .users import app as users_app
from .workflows import app as workflows_app


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        rich_print(f"[bold]vf[/bold] version [green]{__version__}[/green]")
        raise typer.Exit()


app = typer.Typer(
    name="vf",
    help="Value Fabric SDK CLI",
    epilog="Use 'vf auth login' to authenticate and get started.",
)


@app.callback()
def main_callback(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Value Fabric SDK CLI - Manage workflows, models, and feature flags."""
    pass

app.add_typer(auth_app, name="auth", help="Authentication management")
app.add_typer(config_app, name="config", help="Manage CLI configuration")
app.add_typer(tenants_app, name="tenants", help="Tenant management")
app.add_typer(users_app, name="users", help="User management")
app.add_typer(api_keys_app, name="api-keys", help="API key management")
app.add_typer(workflows_app, name="workflows", help="Workflow management")
app.add_typer(models_app, name="models", help="Model registry")
app.add_typer(flags_app, name="feature-flags", help="Feature flags")
app.command("health")(health_command)
app.command("search", help="Hybrid entity search (BM25 + vector + graph)")(search_command)


def main() -> None:
    try:
        app()
    except ConfigurationError as e:
        rich_print(f"[red]Configuration error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
