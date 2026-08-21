<!-- Migrated from services/ADRs/ during legacy path cleanup. -->

# ADR-017: JWT + API Key Hybrid Authentication

**Status:** Accepted  
**Date:** April 2026  
**Authors:** Distinguished Engineering Team  
**Reviewers:** Security Architecture Committee

---

## Context

Value Fabric serves multiple authentication scenarios:
1. **Web UI Users**: Interactive sessions with SSO
2. **API Integrations**: Third-party system integrations
3. **Service-to-Service**: Internal layer communication
4. **Machine Users**: Automated scripts and ETL

Requirements:
- Stateless authentication (horizontal scaling)
- Token refresh without re-authentication
- API keys for long-lived integrations
- SSO integration (OIDC/SAML)
- Multi-tenancy context in tokens

We evaluated:
1. **JWT (JSON Web Tokens)** - Self-contained stateless tokens
2. **API Keys** - Simple key-based authentication
3. **Session Cookies** - Server-side session state
4. **mTLS** - Certificate-based authentication
5. **Hybrid** - JWT for UI, API Keys for integrations

## Decision

We chose a **Hybrid approach**: JWT for interactive users + API Keys for integrations

```
┌─────────────────────────────────────────────────────────────────┐
│ Authentication Methods                                            │
├─────────────────────────────────────────────────────────────────┤
│ 1. JWT Access Token (15 min expiry)                             │
│    - Web UI authentication                                      │
│    - Contains: tenant_id, user_id, roles, permissions           │
│    - Refresh token for renewal (7 days)                       │
│                                                                 │
│ 2. API Key (SHA-256 hashed, never stored raw)                  │
│    - Third-party integrations                                   │
│    - Service accounts                                           │
│    - Contains: tenant_id, permissions, expiry                 │
│                                                                 │
│ 3. OIDC (SSO integration)                                     │
│    - Enterprise SSO                                             │
│    - Maps to internal JWT                                       │
│                                                                 │
│ 4. X-Tenant-ID (service-to-service)                           │
│    - Internal layer communication                               │
│    - Requires IP allowlist + mTLS                             │
└─────────────────────────────────────────────────────────────────┘
```

## Rationale

### Why JWT?

1. **Stateless**: No server-side session storage
   ```python
   # Self-contained token
   JWT = {
     "sub": "user-123",
     "tenant_id": "tenant-456",
     "roles": ["editor"],
     "iat": 1713690000,
     "exp": 1713690900  # 15 minutes
   }
   ```

2. **Horizontal Scaling**: Any service can verify without database lookup
   ```python
   # Verify signature locally
   claims = jwt.decode(token, key=JWT_SECRET, algorithms=["HS256"])
   ```

3. **Rich Claims**: Embed permissions, reducing database lookups
   ```python
   # All auth info in token
   permissions = claims["permissions"]  # No DB query needed
   ```

### Why API Keys?

1. **Long-Lived**: Don't expire quickly like JWTs
   ```python
   # API key valid for 90 days
   api_key = "vf_test_dummy_32_char_random_string"
   ```

2. **Revocable**: Can be disabled without affecting other keys
   ```python
   # Store in database with enabled flag
   UPDATE api_keys SET enabled = false WHERE key_hash = '...';
   ```

3. **Auditable**: Track usage per key
   ```python
   # Log all API key usage
   api_key.last_used_at = datetime.utcnow()
   api_key.usage_count += 1
   ```

### Why Not Sessions?

- Requires sticky sessions or shared session store
- Database lookup for every request
- Doesn't scale horizontally as well

### Why Not mTLS for Everything?

- Complex certificate management
- Hard to rotate certificates
- Not suitable for browser clients
- Overkill for most use cases

## Trade-offs

### Positive
- Stateless scaling for JWT
- Long-lived integrations with API keys
- Flexible for different client types
- SSO integration via OIDC

### Negative
- Multiple authentication paths to maintain
- Token revocation complexity (JWT)
- API key storage security
- Potential for confusion about which to use

## Mitigations

| Risk | Mitigation |
|------|-----------|
| JWT revocation | Short expiry (15 min) + refresh tokens |
| API key leaks | SHA-256 hashing, never log raw keys, rate limiting |
| Multiple paths | Clear documentation, client SDKs |
| Token size | Minimal claims, compression if needed |

## Implementation

### JWT Structure

```python
class JWTClaims(BaseModel):
    """JWT payload structure."""
    
    # Standard claims
    sub: str                    # User ID (subject)
    iss: str = "value-fabric"   # Issuer
    aud: str = "value-fabric"   # Audience
    iat: int                    # Issued at (epoch)
    exp: int                    # Expiration (epoch)
    jti: str                    # JWT ID (for revocation)
    
    # Custom claims
    tenant_id: UUID             # Tenant context
    user_id: str                # User identifier
    email: str                  # User email
    roles: list[str]            # Role assignments
    permissions: list[str]      # Derived permissions
    api_key_id: Optional[str]   # If authenticated via API key

def create_jwt_pair(
    user: User,
    tenant_id: UUID,
    secret: str,
) -> JWTPair:
    """Create access + refresh token pair."""
    
    now = datetime.utcnow()
    
    # Access token (short-lived)
    access_claims = JWTClaims(
        sub=str(user.id),
        tenant_id=tenant_id,
        user_id=str(user.id),
        email=user.email,
        roles=user.roles,
        permissions=get_permissions(user.roles),
        iat=int(now.timestamp()),
        exp=int((now + timedelta(minutes=15)).timestamp()),
        jti=str(uuid4()),
    )
    
    access_token = jwt.encode(
        access_claims.model_dump(),
        secret,
        algorithm="HS256",
    )
    
    # Refresh token (longer-lived, single use)
    refresh_token = secrets.token_urlsafe(32)
    
    # Store refresh token hash for validation
    store_refresh_token_hash(user.id, hashlib.sha256(refresh_token.encode()).hexdigest())
    
    return JWTPair(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=900,  # 15 minutes
    )
```

### API Key Structure

```python
class APIKeyManager:
    """Secure API key lifecycle management."""
    
    PREFIX = "vf_live_"
    
    async def create_key(
        self,
        tenant_id: UUID,
        name: str,
        permissions: list[Permission],
        expires_days: int = 90,
    ) -> APIKeyCreationResult:
        """Create new API key with secure storage."""
        
        # Generate cryptographically secure key
        raw_key = f"{self.PREFIX}{secrets.token_urlsafe(32)}"
        
        # Hash for storage (never store raw)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        
        # Store metadata
        db_key = APIKey(
            id=uuid4(),
            tenant_id=tenant_id,
            name=name,
            key_hash=key_hash,
            permissions=[p.value for p in permissions],
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
            created_at=datetime.utcnow(),
            enabled=True,
        )
        
        await self._db.add(db_key)
        await self._db.commit()
        
        # Return raw key ONLY ONCE
        return APIKeyCreationResult(
            id=db_key.id,
            key=raw_key,  # Never stored, never logged
            name=name,
            expires_at=db_key.expires_at,
        )
    
    async def verify_key(self, raw_key: str) -> Optional[APIKeyContext]:
        """Verify API key and return context."""
        
        # Validate prefix
        if not raw_key.startswith(self.PREFIX):
            return None
        
        # Hash and lookup
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        db_key = await self._db.get(APIKey, key_hash=key_hash)
        
        if not db_key:
            return None
        
        # Check enabled and expiry
        if not db_key.enabled:
            await self._audit_log("disabled_key_used", key_id=db_key.id)
            return None
        
        if db_key.expires_at < datetime.utcnow():
            await self._audit_log("expired_key_used", key_id=db_key.id)
            return None
        
        # Update usage
        db_key.last_used_at = datetime.utcnow()
        db_key.usage_count += 1
        await self._db.commit()
        
        return APIKeyContext(
            key_id=str(db_key.id),
            tenant_id=db_key.tenant_id,
            permissions={Permission(p) for p in db_key.permissions},
        )
```

### Governance Middleware

```python
class GovernanceMiddleware(BaseHTTPMiddleware):
    """Unified authentication middleware."""
    
    async def dispatch(self, request: Request, call_next):
        ctx = await self._resolve_identity(request)
        
        if ctx:
            # Set context for downstream
            set_request_context(ctx)
            request.state.governance_context = ctx
        
        response = await call_next(request)
        
        # Add tenant resolution header
        if ctx:
            response.headers["X-Tenant-ID-Resolved"] = str(ctx.tenant_id)
        
        return response
    
    async def _resolve_identity(
        self,
        request: Request,
    ) -> Optional[RequestContext]:
        """Try authentication methods in priority order."""
        
        # 1. Bearer JWT
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await self._resolve_jwt(auth_header[7:])
        
        # 2. API Key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return await self._resolve_api_key(api_key)
        
        # 3. Service-to-service (internal)
        tenant_header = request.headers.get("X-Tenant-ID")
        if tenant_header and self._is_internal_request(request):
            return self._resolve_service_identity(tenant_header)
        
        return None
```

## Consequences

### Accepted
- Multiple authentication code paths
- JWT refresh token complexity
- API key secure storage requirements

### Mitigated
- Paths via unified middleware abstraction
- Refresh tokens via secure hashing and rotation
- API keys via hashing and audit logging

## Security Considerations

| Threat | Mitigation |
|--------|-----------|
| JWT theft | Short expiry (15 min), HTTPS only, secure storage |
| API key leak | SHA-256 hashing, never log, rate limiting per key |
| Token replay | JWT ID (jti) for revocation tracking |
| Privilege escalation | Claims verification on every request |
| Session fixation | Refresh token rotation on use |

## Related Decisions

- ADR-003: PostgreSQL + RLS for multi-tenancy
- ADR-005: Circuit breaker pattern (auth failures)

---

**Last Updated:** April 21, 2026
