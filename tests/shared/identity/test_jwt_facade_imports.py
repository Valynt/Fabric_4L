"""Public import compatibility for the shared JWT façade."""

from value_fabric.shared.identity.jwt import decode_jwt, encode_jwt, get_jwks
from value_fabric.shared.identity.jwt_tokens import (
    decode_jwt as implementation_decode_jwt,
)
from value_fabric.shared.identity.jwt_tokens import (
    encode_jwt as implementation_encode_jwt,
)


def test_established_jwt_imports_resolve_to_implementation_functions() -> None:
    assert decode_jwt is implementation_decode_jwt
    assert encode_jwt is implementation_encode_jwt
    assert callable(get_jwks)


def test_get_jwks_mapping_interface() -> None:
    jwks = get_jwks()
    assert isinstance(jwks["keys"], list)
    assert jwks.get("keys") == jwks["keys"]
    assert jwks.get("nonexistent", "fallback") == "fallback"
    assert "keys" in jwks
    assert list(jwks.keys) == jwks["keys"]
    assert ("keys", jwks["keys"]) in list(jwks.items())
    assert jwks["keys"] in list(jwks.values())
    assert "keys" in list(iter(jwks))
    assert len(jwks) >= 1
