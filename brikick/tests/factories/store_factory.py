from __future__ import annotations

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.stores import Store, StorePaymentMethod, StoreShippingMethod

faker = Faker()


class StoreFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        user_id: int,
        name: str | None = None,
        slug: str | None = None,
        status: str = "ACTIVE",
        currency_id: int = 978,
    ) -> Store:
        store = Store(
            user_id=user_id,
            name=name or faker.company(),
            slug=slug or faker.unique.slug(),
            country_code="PT",
            currency_id=currency_id,
            feedback_score=0,
            status=status,
            min_buy_amount=None,
            instant_checkout_enabled=True,
            require_approval_for_risky_buyers=False,
            risk_threshold_score=50.0,
        )
        db.add(store)
        await db.flush()
        return store

    @staticmethod
    async def create_shipping_method(
        db: AsyncSession,
        *,
        store_id: int,
        name: str | None = None,
        base_cost: float = 3.50,
    ) -> StoreShippingMethod:
        method = StoreShippingMethod(
            store_id=store_id,
            name=name or "Standard",
            cost_type="FIXED",
            base_cost=base_cost,
            tracking_type="NO_TRACKING",
            is_active=True,
        )
        db.add(method)
        await db.flush()
        return method

    @staticmethod
    async def create_payment_method(
        db: AsyncSession,
        *,
        store_id: int,
        name: str | None = None,
        method_type: str = "CARD",
    ) -> StorePaymentMethod:
        method = StorePaymentMethod(
            store_id=store_id,
            method_type=method_type,
            name=name or "Card",
            is_on_site=True,
            is_active=True,
        )
        db.add(method)
        await db.flush()
        return method
