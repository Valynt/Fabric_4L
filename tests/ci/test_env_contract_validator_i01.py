from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATOR_PATH = REPO_ROOT / "scripts" / "ci" / "validate-env-contract.ts"
DEV_CHECKER_PATH = REPO_ROOT / "scripts" / "dev" / "check-env.ts"
CONFIG_ENV_DIR = REPO_ROOT / "packages" / "config" / "src" / "env"


def test_env_contract_validator_targets_active_env_examples_and_fails_closed():
    source = VALIDATOR_PATH.read_text(encoding="utf-8")

    # Backend contract uses root .env.example; frontend uses apps/web/.env.example.
    assert "../../.env.example" in source
    assert "../../apps/web/.env.example" in source
    # Legacy frontend/ path must not be referenced (was removed in frontend migration).
    assert "../../frontend/.env.example" not in source
    # Fail-closed guards must be present.
    assert "existsSync(filePath)" in source
    assert "Contract file does not exist" in source
    assert "Contract file declares no environment variables" in source


def test_config_env_schema_files_back_declared_package_exports():
    for filename in ("shared.ts", "backend.ts", "frontend.ts", "test.ts"):
        schema_path = CONFIG_ENV_DIR / filename
        assert schema_path.is_file(), f"missing config env schema file: {filename}"
        ignore_check = subprocess.run(
            ["git", "check-ignore", str(schema_path.relative_to(REPO_ROOT))],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
        assert ignore_check.returncode == 1, ignore_check.stdout

    dev_checker_source = DEV_CHECKER_PATH.read_text(encoding="utf-8")
    assert "../../packages/config/src/env/backend.js" in dev_checker_source
    assert "../../packages/config/src/env/frontend.js" in dev_checker_source
    assert "from \"../packages/config/src/env" not in dev_checker_source


def test_config_package_env_schemas_compile():
    # tsc is only available after `pnpm install` in packages/config, which
    # requires Node >=22.12.0.  Skip gracefully when the runtime prerequisite
    # is not met rather than failing with a misleading error.
    result = subprocess.run(
        ["pnpm", "--dir", "packages/config", "exec", "tsc", "--noEmit"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    if result.returncode == 254 and "Command" in result.stdout and "not found" in result.stdout:
        import pytest
        pytest.skip(
            "tsc not available — run `pnpm --dir packages/config install` with Node >=22.12.0 first"
        )

    assert result.returncode == 0, result.stdout
