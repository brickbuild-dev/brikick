from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.orders import Order, OrderItem
from tests.factories.user_factory import UserFactory

faker = Faker()


class OrderFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        buyer_id: int | None = None,
        store_id: int,
        status: str = "PENDING",
        items_total: Decimal | None = None,
        shipping_cost: Decimal | None = None,
        shipped_within_hours: int | None = None,
        **kwargs,
    ) -> Order:
        if buyer_id is None:
            buyer = await UserFactory.create(db)
            buyer_id = buyer.id

        items_total = items_total or Decimal("10.00")
        shipping_cost = shipping_cost or Decimal("3.00")
        grand_total = items_total + shipping_cost

        created_at = kwargs.pop("created_at", datetime.now(timezone.utc))
        shipped_at = kwargs.pop("shipped_at", None)
        if shipped_within_hours is not None:
            shipped_at = created_at + timedelta(hours=shipped_within_hours)

        order_id = kwargs.pop("id", faker.unique.random_int(min=1, max=10_000_000))
        order = Order(
            id=order_id,
            order_number=f"BK-2026-{faker.unique.random_int(min=10000, max=99999)}",
            buyer_id=buyer_id,
            store_id=store_id,
            status=status,
            items_total=items_total,
            shipping_cost=shipping_cost,
            insurance_cost=Decimal("0"),
            tax_amount=Decimal("0"),
            grand_total=grand_total,
            tracking_type="NO_TRACKING",
            created_at=created_at,
            shipped_at=shipped_at,
            **kwargs,
        )
        db.add(order)
        await db.commit()
        await db.refresh(order)
        return order

    @staticmethod
    async def add_item(
        db: AsyncSession,
        *,
        order_id: int,
        lot_id: int,
        quantity: int = 1,
        unit_price: Decimal | None = None,
    ) -> OrderItem:
        unit_price = unit_price or Decimal("10.0000")
        line_total = unit_price * quantity
        item_id = faker.unique.random_int(min=1, max=10_000_000)
        item = OrderItem(
            id=item_id,
            order_id=order_id,
            lot_id=lot_id,
            item_snapshot=None,
            quantity=quantity,
            unit_price=unit_price,
            sale_price=None,
            line_total=line_total,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item
