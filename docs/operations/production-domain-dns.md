# Production Domain DNS Runbook

This runbook records the production DNS plan for the Value Fabric public domain
purchased through Spaceship.com.

## Domain inventory

| Purpose                                         | Hostname                | Source of truth                                                                                                                                               |
| ----------------------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Production application (frontend and `/api/v1`) | `www.valuepact.ai`      | `k8s/deployments/prod-nginx/hostname-config.yaml`, `k8s/deployments/prod-istio/hostname-config.yaml`, `k8s/deployments/prod-gateway-api/hostname-config.yaml` |
| Authentication issuer / Clerk custom domain     | `accounts.valuepact.ai` | Clerk production dashboard and Infisical `CLERK_*` secrets                                                                                                    |
| Optional application alias                      | `app.valuepact.ai`      | Reserve for future product app routing; do not point at production until the ingress host is explicitly added.                                                |
| Apex landing redirect                           | `valuepact.ai`          | Registrar/DNS redirect to `https://www.valuepact.ai`, or an A/ALIAS record if the edge provider supports apex hosting.                                        |

## Spaceship DNS records to create

Use the Spaceship Advanced DNS UI or API for `valuepact.ai`. Do not commit
provider validation tokens, mail-provider DKIM values, load-balancer IPs, or
other deployment-specific secrets to this repository.

| Type                                       | Host / name       | Value                                                                      | Notes                                                                                                                |
| ------------------------------------------ | ----------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `A` / `AAAA` or provider-supported `ALIAS` | `www`             | External IP(s) or canonical target of the production ingress/load balancer | Required before cert-manager can validate the application host serving both the frontend and `/api/v1`.              |
| `CNAME`                                    | `accounts`        | Clerk custom-domain target from the production Clerk dashboard             | Clerk owns the exact target and any verification records.                                                            |
| `A`, `ALIAS`, or URL redirect              | `@`               | Redirect or edge target for `https://www.valuepact.ai`                     | Prefer an HTTPS redirect to the `www` canonical host unless the chosen edge provider supports apex hosting directly. |
| `CAA`                                      | `@`               | `0 issue "letsencrypt.org"`                                                | Allows cert-manager's Let's Encrypt issuers to request certificates for the domain.                                  |
| `TXT`                                      | `@`               | Provider verification records                                              | Add only the records requested by Clerk, email, observability, or hosting providers.                                 |
| `MX` / `TXT` / `CNAME`                     | provider-specific | Email provider values                                                      | Add SPF, DKIM, and DMARC before sending mail from `valuepact.ai`.                                                    |

## Email baseline

Before using `valuepact.ai` for product or support email, configure these DNS
controls with the selected mail provider:

- SPF `TXT` at `@` that authorizes only the chosen sender(s).
- DKIM `TXT` or `CNAME` records exactly as issued by the mail provider.
- DMARC `TXT` at `_dmarc` with at least `p=none` during monitoring, then move
  toward quarantine or reject after alignment is verified.

## Deployment alignment checklist

- [ ] `www.valuepact.ai` resolves to the selected production ingress controller.
- [ ] `accounts.valuepact.ai` is verified in the production Clerk application.
- [ ] Clerk allowed origins include `https://www.valuepact.ai`.
- [ ] Clerk authorized parties include `https://www.valuepact.ai` and `https://app.valuepact.ai` only if the app alias is enabled.
- [ ] OAuth redirect URL is `https://www.valuepact.ai/oauth2/callback` for the default `prod-nginx` path.
- [ ] CORS origins in production secrets include `https://www.valuepact.ai` and exclude localhost.
- [ ] DNSSEC is enabled or explicitly tracked as a production-readiness exception.
- [ ] Certificate issuance has completed for the application host.

## Validation commands

Run after DNS changes propagate and the production overlay is applied:

```bash
# Render the default production ingress overlay.
kustomize build k8s/deployments/prod-nginx | kubeconform -strict -summary -

# Confirm public DNS resolution.
dig +short www.valuepact.ai
dig +short accounts.valuepact.ai

# Confirm frontend HTTPS and API gateway routing on the same host.
curl -I https://www.valuepact.ai
python scripts/ci/production_edge_smoke.py --base-url https://www.valuepact.ai

# Inspect cert-manager state in-cluster.
kubectl -n value-fabric get certificate
kubectl -n value-fabric describe certificate frontend-tls
```

## External references

- [Spaceship DNS records API](https://docs.spaceship.dev/) — documents DNS record management permissions, supported record types, and `@` apex record naming.
- [Spaceship domain connection knowledge base](https://www.spaceship.com/en-GB/knowledgebase/connect-domain-to-spaceship-hosting/) — notes that `@` represents the bare domain, that `www` can be configured with a CNAME, and that DNS propagation can take up to 48 hours.

## Registrar notes

Spaceship's DNS API models `@` as the apex host/name and supports DNS record
management for existing domains. Spaceship's customer documentation also notes
that DNS management for Spaceship products is automatic when using Spaceship
nameservers, but this deployment should keep the production ingress IP/CNAME,
Clerk verification, and email records explicit so GitOps/Kubernetes routing and
external provider verification remain auditable.
