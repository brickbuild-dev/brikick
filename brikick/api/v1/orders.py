from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from db.models.orders import Order
from db.models.users import User

orders_router = APIRouter(prefix="/orders", tags=["orders"])


@orders_router.get("")
async def list_orders(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(Order).where(Order.buyer_id == current_user.id)
    )
    orders = result.scalars().all()
    return {
        "orders": [
            {
                "id": order.id,
                "order_number": order.order_number,
                "status": order.status,
                "items_total": float(order.items_total),
                "grand_total": float(order.grand_total),
            }
            for order in orders
        ]
    }
