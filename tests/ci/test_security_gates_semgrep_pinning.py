from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/security-gates.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_semgrep_jobs_share_one_exact_binary_pin() -> None:
    workflow = _workflow()
    assert workflow["env"]["SEMGREP_VERSION"]

    for job_name in ("cypher-dynamic-guard", "semgrep-full-scan"):
        commands = "\n".join(
            step.get("run", "") for step in workflow["jobs"][job_name]["steps"]
        )
        assert 'semgrep==${{ env.SEMGREP_VERSION }}' in commands
        assert "pip install semgrep\n" not in commands


def test_full_scan_uses_only_reviewed_vendored_and_local_rules() -> None:
    workflow_text = WORKFLOW.read_text(encoding="utf-8")
    for registry_pack in (
        "p/security-audit",
        "p/secrets",
        "p/owasp-top-ten",
        "p/python",
        "p/typescript",
        "p/react",
        "p/dockerfile",
        "p/docker-compose",
        "p/kubernetes",
        "p/github-actions",
    ):
        assert f"--config {registry_pack}" not in workflow_text

    assert "--config config/semgrep/registry/" in workflow_text
    assert "--config .semgrep/" in workflow_text


def test_static_scanner_smoke_check_validates_configs_and_sarif() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["semgrep-full-scan"]["steps"]
    smoke = next(
        step for step in steps if step.get("name") == "Smoke check pinned Semgrep"
    )
    command = smoke["run"]

    assert "semgrep scan" in command
    assert "--validate" in command
    assert "--config config/semgrep/registry/" in command
    assert "--config .semgrep/" in command
    assert "--sarif" in command
    assert "json.load" in command
    assert "continue-on-error" not in workflow["jobs"]["semgrep-full-scan"]


def test_dast_ephemeral_stack_provides_required_compose_env_and_evidence_dir() -> None:
    workflow = _workflow()
    steps = workflow["jobs"]["dast-api-scan"]["steps"]
    startup = next(step for step in steps if step.get("name") == "Start ephemeral Value Fabric stack")
    command = startup["run"]

    assert "BEGIN PRIVATE KEY" not in command
    assert "openssl genpkey -algorithm ED25519" in command
    assert "fabric-auth.env" in command
    assert command.index("fabric-auth.env") < command.index("docker compose")
    assert "mkdir -p zap-reports" in command
    assert command.index("mkdir -p zap-reports") < command.index("docker compose")
    assert "OPENAI_API_KEY=dummy-key-for-ci" in command
    assert "OPENAI_API_KEY=${OPENAI_API_KEY:?set OPENAI_API_KEY}" not in command
    assert "JWT_SECRET=valuefabric-ci-jwt-secret-minimum-32-characters" in command
    assert "JWT_SECRET=${JWT_SECRET:?set JWT_SECRET}" not in command
    assert "docker compose -f infra/compose/docker-compose.full.yml --env-file .env up -d --build" in command
    for variable in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "SECRET_KEY",
        "JWT_SECRET",
        "API_KEY_HMAC_SECRET",
        "SERVICE_AUTH_SECRET",
        "LAYER4_DATABASE_URL",
        "NEO4J_PASSWORD",
        "CORS_ORIGINS",
        "CLERK_ISSUER",
        "CLERK_AUTHORIZED_PARTIES",
        "CLERK_JWKS_URL",
        "CLERK_SECRET_KEY",
        "FABRIC_AUTH_SIGNING_KEY",
        "FABRIC_AUTH_PUBLIC_KEYS",
        "FLOWER_PASSWORD",
        "GRAFANA_ADMIN_PASSWORD",
    ):
        assert f"{variable}=" in command

    collect_logs = next(step for step in steps if step.get("name") == "Collect compose logs for evidence")
    assert "mkdir -p zap-reports" in collect_logs["run"]
    assert "docker compose -f infra/compose/docker-compose.full.yml --env-file .env logs --no-color" in collect_logs["run"]

    stop_stack = next(step for step in steps if step.get("name") == "Stop ephemeral stack")
    assert "docker compose -f infra/compose/docker-compose.full.yml --env-file .env down -v" in stop_stack["run"]
