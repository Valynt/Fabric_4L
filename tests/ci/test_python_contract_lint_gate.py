from __future__ import annotations

from collections import Counter
from pathlib import Path

from scripts.ci import python_contract_lint

REPO_ROOT = Path(__file__).resolve().parents[2]


def _findings_for(path: str, content: str):
    return [
        *python_contract_lint.check_file_with_regex(Path(path), content),
        *python_contract_lint.check_file_with_ast(Path(path), content),
    ]


def test_safe_tenant_scoped_signatures_are_allowed():
    content = """
class AccountRepository:
    async def get_account(self, account_id: str, tenant_id: str):
        return account_id, tenant_id
"""

    findings = _findings_for("services/layer4-agents/src/layer4_agents/services/accounts.py", content)

    assert not [finding for finding in findings if finding.contract_id == "tenant_context"]


def test_direct_tenant_header_extraction_is_rejected():
    content = """
async def unsafe_route(request):
    tenant_id = request.headers.get("x-tenant-id")
    return tenant_id
"""

    findings = _findings_for("services/layer4-agents/src/api/routes/accounts.py", content)

    assert any(finding.contract_id == "tenant_context" for finding in findings)


def test_tool_control_flow_exceptions_are_allowed_when_structured_response_is_returned():
    content = """
class CreateTaskTool:
    async def execute(self, input_data):
        try:
            raise ValueError("unsupported provider")
        except Exception:
            return {"success": False, "error": "TASK_CREATE_ERROR"}
"""

    findings = _findings_for(
        "services/layer4-agents/src/layer4_agents/tools/integration_tools.py",
        content,
    )

    assert not [finding for finding in findings if finding.contract_id == "tool_error_contract"]


def test_unstructured_tool_execution_error_is_rejected():
    content = """
async def execute_tool(input_data):
    raise ValueError("boom")
"""

    findings = _findings_for(
        "services/layer4-agents/src/layer4_agents/tools/example.py",
        content,
    )

    assert any(finding.contract_id == "tool_error_contract" for finding in findings)


def test_secret_env_var_key_names_are_allowed_but_literal_secret_values_are_rejected():
    allowed_content = 'API_KEY_FINGERPRINT_SECRET = "API_KEY_FINGERPRINT_SECRET"\n'
    rejected_content = 'PAYMENT_SECRET = "super-secret-production-value"\n'

    allowed = _findings_for("services/api/app/core/config.py", allowed_content)
    rejected = _findings_for("services/api/app/core/config.py", rejected_content)

    assert not [finding for finding in allowed if finding.contract_id == "secret_in_source"]
    assert any(finding.contract_id == "secret_in_source" for finding in rejected)


def test_hashing_imports_are_allowed_but_fix_module_imports_are_rejected():
    allowed_content = "from value_fabric.shared.identity.hashing import hash_api_key\n"
    rejected_content = "from services.layer4_agents.fix_auth import patch_auth\n"

    allowed = _findings_for("services/api/app/core/security.py", allowed_content)
    rejected = _findings_for("services/api/app/core/security.py", rejected_content)

    assert not [finding for finding in allowed if finding.contract_id == "no_fix_imports"]
    assert any(finding.contract_id == "no_fix_imports" for finding in rejected)


def test_strict_python_contract_lint_has_no_blocking_findings():
    report = python_contract_lint.scan_repository(REPO_ROOT)
    counts = Counter(finding.severity for finding in report.findings)

    assert counts["critical"] == 0
    assert counts["high"] == 0
