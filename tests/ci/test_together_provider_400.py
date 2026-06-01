"""Unit tests for together_provider _is_400_error helper."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "services" / "layer4-agents" / "src"))
from layer4_agents.services.together_provider import _is_400_error


class FakeExcWithStatus:
    status_code = 400


class FakeExcWithResponse:
    class response:
        status_code = 400


class FakeExcText:
    def __str__(self):
        return "HTTP 400 bad request"


class FakeExcOther:
    status_code = 500
    def __str__(self):
        return "Internal Server Error"


def test_detects_status_code_400():
    assert _is_400_error(FakeExcWithStatus()) is True


def test_detects_response_status_code_400():
    assert _is_400_error(FakeExcWithResponse()) is True


def test_detects_text_400():
    assert _is_400_error(FakeExcText()) is True


def test_rejects_non_400():
    assert _is_400_error(FakeExcOther()) is False
