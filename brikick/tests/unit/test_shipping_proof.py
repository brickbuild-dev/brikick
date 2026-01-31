from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from db.models.penalties import UserIssue
from services.shipping_proof import (
    enforce_shipping_proof_deadlines,
    set_shipping_proof_deadline,
)
from tests.factories.order_factory import OrderFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestShippingProofDeadlines:
    @pytest.mark.asyncio
    async def test_set_shipping_proof_deadline_sets_48h(self, db_session):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        order = await OrderFactory.create(
            db_session,
            store_id=store.id,
            tracking_type="NO_TRACKING",
        )

        shipped_at = datetime.now(timezone.utc)
        set_shipping_proof_deadline(order, shipped_at=shipped_at)
        await db_session.commit()
        await db_session.refresh(order)

        assert order.shipping_proof_deadline == shipped_at + timedelta(hours=48)

    @pytest.mark.asyncio
    async def test_enforce_deadline_marks_disputed_and_creates_issue(self, db_session):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        now = datetime.now(timezone.utc)
        order = await OrderFactory.create(
            db_session,
            store_id=store.id,
            tracking_type="NO_TRACKING",
            status="SHIPPED",
            shipped_at=now - timedelta(days=3),
            shipping_proof_deadline=now - timedelta(days=1),
            shipping_proof_url=None,
        )

        updated = await enforce_shipping_proof_deadlines(db_session, now=now)
        await db_session.commit()
        await db_session.refresh(order)

        assert updated == 1
        assert order.status == "DISPUTED"

        issue_result = await db_session.execute(
            select(UserIssue).where(UserIssue.user_id == store.user_id)
        )
        issue = issue_result.scalar_one_or_none()
        assert issue is not None
        assert issue.issue_type == "SHIPPING_VIOLATION"
