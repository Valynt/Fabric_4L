import os
os.environ['DATABASE_URL'] = 'postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion'
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
with engine.connect() as conn:
    result = conn.execute(text('''
        SELECT schemaname, tablename, policyname, qual, with_check
        FROM pg_policies
        WHERE schemaname = 'public'
          AND (qual ILIKE '%organization_id%' OR with_check ILIKE '%organization_id%')
    '''))
    org_policies = result.fetchall()
    print('Policies referencing organization_id:', len(org_policies))
    for p in org_policies:
        print('  ', p)

    result = conn.execute(text('''
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
          AND (qual ILIKE '%tenant_id%' OR with_check ILIKE '%tenant_id%')
    '''))
    tenant_policies = result.fetchall()
    print('Policies referencing tenant_id:', len(tenant_policies))
    for p in tenant_policies:
        print('  ', p)

    result = conn.execute(text('''
        SELECT relname, relrowsecurity, relforcerowsecurity
        FROM pg_class
        WHERE relname IN (
            'scraping_targets', 'scraping_jobs', 'raw_content',
            'extracted_data', 'compliance_logs', 'proxy_pools',
            'job_stage_details', 'job_errors', 'crawl_decisions'
        )
        AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
    '''))
    rls_tables = result.fetchall()
    print('RLS enabled tables:')
    for t in rls_tables:
        print('  ', t)
