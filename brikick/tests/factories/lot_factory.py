from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.inventory import Lot


class LotFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        store_id: int,
        catalog_item_id: int,
        color_id: int | None = None,
        quantity: int = 5,
        unit_price: Decimal | None = None,
        status: str = "AVAILABLE",
    ) -> Lot:
        lot = Lot(
            store_id=store_id,
            catalog_item_id=catalog_item_id,
            color_id=color_id,
            condition="N",
            completeness="C",
            quantity=quantity,
            bulk_quantity=1,
            unit_price=unit_price or Decimal("2.5000"),
            sale_percentage=0,
            status=status,
            price_override_approved=False,
        )
        db.add(lot)
        await db.flush()
        return lot
