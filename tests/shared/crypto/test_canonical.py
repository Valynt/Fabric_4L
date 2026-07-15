"""Tests for RFC 8785 canonical JSON hashing utility.

Covers:
- Round-trip stability (key ordering)
- Float normalization edge cases
- Unicode key ordering
- Bytes handling
- Error cases (non-finite floats, unsupported types)
- Hash algorithm validation
"""

from __future__ import annotations

import pytest
from value_fabric.shared.crypto.canonical import canonical_hash, canonical_json_encode

# ═══════════════════════════════════════════════════════════════════════════
# Round-trip stability
# ═══════════════════════════════════════════════════════════════════════════


class TestCanonicalJsonEncode:
    """canonical_json_encode determinism and RFC 8785 compliance."""

    def test_key_order_stability(self) -> None:
        """Keys must be sorted lexicographically regardless of insertion order."""
        a = canonical_json_encode({"b": 1, "a": 2})
        b = canonical_json_encode({"a": 2, "b": 1})
        assert a == b
        assert a == '{"a":2,"b":1}'

    def test_nested_key_order(self) -> None:
        """Nested dicts must also be sorted."""
        obj = {"z": {"b": 1, "a": 2}, "a": 0}
        result = canonical_json_encode(obj)
        assert result == '{"a":0,"z":{"a":2,"b":1}}'

    def test_no_whitespace(self) -> None:
        """Output must have no insignificant whitespace."""
        result = canonical_json_encode({"key": "value", "num": 42})
        assert " " not in result.replace('" "', "")  # allow space in values

    def test_unicode_keys(self) -> None:
        """Unicode keys must be sorted by code-point order."""
        obj = {"ä": 1, "a": 2, "z": 3}
        result = canonical_json_encode(obj)
        # 'a' (U+0061) < 'z' (U+007A) < 'ä' (U+00E4)
        assert result == '{"a":2,"z":3,"ä":1}'

    def test_ensure_ascii_false(self) -> None:
        """Non-ASCII characters must not be escaped."""
        result = canonical_json_encode({"emoji": "🚀"})
        assert "🚀" in result
        assert "\\u" not in result

    def test_bytes_decoded(self) -> None:
        """bytes values must be decoded to UTF-8 strings."""
        result = canonical_json_encode({"data": b"hello"})
        assert result == '{"data":"hello"}'

    def test_set_sorted(self) -> None:
        """set values must be serialized as sorted lists."""
        result = canonical_json_encode({"tags": {"c", "a", "b"}})
        assert result == '{"tags":["a","b","c"]}'

    def test_none_value(self) -> None:
        """None must serialize as null."""
        result = canonical_json_encode({"key": None})
        assert result == '{"key":null}'

    def test_bool_values(self) -> None:
        """Booleans must serialize as true/false."""
        result = canonical_json_encode({"t": True, "f": False})
        assert result == '{"f":false,"t":true}'

    def test_list_order_preserved(self) -> None:
        """List element order must be preserved."""
        result = canonical_json_encode({"items": [3, 1, 2]})
        assert result == '{"items":[3,1,2]}'

    def test_empty_structures(self) -> None:
        """Empty dict and list must serialize correctly."""
        assert canonical_json_encode({}) == "{}"
        assert canonical_json_encode([]) == "[]"
        assert canonical_json_encode({"a": {}, "b": []}) == '{"a":{},"b":[]}'


# ═══════════════════════════════════════════════════════════════════════════
# Float edge cases
# ═══════════════════════════════════════════════════════════════════════════


class TestFloatHandling:
    """RFC 8785 §3.2.2.3 float handling."""

    def test_integer_float(self) -> None:
        """Floats that are integers should serialize deterministically."""
        result = canonical_json_encode({"val": 1.0})
        assert '"val":1.0' in result

    def test_nan_raises(self) -> None:
        """NaN must raise ValueError per RFC 8785."""
        with pytest.raises(ValueError, match="non-finite"):
            canonical_json_encode({"val": float("nan")})

    def test_inf_raises(self) -> None:
        """Infinity must raise ValueError per RFC 8785."""
        with pytest.raises(ValueError, match="non-finite"):
            canonical_json_encode({"val": float("inf")})

    def test_negative_inf_raises(self) -> None:
        """Negative infinity must raise ValueError."""
        with pytest.raises(ValueError, match="non-finite"):
            canonical_json_encode({"val": float("-inf")})


# ═══════════════════════════════════════════════════════════════════════════
# Error cases
# ═══════════════════════════════════════════════════════════════════════════


class TestErrorCases:
    """Unsupported types must raise TypeError."""

    def test_unsupported_type(self) -> None:
        """Custom objects must raise TypeError."""
        with pytest.raises(TypeError, match="not canonicalizable"):
            canonical_json_encode({"obj": object()})


# ═══════════════════════════════════════════════════════════════════════════
# canonical_hash
# ═══════════════════════════════════════════════════════════════════════════


class TestCanonicalHash:
    """canonical_hash determinism and algorithm validation."""

    def test_hash_stability(self) -> None:
        """Same logical object must always produce same hash."""
        h1 = canonical_hash({"b": 1, "a": 2})
        h2 = canonical_hash({"a": 2, "b": 1})
        assert h1 == h2

    def test_hash_is_hex(self) -> None:
        """Hash must be a lowercase hex string."""
        h = canonical_hash({"key": "value"})
        assert len(h) == 64  # SHA-256 hex
        assert h == h.lower()
        int(h, 16)  # must be valid hex

    def test_different_objects_different_hashes(self) -> None:
        """Different objects must produce different hashes."""
        h1 = canonical_hash({"a": 1})
        h2 = canonical_hash({"a": 2})
        assert h1 != h2

    def test_unsupported_algorithm(self) -> None:
        """Unsupported algorithm must raise ValueError."""
        with pytest.raises(ValueError, match="Unsupported hash algorithm"):
            canonical_hash({"a": 1}, algorithm="md5")

    def test_nested_complex_object(self) -> None:
        """Complex nested structures must hash deterministically."""
        obj = {
            "tenant_id": "t-123",
            "tools": [
                {"name": "crm_sync", "version": "1.0"},
                {"name": "graph_query", "version": "2.1"},
            ],
            "metadata": {"created": "2026-01-01", "active": True},
        }
        h1 = canonical_hash(obj)
        # Rebuild with different key order
        obj2 = {
            "metadata": {"active": True, "created": "2026-01-01"},
            "tools": [
                {"name": "crm_sync", "version": "1.0"},
                {"name": "graph_query", "version": "2.1"},
            ],
            "tenant_id": "t-123",
        }
        h2 = canonical_hash(obj2)
        assert h1 == h2
