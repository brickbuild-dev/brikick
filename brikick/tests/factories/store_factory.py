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
        store = Store(
            user_id=user_id,
            name=name or fake.company(),
            slug=fake.slug(),
            country_code="PT",
            currency_id=2,
            status="ACTIVE",
            min_buy_amount=Decimal("5.00"),
            **kwargs,
        )
        db.add(store)
        await db.commit()
        await db.refresh(store)
        return store
