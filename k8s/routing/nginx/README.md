# Routing Stack: NGINX Ingress

**Status: Production-Supported**

Default supported production routing path for Value Fabric with oauth2-proxy authentication, rate limiting, and security headers.

## Public routing contract

NGINX is the canonical production edge. Two same-host Ingress resources keep API-only annotations from affecting frontend assets:

```text
/api/v1/<path> -> api-gateway:8000/v1/<path>
/<path>        -> frontend:3000/<path>
```

The API rule uses an explicit rewrite and has higher path precedence than `/`. L1–L6 Services are `ClusterIP` only and have no public routes. Gateway API and Istio are parity modes; activate exactly one edge implementation.

This stack also defines cert-manager issuers, oauth2-proxy authentication with encrypted cookie sessions, and hardened ingress NetworkPolicies.

## Security Features

### Edge Authentication (oauth2-proxy)

All routes are protected by oauth2-proxy with OIDC/OAuth2 authentication:

- **Session Type**: Encrypted cookies only (no Redis/session store)
- **Headers Passed Upstream**: `X-Auth-Request-User`, `X-Auth-Request-Email`, `Authorization`
- **Secrets**: Referenced from Kubernetes Secrets (not hardcoded in manifests)
- **Allowed Domains**: Configurable per environment via `allowed_domains`

To bypass authentication for specific paths (e.g., health checks), add an Ingress rule before the main auth-protected route.

### Rate Limiting

Default rate limits applied to all Ingress resources:

- **Frontend**: 10 req/sec, 100 req/min, 5 concurrent connections
- **API Layer**: 20 req/sec, 200 req/min, 10 concurrent connections
- **Burst Multiplier**: 5x base rate

### Security Headers

All responses include:

- `Strict-Transport-Security: max-age=31536000; includeSubDomains` (HSTS)
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: strict-origin-when-cross-origin`

### TLS Configuration

- **Minimum TLS Version**: 1.2 (TLS 1.0/1.1 rejected)
- **SSL Redirect**: Forced HTTPS redirect from HTTP
- **Certificate Management**: Automated via cert-manager with Let's Encrypt

### WAF Posture

This stack does NOT include WAF rules. Production deployments require either:

- **Option A**: Enable ModSecurity with OWASP Core Rule Set in NGINX controller ConfigMap
- **Option B**: External WAF (Cloudflare, AWS WAF, etc.) as documented prerequisite

### CORS Enforcement

CORS is enforced at the **application layer** (not at edge). Same-origin browsers call `/api/v1`; the API gateway owns downstream service delegation.

### DNSSEC

DNSSEC must be enabled at your DNS provider (Route53, Cloudflare, etc.). This is an **external DNS prerequisite**, not a Kubernetes configuration. Without DNSSEC:

- DNS spoofing can redirect traffic to attacker-controlled IPs
- LetsEncrypt HTTP-01 validation is vulnerable to DNS-based attacks

## Required cluster prerequisites

- **NGINX Ingress Controller** with `IngressClass: nginx` available.
  - Typical install: `helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx -n ingress-nginx --create-namespace`.
- **cert-manager** v1.13+ installed cluster-wide.
  - Typical install: `helm upgrade --install cert-manager jetstack/cert-manager -n cert-manager --create-namespace --set installCRDs=true`.
- **OIDC Provider** configured (e.g., Auth0, Okta, Keycloak, Google Workspace).
- One DNS A record for `__HOST__` pointing at the NGINX controller's external LoadBalancer IP.
- DNSSEC enabled at DNS provider.

This stack does **not** import `../../base`. It is composed with an env overlay
under `k8s/deployments/<env>-nginx/`, which also provides the `routing-host`
ConfigMap used to substitute `__HOST__`.

## Apply (via deployment overlay)

```bash
# Supported deployments:
kubectl apply -k k8s/deployments/dev-nginx
kubectl apply -k k8s/deployments/prod-nginx
```

Do not `kubectl apply -k k8s/routing/nginx` directly — it is missing the application workloads.

## Validation

```bash
# Render only:
kustomize build k8s/deployments/prod-nginx | kubeconform -strict -summary -

# Verify TLS certificate issuance:
kubectl -n value-fabric get certificate
kubectl -n value-fabric describe certificate frontend-tls

# Verify ingress is reachable:
curl -I https://<your-host>

# Verify API routing returns JSON rather than frontend HTML:
make production-edge-smoke APPLICATION_URL=https://<your-host>
# If edge authentication requires credentials, set EDGE_SMOKE_AUTHORIZATION
# (for example, "Bearer ...") or EDGE_SMOKE_COOKIE in the environment.
```

## Troubleshooting

- **Cert stuck in `Pending`**: confirm the `ClusterIssuer` solver reaches the cluster's external IP and the DNS record exists. `kubectl describe certificaterequest` shows ACME challenge state.
- **404 from NGINX**: confirm Service names in `ingress.yaml` match the rendered Services from the env overlay (`kubectl -n value-fabric get svc`).
- **Sentinel `__HOST__` visible in cluster**: deployment overlay's `replacements:` did not run. Re-render with `kustomize build` and grep the output.
