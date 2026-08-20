"""Tool manifest signing and verification (ETDI - External Tool Description with Integrity).

Implements manifest signing using JSON Web Signature (JWS) to ensure
tool provenance and prevent supply chain attacks.

Reference:
    - JWS: https://tools.ietf.org/html/rfc7515
    - ETDI: External Tool Description with Integrity (emerging standard)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import asdict
from datetime import datetime, timedelta
from typing import Any

import jwt

from .mcp_types import ManifestValidationError, ToolManifest
from value_fabric.shared.models.typed_dict import TypedDictModel


class ManifestSigner__create_payloadResult(TypedDictModel):
    capabilities: Any
    description: Any
    endpoint: Any
    exp: Any
    iat: Any
    required_scopes: Any
    tenant_scoped: Any
    tool_name: Any
    version: Any

logger = logging.getLogger(__name__)


class ManifestVerifier:
    """Verify tool manifest signatures using compact JWS."""

    ALLOWED_ALGORITHMS = ("RS256",)

    def __init__(
        self,
        public_key: str | dict[str, str] | None = None,
        *,
        trusted_keys: dict[str, str] | None = None,
        enforce_expiry: bool = True,
        leeway_seconds: int = 0,
    ):
        """Initialize verifier.

        Args:
            public_key: Default PEM public key or {kid: pem} map.
            trusted_keys: Optional trusted key set for kid-based selection.
            enforce_expiry: Validate exp/iat claims when present.
            leeway_seconds: Clock skew tolerance for time-based claims.
        """
        self.public_key = public_key
        self.trusted_keys = trusted_keys or {}
        self.enforce_expiry = enforce_expiry
        self.leeway_seconds = leeway_seconds

    def verify_manifest(self, manifest: ToolManifest, public_key: str | dict[str, str] | None = None) -> bool:
        """Verify the JWS signature of a tool manifest."""
        if not manifest.signature:
            logger.warning("Manifest for tool '%s' has no signature", manifest.tool_name)
            return False

        try:
            return self._verify_jws(manifest.signature, manifest, public_key)
        except Exception as exc:  # defensive, verification must fail closed
            logger.error("Manifest signature verification failed: %s", exc)
            return False

    def _verify_jws(
        self,
        signature: str,
        manifest: ToolManifest,
        public_key: str | dict[str, str] | None,
    ) -> bool:
        """Verify JWS signature and claims/payload bindings."""
        try:
            header = jwt.get_unverified_header(signature)
        except jwt.PyJWTError as exc:
            logger.error("Invalid JWS header: %s", exc)
            return False

        algorithm = header.get("alg")
        if algorithm == "none" or not algorithm:
            logger.warning("Rejected manifest JWS using insecure/empty algorithm")
            return False
        if algorithm not in self.ALLOWED_ALGORITHMS:
            logger.warning("Rejected manifest JWS algorithm '%s'", algorithm)
            return False

        key = self._resolve_verification_key(public_key, header)
        if not key:
            logger.error("No trusted key available for manifest verification")
            raise ManifestValidationError("Cannot verify manifest - no trusted key available")

        decode_options = {
            "verify_signature": True,
            "verify_exp": self.enforce_expiry,
            "verify_iat": self.enforce_expiry,
        }
        required_claims = ["tool_name", "version", "endpoint", "capabilities", "iat", "exp"]

        try:
            payload = jwt.decode(
                signature,
                key=key,
                algorithms=list(self.ALLOWED_ALGORITHMS),
                options=decode_options,
                leeway=self.leeway_seconds,
                audience=None,
                issuer=None,
                require=required_claims,
            )
        except jwt.PyJWTError as exc:
            logger.error("Manifest JWS cryptographic verification failed: %s", exc)
            return False

        if not self._validate_payload_binding(payload, manifest):
            return False

        return True

    def _resolve_verification_key(
        self,
        public_key: str | dict[str, str] | None,
        header: dict[str, Any],
    ) -> str | None:
        """Resolve trusted verification key, supporting kid rotation hooks."""
        kid = header.get("kid")

        explicit_key = public_key if public_key is not None else self.public_key
        if isinstance(explicit_key, dict):
            if not kid:
                logger.error("JWS missing kid while multiple explicit keys are configured")
                return None
            return explicit_key.get(kid)
        if isinstance(explicit_key, str) and explicit_key.strip():
            return explicit_key

        if kid and kid in self.trusted_keys:
            return self.trusted_keys[kid]

        trusted = self._get_trusted_keys_from_env()
        if kid:
            return trusted.get(kid)

        if len(trusted) == 1:
            return next(iter(trusted.values()))

        return self._get_trusted_key()

    @staticmethod
    def _validate_payload_binding(payload: dict[str, Any], manifest: ToolManifest) -> bool:
        """Bind JWS claims to the exact manifest fields protected by policy."""
        expected: dict[str, Any] = {
            "tool_name": manifest.tool_name,
            "version": manifest.version,
            "description": manifest.description,
            "endpoint": manifest.endpoint,
            "capabilities": manifest.capabilities,
            "required_scopes": manifest.required_scopes,
            "tenant_scoped": manifest.tenant_scoped,
        }
        for field, expected_value in expected.items():
            actual_value = payload.get(field)
            if actual_value != expected_value:
                logger.error(
                    "Manifest payload binding mismatch for '%s' (expected=%r actual=%r)",
                    field,
                    expected_value,
                    actual_value,
                )
                return False

        exp = payload.get("exp")
        iat = payload.get("iat")
        if isinstance(exp, int) and isinstance(iat, int) and exp <= iat:
            logger.error("Manifest payload has invalid temporal claims: exp <= iat")
            return False

        return True

    @staticmethod
    def _get_trusted_keys_from_env() -> dict[str, str]:
        """Load trusted keyset for kid-based rotation behavior.

        Supported hooks:
          - MCP_MANIFEST_TRUSTED_KEYS_JSON: JSON object {"kid": "-----BEGIN PUBLIC KEY-----..."}
          - MCP_MANIFEST_JWKS_PATH: file containing JWKS (local hook for key rotation)
        """
        trusted: dict[str, str] = {}

        keys_json = os.getenv("MCP_MANIFEST_TRUSTED_KEYS_JSON")
        if keys_json:
            try:
                parsed = json.loads(keys_json)
                if isinstance(parsed, dict):
                    trusted.update({str(k): str(v) for k, v in parsed.items()})
            except Exception as exc:  # noqa: BLE001 - fail closed with logging
                logger.error("Failed parsing MCP_MANIFEST_TRUSTED_KEYS_JSON: %s", exc)

        jwks_path = os.getenv("MCP_MANIFEST_JWKS_PATH")
        if jwks_path:
            try:
                with open(jwks_path, encoding="utf-8") as fp:
                    jwks = json.load(fp)
                for jwk in jwks.get("keys", []):
                    kid = jwk.get("kid")
                    if not kid:
                        continue
                    pem = jwk.get("x5c_pem") or jwk.get("pem")
                    if pem:
                        trusted[str(kid)] = str(pem)
            except Exception as exc:  # noqa: BLE001 - fail closed with logging
                logger.error("Failed loading manifest JWKS from %s: %s", jwks_path, exc)

        return trusted

    @staticmethod
    def _get_trusted_key() -> str | None:
        """Get trusted public key for manifest verification."""
        key_path = os.getenv("MCP_MANIFEST_PUBLIC_KEY_PATH")
        if key_path:
            try:
                with open(key_path, encoding="utf-8") as f:
                    return f.read()
            except Exception as exc:  # noqa: BLE001 - fail closed with logging
                logger.error("Failed to load public key from %s: %s", key_path, exc)

        key_pem = os.getenv("MCP_MANIFEST_PUBLIC_KEY")
        if key_pem:
            return key_pem

        return None

    @classmethod
    def compute_manifest_hash(cls, manifest: ToolManifest) -> str:
        """Compute canonical hash of manifest content (for signing)."""
        manifest_dict = asdict(manifest)
        manifest_dict.pop("signature", None)

        canonical = json.dumps(manifest_dict, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()


class ManifestSigner:
    """Sign tool manifests using JWS."""

    def __init__(self, private_key: str, key_id: str | None = None, token_ttl_seconds: int = 300):
        self.private_key = private_key
        self.key_id = key_id
        self.token_ttl_seconds = token_ttl_seconds

    def sign_manifest(self, manifest: ToolManifest) -> ToolManifest:
        """Sign a tool manifest and return signed copy."""
        try:
            payload = self._create_payload(manifest)
            header = {"alg": "RS256", "typ": "JWT"}
            if self.key_id:
                header["kid"] = self.key_id

            signature = self._create_jws(header, payload)

            return ToolManifest(
                tool_name=manifest.tool_name,
                version=manifest.version,
                description=manifest.description,
                endpoint=manifest.endpoint,
                capabilities=manifest.capabilities,
                required_scopes=manifest.required_scopes,
                signature=signature,
                tenant_scoped=manifest.tenant_scoped,
            )
        except Exception as exc:  # noqa: BLE001 - normalization to gateway error
            logger.error("Failed to sign manifest: %s", exc)
            raise ManifestValidationError(f"Failed to sign manifest: {exc}") from exc

    def _create_payload(self, manifest: ToolManifest) -> dict[str, Any]:
        now = datetime.utcnow()
        exp = now + timedelta(seconds=self.token_ttl_seconds)
        return ManifestSigner__create_payloadResult.model_validate({
            "tool_name": manifest.tool_name,
            "version": manifest.version,
            "description": manifest.description,
            "endpoint": manifest.endpoint,
            "capabilities": manifest.capabilities,
            "required_scopes": manifest.required_scopes,
            "tenant_scoped": manifest.tenant_scoped,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        })


    def _create_jws(self, header: dict[str, Any], payload: dict[str, Any] | TypedDictModel) -> str:
        """Create compact JWS using RS256 private-key signing."""
        payload_dict = payload.model_dump() if isinstance(payload, TypedDictModel) else payload
        return jwt.encode(
            payload_dict,
            key=self.private_key,
            algorithm="RS256",
            headers=header,
        )
