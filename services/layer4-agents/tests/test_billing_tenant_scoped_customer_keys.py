from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from layer4_agents.models.billing import (
    BillingCustomer,
    BillingPlanVersion,
    BillingSubscription,
)


@pytest.fixture(scope="function")
def billing_db(postgres_container):
    """Create isolated billing tables for each test."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    username = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname

    database_url = f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
    engine = create_engine(database_url)

    # Create billing tables
    BillingCustomer.__table__.create(engine, checkfirst=True)
    BillingPlanVersion.__table__.create(engine, checkfirst=True)
    BillingSubscription.__table__.create(engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Bypass tenant context enforcement for billing tests
    from layer4_agents.database import _mark_session_tenant_bypass
    _mark_session_tenant_bypass(session, reason="billing_test")

    yield session

    session.close()
    # Drop tables for cleanup
    BillingSubscription.__table__.drop(engine)
    BillingPlanVersion.__table__.drop(engine)
    BillingCustomer.__table__.drop(engine)


@pytest.mark.postgres
def test_same_logical_customer_id_can_exist_in_multiple_tenants(billing_db: Session) -> None:
    """Test that same logical customer_id can exist across tenants (PostgreSQL required for JSONB)."""
    billing_db.add_all([
        BillingCustomer(id="cust_1", tenant_id="tenant_a", email="a@example.com"),
        BillingCustomer(id="cust_1", tenant_id="tenant_b", email="b@example.com"),
    ])
    billing_db.commit()

    rows = billing_db.query(BillingCustomer).filter(BillingCustomer.id == "cust_1").all()
    assert len(rows) == 2
    assert {row.tenant_id for row in rows} == {"tenant_a", "tenant_b"}


@pytest.mark.postgres
def test_subscription_fk_is_scoped_by_tenant_and_customer(billing_db: Session) -> None:
    """Test subscription FK is scoped by tenant and customer (PostgreSQL required for JSONB)."""
    billing_db.add(BillingCustomer(id="cust_1", tenant_id="tenant_a", email="a@example.com"))
    billing_db.commit()

    billing_db.add(
        BillingSubscription(
            id="sub_1",
            tenant_id="tenant_a",
            customer_id="cust_1",
            plan_id="free",
            status="active",
        )
    )
    billing_db.commit()

    stored = billing_db.query(BillingSubscription).one()
    assert stored.tenant_id == "tenant_a"
    assert stored.customer_id == "cust_1"
