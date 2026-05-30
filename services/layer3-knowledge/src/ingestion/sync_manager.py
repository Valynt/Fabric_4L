"""Sync manager for handling incremental updates from Layer 2."""

import hashlib
import logging
from datetime import datetime
from typing import Any

from neo4j import AsyncDriver
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..config import Settings, get_settings
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
=======
from ..db.audited_mutation import AuditedGraphMutation
>>>>>>> theirs
=======
from ..db.audited_mutation import AuditedGraphMutation
>>>>>>> theirs
=======
from ..db.audited_mutation import AuditedGraphMutation
>>>>>>> theirs
from ..db.query_execution import run_validated_query
from ..ingestion.neo4j_loader import (
    Neo4jLoader,
    RDFLoadError,
    validate_ingestion_tenant_id,
)


class SyncManager_sync_extraction_resultResult(TypedDictModel):
    reason: str
    source_id: Any
    status: str

class SyncManager_get_sync_statusResult(TypedDictModel):
    content_hash: Any
    error: Any
    last_extraction_job_id: Any
    source_id: Any
    status: Any
    synced_at: Any
    tenant_id: Any

logger = logging.getLogger(__name__)


class SyncConflictError(Exception):
    """Raised when a sync conflict is detected."""

    pass


class SyncManager:
    """Manage incremental synchronization from Layer 2 extraction pipeline.

    Handles:
    - Change detection based on content hash
    - Incremental updates (add/modify/delete)
    - Conflict resolution for concurrent updates
    - Sync state tracking
    """

    def __init__(
        self,
        loader: Neo4jLoader | None = None,
        driver: AsyncDriver | None = None,
        settings: Settings | None = None,
    ):
        """Initialize sync manager.

        Args:
            loader: Neo4jLoader instance. If None, creates new one.
            driver: Neo4j async driver
            settings: Application settings
        """
        self.settings = settings or get_settings()
        self.loader = loader or Neo4jLoader(driver=driver, settings=self.settings)

    async def close(self) -> None:
        """Close resources."""
        await self.loader.close()

    async def sync_extraction_result(
        self,
        rdf_data: str,
        source_id: str,
        extraction_job_id: str,
        content_hash: str | None = None,
        force_full_sync: bool = False,
        tenant_id: str | None = None,
    ) -> dict:
        """Synchronize an extraction result from Layer 2.

        Args:
            rdf_data: RDF/Turtle string from Layer 2
            source_id: Unique identifier for the source document
            extraction_job_id: ID of the extraction job
            content_hash: Hash of the content for change detection
            force_full_sync: If True, performs full reload regardless of hash
            tenant_id: Validated tenant UUID for data isolation

        Returns:
            Dictionary with sync statistics
        """
        start_time = datetime.utcnow()
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)

        # Compute content hash if not provided
        if content_hash is None:
            content_hash = self._compute_hash(rdf_data)

        # Check if sync is needed
        if not force_full_sync:
            existing_hash = await self._get_source_hash(source_id, tenant_id=validated_tenant_id)
            if existing_hash == content_hash:
                logger.info(f"Source {source_id} unchanged, skipping sync")
                return SyncManager_sync_extraction_resultResult.model_validate({
                    "status": "skipped",
                    "reason": "content_unchanged",
                    "source_id": source_id,
                })


        # Perform sync
        stats = {
            "status": "synced",
            "source_id": source_id,
            "extraction_job_id": extraction_job_id,
            "content_hash": content_hash,
            "sync_type": "full" if force_full_sync else "incremental",
            "started_at": start_time.isoformat(),
        }

        try:
            # For incremental syncs, we'd compare and only update changed entities
            # For now, we do a full delete and reload for simplicity
            if force_full_sync:
                # Delete existing data from this source
                delete_stats = await self.loader.delete_by_source(
                    source_id, tenant_id=validated_tenant_id
                )
                stats["deleted"] = delete_stats

            # Load new data with tenant isolation
            load_stats = await self.loader.load_turtle_string(
                rdf_data,
                source_id=source_id,
                extraction_job_id=extraction_job_id,
                tenant_id=validated_tenant_id,
            )
            stats.update(load_stats)

            # Update sync metadata
            await self._update_sync_metadata(
                source_id,
                extraction_job_id,
                content_hash,
                "success",
                tenant_id=validated_tenant_id,
            )

            stats["completed_at"] = datetime.utcnow().isoformat()
            stats["duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()

            logger.info(
                f"Successfully synced source {source_id} "
                f"({stats.get('entities_loaded', 0)} entities, "
                f"{stats.get('relationships_loaded', 0)} relationships)"
            )

        except RDFLoadError as e:
            stats["status"] = "failed"
            stats["error"] = repr(e)
            await self._update_sync_metadata(
                source_id,
                extraction_job_id,
                content_hash,
                "failed",
                repr(e),
                tenant_id=validated_tenant_id,
            )
            raise

        return stats

    async def get_sync_status(self, source_id: str, tenant_id: str | None) -> dict | None:
        """Get synchronization status for a source.

        Args:
            source_id: Source document ID
            tenant_id: Tenant context required for metadata isolation

        Returns:
            Sync status dictionary or None if not found
        """
        tenant_id = validate_ingestion_tenant_id(tenant_id)
        driver = await self.loader._get_driver()

        async with driver.session(database=self.settings.neo4j_database) as session:
            result = await run_validated_query(
                session,
                """
                MATCH (s:SyncMetadata {source_id: $source_id, tenant_id: $tenant_id})
                RETURN s
                ORDER BY s.synced_at DESC
                LIMIT 1
                """,
                {"source_id": source_id, "tenant_id": tenant_id},
                tenant_id=tenant_id,
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
                query_name="sync_manager.get_sync_status",
=======
                query_name="sync_manager_get_sync_status",
>>>>>>> theirs
=======
                query_name="sync_manager_get_sync_status",
>>>>>>> theirs
=======
                query_name="sync_manager_get_sync_status",
>>>>>>> theirs
            )
            record = await result.single()

            if record:
                node = record["s"]
                return SyncManager_get_sync_statusResult.model_validate({
                    "source_id": node["source_id"],
                    "last_extraction_job_id": node.get("extraction_job_id"),
                    "content_hash": node.get("content_hash"),
                    "synced_at": node.get("synced_at"),
                    "status": node.get("status"),
                    "error": node.get("error"),
                    "tenant_id": node.get("tenant_id"),
                })


            return None

    async def list_synced_sources(self, tenant_id: str | None) -> list[dict]:
        """List all sources that have been synchronized.

        Args:
            tenant_id: Tenant context required for metadata isolation

        Returns:
            List of sync status dictionaries
        """
        tenant_id = validate_ingestion_tenant_id(tenant_id)
        driver = await self.loader._get_driver()
        sources = []

        async with driver.session(database=self.settings.neo4j_database) as session:
            result = await run_validated_query(
                session,
                """
                MATCH (s:SyncMetadata {tenant_id: $tenant_id})
                WITH s.source_id as source_id, max(s.synced_at) as latest
                MATCH (s:SyncMetadata {source_id: source_id, tenant_id: $tenant_id, synced_at: latest})
                RETURN s
                ORDER BY s.synced_at DESC
                """,
                {"tenant_id": tenant_id},
                tenant_id=tenant_id,
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
                query_name="sync_manager.list_synced_sources",
=======
                query_name="sync_manager_list_synced_sources",
>>>>>>> theirs
=======
                query_name="sync_manager_list_synced_sources",
>>>>>>> theirs
=======
                query_name="sync_manager_list_synced_sources",
>>>>>>> theirs
            )

            async for record in result:
                node = record["s"]
                sources.append(
                    {
                        "source_id": node["source_id"],
                        "last_extraction_job_id": node.get("extraction_job_id"),
                        "content_hash": node.get("content_hash"),
                        "synced_at": node.get("synced_at"),
                        "status": node.get("status"),
                        "tenant_id": node.get("tenant_id"),
                    }
                )

        return sources

    async def delete_source(self, source_id: str, tenant_id: str | None) -> dict:
        """Delete all data from a source and its sync metadata.

        Args:
            source_id: Source document ID
            tenant_id: Validated tenant UUID for deletion scope

        Returns:
            Deletion statistics
        """
        validated_tenant_id = validate_ingestion_tenant_id(tenant_id)
        # Delete entities and relationships
        stats = await self.loader.delete_by_source(source_id, tenant_id=validated_tenant_id)

        # Delete sync metadata
        driver = await self.loader._get_driver()
        async with driver.session(database=self.settings.neo4j_database) as session:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
            await run_validated_query(
=======
            result = await run_validated_query(
>>>>>>> theirs
=======
            result = await run_validated_query(
>>>>>>> theirs
=======
            result = await run_validated_query(
>>>>>>> theirs
                session,
                """
                MATCH (s:SyncMetadata {source_id: $source_id, tenant_id: $tenant_id})
                DELETE s
                RETURN count(s) as deleted
                """,
                {"source_id": source_id, "tenant_id": validated_tenant_id},
                tenant_id=validated_tenant_id,
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
                allow_system_query=True,
                query_name="sync_manager.delete_sync_metadata",
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
                query_name="sync_manager_delete_metadata",
            )
            record = await result.single()
            mutation = AuditedGraphMutation(
                tenant_id=validated_tenant_id,
                session=session,
                operation_source="sync_manager.delete_source",
            )
            await mutation._audit_node(
                "DELETE_SYNC_METADATA",
                "SyncMetadata",
                source_id,
                {"source_id": source_id, "deleted": record["deleted"] if record else 0},
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
            )

        stats["source_id"] = source_id
        stats["sync_metadata_deleted"] = True

        logger.info(f"Deleted source {source_id} and all associated data")
        return stats

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content.

        Args:
            content: String content to hash

        Returns:
            Hex digest of hash
        """
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _get_source_hash(self, source_id: str, tenant_id: str | None) -> str | None:
        """Get the last known content hash for a source.

        Args:
            source_id: Source document ID
            tenant_id: Tenant context required for metadata isolation

        Returns:
            Content hash or None if source not found
        """
        status = await self.get_sync_status(source_id, tenant_id=tenant_id)
        return status.get("content_hash") if status else None

    async def _update_sync_metadata(
        self,
        source_id: str,
        extraction_job_id: str,
        content_hash: str,
        status: str,
        error: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Update sync metadata for a source.

        Args:
            source_id: Source document ID
            extraction_job_id: Extraction job ID
            content_hash: Content hash
            status: Sync status (success, failed)
            error: Error message if failed
            tenant_id: Tenant context required for metadata updates
        """
        tenant_id = validate_ingestion_tenant_id(tenant_id)
        driver = await self.loader._get_driver()

        metadata = {
            "source_id": source_id,
            "tenant_id": tenant_id,
            "extraction_job_id": extraction_job_id,
            "content_hash": content_hash,
            "synced_at": datetime.utcnow().isoformat(),
            "status": status,
        }

        if error:
            metadata["error"] = error

        async with driver.session(database=self.settings.neo4j_database) as session:
<<<<<<< ours
<<<<<<< ours
<<<<<<< ours
            await run_validated_query(
                session,
                """
                CREATE (s:SyncMetadata $metadata)
                RETURN s
                """,
                {"metadata": metadata},
                tenant_id=tenant_id,
                allow_system_query=True,
                query_name="sync_manager.update_sync_metadata",
=======
=======
>>>>>>> theirs
=======
>>>>>>> theirs
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=session,
                operation_source="sync_manager._update_sync_metadata",
            )
            await mutation.write_node(
                "SyncMetadata",
                f"{source_id}:{extraction_job_id}:{metadata['synced_at']}",
                metadata,
<<<<<<< ours
<<<<<<< ours
>>>>>>> theirs
=======
>>>>>>> theirs
=======
>>>>>>> theirs
            )
