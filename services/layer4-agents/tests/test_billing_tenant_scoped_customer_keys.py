from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from value_fabric.layer4.database import Base
from value_fabric.layer4.models.billing import BillingCustomer, BillingSubscription


def test_same_logical_customer_id_can_exist_in_multiple_tenants() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all([
            BillingCustomer(id="cust_1", tenant_id="tenant_a", email="a@example.com"),
            BillingCustomer(id="cust_1", tenant_id="tenant_b", email="b@example.com"),
        ])
        session.commit()

        rows = session.query(BillingCustomer).filter(BillingCustomer.id == "cust_1").all()
        assert len(rows) == 2
        assert {row.tenant_id for row in rows} == {"tenant_a", "tenant_b"}


def test_subscription_fk_is_scoped_by_tenant_and_customer() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(BillingCustomer(id="cust_1", tenant_id="tenant_a", email="a@example.com"))
        session.commit()

        session.add(
            BillingSubscription(
                id="sub_1",
                tenant_id="tenant_a",
                customer_id="cust_1",
                plan_id="free",
                status="active",
            )
        )
        session.commit()

        stored = session.query(BillingSubscription).one()
        assert stored.tenant_id == "tenant_a"
        assert stored.customer_id == "cust_1"
