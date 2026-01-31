from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import FairShippingError
from db.models.penalties import UserIssue, UserPenaltyConfig
from db.models.shipping_fairness import (
    ShippingCostBenchmark,
    ShippingFairnessConfig,
    ShippingFairnessFlag,
)
from db.models.stores import Store


@dataclass
class ShippingValidation:
    valid: bool
    warning: str | None = None
    error_code: str | None = None
    message: str | None = None


DEFAULT_FAIRNESS_CONFIG = {
    "max_markup_percentage": Decimal("15.0"),
    "alert_threshold_percentage": Decimal("25.0"),
    "auto_flag_threshold": Decimal("50.0"),
}

DEFAULT_DECAY_MONTHS = 12


def validate_fair_shipping(shipping_cost: Decimal, benchmark_max: Decimal) -> None:
    if shipping_cost > benchmark_max:
        raise FairShippingError(
            shipping_cost=shipping_cost,
            benchmark_max=benchmark_max,
        )


async def get_fairness_config(db: AsyncSession) -> ShippingFairnessConfig:
    stmt = select(ShippingFairnessConfig).order_by(ShippingFairnessConfig.id).limit(1)
    result = await db.execute(stmt)
    config = result.scalars().first()
    if config:
        return config

    config = ShippingFairnessConfig(**DEFAULT_FAIRNESS_CONFIG)
    db.add(config)
    await db.flush()
    return config


async def get_penalty_config(db: AsyncSession) -> UserPenaltyConfig | None:
    stmt = select(UserPenaltyConfig).order_by(UserPenaltyConfig.id).limit(1)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_shipping_benchmark(
    db: AsyncSession,
    origin_country: str,
    destination_country: str,
    weight_grams: int,
) -> ShippingCostBenchmark | None:
    stmt = (
        select(ShippingCostBenchmark)
        .where(
            ShippingCostBenchmark.origin_country == origin_country,
            ShippingCostBenchmark.destination_country == destination_country,
            ShippingCostBenchmark.weight_min_grams <= weight_grams,
            ShippingCostBenchmark.weight_max_grams >= weight_grams,
        )
        .order_by(
            ShippingCostBenchmark.last_updated.desc().nullslast(),
            ShippingCostBenchmark.id.desc(),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def create_shipping_flag(
    db: AsyncSession,
    order_id: int,
    store_id: int,
    charged_cost: Decimal,
    estimated_cost: Decimal,
    markup: Decimal,
    flag_type: str,
) -> ShippingFairnessFlag:
    flag = ShippingFairnessFlag(
        order_id=order_id,
        store_id=store_id,
        charged_shipping=charged_cost,
        estimated_real_cost=estimated_cost,
        markup_percentage=markup,
        flag_type=flag_type,
    )
    db.add(flag)
    await db.flush()
    return flag


async def create_user_issue(
    db: AsyncSession,
    user_id: int,
    issue_type: str,
    severity: int,
    description: str | None = None,
) -> UserIssue:
    now = datetime.now(timezone.utc)
    penalty_config = await get_penalty_config(db)
    decay_months = (
        penalty_config.issue_decay_months
        if penalty_config is not None
        else DEFAULT_DECAY_MONTHS
    )
    expires_at = now + timedelta(days=30 * decay_months)
    issue = UserIssue(
        user_id=user_id,
        issue_type=issue_type,
        severity=severity,
        description=description,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(issue)
    await db.flush()
    return issue


async def validate_shipping_cost(
    origin_country: str,
    destination_country: str,
    weight_grams: int,
    charged_cost: Decimal,
    store_id: int,
    order_id: int,
    db: AsyncSession,
) -> ShippingValidation:
    """Validates if shipping cost is within acceptable limits."""
    benchmark = await get_shipping_benchmark(
        db,
        origin_country,
        destination_country,
        weight_grams,
    )

    if not benchmark:
        return ShippingValidation(valid=True, warning="No benchmark available")

    if benchmark.benchmark_cost <= 0:
        return ShippingValidation(valid=True, warning="Invalid benchmark cost")

    markup = ((charged_cost - benchmark.benchmark_cost) / benchmark.benchmark_cost) * 100
    config = await get_fairness_config(db)

    if markup > config.auto_flag_threshold:
        await create_shipping_flag(
            db,
            order_id,
            store_id,
            charged_cost,
            benchmark.benchmark_cost,
            markup,
            "VIOLATION",
        )
        store = await db.get(Store, store_id)
        if store:
            await create_user_issue(
                db,
                store.user_id,
                "SHIPPING_VIOLATION",
                severity=3,
            )
        return ShippingValidation(
            valid=False,
            error_code="SHIPPING_COST_EXCESSIVE",
            message=(
                f"Shipping cost {markup:.0f}% above benchmark"
            ),
        )

    if markup > config.alert_threshold_percentage:
        await create_shipping_flag(
            db,
            order_id,
            store_id,
            charged_cost,
            benchmark.benchmark_cost,
            markup,
            "WARNING",
        )

    return ShippingValidation(valid=True)
