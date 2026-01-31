from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.orders import Order
from db.models.penalties import UserIssue, UserPenaltyConfig
from db.models.stores import Store

DEFAULT_DECAY_MONTHS = 12


def set_shipping_proof_deadline(
    order: Order,
    shipped_at: datetime | None = None,
) -> None:
    if order.tracking_type != "NO_TRACKING":
        return
    shipped_at_value = shipped_at or order.shipped_at or datetime.now(timezone.utc)
    order.shipped_at = shipped_at_value
    order.shipping_proof_deadline = shipped_at_value + timedelta(hours=48)


async def _get_penalty_config(db: AsyncSession) -> UserPenaltyConfig | None:
    stmt = select(UserPenaltyConfig).order_by(UserPenaltyConfig.id).limit(1)
    result = await db.execute(stmt)
    return result.scalars().first()


async def _create_user_issue(
    db: AsyncSession,
    user_id: int,
    now: datetime,
) -> UserIssue:
    penalty_config = await _get_penalty_config(db)
    decay_months = (
        penalty_config.issue_decay_months
        if penalty_config is not None
        else DEFAULT_DECAY_MONTHS
    )
    expires_at = now + timedelta(days=30 * decay_months)
    issue = UserIssue(
        user_id=user_id,
        issue_type="SHIPPING_VIOLATION",
        severity=3,
        description="Shipping proof not provided within deadline.",
        created_at=now,
        expires_at=expires_at,
    )
    db.add(issue)
    await db.flush()
    return issue


async def enforce_shipping_proof_deadlines(
    db: AsyncSession,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now(timezone.utc)
    stmt = select(Order).where(
        Order.tracking_type == "NO_TRACKING",
        Order.shipping_proof_deadline.is_not(None),
        Order.shipping_proof_deadline < current_time,
        Order.shipping_proof_url.is_(None),
        Order.status != "DISPUTED",
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()
    count = 0

    for order in orders:
        order.status = "DISPUTED"
        store = await db.get(Store, order.store_id)
        if store:
            await _create_user_issue(db, store.user_id, current_time)
        count += 1

    await db.flush()
    return count
