# Key Rotation and Trust Boundary Runbook

## Overview

This runbook documents the operational procedures for zero-downtime key rotation across Fabric 4L's authentication plane:
1. **Clerk JWKS Rotation** (External RSA key pair used by Clerk to sign user JWTs).
2. **Fabric Gateway Ed25519 Signing Key Rotation** (Internal asymmetric key pair used to mint `AuthContext` envelopes for L1–L6).

---

## 1. Clerk JWKS Key Rotation

Clerk handles key rotation via standard JSON Web Key Sets (JWKS) hosted at:
`https://<clerk-domain>/.well-known/jwks.json`

### Rotation Lifecycle & Gateway Caching Behavior
- The Fabric API Gateway (`services/api/app/core/clerk_verifier.py`) maintains an in-memory `ClerkJWKSCache` with a 10-minute TTL.
- **Cache-miss on new `kid`**: When Clerk introduces a new key (`kid_new`), the first incoming token bearing `kid_new` triggers a single on-demand force-refresh of the JWKS endpoint.
- **Outage Resilience**: If the JWKS endpoint is unreachable or returns a 5xx error during rotation, the gateway falls back gracefully to previously cached keys.
- **Clock Skew**: The gateway enforces a configurable leeway window (`CLERK_JWT_LEEWAY_SECONDS`, default: 10s, max: 60s) to absorb minor NTP drift.

### Manual JWKS Verification Procedure
```bash
# Verify live Clerk JWKS keys
curl -s https://clerk.valuepact.ai/.well-known/jwks.json | jq .
```

---

## 2. Gateway Ed25519 Envelope Key Rotation

Fabric 4L uses an Ed25519 asymmetric key pair to re-wrap verified Clerk claims into an immutable `AuthContext` internal envelope.

### Zero-Downtime Rotation Protocol

To rotate the Ed25519 gateway keys without dropping active service-to-service requests:

#### Step 1: Generate New Ed25519 Key Pair
```bash
# Generate private key for gateway
openssl genpkey -algorithm ed25519 -out /tmp/gateway_k2.pem

# Extract public key for L1–L6 verification
openssl pkey -in /tmp/gateway_k2.pem -pubout -out /tmp/gateway_k2_pub.pem
```

#### Step 2: Publish Public Key into `FABRIC_AUTH_PUBLIC_KEYS` (Dual-Key Period)
Update Infisical / environment configuration across all services (Gateway + L1–L6) with both keys in the verification set:
```json
[
  {
    "kid": "gateway-k1",
    "public_pem": "-----BEGIN PUBLIC KEY-----\n..."
  },
  {
    "kid": "gateway-k2",
    "public_pem": "-----BEGIN PUBLIC KEY-----\n..."
  }
]
```

#### Step 3: Switch Active Gateway Signing Key
Update the API Gateway's environment variables to begin minting envelopes with `gateway-k2`:
```bash
FABRIC_AUTH_SIGNING_KID=gateway-k2
FABRIC_AUTH_SIGNING_KEY="<private_pem_k2>"
```
*Note: Because L1–L6 already possess `gateway-k2` in their `KeySet`, new tokens are verified immediately, while in-flight tokens signed with `gateway-k1` continue to pass.*

#### Step 4: Decommission Legacy Key (`gateway-k1`)
After the envelope TTL expires (default: 300 seconds + 60s buffer), remove `gateway-k1` from `FABRIC_AUTH_PUBLIC_KEYS`:
```json
[
  {
    "kid": "gateway-k2",
    "public_pem": "-----BEGIN PUBLIC KEY-----\n..."
  }
]
```

---

## 3. Clock Skew & Lifetime Misalignment Detection

- **Token Lifetime**: Clerk tokens typically have a 60-second TTL. The internal envelope has a 300-second TTL.
- **Clock Skew Anomaly Alert**: If `abs(now - iat) > 300s`, the gateway logs an anomaly alert `auth.clock_skew_detected`.
- **Mitigation**: Ensure NTP synchronization across host VMs / Kubernetes worker nodes (`chronyd` or `systemd-timesyncd`).
