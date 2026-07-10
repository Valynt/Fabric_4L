# Security Headers Specification — Fabric 4L

## Status: PRODUCTION-READY
## Version: 1.2.0
## Owner: Security Engineering

---

## 1. Header Reference Table

| Header | Production Value | Dev Value | OWASP Ref |
|--------|-----------------|-----------|-----------|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | `max-age=0` | [OWASP HSTS](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html) |
| `X-Content-Type-Options` | `nosniff` | `nosniff` | [OWASP MIME Sniffing](https://owasp.org/www-community/Security_Headers) |
| `X-Frame-Options` | `DENY` | `DENY` | [OWASP Clickjacking](https://cheatsheetseries.owasp.org/cheatsheets/Clickjacking_Defense_Cheat_Sheet.html) |
| `Content-Security-Policy` | (see §2) | `default-src 'self'; script-src 'self' 'unsafe-eval'; style-src 'self' 'unsafe-inline'` | [OWASP CSP](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | `strict-origin-when-cross-origin` | [W3C Referrer Policy](https://www.w3.org/TR/referrer-policy/) |
| `Permissions-Policy` | (see §3) | (see §3) | [W3C Permissions Policy](https://www.w3.org/TR/permissions-policy-1/) |
| `Cross-Origin-Embedder-Policy` | `require-corp` | `unsafe-none` | [MDN COEP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Embedder-Policy) |
| `Cross-Origin-Opener-Policy` | `same-origin` | `same-origin-allow-popups` | [MDN COOP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Opener-Policy) |
| `Cross-Origin-Resource-Policy` | `same-site` | `cross-origin` | [MDN CORP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cross-Origin-Resource-Policy) |

---

## 2. Content-Security-Policy Detail

### Production CSP

```http
Content-Security-Policy:
  default-src 'self';
  script-src 'self' 'nonce-{generated}';
  style-src 'self' 'nonce-{generated}';
  img-src 'self' data: https://cdn.fabric4l.dev;
  connect-src 'self' https://api.fabric4l.dev https://telemetry.fabric4l.dev wss://realtime.fabric4l.dev;
  font-src 'self' https://fonts.gstatic.com;
  media-src 'self';
  object-src 'none';
  frame-ancestors 'none';
  base-uri 'self';
  form-action 'self';
  upgrade-insecure-requests;
  report-uri https://security-report.fabric4l.dev/csp;
  report-to csp-group;
```

### Directive Breakdown

| Directive | Value | Justification |
|-----------|-------|---------------|
| `default-src` | `'self'` | Fallback — only same-origin by default |
| `script-src` | `'self' 'nonce-{generated}'` | No `unsafe-inline`; nonce-based inline script approval |
| `style-src` | `'self' 'nonce-{generated}'` | No `unsafe-inline`; nonce-based inline style approval |
| `img-src` | `'self' data: https://cdn.fabric4l.dev` | data: for inline SVG; CDN for static assets |
| `connect-src` | API + telemetry + WebSocket | Restricts XHR/fetch/WebSocket targets |
| `font-src` | `'self' https://fonts.gstatic.com` | Google Fonts CDN |
| `object-src` | `'none'` | Blocks Flash, Java applets, PDF plugins |
| `frame-ancestors` | `'none'` | Stricter than X-Frame-Options; no embedding |
| `base-uri` | `'self'` | Prevents base tag hijacking |
| `form-action` | `'self'` | Prevents form submission to external domains |
| `report-uri` | `https://security-report.fabric4l.dev/csp` | Centralized CSP violation reporting |

### CSP Nonce Generation

```python
import secrets

def generate_csp_nonce() -> str:
    """Generate a cryptographically random CSP nonce."""
    return secrets.token_urlsafe(16)  # 128 bits
```

The nonce must be:
1. Generated per-request (never cached)
2. Injected into the CSP header
3. Applied to all inline `<script>` and `<style>` tags via `nonce="..."` attribute
4. Minimum 128 bits of entropy

---

## 3. Permissions-Policy Detail

### Production

```http
Permissions-Policy:
  accelerometer=(),
  ambient-light-sensor=(),
  autoplay=(),
  battery=(),
  camera=(),
  display-capture=(),
  document-domain=(),
  encrypted-media=(),
  execution-while-not-rendered=(),
  execution-while-out-of-viewport=(),
  fullscreen=(self),
  geolocation=(),
  gyroscope=(),
  layout-animations=(self),
  legacy-image-formats=(self),
  magnetometer=(),
  microphone=(),
  midi=(),
  navigation-override=(),
  payment=(),
  picture-in-picture=(),
  publickey-credentials-get=(),
  speaker-selection=(),
  sync-xhr=(self),
  usb=(),
  web-share=(),
  xr-spatial-tracking=()
```

### Rationale

| Feature | Policy | Reason |
|---------|--------|--------|
| `camera` | `()` | Fabric 4L does not use camera; block to prevent abuse |
| `microphone` | `()` | Same as camera |
| `geolocation` | `()` | No location-based features |
| `payment` | `()` | No in-browser payment processing |
| `fullscreen` | `(self)` | Allow for document viewer only |
| `sync-xhr` | `(self)` | Required for some legacy upload flows; restrict to same-origin |

---

## 4. Response Header Example (Production)

```http
HTTP/2 200 OK
Date: Mon, 15 Jan 2024 09:23:47 GMT
Content-Type: application/json
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Content-Security-Policy: default-src 'self'; script-src 'self' 'nonce-aB3x9K...'; style-src 'self' 'nonce-aB3x9K...'; img-src 'self' data: https://cdn.fabric4l.dev; connect-src 'self' https://api.fabric4l.dev; frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'; upgrade-insecure-requests; report-uri https://security-report.fabric4l.dev/csp
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=()
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-site
X-Content-Security-Policy: ...
X-WebKit-CSP: ...
Cache-Control: no-store, private
```

---

## 5. Environment-Specific Behavior

### Production (`ENV=production`)

- All headers at strictest values
- CSP nonces enabled
- CSP report-only mode: OFF (enforce)
- HSTS preload enabled
- COEP: require-corp

### Staging (`ENV=staging`)

- Same as production
- CSP report-only mode: ON (violations logged but not blocked)
- HSTS: max-age=86400 (1 day, not preload)

### Development (`ENV=development`)

- HSTS: disabled (`max-age=0`)
- CSP relaxed: `'unsafe-eval'` allowed (for React devtools)
- COEP: `unsafe-none`
- COOP: `same-origin-allow-popups`
- CORP: `cross-origin`

### Testing (`ENV=test`)

- Headers explicitly set to production values
- CSP nonces deterministic (for snapshot testing)

---

## 6. Per-Endpoint Overrides

Certain endpoints require header relaxation:

| Endpoint | Override | Reason |
|----------|----------|--------|
| `/health` | No security headers | Load balancer health checks |
| `/metrics` | No security headers | Prometheus scraping |
| `/api/v1/embed` | `X-Frame-Options: SAMEORIGIN` | Embedded widget |
| `/api/v1/export/*` | `Content-Disposition: attachment` | File downloads |
| `/static/*` | CORP: `cross-origin` | CDN serving |

---

## 7. Testing Requirements

1. **Header presence**: Every response must include all 9 headers
2. **Value accuracy**: Values must match this specification exactly
3. **Environment variance**: Dev headers ≠ Prod headers
4. **Nonce freshness**: CSP nonce must differ per-request
5. **Override compliance**: Per-endpoint overrides must apply correctly

See `tests/security/test_security_headers.py` for automated validation.

---

## 8. Compliance Mapping

| Regulation | Requirement | Header Coverage |
|------------|-------------|-----------------|
| GDPR Art. 32 | Security of processing | HSTS, CSP, COEP, COOP |
| GDPR Art. 25 | Data protection by design | Permissions-Policy |
| SOC 2 CC6.6 | Security infrastructure | All headers |
| OWASP ASVS V14 | Configuration | Full spec compliance |

---

## 9. References

- [OWASP Secure Headers Project](https://owasp.org/www-project-secure-headers/)
- [OWASP CSP Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Content_Security_Policy_Cheat_Sheet.html)
- [Mozilla Web Security Guidelines](https://infosec.mozilla.org/guidelines/web_security)
- [W3C Permissions Policy](https://www.w3.org/TR/permissions-policy-1/)
- [MDN Security Headers](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers#security)
