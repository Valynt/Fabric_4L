from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Literal

LoadStatsActionType = Literal[
    "start",
    "entities_loaded",
    "relationships_loaded",
    "triples_processed",
    "error",
    "finish",
]


@dataclass(frozen=True)
class LoadStatsAction:
    type: LoadStatsActionType
    count: int = 0
    message: str = ""
    timestamp: str = ""

    @classmethod
    def start(cls) -> LoadStatsAction:
        return cls(type="start", timestamp=datetime.utcnow().isoformat())

    @classmethod
    def entities_loaded(cls, count: int) -> LoadStatsAction:
        return cls(type="entities_loaded", count=count)

    @classmethod
    def relationships_loaded(cls, count: int) -> LoadStatsAction:
        return cls(type="relationships_loaded", count=count)

    @classmethod
    def triples_processed(cls, count: int) -> LoadStatsAction:
        return cls(type="triples_processed", count=count)

    @classmethod
    def error(cls, message: str) -> LoadStatsAction:
        return cls(type="error", message=message)

    @classmethod
    def finish(cls) -> LoadStatsAction:
        return cls(type="finish", timestamp=datetime.utcnow().isoformat())


@dataclass(frozen=True)
class LoadStats:
    entities_loaded: int = 0
    relationships_loaded: int = 0
    triples_processed: int = 0
    errors: tuple[str, ...] = ()
    start_time: str | None = None
    end_time: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entities_loaded": self.entities_loaded,
            "relationships_loaded": self.relationships_loaded,
            "triples_processed": self.triples_processed,
            "errors": list(self.errors),
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


def reduce_stats(stats: LoadStats, action: LoadStatsAction) -> LoadStats:
    """Pure reducer for load statistics."""
    if action.type == "start":
        return replace(stats, start_time=action.timestamp)
    if action.type == "entities_loaded":
        return replace(stats, entities_loaded=stats.entities_loaded + action.count)
    if action.type == "relationships_loaded":
        return replace(
            stats, relationships_loaded=stats.relationships_loaded + action.count
        )
    if action.type == "triples_processed":
        return replace(stats, triples_processed=action.count)
    if action.type == "error":
        return replace(stats, errors=stats.errors + (action.message,))
    if action.type == "finish":
        return replace(stats, end_time=action.timestamp)
    return stats
