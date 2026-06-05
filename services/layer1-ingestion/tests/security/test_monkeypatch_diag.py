import pytest
from sqlalchemy import text

pytestmark = pytest.mark.requires_postgres


@pytest.fixture
def diag(postgres_db):
    import layer1_ingestion.shared.database as db_module
    print(f"ENGINE URL: {db_module.engine.url}")
    print(f"SESSIONLOCAL BIND: {db_module.SessionLocal.kw['bind'].url}")
    with db_module.SessionLocal() as s:
        result = s.execute(text("SELECT current_database()")).fetchone()
        print(f"DB FROM SessionLocal: {result[0]}")
    with db_module.get_db_session(tenant_id='test', require_tenant=True) as s:
        result = s.execute(text("SELECT current_database()")).fetchone()
        print(f"DB FROM get_db_session: {result[0]}")
    return True

def test_diag(diag):
    assert diag
