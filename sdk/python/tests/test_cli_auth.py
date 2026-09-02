import pytest
from valuefabric.cli.auth import _is_jwt

@pytest.mark.parametrize(
    "token, expected",
    [
        ("header.payload.signature", True),
        ("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", True),
        ("not_a_jwt", False),
        ("header.payload", False),
        ("header.payload.signature.extra", False),
        ("..", False),
        (".payload.signature", False),
        ("header..signature", False),
        ("header.payload.", False),
        ("", False),
    ],
)
def test_is_jwt(token: str, expected: bool):
    assert _is_jwt(token) == expected
