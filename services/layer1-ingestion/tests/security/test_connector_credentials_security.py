import pytest

from src.api.main import AuthenticationInput, AuthenticationType, CreateTargetRequest


def test_rejects_inline_auth_secret_material():
    with pytest.raises(ValueError, match="Inline authentication secrets are forbidden"):
        CreateTargetRequest.model_validate(
            {
                "name": "test",
                "url": "https://example.com",
                "authentication": {
                    "type": "basic",
                    "credentials_ref": "vault://team/connector",
                    "password": "inline-secret",
                },
            }
        )


def test_requires_valid_credentials_reference_for_non_none_auth():
    with pytest.raises(ValueError, match="credentials_ref"):
        AuthenticationInput(type=AuthenticationType.BASIC, credentials_ref="not-a-ref")
