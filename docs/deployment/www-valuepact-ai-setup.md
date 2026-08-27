# Production Setup for www.valuepact.ai

This guide covers the complete production deployment setup for the www.valuepact.ai domain.

## Prerequisites

- Domain purchased from Spaceship.com (www.valuepact.ai)
- Kubernetes cluster ready for production deployment
- Infisical configured for production secrets
- Clerk account configured for authentication

## DNS Configuration

### Step 1: Configure DNS Records at Spaceship.com

Log into your Spaceship.com account and configure the following DNS records for `valuepact.ai`:

```
Type: A Record
Name: www
Value: <your-kubernetes-load-balancer-ip>
TTL: 300

Type: A Record
Name: accounts
Value: <your-kubernetes-load-balancer-ip>
TTL: 300
```

**Note**: Replace `<your-kubernetes-load-balancer-ip>` with your actual Kubernetes load balancer IP address.

### Step 2: Verify DNS Propagation

After updating DNS records, verify propagation:

```bash
# Check www subdomain
dig www.valuepact.ai

# Check accounts subdomain (for Clerk)
dig accounts.valuepact.ai
```

## SSL/TLS Certificate Setup

The Kubernetes configuration uses cert-manager with Let's Encrypt for automatic SSL certificate management.

### Step 1: Verify ClusterIssuer Configuration

Ensure the ClusterIssuer is configured in your cluster:

```bash
kubectl get clusterissuer letsencrypt-prod -n value-fabric
```

### Step 2: Update ClusterIssuer Email

The hostname-config.yaml has been updated to use `security@valuepact.ai`. Ensure this email is valid for Let's Encrypt notifications.

### Step 3: Deploy with cert-manager

When you deploy the production stack, cert-manager will automatically:

1. Create a CertificateRequest for www.valuepact.ai
2. Request the certificate from Let's Encrypt
3. Handle ACME challenges via HTTP-01
4. Store certificates in Kubernetes secrets

## Clerk Authentication Configuration

### Step 1: Update Clerk Application

In your Clerk Dashboard, update the following:

**Allowed Origins:**

- https://www.valuepact.ai

**Redirect URLs:**

- After sign-in: https://www.valuepact.ai/workspaces
- After sign-up: https://www.valuepact.ai/onboarding

**JWT Template:** fabric4l-api

### Step 2: Configure Clerk Webhook

The canonical application edge intentionally exposes only `/api/v1` to the
gateway. Do not publish the internal webhook on a separate API host. Before
enabling Clerk webhooks, provision a separately reviewed webhook route on the
application host (with signature verification and dedicated rate limits) and
document that route in the edge contract.

Subscribe to events:

- user.created
- user.updated
- user.deleted
- organization.created
- organization.updated
- organization.deleted
- organizationMembership.created
- organizationMembership.updated
- organizationMembership.deleted

### Step 3: Update Infisical Secrets

Update the following Infisical secrets for production:

**Path: /shared/auth**

```
CLERK_ISSUER=https://accounts.valuepact.ai
CLERK_JWT_AUDIENCE=fabric4l-api
CLERK_AUTHORIZED_PARTIES=https://www.valuepact.ai
CLERK_JWKS_URL=https://accounts.valuepact.ai/.well-known/jwks.json
```

**Path: /api-gateway**

```
CLERK_SECRET_KEY=<your-clerk-secret-key>
CLERK_WEBHOOK_SECRET=<your-clerk-webhook-secret>
FABRIC_AUTH_SIGNING_KEY=<ed25519-private-pem>
FABRIC_AUTH_SIGNING_KID=gateway-k1
FABRIC_AUTH_PUBLIC_KEYS=<json-public-key-set>
```

**Path: /apps/web**

```
VITE_CLERK_PUBLISHABLE_KEY=<your-clerk-publishable-key>
VITE_AUTH_PROVIDER=clerk
```

## Kubernetes Deployment

### Step 1: Apply Production Configuration

```bash
# Using prod-nginx (recommended)
kubectl apply -k k8s/deployments/prod-nginx

# Or using prod-gateway-api
kubectl apply -k k8s/deployments/prod-gateway-api

# Or using prod-istio
kubectl apply -k k8s/deployments/prod-istio
```

### Step 2: Verify Ingress and Certificates

```bash
# Check Ingress resources
kubectl get ingress -n value-fabric

# Check Certificate resources
kubectl get certificate -n value-fabric

# Check CertificateRequest status
kubectl get certificaterequest -n value-fabric

# View certificate details
kubectl describe certificate www-valuepact-ai-tls -n value-fabric
```

### Step 3: Verify DNS Resolution

```bash
# Test from cluster
kubectl run -it --rm debug --image=busybox --restart=Never -- nslookup www.valuepact.ai

# Test from local machine
curl -I https://www.valuepact.ai
```

## Environment Variables

The following environment files have been updated:

- `.env.example` - Updated CLERK_AUTHORIZED_PARTIES to include www.valuepact.ai
- `k8s/deployments/prod-nginx/hostname-config.yaml` - Updated host to www.valuepact.ai
- `k8s/deployments/prod-gateway-api/hostname-config.yaml` - Updated host to www.valuepact.ai
- `k8s/deployments/prod-istio/hostname-config.yaml` - Updated host to www.valuepact.ai
- `docs/auth/clerk-configuration.md` - Updated documentation references

## Verification Checklist

- [ ] DNS records configured at Spaceship.com
- [ ] DNS propagation verified
- [ ] Load balancer IP obtained from Kubernetes
- [ ] ClusterIssuer configured for Let's Encrypt
- [ ] Clerk application updated with new domains
- [ ] Clerk webhook configured
- [ ] Infisical secrets updated for production
- [ ] Kubernetes deployment applied
- [ ] Ingress resources created
- [ ] Certificates issued successfully
- [ ] HTTPS accessible at https://www.valuepact.ai
- [ ] API returns JSON at https://www.valuepact.ai/api/v1/auth/health
- [ ] Authentication flow tested
- [ ] Health checks passing

## Troubleshooting

### Certificate Not Issuing

Check cert-manager logs:

```bash
kubectl logs -n cert-manager deployment/cert-manager
kubectl logs -n cert-manager deployment/cert-manager-webhook
```

Check CertificateRequest events:

```bash
kubectl describe certificaterequest <name> -n value-fabric
```

### DNS Not Resolving

- Verify DNS records are correct in Spaceship.com
- Check DNS propagation with `dig www.valuepact.ai`
- Ensure load balancer IP is correct

### Clerk Authentication Failing

- Verify JWKS URL is accessible: `curl https://accounts.valuepact.ai/.well-known/jwks.json`
- Check CLERK_AUTHORIZED_PARTIES includes correct domains
- Verify Clerk webhook is receiving events

## Production Deployment Command

Once DNS and certificates are configured, deploy the full stack:

```bash
# Using Infisical for secrets
infisical run --env=prod -- docker compose -f docker-compose.prod.yml up -d

# Or using Kubernetes
kubectl apply -k k8s/deployments/prod-nginx
```

## Monitoring

After deployment, monitor:

- Certificate expiry (cert-manager auto-renews 30 days before expiry)
- Ingress health
- SSL certificate status
- DNS resolution
- Clerk webhook delivery

## Security Notes

- Never commit .env files with production secrets
- Use Infisical for all production secrets
- Rotate Clerk keys regularly
- Monitor certificate expiry
- Keep cert-manager updated
- Enable security headers in Ingress
