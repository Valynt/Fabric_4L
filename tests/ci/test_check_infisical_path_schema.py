from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MODULE_PATH = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "ci"
    / "check_infisical_path_schema.py"
)
SPEC = spec_from_file_location("check_infisical_path_schema", MODULE_PATH)
assert SPEC and SPEC.loader
guard = module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def test_flags_legacy_infisical_cli_path() -> None:
    assert guard.is_legacy_infisical_ref(
        "infisical secrets get --path=/llm OPENAI_API_KEY"
    )
    assert guard.is_legacy_infisical_ref("infisical run --path=/app -- npm run dev")
    assert guard.is_legacy_infisical_ref(
        'infisical secrets set --path=//storage S3_KEY="x"'
    )


def test_flags_legacy_infisical_crud_path() -> None:
    assert guard.is_legacy_infisical_ref("secretPath: /auth")
    assert guard.is_legacy_infisical_ref('"secretPath": "/database"')
    assert guard.is_legacy_infisical_ref('"secretsPath": "/integrations"')


def test_flags_legacy_env_example_annotation() -> None:
    assert guard.is_legacy_infisical_ref("# Infisical path: /llm")
    assert guard.is_legacy_infisical_ref("# Infisical path: /app  (runtime config)")


def test_flags_legacy_gitbash_fix_call() -> None:
    assert guard.is_legacy_infisical_ref("f\"--path={fix_path_for_git_bash('/llm')}\"")


def test_accepts_canonical_by_layer_paths() -> None:
    canonical = [
        "infisical secrets get --path=/layer4-agents OPENAI_API_KEY",
        "infisical run --path=/shared -- pnpm dev:web",
        "--path=/infra",
        "--path=/apps/web",
        "--path=/layer1-ingestion",
        "# Infisical path: /shared/auth  (backend gateway auth config)",
        "f\"--path={fix_path_for_git_bash('/layer4-agents')}\"",
        '"secretPath": "/shared"',
        '"secretsPath": "/layer3-knowledge"',
    ]
    for line in canonical:
        assert not guard.is_legacy_infisical_ref(
            line
        ), f"unexpectedly flagged canonical: {line}"


def test_ignores_unrelated_path_uses() -> None:
    # ASGI/HTTP scope "path" values are not Infisical paths.
    unrelated = [
        'return Request(scope={"type": "http", "method": "GET", "path": "/v1/auth/clerk/tenant"})',
        '"path": "/auth/authorization-snapshot"',
        '"path": "services/api/app/main.py"',
        "PYTHONPATH: /app",
        "https://app.example.com/auth/login",
        "/var/log/value-fabric/app.log",
    ]
    for line in unrelated:
        assert not guard.is_legacy_infisical_ref(
            line
        ), f"unexpectedly flagged unrelated: {line}"


def test_should_scan_skips_archives_and_cache(tmp_path: Path) -> None:
    repo = tmp_path
    archive = repo / "docs" / "archive" / "legacy.md"
    archive.parent.mkdir(parents=True, exist_ok=True)
    cache = repo / "scripts" / "ci" / "__pycache__" / "guard.pyc"
    cache.parent.mkdir(parents=True, exist_ok=True)
    active = repo / "scripts" / "run.sh"
    active.parent.mkdir(parents=True, exist_ok=True)

    assert not guard.should_scan(archive, repo)
    assert not guard.should_scan(cache, repo)
    assert guard.should_scan(active, repo)


def test_main_passes_on_clean_repo(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "ok.sh").write_text(
        "infisical run --path=/layer4-agents -- pnpm dev:layer4\n", encoding="utf-8"
    )
    # Invoke main with the clean repo root.
    import sys

    orig_argv = sys.argv
    sys.argv = ["check_infisical_path_schema.py", "--repo-root", str(repo)]
    try:
        rc = guard.main()
    finally:
        sys.argv = orig_argv
    assert rc == 0


def test_main_fails_on_legacy_violation(tmp_path: Path) -> None:
    repo = tmp_path
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "bad.sh").write_text(
        "infisical secrets get --path=/llm OPENAI_API_KEY\n", encoding="utf-8"
    )
    import contextlib
    import io
    import sys

    orig_argv = sys.argv
    sys.argv = ["check_infisical_path_schema.py", "--repo-root", str(repo)]
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = guard.main()
    finally:
        sys.argv = orig_argv
    assert rc == 1
    assert "llm" in buf.getvalue()


def test_main_fails_on_legacy_infisical_json(tmp_path: Path) -> None:
    """Root .infisical.json with a legacy secretPath must be caught (regression
    for an earlier inverted scan condition that let it pass)."""
    repo = tmp_path
    (repo / ".infisical.json").write_text(
        '{"secretPaths":{"llm":{"dev":"/llm"}}}', encoding="utf-8"
    )
    import sys

    orig_argv = sys.argv
    sys.argv = ["check_infisical_path_schema.py", "--repo-root", str(repo)]
    try:
        rc = guard.main()
    finally:
        sys.argv = orig_argv
    assert rc == 1


def test_main_fails_on_legacy_env_example_annotation(tmp_path: Path) -> None:
    """Root .env.example is the mapping source of truth and must be scanned."""
    repo = tmp_path
    (repo / ".env.example").write_text(
        "# Infisical path: /llm\nOPENAI_API_KEY=\n", encoding="utf-8"
    )
    import sys

    orig_argv = sys.argv
    sys.argv = ["check_infisical_path_schema.py", "--repo-root", str(repo)]
    try:
        rc = guard.main()
    finally:
        sys.argv = orig_argv
    assert rc == 1


def test_main_fails_on_legacy_package_json_script(tmp_path: Path) -> None:
    """Root package.json carries runtime infisical commands and must be scanned."""
    repo = tmp_path
    (repo / "package.json").write_text(
        '{"scripts":{"dev:layer4":"infisical run --path=/llm -- python -m layer4"}}',
        encoding="utf-8",
    )
    import sys

    orig_argv = sys.argv
    sys.argv = ["check_infisical_path_schema.py", "--repo-root", str(repo)]
    try:
        rc = guard.main()
    finally:
        sys.argv = orig_argv
    assert rc == 1
