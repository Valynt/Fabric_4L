from layer1_ingestion.shared.database import _normalize_sync_database_url


def test_normalize_sync_database_url_pins_generic_postgres_to_psycopg2() -> None:
    assert _normalize_sync_database_url(
        "postgresql://postgres:postgres@localhost:5432/layer1_ingestion"
    ) == "postgresql+psycopg2://postgres:postgres@localhost:5432/layer1_ingestion"


def test_normalize_sync_database_url_preserves_explicit_driver() -> None:
    explicit_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/layer1_ingestion"
    assert _normalize_sync_database_url(explicit_url) == explicit_url
