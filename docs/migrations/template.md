# Migration Guide Template

Use this template for all future version migration guides. Copy this file, replace all `{{placeholders}}`, and fill in the relevant sections.

---

```markdown
# Migrating from v{{SOURCE_VERSION}} to v{{TARGET_VERSION}}

**Target Version:** v{{TARGET_VERSION}}  
**Source Version:** v{{SOURCE_VERSION}} (last: v{{SOURCE_VERSION_LAST}})  
**Estimated Effort:** {{ESTIMATED_EFFORT}}  
**Risk Level:** {{RISK_LEVEL}} — Low / Medium / High / Critical  
**Release Date:** {{RELEASE_DATE}}

---

## Summary of Changes

{{1-2 paragraph summary of what this release introduces, changes, and removes.}}

### New Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/{{new-endpoint}}` | `{{METHOD}}` | {{Description}} |

### Modified Endpoints

| Endpoint | Change | Details |
|----------|--------|---------|
| `/api/v1/{{modified-endpoint}}` | {{Change type}} | {{Details}} |

### Deprecated Endpoints

| Endpoint | Replacement | Removal Target |
|----------|-------------|----------------|
| `/api/v1/{{deprecated-endpoint}}` | `/api/v1/{{replacement}}` | v{{REMOVAL_VERSION}} |

### Removed Endpoints

| Endpoint | Removal Reason | Migration Path |
|----------|----------------|----------------|
| `/api/v1/{{removed-endpoint}}` | {{Reason}} | Use `/api/v1/{{alternative}}` |

---

## Breaking Changes

### BC-1: {{Breaking Change Title}}

**Before (v{{SOURCE_VERSION}}):**
```{{language}}
{{Code showing old behavior}}
```

**After (v{{TARGET_VERSION}}):**
```{{language}}
{{Code showing new behavior}}
```

**Migration:**
{{Step-by-step migration instructions.}}

---

## Step-by-Step Migration Checklist

### Phase 1: Preparation ({{Estimated time}})

- [ ] **Read release notes** — `cat RELEASE_NOTES_v{{TARGET_VERSION}}.md`
- [ ] **Review breaking changes** — Confirm all BC items are understood
- [ ] **Backup database** — `pg_dump fabric4l > fabric4l-v{{SOURCE_VERSION}}-backup-$(date +%Y%m%d).sql`
- [ ] **Backup configuration** — `cp .env .env.v{{SOURCE_VERSION}}-backup`
- [ ] **Run compatibility check** — `python scripts/migrations/v{{SOURCE_VERSION}}-to-v{{TARGET_VERSION}}/check-compatibility.py`
- [ ] **Schedule maintenance window** — Estimated {{downtime}} minutes downtime

### Phase 2: Environment & Configuration ({{Estimated time}})

- [ ] **Pull v{{TARGET_VERSION}} code** — `git fetch origin && git checkout v{{TARGET_VERSION}}`
- [ ] **Install dependencies** — `pip install -r requirements.txt`
- [ ] **Update environment variables** (see table below)

### Phase 3: Database Migration ({{Estimated time}})

- [ ] **Run migrations** — `make migrate` or `alembic upgrade head`
- [ ] **Verify migration success** — `alembic current` should show latest revision

### Phase 4: Code Migration ({{Estimated time}})

- [ ] **Update API clients** — {{Specific changes}}
- [ ] **Update response handling** — {{Specific changes}}
- [ ] **Remove deprecated usage** — {{Specific changes}}

### Phase 5: Validation ({{Estimated time}})

- [ ] **Run full test suite** — `make test`
- [ ] **Run integration tests** — `make test-integration`
- [ ] **Verify API docs** — Check `/api/docs`
- [ ] **Monitor dashboards** — Watch error rates and latency

### Phase 6: Production Deployment ({{Estimated time}})

- [ ] **Deploy to staging** — `make deploy-staging`
- [ ] **Run smoke tests** — `make smoke-test`
- [ ] **Deploy to production** — `make deploy-production`
- [ ] **Verify health** — `curl /api/v1/health/detailed | jq '.status'`
- [ ] **Monitor for 24 hours** — Watch dashboards and alert channels

---

## Environment Variable Changes

### New Required Variables

| Variable | Example | Description |
|----------|---------|-------------|
| `{{NEW_VAR}}` | `{{example}}` | {{Description}} |

### New Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `{{NEW_OPTIONAL_VAR}}` | `{{default}}` | {{Description}} |

### Changed Variables

| Variable | Old Default | New Default | Notes |
|----------|-------------|-------------|-------|
| `{{CHANGED_VAR}}` | `{{old}}` | `{{new}}` | {{Notes}} |

### Removed Variables

| Variable | Reason |
|----------|--------|
| `{{REMOVED_VAR}}` | {{Reason}} |

---

## Code Examples

### Python SDK

**Before (v{{SOURCE_VERSION}}):**
```python
from fabric4l import FabricClient

client = FabricClient({{old_config}})
{{old_usage}}
```

**After (v{{TARGET_VERSION}}):**
```python
from fabric4l import FabricClient

client = FabricClient({{new_config}})
{{new_usage}}
```

### JavaScript/TypeScript SDK

**Before (v{{SOURCE_VERSION}}):**
```typescript
import { FabricClient } from '@fabric4l/sdk';

const client = new FabricClient({{old_config}});
{{old_usage}}
```

**After (v{{TARGET_VERSION}}):**
```typescript
import { FabricClient } from '@fabric4l/sdk';

const client = new FabricClient({{new_config}});
{{new_usage}}
```

### cURL Examples

**Before (v{{SOURCE_VERSION}}):**
```bash
{{old_curl}}
```

**After (v{{TARGET_VERSION}}):**
```bash
{{new_curl}}
```

---

## Rollback Procedure

If migration fails, rollback to v{{SOURCE_VERSION}}:

```bash
# 1. Stop services
docker compose down

# 2. Restore database
psql fabric4l < fabric4l-v{{SOURCE_VERSION}}-backup-$(date +%Y%m%d).sql

# 3. Restore configuration
cp .env.v{{SOURCE_VERSION}}-backup .env

# 4. Checkout v{{SOURCE_VERSION}} code
git checkout v{{SOURCE_VERSION_LAST}}

# 5. Start services
docker compose -f infra/compose/docker-compose.prod.yml up -d

# 6. Verify rollback
curl http://localhost:8001/api/v1/health/detailed | jq '.status'
```

---

## Troubleshooting

### "{{Error message}}"

**Cause:** {{Root cause}}  
**Fix:**
```bash
{{Fix commands}}
```

---

## Support

- **GitHub Issues:** [bmsull560/Fabric_4L/issues](https://github.com/bmsull560/Fabric_4L/issues)  
- **Migration Discussion:** [GitHub Discussions #migrations](https://github.com/bmsull560/Fabric_4L/discussions/categories/migrations)  
- **Emergency Contact:** operations@fabric4l.io
```

---

## Checklist for Migration Guide Author

Before publishing a migration guide, verify:

- [ ] All breaking changes have before/after code examples
- [ ] Environment variable changes are complete
- [ ] Migration checklist is ordered and time-estimated
- [ ] Rollback procedure is tested
- [ ] Troubleshooting covers the top 3-5 expected issues
- [ ] SDK examples are provided for Python and TypeScript
- [ ] cURL examples work when copy-pasted
- [ ] Validation commands are included
- [ ] Links to full release notes and ADRs are provided
- [ ] The guide follows this template structure

---

## Version History for This Template

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-07-14 | Initial template for v1.2.0 release |
