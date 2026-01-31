from decimal import Decimal

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.stores import Store

fake = Faker()


class StoreFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        user_id: int,
        name: str = None,
        **kwargs,
    ) -> Store:
        status = kwargs.pop("status", "ACTIVE")
        min_buy_amount = kwargs.pop("min_buy_amount", Decimal("5.00"))
        store_id = kwargs.pop("id", fake.unique.random_int(min=1, max=10_000_000))
        store = Store(
            id=store_id,
            user_id=user_id,
            name=name or fake.company(),
            slug=fake.slug(),
            country_code="PT",
            currency_id=2,
            status=status,
            min_buy_amount=min_buy_amount,
            **kwargs,
        )
        db.add(store)
        await db.commit()
        await db.refresh(store)
        return store
