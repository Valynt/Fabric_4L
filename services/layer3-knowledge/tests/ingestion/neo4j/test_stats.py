from src.ingestion.neo4j.stats import LoadStats, LoadStatsAction, reduce_stats


def test_reduce_stats_accumulates_counts():
    stats = LoadStats()
    stats = reduce_stats(stats, LoadStatsAction.start())
    stats = reduce_stats(stats, LoadStatsAction.entities_loaded(3))
    stats = reduce_stats(stats, LoadStatsAction.relationships_loaded(5))
    stats = reduce_stats(stats, LoadStatsAction.triples_processed(12))
    stats = reduce_stats(stats, LoadStatsAction.error("boom"))
    stats = reduce_stats(stats, LoadStatsAction.finish())

    assert stats.entities_loaded == 3
    assert stats.relationships_loaded == 5
    assert stats.triples_processed == 12
    assert stats.errors == ("boom",)
    assert stats.start_time is not None
    assert stats.end_time is not None
    assert stats.to_dict()["errors"] == ["boom"]
