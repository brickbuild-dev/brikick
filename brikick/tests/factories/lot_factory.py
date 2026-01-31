from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.inventory import Lot


class LotFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        store_id: int,
        catalog_item_id: int,
        unit_price: Decimal = Decimal("0.50"),
        quantity: int = 10,
        **kwargs,
    ) -> Lot:
        lot_id = kwargs.pop("id", None)
        if lot_id is None:
            from faker import Faker

            fake = Faker()
            lot_id = fake.unique.random_int(min=1, max=10_000_000)
        status = kwargs.pop("status", "AVAILABLE")
        color_id = kwargs.pop("color_id", 0)
        condition = kwargs.pop("condition", "N")
        lot = Lot(
            id=lot_id,
            store_id=store_id,
            catalog_item_id=catalog_item_id,
            color_id=color_id,
            condition=condition,
            quantity=quantity,
            unit_price=unit_price,
            status=status,
            **kwargs,
        )
        db.add(lot)
        await db.commit()
        await db.refresh(lot)
        return lot
