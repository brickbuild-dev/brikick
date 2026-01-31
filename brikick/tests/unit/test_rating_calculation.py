import pytest
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from services.rating import (
    calculate_user_rating,
    calculate_sla_score,
    evaluate_badges,
)
from tests.factories.user_factory import UserFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.order_factory import OrderFactory


class TestSLACalculation:
    """Tests for SLA score calculation"""

    @pytest.mark.asyncio
    async def test_all_orders_shipped_24h_gets_100(self, db_session: AsyncSession):
        """100% orders shipped within 24h = score 100"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)

        for _ in range(10):
            await OrderFactory.create(
                db_session,
                store_id=store.id,
                shipped_within_hours=12,
            )

        score = await calculate_sla_score(db_session, store.id)
        assert score.shipping_sla_score == 100.0

    @pytest.mark.asyncio
    async def test_mixed_shipping_times_weighted_correctly(self, db_session: AsyncSession):
        """Mixed shipping times should be weighted: 24h=100%, 48h=80%, 72h=50%, late=0%"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)

        for _ in range(5):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=20)
        for _ in range(3):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=40)
        for _ in range(2):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=60)

        score = await calculate_sla_score(db_session, store.id)
        assert score.shipping_sla_score == pytest.approx(84.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_late_orders_penalize_heavily(self, db_session: AsyncSession):
        """Orders shipped after 72h should contribute 0 to score"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)

        for _ in range(5):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=24)
        for _ in range(5):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=100)

        score = await calculate_sla_score(db_session, store.id)
        assert score.shipping_sla_score == 50.0


class TestRatingCalculation:
    """Tests for overall rating calculation"""

    @pytest.mark.asyncio
    async def test_new_seller_starts_with_neutral_rating(self, db_session: AsyncSession):
        """New seller without history should have neutral rating"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        await StoreFactory.create(db_session, user_id=seller.id)

        rating = await calculate_user_rating(db_session, seller.id)
        assert rating.overall_score == pytest.approx(50.0, abs=5)
        assert rating.score_tier == "AVERAGE"

    @pytest.mark.asyncio
    async def test_excellent_seller_gets_high_rating(self, db_session: AsyncSession):
        """Seller with excellent metrics should get high rating"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)

        for _ in range(20):
            await OrderFactory.create(db_session, store_id=store.id, shipped_within_hours=12)

        rating = await calculate_user_rating(db_session, seller.id)
        assert rating.overall_score >= 85.0
        assert rating.score_tier == "EXCELLENT"


class TestBadgeAward:
    """Tests for badge awarding"""

    @pytest.mark.asyncio
    async def test_trusted_seller_badge_requires_85_score(self, db_session: AsyncSession):
        """Trusted Seller badge requires overall score >= 85"""
        seller = await UserFactory.create(db_session, roles=["seller"])

        badges = await evaluate_badges(db_session, seller.id, overall_score=90.0)
        assert any(b.code == "TRUSTED_SELLER" for b in badges)

    @pytest.mark.asyncio
    async def test_fast_shipper_badge_requires_95_sla(self, db_session: AsyncSession):
        """Fast Shipper badge requires shipping SLA >= 95%"""
        seller = await UserFactory.create(db_session, roles=["seller"])

        badges = await evaluate_badges(
            db_session,
            seller.id,
            shipping_sla_score=96.0,
        )
        assert any(b.code == "FAST_SHIPPER" for b in badges)

    @pytest.mark.asyncio
    async def test_monthly_badges_expire(self, db_session: AsyncSession):
        """Monthly badges should have valid_until set"""
        seller = await UserFactory.create(db_session, roles=["seller"])

        badges = await evaluate_badges(db_session, seller.id, overall_score=90.0)

        trusted_seller = next(b for b in badges if b.code == "TRUSTED_SELLER")
        assert trusted_seller.valid_until is not None
        assert trusted_seller.valid_until > datetime.now(timezone.utc)
