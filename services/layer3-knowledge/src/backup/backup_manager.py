"""Comprehensive backup and disaster recovery system."""

import asyncio
import gzip
import hashlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, model_validator

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None  # type: ignore

from value_fabric.shared.models.typed_dict import TypedDictModel

from src.logging_config import get_logger

from ..backup.interfaces import BackupStoragePort
from ..utils.cypher_security import (
    ALLOWED_REL_TYPES,
    ALLOWED_TARGET_LABELS,
    validate_cypher_identifier,
)


class BackupMetadata_to_dictResult(TypedDictModel):
    backup_id: Any
    backup_type: Any
    checksum: Any
    completed_at: Any
    compressed_size_bytes: Any
    compression_algorithm: Any
    created_at: Any
    description: Any
    encrypted: Any
    file_path: Any
    retention_days: Any
    size_bytes: Any
    status: Any
    storage_type: Any
    tags: Any

class LocalStorage_get_backup_infoResult(TypedDictModel):
    backup_id: Any
    created_at: Any
    file_path: Any
    modified_at: Any
    size_bytes: Any

class BackupManager_get_backup_statisticsResult(TypedDictModel):
    backup_type_distribution: Any
    completed_backups: Any
    compressed_size_bytes: Any
    compression_ratio: Any
    failed_backups: Any
    newest_backup: Any
    oldest_backup: Any
    storage_type_distribution: Any
    total_backups: Any
    total_size_bytes: Any

logger = get_logger(__name__)


class BackupType(str, Enum):
    """Backup operation types."""

    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"
    SCHEMA = "schema"
    CONFIG = "config"


class BackupStatus(str, Enum):
    """Backup operation status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StorageType(str, Enum):
    """Backup storage types."""

    LOCAL = "local"
    S3 = "s3"
    GCS = "gcs"
    AZURE = "azure"
    FTP = "ftp"


@dataclass
class BackupMetadata:
    """Backup metadata information."""

    backup_id: str
    backup_type: BackupType
    created_at: datetime
    completed_at: datetime | None = None
    status: BackupStatus = BackupStatus.PENDING
    size_bytes: int = 0
    compressed_size_bytes: int = 0
    file_path: str | None = None
    storage_type: StorageType = StorageType.LOCAL
    checksum: str | None = None
    description: str | None = None
    tags: list[str] = field(default_factory=list)
    retention_days: int = 30
    encrypted: bool = False
    compression_algorithm: str = "gzip"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return BackupMetadata_to_dictResult.model_validate({
            "backup_id": self.backup_id,
            "backup_type": self.backup_type.value,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "status": self.status.value,
            "size_bytes": self.size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "file_path": self.file_path,
            "storage_type": self.storage_type.value,
            "checksum": self.checksum,
            "description": self.description,
            "tags": self.tags,
            "retention_days": self.retention_days,
            "encrypted": self.encrypted,
            "compression_algorithm": self.compression_algorithm,
        })


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BackupMetadata":
        """Create from dictionary."""
        return cls(
            backup_id=data["backup_id"],
            backup_type=BackupType(data["backup_type"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            completed_at=datetime.fromisoformat(data["completed_at"])
            if data.get("completed_at")
            else None,
            status=BackupStatus(data["status"]),
            size_bytes=data["size_bytes"],
            compressed_size_bytes=data["compressed_size_bytes"],
            file_path=data.get("file_path"),
            storage_type=StorageType(data["storage_type"]),
            checksum=data.get("checksum"),
            description=data.get("description"),
            tags=data.get("tags", []),
            retention_days=data.get("retention_days", 30),
            encrypted=data.get("encrypted", False),
            compression_algorithm=data.get("compression_algorithm", "gzip"),
        )


class BackupConfig(BaseModel):
    """Backup configuration."""

    enabled: bool = Field(default=True, description="Whether backup is enabled")
    backup_directory: str = Field(
        default="./backups", description="Local backup directory"
    )
    compression_enabled: bool = Field(default=True, description="Enable compression")
    encryption_enabled: bool = Field(default=False, description="Enable encryption")
    encryption_key: str | None = Field(None, description="Encryption key")
    retention_days: int = Field(
        default=30, description="Default retention period in days"
    )
    max_backups: int = Field(
        default=100, description="Maximum number of backups to keep"
    )
    schedule: str | None = Field(None, description="Backup schedule (cron format)")
    auto_cleanup: bool = Field(
        default=True, description="Automatically cleanup old backups"
    )

    # Storage configuration
    storage_type: StorageType = Field(
        default=StorageType.LOCAL, description="Primary storage type"
    )
    s3_config: dict[str, Any] | None = Field(None, description="S3 configuration")
    gcs_config: dict[str, Any] | None = Field(None, description="GCS configuration")
    azure_config: dict[str, Any] | None = Field(None, description="Azure configuration")
    ftp_config: dict[str, Any] | None = Field(None, description="FTP configuration")




class SignedAdminCapability(BaseModel):
    """Signed entitlement proving platform-admin scope for global export."""

    actor_id: str = Field(..., description="Authenticated caller principal ID")
    role: str = Field(..., description="Caller role")
    tenant_domain: str = Field(..., description="Tenant domain context for authorization")
    platform_scope: bool = Field(..., description="True when entitlement is platform-global")
    signature: str = Field(..., description="Detached signature or token hash")
    reason_code: str = Field(..., description="Governance-approved reason code")
    ticket_reference: str = Field(..., description="Change/ticket reference")
    correlation_id: str = Field(..., description="Request correlation ID")

    @model_validator(mode="after")
    def _validate_platform_scope(self):
        if not self.platform_scope:
            raise ValueError("Global export requires platform_scope entitlement")
        return self


class BackupRequest(BaseModel):
    """Backup operation request."""

    backup_type: BackupType = Field(..., description="Type of backup")
    description: str | None = Field(None, description="Backup description")
    tags: list[str] = Field(default_factory=list, description="Backup tags")
    retention_days: int | None = Field(None, description="Custom retention period")
    storage_type: StorageType | None = Field(None, description="Override storage type")
    compression: bool | None = Field(None, description="Override compression setting")
    encryption: bool | None = Field(None, description="Override encryption setting")
    tenant_id: str | None = Field(
        None,
        description=(
            "Tenant scope for standard backups. Required unless running an "
            "explicit platform-admin global backup."
        ),
    )
    global_export: bool = Field(
        default=False,
        description=(
            "When true, performs a cross-tenant export. Requires platform-admin "
            "governance authorization and immutable audit emission."
        ),
    )
    admin_capability: SignedAdminCapability | None = Field(
        default=None,
        description=(
            "Signed platform-admin entitlement payload required for global_export."
        ),
    )


class BackupResponse(BaseModel):
    """Backup operation response."""

    backup_id: str = Field(..., description="Backup ID")
    status: BackupStatus = Field(..., description="Backup status")
    backup_type: BackupType = Field(..., description="Backup type")
    created_at: datetime = Field(..., description="Creation timestamp")
    size_bytes: int = Field(default=0, description="Backup size in bytes")
    file_path: str | None = Field(None, description="Backup file path")
    checksum: str | None = Field(None, description="Backup checksum")
    duration_seconds: float | None = Field(None, description="Backup duration")
    error: str | None = Field(None, description="Error message if failed")


class RestoreRequest(BaseModel):
    """Restore operation request."""

    backup_id: str = Field(..., description="Backup ID to restore")
    target_database: str | None = Field(None, description="Target database name")
    restore_schema: bool = Field(default=True, description="Restore schema")
    restore_data: bool = Field(default=True, description="Restore data")
    dry_run: bool = Field(
        default=False, description="Perform dry run without actual restore"
    )
    force_overwrite: bool = Field(
        default=False, description="Force overwrite existing data"
    )


class RestoreResponse(BaseModel):
    """Restore operation response."""

    backup_id: str = Field(..., description="Backup ID")
    status: str = Field(..., description="Restore status")
    restored_at: datetime = Field(..., description="Restore timestamp")
    entities_restored: int = Field(default=0, description="Number of entities restored")
    relationships_restored: int = Field(
        default=0, description="Number of relationships restored"
    )
    duration_seconds: float | None = Field(None, description="Restore duration")
    error: str | None = Field(None, description="Error message if failed")
    warnings: list[str] = Field(default_factory=list, description="Restore warnings")


class BackupStorage(BackupStoragePort):
    """Backward-compatible alias for backup storage port."""

    def __init__(self, config: BackupConfig):
        """Initialize storage backend.

        Args:
            config: Backup configuration
        """
        self.config = config

    async def store_backup(self, backup_id: str, data: bytes) -> str:
        """Store backup data.

        Args:
            backup_id: Backup ID
            data: Backup data

        Returns:
            Storage path or identifier
        """
        ...

    async def retrieve_backup(self, backup_id: str) -> bytes:
        """Retrieve backup data.

        Args:
            backup_id: Backup ID

        Returns:
            Backup data
        """
        ...

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete backup data.

        Args:
            backup_id: Backup ID

        Returns:
            True if deleted
        """
        ...

    async def list_backups(self) -> list[str]:
        """List available backups.

        Returns:
            List of backup IDs
        """
        ...

    async def get_backup_info(self, backup_id: str) -> dict[str, Any]:
        """Get backup information.

        Args:
            backup_id: Backup ID

        Returns:
            Backup information
        """
        ...


class LocalStorage(BackupStorage):
    """Local filesystem storage for backups."""

    def __init__(self, config: BackupConfig):
        """Initialize local storage.

        Args:
            config: Backup configuration
        """
        super().__init__(config)
        self.backup_dir = Path(config.backup_directory)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _write_bytes(self, file_path: Path, data: bytes) -> None:
        """Synchronous helper: write backup bytes to disk."""
        with open(file_path, "wb") as f:
            f.write(data)

    def _read_bytes(self, file_path: Path) -> bytes:
        """Synchronous helper: read backup bytes from disk."""
        with open(file_path, "rb") as f:
            return f.read()

    async def store_backup(self, backup_id: str, data: bytes) -> str:
        """Store backup data locally without blocking the event loop.

        Args:
            backup_id: Backup ID
            data: Backup data

        Returns:
            File path
        """
        file_path = self.backup_dir / f"{backup_id}.backup"
        await asyncio.to_thread(self._write_bytes, file_path, data)
        logger.info(f"Stored backup locally: {file_path}")
        return str(file_path)

    async def retrieve_backup(self, backup_id: str) -> bytes:
        """Retrieve backup data from local storage without blocking the event loop.

        Args:
            backup_id: Backup ID

        Returns:
            Backup data
        """
        file_path = self.backup_dir / f"{backup_id}.backup"

        if not await asyncio.to_thread(file_path.exists):
            raise FileNotFoundError(f"Backup file not found: {file_path}")

        data = await asyncio.to_thread(self._read_bytes, file_path)
        logger.info(f"Retrieved backup from local storage: {file_path}")
        return data

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete backup from local storage without blocking the event loop.

        Args:
            backup_id: Backup ID

        Returns:
            True if deleted
        """
        file_path = self.backup_dir / f"{backup_id}.backup"

        try:
            if await asyncio.to_thread(file_path.exists):
                await asyncio.to_thread(file_path.unlink)
                logger.info(f"Deleted local backup: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete local backup {backup_id}: {e}")
            return False

    async def list_backups(self) -> list[str]:
        """List local backups without blocking the event loop.

        Returns:
            List of backup IDs
        """
        files = await asyncio.to_thread(list, self.backup_dir.glob("*.backup"))
        backup_ids = []

        for file_path in files:
            backup_id = file_path.stem
            backup_ids.append(backup_id)

        return sorted(backup_ids)

    async def get_backup_info(self, backup_id: str) -> dict[str, Any]:
        """Get local backup information without blocking the event loop.

        Args:
            backup_id: Backup ID

        Returns:
            Backup information
        """
        file_path = self.backup_dir / f"{backup_id}.backup"

        if not await asyncio.to_thread(file_path.exists):
            raise FileNotFoundError(f"Backup file not found: {file_path}")

        stat = await asyncio.to_thread(file_path.stat)

        return LocalStorage_get_backup_infoResult.model_validate({
            "backup_id": backup_id,
            "file_path": str(file_path),
            "size_bytes": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_ctime),
            "modified_at": datetime.fromtimestamp(stat.st_mtime),
        })


class BackupManager:
    """Manages backup and restore operations."""

    def __init__(
        self,
        config: BackupConfig,
        neo4j_driver=None,
        global_backup_authorizer=None,
        immutable_audit_logger=None,
    ):
        """Initialize backup manager.

        Args:
            config: Backup configuration
            neo4j_driver: Optional Neo4j driver for restore operations
        """
        self.config = config
        self.storage = self._create_storage()
        self.neo4j_driver = neo4j_driver
        self.global_backup_authorizer = global_backup_authorizer
        self.immutable_audit_logger = immutable_audit_logger
        self.active_backups: dict[str, BackupMetadata] = {}
        self.backup_history: list[BackupMetadata] = []
        self._loaded_existing = False

    async def load_existing_backups(self) -> None:
        """Load existing backup metadata."""
        if self._loaded_existing:
            return

        try:
            backup_ids = await self.storage.list_backups()

            for backup_id in backup_ids:
                try:
                    info = await self.storage.get_backup_info(backup_id)
                    metadata = BackupMetadata(
                        backup_id=backup_id,
                        backup_type=BackupType.FULL,  # Default, should be stored separately
                        created_at=info["created_at"],
                        status=BackupStatus.COMPLETED,
                        size_bytes=info["size_bytes"],
                        file_path=info["file_path"],
                        storage_type=self.config.storage_type,
                    )
                    self.backup_history.append(metadata)
                except Exception as e:
                    logger.warning(
                        f"Failed to load backup metadata for {backup_id}: {e}"
                    )

            logger.info(f"Loaded {len(self.backup_history)} existing backups")
            self._loaded_existing = True

        except Exception as e:
            logger.error(f"Failed to load existing backups: {e}")

    def _create_storage(self) -> BackupStorage:
        """Create storage backend based on configuration.

        Returns:
            Storage backend
        """
        if self.config.storage_type == StorageType.LOCAL:
            return LocalStorage(self.config)
        # Add other storage types as needed
        else:
            raise ValueError(f"Unsupported storage type: {self.config.storage_type}")

    async def _load_existing_backups(self) -> None:
        """Load existing backup metadata."""
        try:
            backup_ids = await self.storage.list_backups()

            for backup_id in backup_ids:
                try:
                    info = await self.storage.get_backup_info(backup_id)
                    metadata = BackupMetadata(
                        backup_id=backup_id,
                        backup_type=BackupType.FULL,  # Default, should be stored separately
                        created_at=info["created_at"],
                        status=BackupStatus.COMPLETED,
                        size_bytes=info["size_bytes"],
                        file_path=info["file_path"],
                        storage_type=self.config.storage_type,
                    )
                    self.backup_history.append(metadata)
                except Exception as e:
                    logger.warning(
                        f"Failed to load backup metadata for {backup_id}: {e}"
                    )

            logger.info(f"Loaded {len(self.backup_history)} existing backups")

        except Exception as e:
            logger.error(f"Failed to load existing backups: {e}")

    async def create_backup(
        self,
        request: BackupRequest,
        *,
        authenticated_tenant_id: str | None = None,
    ) -> BackupResponse:
        """Create a new backup.

        Args:
            request: Backup request

        Returns:
            Backup response
        """
        start_time = datetime.now(UTC)
        backup_id = f"backup_{int(start_time.timestamp())}_{uuid.uuid4().hex[:8]}"

        # Create backup metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=request.backup_type,
            created_at=start_time,
            status=BackupStatus.RUNNING,
            description=request.description,
            tags=request.tags,
            retention_days=request.retention_days or self.config.retention_days,
            storage_type=request.storage_type or self.config.storage_type,
            encrypted=request.encryption
            if request.encryption is not None
            else self.config.encryption_enabled,
            compression_algorithm="gzip"
            if (
                request.compression
                if request.compression is not None
                else self.config.compression_enabled
            )
            else "none",
        )

        self.active_backups[backup_id] = metadata

        try:
            tenant_id = request.tenant_id
            if authenticated_tenant_id is not None:
                tenant_id = authenticated_tenant_id
                if request.tenant_id and request.tenant_id != authenticated_tenant_id:
                    raise ValueError(
                        json.dumps(
                            {
                                "code": "TENANT_SCOPE_MISMATCH",
                                "requested_tenant_hint": request.tenant_id,
                            },
                            sort_keys=True,
                        )
                    )

            if request.global_export:
                await self._authorize_global_backup(admin_capability=request.admin_capability)

            # Generate backup data
            backup_data = await self._generate_backup_data(
                backup_type=request.backup_type,
                tenant_id=tenant_id,
                global_export=request.global_export,
                admin_capability=request.admin_capability,
            )

            # Compress if enabled
            if metadata.compression_algorithm != "none":
                backup_data = await self._compress_data(
                    backup_data, metadata.compression_algorithm
                )
                metadata.compressed_size_bytes = len(backup_data)
            else:
                metadata.compressed_size_bytes = len(backup_data)

            metadata.size_bytes = len(backup_data)

            # Encrypt if enabled
            if metadata.encrypted:
                backup_data = await self._encrypt_data(backup_data)

            # Calculate checksum
            metadata.checksum = hashlib.sha256(backup_data).hexdigest()

            # Store backup
            file_path = await self.storage.store_backup(backup_id, backup_data)
            metadata.file_path = file_path

            # Update metadata
            metadata.status = BackupStatus.COMPLETED
            metadata.completed_at = datetime.now(UTC)

            # Move to history
            self.backup_history.append(metadata)
            del self.active_backups[backup_id]

            # Cleanup old backups if enabled
            if self.config.auto_cleanup:
                await self._cleanup_old_backups()

            duration = (datetime.now(UTC) - start_time).total_seconds()

            logger.info(f"Backup completed: {backup_id} ({metadata.backup_type.value})")

            return BackupResponse(
                backup_id=backup_id,
                status=metadata.status.value,
                backup_type=metadata.backup_type,
                created_at=metadata.created_at,
                size_bytes=metadata.size_bytes,
                file_path=metadata.file_path,
                checksum=metadata.checksum,
                duration_seconds=duration,
            )

        except PermissionError:
            metadata.status = BackupStatus.FAILED
            metadata.completed_at = datetime.now(UTC)
            raise
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.completed_at = datetime.now(UTC)

            logger.error(f"Backup failed: {backup_id} - {e}")

            return BackupResponse(
                backup_id=backup_id,
                status=metadata.status.value,
                backup_type=metadata.backup_type,
                created_at=metadata.created_at,
                error=str(e) if str(e) else "backup_failed",
            )

    async def _generate_backup_data(
        self,
        backup_type: BackupType,
        tenant_id: str | None = None,
        global_export: bool = False,
        admin_capability: SignedAdminCapability | None = None,
    ) -> bytes:
        """Generate backup data based on type from Neo4j.

        Args:
            backup_type: Type of backup

        Returns:
            Backup data as JSON bytes
        """
        if not self.neo4j_driver:
            raise RuntimeError("Neo4j driver required for backup generation")

        if backup_type == BackupType.FULL:
            if global_export:
                await self._authorize_global_backup(admin_capability=admin_capability)
                await self._emit_immutable_global_backup_audit_event(
                    backup_type=backup_type,
                    stage="before",
                    admin_capability=admin_capability,
                )
            elif not tenant_id:
                raise ValueError(
                    "tenant_id is required for standard backup exports. "
                    "Use explicit platform-admin global_export for cross-tenant export."
                )
            # Export all entities and relationships from Neo4j
            entities = []
            relationships = []
            schema_info = {"constraints": [], "indexes": []}

            async with self.neo4j_driver.session() as session:
                # Get all entities
                entity_query = """
                    MATCH (n)
                    RETURN n, labels(n) as types, id(n) as node_id
                    LIMIT 10000
                """
                entity_params = {}
                if not global_export:
                    entity_query = """
                        MATCH (n {tenant_id: $tenant_id})
                        RETURN n, labels(n) as types, id(n) as node_id
                        LIMIT 10000
                    """
                    entity_params["tenant_id"] = tenant_id
                entity_result = await session.run(entity_query, **entity_params)
                async for record in entity_result:
                    node = record["n"]
                    node_data = dict(node)
                    entities.append({
                        "id": node_data.get("id", str(record["node_id"])),
                        "type": record["types"][0] if record["types"] else "Entity",
                        "properties": {k: v for k, v in node_data.items() if k != "id"},
                        "tenant_id": node_data.get("tenant_id", "default"),
                    })

                # Get all relationships
                relationship_query = """
                    MATCH (n)-[r]->(m)
                    RETURN n.id as source_id, m.id as target_id,
                           type(r) as rel_type, properties(r) as rel_props
                    LIMIT 50000
                """
                relationship_params = {}
                if not global_export:
                    relationship_query = """
                        MATCH (n {tenant_id: $tenant_id})-[r]->(m {tenant_id: $tenant_id})
                        RETURN n.id as source_id, m.id as target_id,
                               type(r) as rel_type, properties(r) as rel_props
                        LIMIT 50000
                    """
                    relationship_params["tenant_id"] = tenant_id
                rel_result = await session.run(relationship_query, **relationship_params)
                async for record in rel_result:
                    if record["source_id"] and record["target_id"]:
                        relationships.append({
                            "source_id": record["source_id"],
                            "target_id": record["target_id"],
                            "type": record["rel_type"],
                            "properties": record["rel_props"] or {},
                        })

                # Get schema constraints
                try:
                    constraints_result = await session.run("SHOW CONSTRAINTS")
                    async for record in constraints_result:
                        schema_info["constraints"].append(dict(record))
                except Exception as e:
                    logger.warning(f"Could not retrieve constraints: {e}")

                # Get indexes
                try:
                    indexes_result = await session.run("SHOW INDEXES")
                    async for record in indexes_result:
                        schema_info["indexes"].append(dict(record))
                except Exception as e:
                    logger.warning(f"Could not retrieve indexes: {e}")

            backup_data = {
                "type": "full",
                "timestamp": datetime.now(UTC).isoformat(),
                "entities": entities,
                "relationships": relationships,
                "schema": schema_info,
                "metadata": {
                    "version": "1.0.0",
                    "source": "value-fabric-layer3",
                    "entity_count": len(entities),
                    "relationship_count": len(relationships),
                },
            }
            if global_export:
                await self._emit_immutable_global_backup_audit_event(
                    backup_type=backup_type,
                    stage="after",
                    admin_capability=admin_capability,
                )
        elif backup_type == BackupType.INCREMENTAL:
            # Incremental backup - changes since last backup
            last_backup = self._get_last_full_backup_id()
            backup_data = {
                "type": "incremental",
                "timestamp": datetime.now(UTC).isoformat(),
                "base_backup": last_backup,
                "changes": [],  # Would need timestamp tracking for true incremental
                "metadata": {"version": "1.0.0", "source": "value-fabric-layer3"},
            }
        elif backup_type == BackupType.SCHEMA:
            # Schema-only backup
            schema_info = {"constraints": [], "indexes": []}

            if self.neo4j_driver:
                async with self.neo4j_driver.session() as session:
                    try:
                        constraints_result = await session.run("SHOW CONSTRAINTS")
                        async for record in constraints_result:
                            schema_info["constraints"].append(dict(record))
                    except Exception as e:
                        logger.warning(f"Could not retrieve constraints: {e}")

                    try:
                        indexes_result = await session.run("SHOW INDEXES")
                        async for record in indexes_result:
                            schema_info["indexes"].append(dict(record))
                    except Exception as e:
                        logger.warning(f"Could not retrieve indexes: {e}")

            backup_data = {
                "type": "schema",
                "timestamp": datetime.now(UTC).isoformat(),
                "schema": schema_info,
                "constraints": schema_info["constraints"],
                "indexes": schema_info["indexes"],
                "metadata": {"version": "1.0.0", "source": "value-fabric-layer3"},
            }
        else:
            raise ValueError(f"Unsupported backup type: {backup_type}")

        return json.dumps(backup_data, indent=2, default=str).encode("utf-8")

    async def _authorize_global_backup(
        self, admin_capability: SignedAdminCapability | None
    ) -> None:
        """Enforce RBAC/governance authorization for global export."""
        if admin_capability is None:
            raise PermissionError("Signed admin capability is required for global export.")
        if admin_capability.role != "platform_admin" or admin_capability.tenant_domain != "platform":
            raise PermissionError(
                "Global backup export requires platform_admin role in platform tenant domain."
            )
        if self.global_backup_authorizer is None:
            raise PermissionError(
                "Global backup export requires platform-admin governance authorization."
            )
        is_allowed = await self.global_backup_authorizer(admin_capability)
        if not is_allowed:
            raise PermissionError(
                "Caller is not authorized for platform-admin global backup export."
            )

    async def _emit_immutable_global_backup_audit_event(
        self,
        backup_type: BackupType,
        stage: str,
        admin_capability: SignedAdminCapability | None,
    ) -> None:
        """Emit immutable audit event for global exports."""
        if self.immutable_audit_logger is None:
            raise PermissionError(
                "Global backup export requires immutable audit event emission."
            )
        if admin_capability is None:
            raise PermissionError("Signed admin capability is required for immutable audit logging.")
        await self.immutable_audit_logger(
            {
                "event_type": "platform_admin_global_backup_export",
                "stage": stage,
                "backup_type": backup_type.value,
                "occurred_at": datetime.now(UTC).isoformat(),
                "immutability_required": True,
                "actor_id": admin_capability.actor_id,
                "reason_code": admin_capability.reason_code,
                "ticket_reference": admin_capability.ticket_reference,
                "correlation_id": admin_capability.correlation_id,
            }
        )

    def _get_last_full_backup_id(self) -> str | None:
        """Get the ID of the last full backup.

        Returns:
            Backup ID or None
        """
        for backup in reversed(self.backup_history):
            if (
                backup.backup_type == BackupType.FULL
                and backup.status == BackupStatus.COMPLETED
            ):
                return backup.backup_id
        return None

    async def _compress_data(self, data: bytes, algorithm: str) -> bytes:
        """Compress backup data.

        Args:
            data: Data to compress
            algorithm: Compression algorithm

        Returns:
            Compressed data
        """
        if algorithm == "gzip":
            return gzip.compress(data)
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")

    async def _encrypt_data(self, data: bytes) -> bytes:
        """Encrypt backup data using Fernet (AES-256-CBC with HMAC).

        Args:
            data: Data to encrypt

        Returns:
            Encrypted data
        """
        if not HAS_CRYPTOGRAPHY or not Fernet:
            raise RuntimeError(
                "Encryption requires 'cryptography' package. "
                "Install with: pip install cryptography"
            )

        encryption_key = self.config.encryption_key
        if not encryption_key:
            # Generate a key from environment or raise error
            encryption_key = os.environ.get('BACKUP_ENCRYPTION_KEY')
            if not encryption_key:
                raise RuntimeError(
                    "Encryption enabled but no key provided. "
                    "Set encryption_key in config or BACKUP_ENCRYPTION_KEY env var"
                )

        # Ensure key is valid Fernet key (32 bytes base64-encoded)
        try:
            fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key format: {e}")

        encrypted = fernet.encrypt(data)
        logger.info(f"Encrypted backup data: {len(data)} bytes -> {len(encrypted)} bytes")
        return encrypted

    async def restore_backup(self, request: RestoreRequest) -> RestoreResponse:
        """Restore from backup.

        Args:
            request: Restore request

        Returns:
            Restore response
        """
        start_time = datetime.now(UTC)

        try:
            # Retrieve backup data
            backup_data = await self.storage.retrieve_backup(request.backup_id)

            # Decrypt if needed
            backup_metadata = self._get_backup_metadata(request.backup_id)
            if backup_metadata and backup_metadata.encrypted:
                backup_data = await self._decrypt_data(backup_data)

            # Decompress if needed
            if backup_metadata and backup_metadata.compression_algorithm != "none":
                backup_data = await self._decompress_data(
                    backup_data, backup_metadata.compression_algorithm
                )

            # Parse backup data
            backup_json = json.loads(backup_data.decode("utf-8"))

            if request.dry_run:
                # Dry run - just validate and return info
                entities_count = len(backup_json.get("entities", []))
                relationships_count = len(backup_json.get("relationships", []))

                return RestoreResponse(
                    backup_id=request.backup_id,
                    status="dry_run_completed",
                    restored_at=datetime.now(UTC),
                    entities_restored=entities_count,
                    relationships_restored=relationships_count,
                    duration_seconds=(datetime.now(UTC) - start_time).total_seconds(),
                    warnings=["Dry run - no actual restore performed"],
                )

            # Perform actual restore
            entities_restored = 0
            relationships_restored = 0
            warnings = []

            if request.restore_data:
                entities_restored = await self._restore_entities(
                    backup_json.get("entities", []), request.target_database
                )
                relationships_restored = await self._restore_relationships(
                    backup_json.get("relationships", []), request.target_database
                )

            if request.restore_schema:
                await self._restore_schema(
                    backup_json.get("schema", {}), request.target_database
                )

            duration = (datetime.now(UTC) - start_time).total_seconds()

            logger.info(f"Restore completed: {request.backup_id}")

            return RestoreResponse(
                backup_id=request.backup_id,
                status="completed",
                restored_at=datetime.now(UTC),
                entities_restored=entities_restored,
                relationships_restored=relationships_restored,
                duration_seconds=duration,
                warnings=warnings,
            )

        except Exception as e:
            logger.error(f"Restore failed: {request.backup_id} - {e}")

            return RestoreResponse(
                backup_id=request.backup_id,
                status="failed",
                restored_at=datetime.now(UTC),
                error="backup_failed",
            )

    def _get_backup_metadata(self, backup_id: str) -> BackupMetadata | None:
        """Get backup metadata.

        Args:
            backup_id: Backup ID

        Returns:
            Backup metadata or None
        """
        for backup in self.backup_history:
            if backup.backup_id == backup_id:
                return backup
        return None

    async def _decrypt_data(self, data: bytes) -> bytes:
        """Decrypt backup data using Fernet.

        Args:
            data: Encrypted data

        Returns:
            Decrypted data
        """
        if not HAS_CRYPTOGRAPHY or not Fernet:
            raise RuntimeError(
                "Decryption requires 'cryptography' package. "
                "Install with: pip install cryptography"
            )

        encryption_key = self.config.encryption_key
        if not encryption_key:
            encryption_key = os.environ.get('BACKUP_ENCRYPTION_KEY')
            if not encryption_key:
                raise RuntimeError("Decryption enabled but no key provided")

        try:
            fernet = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)
            decrypted = fernet.decrypt(data)
            logger.info(f"Decrypted backup data: {len(data)} bytes -> {len(decrypted)} bytes")
            return decrypted
        except Exception as e:
            raise ValueError(f"Failed to decrypt backup data: {e}")

    async def _decompress_data(self, data: bytes, algorithm: str) -> bytes:
        """Decompress backup data.

        Args:
            data: Compressed data
            algorithm: Compression algorithm

        Returns:
            Decompressed data
        """
        if algorithm == "gzip":
            return gzip.decompress(data)
        else:
            raise ValueError(f"Unsupported compression algorithm: {algorithm}")

    async def _restore_entities(
        self, entities: list[dict[str, Any]], target_database: str | None
    ) -> int:
        """Restore entities from backup to Neo4j.

        Args:
            entities: Entity data
            target_database: Target database (not used, Neo4j handles this)

        Returns:
            Number of entities restored
        """
        if not self.neo4j_driver:
            logger.warning("No Neo4j driver available, cannot restore entities")
            return 0

        restored_count = 0
        async with self.neo4j_driver.session() as session:
            for entity in entities:
                try:
                    # Extract entity properties
                    entity_id = entity.get("id")
                    entity_type = entity.get("type", "Entity")
                    properties = entity.get("properties", {})
                    tenant_id = entity.get("tenant_id", "default")

                    # SEC-L3-CYPHER-003: Validate the backup-supplied entity_type
                    # against a closed label allowlist before interpolating it into
                    # Cypher; a tampered backup must fail closed rather than inject.
                    validate_cypher_identifier(
                        entity_type, ALLOWED_TARGET_LABELS, kind="backup entity type"
                    )

                    # Create or merge entity node
                    query = (
                        f"MERGE (n:{entity_type} {{id: $entity_id, tenant_id: $tenant_id}})\n"  # cypher-dynamic-safe: validated against ALLOWED_TARGET_LABELS allowlist  # cypher-mutation-safe: label validated, tenant-scoped restore
                        "                    SET n += $properties\n"
                        "                    "
                    )
                    await session.run(
                        query,
                        entity_id=entity_id,
                        tenant_id=tenant_id,
                        properties=properties,
                    )
                    restored_count += 1
                except Exception as e:
                    logger.error(f"Failed to restore entity {entity.get('id')}: {e}")

        logger.info(f"Restored {restored_count}/{len(entities)} entities")
        return restored_count

    async def _restore_relationships(
        self, relationships: list[dict[str, Any]], target_database: str | None
    ) -> int:
        """Restore relationships from backup to Neo4j.

        Args:
            relationships: Relationship data
            target_database: Target database (not used)

        Returns:
            Number of relationships restored
        """
        if not self.neo4j_driver:
            logger.warning("No Neo4j driver available, cannot restore relationships")
            return 0

        restored_count = 0
        async with self.neo4j_driver.session() as session:
            for rel in relationships:
                try:
                    # Extract relationship properties
                    source_id = rel.get("source_id")
                    target_id = rel.get("target_id")
                    rel_type = rel.get("type", "RELATED_TO")
                    properties = rel.get("properties", {})
                    tenant_id = rel.get("tenant_id", "default")

                    if not source_id or not target_id:
                        logger.warning(f"Skipping relationship with missing source/target: {rel}")
                        continue

                    # SEC-L3-CYPHER-003: Validate the backup-supplied rel_type against
                    # a closed allowlist before interpolating it into Cypher; a tampered
                    # backup must fail closed rather than inject.
                    validate_cypher_identifier(
                        rel_type, ALLOWED_REL_TYPES, kind="backup relationship type"
                    )

                    # Create relationship between entities
                    query = (
                        "MATCH (source {id: $source_id, tenant_id: $tenant_id})\n"
                        "                    MATCH (target {id: $target_id, tenant_id: $tenant_id})\n"
                        f"                    MERGE (source)-[r:{rel_type}]->(target)\n"  # cypher-dynamic-safe: validated against ALLOWED_REL_TYPES allowlist
                        "                    SET r += $properties\n"
                        "                    "
                    )
                    await session.run(
                        query,
                        source_id=source_id,
                        target_id=target_id,
                        tenant_id=tenant_id,
                        properties=properties,
                    )
                    restored_count += 1
                except Exception as e:
                    logger.error(f"Failed to restore relationship: {e}")

        logger.info(f"Restored {restored_count}/{len(relationships)} relationships")
        return restored_count

    async def _restore_schema(
        self, schema: dict[str, Any], target_database: str | None
    ) -> None:
        """Restore schema constraints and indexes from backup.

        Args:
            schema: Schema data with constraints and indexes
            target_database: Target database (not used)
        """
        if not self.neo4j_driver:
            logger.warning("No Neo4j driver available, cannot restore schema")
            return

        constraints = schema.get("constraints", [])
        indexes = schema.get("indexes", [])

        async with self.neo4j_driver.session() as session:
            # Restore constraints
            for constraint in constraints:
                try:
                    cypher = constraint.get("cypher")
                    if cypher:
                        await session.run(cypher)
                        logger.info(f"Restored constraint: {constraint.get('name')}")
                except Exception as e:
                    logger.warning(f"Failed to restore constraint: {e}")

            # Restore indexes
            for index in indexes:
                try:
                    cypher = index.get("cypher")
                    if cypher:
                        await session.run(cypher)
                        logger.info(f"Restored index: {index.get('name')}")
                except Exception as e:
                    logger.warning(f"Failed to restore index: {e}")

        logger.info(f"Schema restore completed: {len(constraints)} constraints, {len(indexes)} indexes")

    async def list_backups(
        self, backup_type: BackupType | None = None
    ) -> list[BackupMetadata]:
        """List available backups.

        Args:
            backup_type: Filter by backup type

        Returns:
            List of backup metadata
        """
        backups = self.backup_history.copy()

        if backup_type:
            backups = [b for b in backups if b.backup_type == backup_type]

        return sorted(backups, key=lambda b: b.created_at, reverse=True)

    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup.

        Args:
            backup_id: Backup ID

        Returns:
            True if deleted
        """
        try:
            # Delete from storage
            storage_deleted = await self.storage.delete_backup(backup_id)

            # Remove from history
            self.backup_history = [
                b for b in self.backup_history if b.backup_id != backup_id
            ]

            logger.info(f"Deleted backup: {backup_id}")
            return storage_deleted

        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False

    async def _cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy.

        Returns:
            Number of backups deleted
        """
        deleted_count = 0
        now = datetime.now(UTC)

        for backup in self.backup_history.copy():
            # Check retention period
            if (now - backup.created_at).days > backup.retention_days:
                if await self.delete_backup(backup.backup_id):
                    deleted_count += 1

        # Also check max backups limit
        if len(self.backup_history) > self.config.max_backups:
            # Sort by creation date (oldest first)
            sorted_backups = sorted(self.backup_history, key=lambda b: b.created_at)
            excess_count = len(self.backup_history) - self.config.max_backups

            for backup in sorted_backups[:excess_count]:
                if await self.delete_backup(backup.backup_id):
                    deleted_count += 1

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old backups")

        return deleted_count

    async def get_backup_statistics(self) -> dict[str, Any]:
        """Get backup statistics.

        Returns:
            Backup statistics
        """
        total_backups = len(self.backup_history)
        completed_backups = len(
            [b for b in self.backup_history if b.status == BackupStatus.COMPLETED]
        )
        failed_backups = len(
            [b for b in self.backup_history if b.status == BackupStatus.FAILED]
        )

        # Size statistics
        total_size = sum(b.size_bytes for b in self.backup_history)
        compressed_size = sum(b.compressed_size_bytes for b in self.backup_history)

        # Type distribution
        type_counts = {}
        for backup in self.backup_history:
            backup_type = backup.backup_type.value
            type_counts[backup_type] = type_counts.get(backup_type, 0) + 1

        # Storage distribution
        storage_counts = {}
        for backup in self.backup_history:
            storage_type = backup.storage_type.value
            storage_counts[storage_type] = storage_counts.get(storage_type, 0) + 1

        return BackupManager_get_backup_statisticsResult.model_validate({
            "total_backups": total_backups,
            "completed_backups": completed_backups,
            "failed_backups": failed_backups,
            "total_size_bytes": total_size,
            "compressed_size_bytes": compressed_size,
            "compression_ratio": (total_size - compressed_size) / total_size
            if total_size > 0
            else 0,
            "backup_type_distribution": type_counts,
            "storage_type_distribution": storage_counts,
            "oldest_backup": min(
                (b.created_at for b in self.backup_history), default=None
            ),
            "newest_backup": max(
                (b.created_at for b in self.backup_history), default=None
            ),
        })


# Global backup manager instance
_backup_manager: BackupManager | None = None


def get_backup_manager() -> BackupManager | None:
    """Get global backup manager instance.

    Returns:
        Backup manager instance
    """
    return _backup_manager


def initialize_backup_manager(config: BackupConfig) -> BackupManager:
    """Initialize global backup manager.

    Args:
        config: Backup configuration

    Returns:
        Backup manager instance
    """
    global _backup_manager
    _backup_manager = BackupManager(config)
    logger.info("Backup manager initialized")
    return _backup_manager
