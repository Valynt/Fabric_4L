import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion'
from layer1_ingestion.shared.database import get_db_session
with get_db_session(tenant_id='test-tenant', require_tenant=True) as session:
    result = session.execute("SELECT current_database()").fetchone()
    print('current_database:', result[0])
