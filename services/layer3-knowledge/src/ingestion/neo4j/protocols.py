from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ResultLike(Protocol):
    async def single(self) -> dict[str, Any] | None: ...


@runtime_checkable
class SessionLike(Protocol):
    async def run(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> ResultLike: ...

    async def __aenter__(self) -> SessionLike: ...

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool | None: ...


@runtime_checkable
class EmbeddingModel(Protocol):
    def encode(self, text: str, normalize_embeddings: bool = True) -> Any: ...


@runtime_checkable
class MutationGateway(Protocol):
    async def write_nodes_batch(
        self, label: str, nodes: list[dict[str, Any]]
    ) -> dict[str, Any]: ...

    async def write_relationships_batch(
        self, rel_type: str, triples: list[dict[str, str]]
    ) -> dict[str, Any]: ...

    async def write_relationship(
        self,
        src_id: str,
        rel_type: str,
        tgt_id: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...

    async def delete_by_source(self, source_id: str) -> dict[str, Any]: ...
