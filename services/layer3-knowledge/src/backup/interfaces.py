from __future__ import annotations

"""Ports for Layer 3 backup storage adapters."""


from abc import ABC, abstractmethod
from typing import Any


class BackupStoragePort(ABC):
    """Contract for backup object storage adapters."""

    @abstractmethod
    async def store_backup(self, backup_id: str, data: bytes) -> str: ...

    @abstractmethod
    async def retrieve_backup(self, backup_id: str) -> bytes: ...

    @abstractmethod
    async def delete_backup(self, backup_id: str) -> bool: ...

    @abstractmethod
    async def list_backups(self) -> list[str]: ...

    @abstractmethod
    async def get_backup_info(self, backup_id: str) -> dict[str, Any]: ...
