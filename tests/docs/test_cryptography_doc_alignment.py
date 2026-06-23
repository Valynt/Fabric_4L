"""Assertions that cryptography docs match runtime implementation."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_FILE = REPO_ROOT / "services/layer4-agents/src/layer4_agents/services/encryption_service.py"
SECURITY_MODEL_DOC = REPO_ROOT / "docs/core-concepts/security-model.md"
COMPLIANCE_DOC = REPO_ROOT / "docs/reference/compliance.md"

CANONICAL_ALGORITHM_TEXT = "Fernet (AES-128-CBC + HMAC-SHA256)"


def test_runtime_declares_canonical_algorithm() -> None:
    runtime_source = RUNTIME_FILE.read_text(encoding="utf-8")
    assert (
        f'ENCRYPTION_ALGORITHM: str = "{CANONICAL_ALGORITHM_TEXT}"' in runtime_source
    ), "Runtime encryption algorithm constant must match canonical value."


def test_docs_match_runtime_algorithm() -> None:
    security_model = SECURITY_MODEL_DOC.read_text(encoding="utf-8")
    compliance = COMPLIANCE_DOC.read_text(encoding="utf-8")

    assert CANONICAL_ALGORITHM_TEXT in security_model
    assert CANONICAL_ALGORITHM_TEXT in compliance
