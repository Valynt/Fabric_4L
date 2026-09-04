"""Parameterized tests for CLI auth _is_jwt helper."""

from __future__ import annotations

import pytest

from valuefabric.cli.auth import _is_jwt


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("header_part.payload_part.signature_part", True),
        ("part1.part2.part3", True),
        ("header.payload", False),
        ("header.payload.signature.extra", False),
        ("", False),
        ("header..signature", False),
        ("just_a_random_string", False),
    ],
)
def test_is_jwt(token: str, expected: bool) -> None:
    assert _is_jwt(token) is expected
