"""Regression tests: push_secrets_to_infisical maps to by-layer paths only.

These guard against a regression to the retired by-consumer Infisical path
taxonomy (/app, /auth, /database, /integrations, /llm, /storage). Every
variable in .env.example must resolve to a canonical by-layer path, and the
fallback constant must be /shared (never /app).
"""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "push_secrets_to_infisical.py"
SPEC = spec_from_file_location("push_secrets_to_infisical", MODULE_PATH)
assert SPEC and SPEC.loader
push = module_from_spec(SPEC)
SPEC.loader.exec_module(push)

LEGACY_ROOTS = ("/app", "/auth", "/database", "/integrations", "/llm", "/storage")


def _is_legacy_root(path: str) -> bool:
    return any(path == root or path.startswith(root + "/") for root in LEGACY_ROOTS)


def test_fallback_constant_is_shared_not_app() -> None:
    assert push.DEFAULT_FALLBACK_PATH == "/shared"


def test_real_env_example_maps_nothing_to_legacy_root() -> None:
    schema = push.load_schema_from_example(REPO_ROOT / ".env.example")
    assert schema, "expected .env.example to yield a non-empty schema"
    for var, path in schema.items():
        assert not _is_legacy_root(
            path
        ), f"{var} maps to legacy path {path!r}; must be by-layer"


def test_real_env_example_resolves_to_non_legacy_paths() -> None:
    schema = push.load_schema_from_example(REPO_ROOT / ".env.example")
    # Every resolved path must be a leading-slash path whose first segment is
    # NOT one of the retired by-consumer roots.
    for var, path in schema.items():
        assert path.startswith("/"), f"{var} maps to {path!r}; must start with /"
        assert not _is_legacy_root(path), f"{var} maps to legacy root {path!r}"


def test_explicit_annotation_overrides_section_header() -> None:
    # AUTH_PROVIDER sits under a `# Infisical path: /shared/auth` annotation,
    # which must win over any enclosing section header and resolve to a
    # /shared sub-path (not the legacy /auth root).
    schema = push.load_schema_from_example(REPO_ROOT / ".env.example")
    assert "AUTH_PROVIDER" in schema, "expected AUTH_PROVIDER in .env.example"
    assert schema["AUTH_PROVIDER"] == "/shared/auth"
    # /shared/auth is canonical: first segment is /shared, not /auth.
    assert not _is_legacy_root(schema["AUTH_PROVIDER"])


def test_vite_var_maps_to_apps_web() -> None:
    schema = push.load_schema_from_example(REPO_ROOT / ".env.example")
    assert "VITE_AUTH_PROVIDER" in schema, "expected VITE_AUTH_PROVIDER in .env.example"
    assert schema["VITE_AUTH_PROVIDER"] == "/apps/web"


def test_classify_secrets_never_yields_legacy_root() -> None:
    schema = push.load_schema_from_example(REPO_ROOT / ".env.example")
    # Synthesize non-placeholder values for every schema variable so they
    # survive the placeholder/empty filters and we exercise the real path
    # assignment.
    env_vars = dict.fromkeys(schema, "nonempty-value")
    to_push, _skipped_placeholder, _skipped_empty = push.classify_secrets(
        env_vars=env_vars,
        schema=schema,
        include_empty=False,
        path_override=None,
    )
    assert to_push, "expected at least one pushable secret"
    for secret in to_push:
        assert not _is_legacy_root(
            secret.path
        ), f"{secret.name} assigned legacy path {secret.path!r}"


def test_classify_secrets_fallback_is_shared() -> None:
    # A variable absent from the schema must fall back to /shared, not /app.
    schema = push.load_schema_from_example(REPO_ROOT / ".env.example")
    env_vars = {"UNKNOWN_NEW_VAR": "some-value"}
    to_push, _p, _e = push.classify_secrets(
        env_vars=env_vars,
        schema=schema,
        include_empty=False,
        path_override=None,
    )
    assert len(to_push) == 1
    assert to_push[0].path == "/shared"
