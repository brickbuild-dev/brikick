from decimal import Decimal

import pytest
from sqlalchemy import select

from db.models.penalties import UserIssue
from db.models.shipping_fairness import ShippingCostBenchmark, ShippingFairnessFlag
from services.shipping_fairness import validate_fair_shipping, validate_shipping_cost
from tests.factories.order_factory import OrderFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


def test_validate_fair_shipping_allows_within_benchmark():
    validate_fair_shipping(Decimal("5.00"), Decimal("10.00"))


class TestShippingFairnessValidation:
    @pytest.mark.asyncio
    async def test_no_benchmark_returns_warning(self, db_session):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        order = await OrderFactory.create(db_session, store_id=store.id)

        result = await validate_shipping_cost(
            origin_country="PT",
            destination_country="ES",
            weight_grams=500,
            charged_cost=Decimal("5.00"),
            store_id=store.id,
            order_id=order.id,
            db=db_session,
        )
        assert result.valid is True
        assert result.warning == "No benchmark available"

    @pytest.mark.asyncio
    async def test_markup_warning_creates_flag(self, db_session):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        order = await OrderFactory.create(db_session, store_id=store.id)

        benchmark = ShippingCostBenchmark(
            origin_country="PT",
            destination_country="ES",
            destination_region=None,
            carrier="CTT",
            service_type="STANDARD",
            weight_min_grams=0,
            weight_max_grams=1000,
            benchmark_cost=Decimal("10.00"),
            benchmark_currency="EUR",
            source="MANUAL",
        )
        db_session.add(benchmark)
        await db_session.commit()

        result = await validate_shipping_cost(
            origin_country="PT",
            destination_country="ES",
            weight_grams=500,
            charged_cost=Decimal("13.00"),
            store_id=store.id,
            order_id=order.id,
            db=db_session,
        )
        assert result.valid is True

        flag_result = await db_session.execute(
            select(ShippingFairnessFlag).where(ShippingFairnessFlag.order_id == order.id)
        )
        flag = flag_result.scalar_one_or_none()
        assert flag is not None
        assert flag.flag_type == "WARNING"

        issue_result = await db_session.execute(
            select(UserIssue).where(UserIssue.user_id == store.user_id)
        )
        assert issue_result.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_markup_violation_creates_issue(self, db_session):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        order = await OrderFactory.create(db_session, store_id=store.id)

        benchmark = ShippingCostBenchmark(
            origin_country="PT",
            destination_country="ES",
            destination_region=None,
            carrier="CTT",
            service_type="STANDARD",
            weight_min_grams=0,
            weight_max_grams=1000,
            benchmark_cost=Decimal("10.00"),
            benchmark_currency="EUR",
            source="MANUAL",
        )
        db_session.add(benchmark)
        await db_session.commit()

        result = await validate_shipping_cost(
            origin_country="PT",
            destination_country="ES",
            weight_grams=500,
            charged_cost=Decimal("20.00"),
            store_id=store.id,
            order_id=order.id,
            db=db_session,
        )
        assert result.valid is False
        assert result.error_code == "SHIPPING_COST_EXCESSIVE"

        flag_result = await db_session.execute(
            select(ShippingFairnessFlag).where(ShippingFairnessFlag.order_id == order.id)
        )
        flag = flag_result.scalar_one_or_none()
        assert flag is not None
        assert flag.flag_type == "VIOLATION"

        issue_result = await db_session.execute(
            select(UserIssue).where(UserIssue.user_id == store.user_id)
        )
        issue = issue_result.scalar_one_or_none()
        assert issue is not None
        assert issue.issue_type == "SHIPPING_VIOLATION"
