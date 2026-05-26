# Embedding Dimension Migration Strategy

When changing `EMBEDDING_DIMENSION` (for example from `384` to `1536`), do **not** reuse old vector indexes silently.

## Required cutover flow

1. **Add parallel property and indexes**
   - Add `embedding_v2` node property.
   - Create parallel vector indexes (`*_embedding_v2_idx`) with the new dimension.
2. **Backfill**
   - Re-embed all eligible entities into `embedding_v2` using the new adapter/model.
3. **Dual-read validation**
   - Compare retrieval quality and query correctness between old and new indexes.
4. **Cut over writes/reads**
   - Switch writes to `embedding_v2`.
   - Switch query paths to new index names.
5. **Cleanup**
   - Remove legacy `embedding` indexes and optionally the legacy property after rollback window.

## Runtime guardrails

- Startup fails if configured dimension and adapter dimension disagree.
- Schema initialization fails if existing Neo4j vector indexes have a different dimension from `EMBEDDING_DIMENSION`.
