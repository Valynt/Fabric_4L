# Layer 1 Security & Tenancy Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove hardcoded MinIO credentials from Layer 1 and enforce explicit tenant filtering in crawl-decision queries.

**Architecture:** Move MinIO secrets to environment-only configuration and fail closed at startup when they are missing. Add defense-in-depth `tenant_id` predicates to `CrawlDecisionRepository` so it no longer relies solely on RLS.

**Tech Stack:** Python 3.12, Pydantic v2 Settings, SQLAlchemy, Docker Compose.

---

## Task 1: Remove hardcoded MinIO credentials

**Files:**
- Modify: `services/layer1-ingestion/src/layer1_ingestion/shared/config.py`
- Modify: `services/layer1-ingestion/src/shared/config.py`
- Modify: `services/layer1-ingestion/docker-compose.yml`
- Modify: `docker-compose.dev.yml`
- Modify: `docker-compose.backend-integrated.yml`
- Modify: `.env.example`
- Test: `services/layer1-ingestion/tests/test_config_secrets.py` (create)

- [ ] **Step 1: Write the failing test**

Create `services/layer1-ingestion/tests/test_config_secrets.py`:

```python
import os

import pytest
from pydantic import ValidationError

from layer1_ingestion.shared.config import Settings


class TestMinIOSecrets:
    def test_missing_s3_access_key_raises(self, monkeypatch):
        monkeypatch.setenv("LAYER1_S3_ACCESS_KEY", "")
        monkeypatch.setenv("LAYER1_S3_SECRET_KEY", "")
        with pytest.raises(ValidationError):
            Settings()

    def test_explicit_credentials_are_accepted(self, monkeypatch):
        monkeypatch.setenv("LAYER1_S3_ACCESS_KEY", "test-key")
        monkeypatch.setenv("LAYER1_S3_SECRET_KEY", "test-secret")
        settings = Settings()
        assert settings.s3_access_key == "test-key"
        assert settings.s3_secret_key == "test-secret"
```

- [ ] **Step 2: Run the test to confirm it fails**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer1-ingestion
python -m pytest tests/test_config_secrets.py -v
```

Expected: `test_missing_s3_access_key_raises` FAILS because defaults still exist.

- [ ] **Step 3: Remove hardcoded defaults from the canonical config**

Modify `services/layer1-ingestion/src/layer1_ingestion/shared/config.py` (lines 259–262):

```python
    # Storage (MinIO/S3)
    s3_endpoint: str = Field(default="http://localhost:9000", description="S3/MinIO endpoint")
    s3_access_key: str = Field(description="S3 access key (required)")
    s3_secret_key: str = Field(description="S3 secret key (required)")
    s3_bucket: str = Field(default="layer1-raw-html", description="S3 bucket for raw HTML")
    s3_region: str = Field(default="us-east-1", description="S3 region")
```

- [ ] **Step 4: Remove hardcoded defaults from the legacy/compat config**

Modify `services/layer1-ingestion/src/shared/config.py` with the same change (lines 259–262):

```python
    # Storage (MinIO/S3)
    s3_endpoint: str = Field(default="http://localhost:9000", description="S3/MinIO endpoint")
    s3_access_key: str = Field(description="S3 access key (required)")
    s3_secret_key: str = Field(description="S3 secret key (required)")
    s3_bucket: str = Field(default="layer1-raw-html", description="S3 bucket for raw HTML")
    s3_region: str = Field(default="us-east-1", description="S3 region")
```

- [ ] **Step 5: Update `.env.example` with local-only MinIO defaults**

Append or update in `.env.example`:

```bash
# MinIO local dev credentials — DO NOT USE IN PRODUCTION
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Layer 1 S3/MinIO credentials — local dev only
LAYER1_S3_ACCESS_KEY=minioadmin
LAYER1_S3_SECRET_KEY=minioadmin
```

- [ ] **Step 6: Replace literals in `services/layer1-ingestion/docker-compose.yml`**

Before (example lines):

```yaml
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
```

After:

```yaml
      MINIO_ROOT_USER: ${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}
```

Before:

```yaml
      /usr/bin/mc config host add myminio http://minio:9000 minioadmin minioadmin;
```

After:

```yaml
      /usr/bin/mc config host add myminio http://minio:9000 $${MINIO_ROOT_USER:?} $${MINIO_ROOT_PASSWORD:?};
```

Before:

```yaml
      LAYER1_S3_ACCESS_KEY: minioadmin
      LAYER1_S3_SECRET_KEY: minioadmin
```

After (in both the worker and api service blocks):

```yaml
      LAYER1_S3_ACCESS_KEY: ${LAYER1_S3_ACCESS_KEY:?LAYER1_S3_ACCESS_KEY is required}
      LAYER1_S3_SECRET_KEY: ${LAYER1_S3_SECRET_KEY:?LAYER1_S3_SECRET_KEY is required}
```

- [ ] **Step 7: Replace literals in `docker-compose.dev.yml`**

Before:

```yaml
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
```

After:

```yaml
      - MINIO_ROOT_USER=${MINIO_ROOT_USER:?MINIO_ROOT_USER is required}
      - MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD:?MINIO_ROOT_PASSWORD is required}
```

- [ ] **Step 8: Replace literals in `docker-compose.backend-integrated.yml`**

Apply the same substitutions as Step 6 for the Layer 1 service and MinIO service blocks.

- [ ] **Step 9: Validate compose files still parse**

```bash
cd /home/bunnyshell/Fabric_4L
set -a && source .env.example && set +a
docker compose -f docker-compose.dev.yml config > /dev/null
docker compose -f docker-compose.backend-integrated.yml config > /dev/null
docker compose -f services/layer1-ingestion/docker-compose.yml config > /dev/null
```

Expected: no errors.

- [ ] **Step 10: Run the config tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer1-ingestion
python -m pytest tests/test_config_secrets.py -v
```

Expected: PASS.

- [ ] **Step 11: Run Layer 1 tests**

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer1
```

Expected: PASS (with env vars set).

- [ ] **Step 12: Commit**

```bash
git add services/layer1-ingestion/src/layer1_ingestion/shared/config.py \
        services/layer1-ingestion/src/shared/config.py \
        services/layer1-ingestion/docker-compose.yml \
        docker-compose.dev.yml \
        docker-compose.backend-integrated.yml \
        services/layer1-ingestion/tests/test_config_secrets.py \
        .env.example
git commit -m "security: remove hardcoded MinIO credentials from Layer 1"
```

---

## Task 2: Enforce explicit tenant filters in `CrawlDecisionRepository`

**Files:**
- Modify: `services/layer1-ingestion/src/layer1_ingestion/crawler/decision_store.py`
- Test: `services/layer1-ingestion/tests/test_crawl_decision_tenant_isolation.py` (create)

- [ ] **Step 1: Find current callers**

```bash
cd /home/bunnyshell/Fabric_4L
grep -R "CrawlDecisionRepository\|decision_store\.get_by" services/layer1-ingestion/src --include="*.py" -n
```

Record every call site; each must be updated to pass `tenant_id`.

- [ ] **Step 2: Write the failing tenant-isolation test**

Create `services/layer1-ingestion/tests/test_crawl_decision_tenant_isolation.py`:

```python
import uuid
from datetime import datetime, timezone

import pytest

from layer1_ingestion.crawler.decision_store import CrawlDecisionRepository
from layer1_ingestion.crawler.models import CrawlDecisionRecord


@pytest.fixture
def repo():
    return CrawlDecisionRepository()


@pytest.fixture
def tenant_a_record():
    return CrawlDecisionRecord(
        decision_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        url="https://example-a.com/page",
        domain="example-a.com",
        final_path="/page",
        decision="crawl",
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def tenant_b_record():
    return CrawlDecisionRecord(
        decision_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        url="https://example-b.com/page",
        domain="example-b.com",
        final_path="/page",
        decision="skip",
        created_at=datetime.now(timezone.utc),
    )


def test_get_by_id_requires_tenant(repo):
    with pytest.raises(TypeError):
        repo.get_by_id_sync(str(uuid.uuid4()))
```

(Use the existing test database fixture in this repo instead of direct sync calls if one exists; the test above is a placeholder to force the signature change.)

- [ ] **Step 3: Add `tenant_id` to repository methods**

Modify `services/layer1-ingestion/src/layer1_ingestion/crawler/decision_store.py`:

```python
    def _get_by_id_sync(self, decision_id: str, tenant_id: str) -> CrawlDecisionRecord | None:
        """Synchronous get by ID implementation."""
        with self._get_session() as session:
            db_record = session.get(CrawlDecisionModel, UUID(decision_id))
            if not db_record or str(db_record.tenant_id) != tenant_id:
                return None
            return self._to_record(db_record)

    async def get_by_id(self, decision_id: str, tenant_id: str) -> CrawlDecisionRecord | None:
        return await asyncio.to_thread(self._get_by_id_sync, decision_id, tenant_id)

    def _get_by_job_sync(
        self,
        job_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CrawlDecisionRecord]:
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.job_id == UUID(job_id))
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
                .order_by(CrawlDecisionModel.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_by_job(
        self,
        job_id: str,
        tenant_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list[CrawlDecisionRecord]:
        return await asyncio.to_thread(self._get_by_job_sync, job_id, tenant_id, limit, offset)

    def _get_by_url_sync(self, url: str, tenant_id: str, limit: int = 100) -> list[CrawlDecisionRecord]:
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.url == url)
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
                .order_by(CrawlDecisionModel.created_at.desc())
                .limit(limit)
            )
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_by_url(self, url: str, tenant_id: str, limit: int = 100) -> list[CrawlDecisionRecord]:
        return await asyncio.to_thread(self._get_by_url_sync, url, tenant_id, limit)

    def _get_by_domain_sync(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[CrawlDecisionRecord]:
        with self._get_session() as session:
            stmt = (
                select(CrawlDecisionModel)
                .where(CrawlDecisionModel.domain == domain)
                .where(CrawlDecisionModel.tenant_id == UUID(tenant_id))
            )
            if since:
                stmt = stmt.where(CrawlDecisionModel.created_at >= since)
            stmt = stmt.order_by(CrawlDecisionModel.created_at.desc()).limit(limit)
            db_records = session.execute(stmt).scalars().all()
            return [self._to_record(r) for r in db_records]

    async def get_by_domain(
        self,
        domain: str,
        tenant_id: str,
        since: datetime | None = None,
        limit: int = 1000,
    ) -> list[CrawlDecisionRecord]:
        return await asyncio.to_thread(self._get_by_domain_sync, domain, tenant_id, since, limit)
```

Also add `tenant_id` to any `list`, `save`, or helper methods that expose decision records.

- [ ] **Step 4: Update all callers**

For every call site found in Step 1, pass the authenticated `tenant_id` from request context. Example pattern:

```python
ctx = get_request_context()
record = await repo.get_by_id(decision_id, tenant_id=str(ctx.tenant_id))
```

If a call site cannot obtain tenant context, fail closed and do not call the repository.

- [ ] **Step 5: Run the repository tests**

```bash
cd /home/bunnyshell/Fabric_4L/services/layer1-ingestion
python -m pytest tests -k decision -v
```

Expected: PASS.

- [ ] **Step 6: Run Layer 1 tests**

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer1
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add services/layer1-ingestion/src/layer1_ingestion/crawler/decision_store.py \
        services/layer1-ingestion/tests/test_crawl_decision_tenant_isolation.py \
        $(git status --short | grep -E "^ M services/layer1-ingestion/src/.*\.py$" | awk '{print $2}')
git commit -m "tenancy: add explicit tenant_id filters to CrawlDecisionRepository"
```

---

## Task 3: Final verification for this plan

- [ ] Run the Layer 1 test suite end-to-end:

```bash
cd /home/bunnyshell/Fabric_4L
make test-layer1
```

Expected: PASS.
