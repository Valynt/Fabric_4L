"""Public import compatibility for the shared JWT façade."""

from value_fabric.shared.identity.jwt import decode_jwt, encode_jwt, get_jwks
from value_fabric.shared.identity.jwt_tokens import decode_jwt as implementation_decode_jwt
from value_fabric.shared.identity.jwt_tokens import encode_jwt as implementation_encode_jwt


def test_established_jwt_imports_resolve_to_implementation_functions() -> None:
    assert decode_jwt is implementation_decode_jwt
    assert encode_jwt is implementation_encode_jwt
    assert callable(get_jwks)
