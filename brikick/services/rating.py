from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.orders import Order
from db.models.stores import Store


@dataclass(frozen=True)
class RatingInputs:
    shipments_sla_score: float
    response_sla_score: float
    dispute_score: float
    cancellation_score: float
    price_fairness_score: float
    activity_score: float


WEIGHTS = {
    "shipments_sla_score": 0.25,
    "response_sla_score": 0.2,
    "dispute_score": 0.2,
    "cancellation_score": 0.15,
    "price_fairness_score": 0.1,
    "activity_score": 0.1,
}


def compute_rating_score(inputs: RatingInputs) -> float:
    weighted = (
        inputs.shipments_sla_score * WEIGHTS["shipments_sla_score"]
        + inputs.response_sla_score * WEIGHTS["response_sla_score"]
        + inputs.dispute_score * WEIGHTS["dispute_score"]
        + inputs.cancellation_score * WEIGHTS["cancellation_score"]
        + inputs.price_fairness_score * WEIGHTS["price_fairness_score"]
        + inputs.activity_score * WEIGHTS["activity_score"]
    )
    return round(weighted, 4)


@dataclass(frozen=True)
class SlaScore:
    shipping_sla_score: float


@dataclass(frozen=True)
class UserRatingResult:
    user_id: int
    overall_score: float
    score_tier: str


@dataclass(frozen=True)
class AwardedBadge:
    code: str
    valid_until: datetime | None


async def calculate_sla_score(db: AsyncSession, store_id: int) -> SlaScore:
    stmt = select(Order).where(
        Order.store_id == store_id,
        Order.shipped_at.is_not(None),
    )
    result = await db.execute(stmt)
    orders = result.scalars().all()

    if not orders:
        return SlaScore(shipping_sla_score=0.0)

    total = len(orders)
    weighted_sum = 0.0

    for order in orders:
        created_at = order.created_at or order.shipped_at
        if not created_at or not order.shipped_at:
            continue
        hours = (order.shipped_at - created_at).total_seconds() / 3600
        if hours <= 24:
            weight = 1.0
        elif hours <= 48:
            weight = 0.8
        elif hours <= 72:
            weight = 0.5
        else:
            weight = 0.0
        weighted_sum += weight

    score = (weighted_sum / total) * 100
    return SlaScore(shipping_sla_score=round(score, 1))


async def calculate_user_rating(db: AsyncSession, user_id: int) -> UserRatingResult:
    store_stmt = select(Store).where(Store.user_id == user_id).limit(1)
    store_result = await db.execute(store_stmt)
    store = store_result.scalars().first()

    if not store:
        return UserRatingResult(user_id=user_id, overall_score=50.0, score_tier="AVERAGE")

    sla_score = await calculate_sla_score(db, store.id)
    if sla_score.shipping_sla_score == 0.0:
        overall = 50.0
    else:
        overall = 50.0 + (sla_score.shipping_sla_score - 50.0) * 0.7
    overall = max(0.0, min(100.0, round(overall, 2)))

    if overall >= 85:
        tier = "EXCELLENT"
    elif overall >= 70:
        tier = "GOOD"
    elif overall >= 50:
        tier = "AVERAGE"
    elif overall >= 30:
        tier = "POOR"
    else:
        tier = "CRITICAL"

    return UserRatingResult(user_id=user_id, overall_score=overall, score_tier=tier)


async def evaluate_badges(
    db: AsyncSession,
    user_id: int,
    overall_score: float | None = None,
    shipping_sla_score: float | None = None,
) -> list[AwardedBadge]:
    awarded: list[AwardedBadge] = []
    now = datetime.now(timezone.utc)
    monthly_valid_until = now + timedelta(days=30)

    if overall_score is not None and overall_score >= 85:
        awarded.append(AwardedBadge(code="TRUSTED_SELLER", valid_until=monthly_valid_until))

    if shipping_sla_score is not None and shipping_sla_score >= 95:
        awarded.append(AwardedBadge(code="FAST_SHIPPER", valid_until=monthly_valid_until))

    return awarded
