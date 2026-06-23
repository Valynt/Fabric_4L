"""Click entrypoint for the ``valuepact`` CLI."""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any
from uuid import uuid4

import click

from valuefabric.__version__ import __version__
from valuefabric.errors import AuthenticationError, ConfigurationError

from .client import ValuePactApiClient
from .config import (
    active_profile_name,
    clear_active_profile,
    get_profile,
    load_config,
    save_config,
    upsert_profile,
)
from .context import ExecutionContext, bind_execution_context
from .errors import EXIT_INVALID, CliError, map_exception
from .output import emit_human_mapping, emit_json, error_envelope, success_envelope

READ_SCOPE = "valuepact:read"
EXECUTE_SCOPE = "valuepact:workspace:execute"
AUDIT_SCOPE = "valuepact:audit:read"


def _json_default(value: Any) -> str:
    return str(value)


def _as_payload(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except TypeError:
        return json.loads(json.dumps(value, default=_json_default))


class GlobalOptions(dict[str, Any]):
    """Global command options attached to Click context."""


def _merge_command_option(ctx: click.Context, param: click.Parameter, value: Any) -> None:
    if value in (None, False):
        return
    root = ctx.find_root()
    if root.obj is None:
        root.obj = GlobalOptions()
    root.obj[param.name] = value


def output_cli_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Allow output-control root options to be supplied after a command name."""

    options = [
        click.option("--verbose", is_flag=True, expose_value=False, callback=_merge_command_option),
        click.option(
            "--no-color",
            "no_color",
            is_flag=True,
            expose_value=False,
            callback=_merge_command_option,
        ),
        click.option("--quiet", is_flag=True, expose_value=False, callback=_merge_command_option),
        click.option(
            "--json",
            "json_output",
            is_flag=True,
            expose_value=False,
            callback=_merge_command_option,
        ),
    ]
    for option in options:
        func = option(func)
    return func


def common_cli_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Allow root context/output options to be supplied after a command name."""

    options = [
        click.option("--tenant-id", expose_value=False, callback=_merge_command_option),
        click.option("--environment", expose_value=False, callback=_merge_command_option),
        click.option("--profile", expose_value=False, callback=_merge_command_option),
    ]
    func = output_cli_options(func)
    for option in options:
        func = option(func)
    return func


@click.group(name="valuepact", context_settings={"help_option_names": ["-h", "--help"]})
@click.option("--json", "json_output", is_flag=True, help="Emit stable JSON envelopes.")
@click.option("--quiet", is_flag=True, help="Suppress non-essential human output.")
@click.option("--no-color", is_flag=True, help="Reserved for color-aware output.")
@click.option("--verbose", is_flag=True, help="Enable verbose diagnostics without secrets.")
@click.option("--profile", help="Named non-secret context profile.")
@click.option("--environment", help="Target environment.")
@click.option("--tenant-id", help="Target tenant ID.")
@click.pass_context
def cli(
    ctx: click.Context,
    *,
    json_output: bool,
    quiet: bool,
    no_color: bool,
    verbose: bool,
    profile: str | None,
    environment: str | None,
    tenant_id: str | None,
) -> None:
    """Operate ValuePact workflows from a tenant-safe terminal adapter."""

    ctx.obj = GlobalOptions(
        json_output=json_output,
        quiet=quiet,
        no_color=no_color,
        verbose=verbose,
        profile=profile,
        environment=environment,
        tenant_id=tenant_id,
    )


def main() -> None:
    cli()


def _global(ctx: click.Context, key: str) -> Any:
    obj = ctx.find_root().obj or {}
    return obj.get(key)


def _request_id() -> str:
    return f"req_{uuid4().hex}"


def _resolve_profile(ctx: click.Context) -> tuple[str, dict[str, Any]]:
    name = active_profile_name(_global(ctx, "profile"))
    return name, get_profile(name)


def _resolve_value(ctx: click.Context, key: str, env_name: str, profile: dict[str, Any]) -> str | None:
    explicit = _global(ctx, key)
    if explicit:
        return str(explicit)
    env_value = os.environ.get(env_name)
    if env_value:
        return env_value
    value = profile.get(key)
    return str(value) if value else None


def _resolve_api_url(ctx: click.Context, profile: dict[str, Any]) -> str:
    api_url = os.environ.get("VALUEPACT_API_URL") or profile.get("api_url")
    if not api_url:
        raise ConfigurationError("Missing API URL. Set VALUEPACT_API_URL or run context use.")
    return str(api_url)


def _load_token() -> str:
    token = os.environ.get("VALUEPACT_SERVICE_TOKEN")
    if not token:
        raise AuthenticationError("Missing VALUEPACT_SERVICE_TOKEN.")
    return token


def _client(ctx: click.Context, *, request_id: str) -> ValuePactApiClient:
    _, profile = _resolve_profile(ctx)
    return ValuePactApiClient(
        api_url=_resolve_api_url(ctx, profile),
        token=_load_token(),
        request_id=request_id,
        command_name=ctx.command_path,
        cli_version=__version__,
    )


def _emit_error(ctx: click.Context, error: CliError, *, request_id: str | None = None) -> None:
    if _global(ctx, "json_output"):
        emit_json(error_envelope(error, request_id=request_id), err=True)
    else:
        click.echo(f"{error.code}: {error.message}", err=True)


def _handle_failure(ctx: click.Context, exc: BaseException, *, request_id: str | None = None) -> None:
    error = map_exception(exc)
    _emit_error(ctx, error, request_id=request_id)
    raise click.exceptions.Exit(error.exit_code)


def _protected_context(
    ctx: click.Context,
    *,
    required_scopes: set[str],
    workspace_id: str | None = None,
) -> tuple[ExecutionContext, ValuePactApiClient]:
    profile_name, profile = _resolve_profile(ctx)
    tenant_id = _resolve_value(ctx, "tenant_id", "VALUEPACT_TENANT_ID", profile)
    environment = _resolve_value(ctx, "environment", "VALUEPACT_ENVIRONMENT", profile)
    if not tenant_id:
        raise CliError("TENANT_CONTEXT_MISSING", "Missing tenant context.", EXIT_INVALID)
    if not environment:
        raise CliError("INVALID_ARGUMENT", "Missing environment.", EXIT_INVALID)

    request_id = _request_id()
    api_client = _client(ctx, request_id=request_id)
    identity = api_client.identity()
    verification = api_client.verify_tenant_access(tenant_id, scopes=required_scopes)
    if verification.get("authorized") is not True:
        raise PermissionError("The current identity is not authorized for this tenant.")
    granted_scopes = set(identity.get("scopes") or []) | set(verification.get("scopes") or [])
    actor_id = identity.get("actor_id") or identity.get("id")
    if not actor_id:
        raise AuthenticationError("Authenticated identity did not include an actor ID.")
    actor_type = identity.get("actor_type", "service_account")
    if actor_type not in {"user", "service_account", "system"}:
        actor_type = "service_account"

    return (
        ExecutionContext(
            environment=environment,
            tenant_id=tenant_id,
            actor_id=str(actor_id),
            actor_type=actor_type,
            scopes=frozenset(str(scope) for scope in granted_scopes),
            request_id=request_id,
            workspace_id=workspace_id,
            profile_name=profile_name,
        ),
        api_client,
    )


def protected_command(required_scopes: set[str]) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            ctx = click.get_current_context()
            request_id: str | None = None
            client: ValuePactApiClient | None = None
            try:
                workspace_id = kwargs.get("workspace_id")
                execution_context, client = _protected_context(
                    ctx,
                    required_scopes=required_scopes,
                    workspace_id=str(workspace_id) if workspace_id else None,
                )
                request_id = execution_context.request_id
                with bind_execution_context(execution_context):
                    data = func(*args, api_client=client, execution_context=execution_context, **kwargs)
                if _global(ctx, "json_output"):
                    emit_json(success_envelope(_as_payload(data), context=execution_context))
                elif not _global(ctx, "quiet") and data is not None:
                    _emit_human(data, execution_context)
            except KeyboardInterrupt as exc:
                _handle_failure(ctx, exc, request_id=request_id)
            except Exception as exc:
                _handle_failure(ctx, exc, request_id=request_id)
            finally:
                if client is not None:
                    client.close()

        return wrapper

    return decorator


def _emit_human(data: Any, context: ExecutionContext) -> None:
    normalized = dict(data) if isinstance(data, dict) else {"result": data}
    leading = {
        "tenant": normalized.pop("tenant", normalized.pop("tenant_id", context.tenant_id)),
        "environment": context.environment,
        "request_id": context.request_id,
    }
    for key in ("workspace_id", "execution_id", "status"):
        if key in normalized:
            leading[key] = normalized.pop(key)
    emit_human_mapping(leading)
    if normalized:
        click.echo(json.dumps(_as_payload(normalized), sort_keys=True))


@cli.command("version")
@common_cli_options
@click.pass_context
def version(ctx: click.Context) -> None:
    """Show the ValuePact CLI version."""

    payload = {"version": __version__, "binary": "valuepact"}
    if _global(ctx, "json_output"):
        emit_json(success_envelope(payload))
    else:
        click.echo(f"valuepact {__version__}")


@cli.command("doctor")
@common_cli_options
@click.pass_context
def doctor(ctx: click.Context) -> None:
    """Run local configuration and API diagnostics."""

    request_id = _request_id()
    try:
        profile_name, profile = _resolve_profile(ctx)
        api_url = _resolve_api_url(ctx, profile)
        token_present = bool(os.environ.get("VALUEPACT_SERVICE_TOKEN"))
        data: dict[str, Any] = {
            "profile": profile_name,
            "api_url": api_url,
            "service_token_present": token_present,
        }
        if token_present:
            client = _client(ctx, request_id=request_id)
            try:
                data["health"] = client.health()
            finally:
                client.close()
        if _global(ctx, "json_output"):
            emit_json(success_envelope(data))
        elif not _global(ctx, "quiet"):
            emit_human_mapping(data)
    except Exception as exc:
        _handle_failure(ctx, exc, request_id=request_id)


@cli.command("completion")
def completion() -> None:
    """Print shell-completion setup guidance."""

    click.echo("Use Click shell completion, for example: _VALUEPACT_COMPLETE=bash_source valuepact")


@cli.group("auth")
def auth_group() -> None:
    """Authentication commands."""


@auth_group.command("login")
@click.option("--api-url", help="ValuePact API URL to store in the active profile.")
@click.option("--profile", "profile_name", default="default", show_default=True)
@output_cli_options
@click.pass_context
def auth_login(ctx: click.Context, *, api_url: str | None, profile_name: str) -> None:
    """Verify VALUEPACT_SERVICE_TOKEN and store non-secret profile metadata."""

    request_id = _request_id()
    try:
        if api_url:
            upsert_profile(profile_name, {"api_url": api_url}, make_active=True)
        profile = get_profile(profile_name)
        client = ValuePactApiClient(
            api_url=_resolve_api_url(ctx, profile),
            token=_load_token(),
            request_id=request_id,
            command_name=ctx.command_path,
            cli_version=__version__,
        )
        try:
            identity = client.identity()
        finally:
            client.close()
        upsert_profile(
            profile_name,
            {
                "api_url": api_url or profile.get("api_url"),
                "actor_id": identity.get("actor_id") or identity.get("id"),
                "actor_type": identity.get("actor_type", "service_account"),
            },
            make_active=True,
        )
        data = {"profile": profile_name, "actor_id": identity.get("actor_id") or identity.get("id")}
        if _global(ctx, "json_output"):
            emit_json(success_envelope(data))
        else:
            emit_human_mapping(data)
    except Exception as exc:
        _handle_failure(ctx, exc, request_id=request_id)


@auth_group.command("status")
@common_cli_options
@click.pass_context
def auth_status(ctx: click.Context) -> None:
    """Show authentication status without printing credentials."""

    try:
        profile_name, profile = _resolve_profile(ctx)
        data = {
            "profile": profile_name,
            "api_url": profile.get("api_url") or os.environ.get("VALUEPACT_API_URL"),
            "service_token_present": bool(os.environ.get("VALUEPACT_SERVICE_TOKEN")),
            "actor_id": profile.get("actor_id"),
            "actor_type": profile.get("actor_type"),
        }
        if _global(ctx, "json_output"):
            emit_json(success_envelope(data))
        else:
            emit_human_mapping(data)
    except Exception as exc:
        _handle_failure(ctx, exc)


@auth_group.command("logout")
@click.option("--profile", "profile_name", default="default", show_default=True)
@output_cli_options
@click.pass_context
def auth_logout(ctx: click.Context, *, profile_name: str) -> None:
    """Remove stored non-secret identity metadata for a profile."""

    try:
        config = load_config()
        profiles = config.get("profiles", {})
        if isinstance(profiles, dict) and profile_name in profiles:
            profile = profiles[profile_name]
            if isinstance(profile, dict):
                for key in ("actor_id", "actor_type", "scopes"):
                    profile.pop(key, None)
        save_config(config)
        data = {"profile": profile_name, "status": "logged_out"}
        if _global(ctx, "json_output"):
            emit_json(success_envelope(data))
        else:
            emit_human_mapping(data)
    except Exception as exc:
        _handle_failure(ctx, exc)


@cli.group("context")
def context_group() -> None:
    """Named tenant/environment context profiles."""


@context_group.command("use")
@click.option("--tenant-id", required=True)
@click.option("--environment", required=True)
@click.option("--api-url")
@click.option("--profile", "profile_name", default="default", show_default=True)
@output_cli_options
@click.pass_context
def context_use(
    ctx: click.Context,
    *,
    tenant_id: str,
    environment: str,
    api_url: str | None,
    profile_name: str,
) -> None:
    """Store non-secret tenant and environment preferences."""

    try:
        upsert_profile(
            profile_name,
            {"tenant_id": tenant_id, "environment": environment, "api_url": api_url},
            make_active=True,
        )
        data = {"profile": profile_name, "tenant_id": tenant_id, "environment": environment}
        if _global(ctx, "json_output"):
            emit_json(success_envelope(data))
        else:
            emit_human_mapping(data)
    except Exception as exc:
        _handle_failure(ctx, exc)


@context_group.command("show")
@common_cli_options
@click.pass_context
def context_show(ctx: click.Context) -> None:
    """Show the resolved non-secret context."""

    try:
        profile_name, profile = _resolve_profile(ctx)
        data = {
            "profile": profile_name,
            "tenant_id": _resolve_value(ctx, "tenant_id", "VALUEPACT_TENANT_ID", profile),
            "environment": _resolve_value(ctx, "environment", "VALUEPACT_ENVIRONMENT", profile),
            "api_url": _resolve_api_url(ctx, profile) if (profile.get("api_url") or os.environ.get("VALUEPACT_API_URL")) else None,
        }
        if _global(ctx, "json_output"):
            emit_json(success_envelope(data))
        else:
            emit_human_mapping(data)
    except Exception as exc:
        _handle_failure(ctx, exc)


@context_group.command("list")
@common_cli_options
@click.pass_context
def context_list(ctx: click.Context) -> None:
    """List stored non-secret profiles."""

    config = load_config()
    data = {
        "active_profile": config.get("active_profile"),
        "profiles": sorted((config.get("profiles") or {}).keys()),
    }
    if _global(ctx, "json_output"):
        emit_json(success_envelope(data))
    else:
        emit_human_mapping(data)


@context_group.command("clear")
@common_cli_options
@click.pass_context
def context_clear(ctx: click.Context) -> None:
    """Clear the active profile marker."""

    clear_active_profile()
    data = {"status": "cleared"}
    if _global(ctx, "json_output"):
        emit_json(success_envelope(data))
    else:
        emit_human_mapping(data)


@cli.group("tenant")
def tenant_group() -> None:
    """Tenant commands."""


@tenant_group.command("list")
@common_cli_options
@protected_command({READ_SCOPE})
def tenant_list(*, api_client: ValuePactApiClient, execution_context: ExecutionContext) -> Any:
    return api_client.list_tenants()


@tenant_group.command("show")
@click.argument("tenant_id")
@common_cli_options
@protected_command({READ_SCOPE})
def tenant_show(
    tenant_id: str,
    *,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    if tenant_id != execution_context.tenant_id:
        raise CliError("TENANT_CONTEXT_MISMATCH", "Requested tenant does not match active context.", EXIT_INVALID)
    return api_client.get_tenant(tenant_id)


@cli.group("workspace")
def workspace_group() -> None:
    """Workspace commands."""


@workspace_group.command("list")
@common_cli_options
@protected_command({READ_SCOPE})
def workspace_list(*, api_client: ValuePactApiClient, execution_context: ExecutionContext) -> Any:
    return api_client.list_workspaces(execution_context.tenant_id)


@workspace_group.command("show")
@click.argument("workspace_id")
@common_cli_options
@protected_command({READ_SCOPE})
def workspace_show(
    workspace_id: str,
    *,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    return api_client.get_workspace(execution_context.tenant_id, workspace_id)


@workspace_group.command("execute")
@click.option("--workspace-id", required=True)
@click.option("--input", "input_file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--yes", is_flag=True, help="Confirm execution for automation.")
@click.option("--dry-run", is_flag=True, help="Preview execution without mutating where supported.")
@common_cli_options
@protected_command({EXECUTE_SCOPE})
def workspace_execute(
    *,
    workspace_id: str,
    input_file: Path | None,
    yes: bool,
    dry_run: bool,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    if not yes and not dry_run:
        if _global(click.get_current_context(), "json_output"):
            raise CliError("INVALID_ARGUMENT", "Mutating JSON command requires --yes or --dry-run.", EXIT_INVALID)
        emit_human_mapping(
            {
                "tenant_id": execution_context.tenant_id,
                "environment": execution_context.environment,
                "workspace_id": workspace_id,
                "action": "execute workspace",
            },
            err=True,
        )
        if not click.confirm("Continue?"):
            raise CliError("INVALID_ARGUMENT", "Operation was not confirmed.", EXIT_INVALID)
    payload: dict[str, Any] = {}
    if input_file is not None:
        payload = json.loads(input_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Workspace input file must contain a JSON object.")
    return api_client.execute_workspace(
        tenant_id=execution_context.tenant_id,
        workspace_id=workspace_id,
        request_id=execution_context.request_id,
        actor_id=execution_context.actor_id,
        input_payload=payload,
        dry_run=dry_run,
    )


@cli.group("execution")
def execution_group() -> None:
    """Execution commands."""


@execution_group.command("list")
@common_cli_options
@protected_command({READ_SCOPE})
def execution_list(*, api_client: ValuePactApiClient, execution_context: ExecutionContext) -> Any:
    return api_client.list_executions(execution_context.tenant_id)


@execution_group.command("status")
@click.argument("execution_id")
@click.option("--watch", is_flag=True, help="Reserved for streaming status polling.")
@common_cli_options
@protected_command({READ_SCOPE})
def execution_status(
    execution_id: str,
    *,
    watch: bool,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    data = api_client.get_execution(execution_context.tenant_id, execution_id)
    if isinstance(data, dict) and watch:
        data["watch"] = True
    return data


@execution_group.command("logs")
@click.argument("execution_id")
@common_cli_options
@protected_command({READ_SCOPE})
def execution_logs(
    execution_id: str,
    *,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    return api_client.execution_logs(execution_context.tenant_id, execution_id)


@execution_group.command("cancel")
@click.argument("execution_id")
@click.option("--yes", is_flag=True, help="Confirm cancellation for automation.")
@click.option("--dry-run", is_flag=True, help="Preview cancellation without mutating.")
@common_cli_options
@protected_command({EXECUTE_SCOPE})
def execution_cancel(
    execution_id: str,
    *,
    yes: bool,
    dry_run: bool,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    if dry_run:
        return {"execution_id": execution_id, "status": "dry_run", "tenant_id": execution_context.tenant_id}
    if not yes:
        if _global(click.get_current_context(), "json_output"):
            raise CliError("INVALID_ARGUMENT", "Mutating JSON command requires --yes or --dry-run.", EXIT_INVALID)
        emit_human_mapping(
            {
                "tenant_id": execution_context.tenant_id,
                "environment": execution_context.environment,
                "execution_id": execution_id,
                "action": "cancel execution",
            },
            err=True,
        )
        if not click.confirm("Continue?"):
            raise CliError("INVALID_ARGUMENT", "Operation was not confirmed.", EXIT_INVALID)
    return api_client.cancel_execution(
        execution_context.tenant_id,
        execution_id,
        execution_context.request_id,
    )


@cli.group("audit")
def audit_group() -> None:
    """Audit commands."""


@audit_group.command("list")
@click.option("--since")
@common_cli_options
@protected_command({AUDIT_SCOPE})
def audit_list(
    *,
    since: str | None,
    api_client: ValuePactApiClient,
    execution_context: ExecutionContext,
) -> Any:
    return api_client.list_audit_events(execution_context.tenant_id, since)


if __name__ == "__main__":
    main()
