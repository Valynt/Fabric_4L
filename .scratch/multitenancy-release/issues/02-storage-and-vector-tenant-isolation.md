# 02: Object Storage and Vector Namespace Adversarial Isolation Harness

**What to build:**
Implement and enforce end-to-end hostile verification across file/object storage and vector retrieval stores. Ensure pre-signed URL generation and vector similarity queries strictly enforce tenant key path prefixes (`{tenant_id}/*`) and dedicated vector collection namespaces, failing closed against cross-tenant data exfiltration attempts.

**Blocked by:** None (can start immediately)

**Status:** ready-for-agent

- [x] File/object storage service rejects pre-signed URL generation or direct read/write requests targeting another tenant's key prefix.
- [x] Vector retrieval layer (pgvector / vector search) injects mandatory tenant filters into all top-k nearest neighbor queries.
- [x] Hostile adversarial tests prove Tenant A cannot retrieve embeddings or documents belonging to Tenant B under simulated key traversal or unbounded search.
