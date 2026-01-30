from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.catalog import PriceGuide, PriceOverrideRequest


@dataclass
class PriceValidationResult:
    valid: bool
    error_code: str | None = None
    message: str | None = None
    data: dict | None = None
    actions: list[str] | None = None


async def get_approved_override(
    db: AsyncSession,
    store_id: int,
    catalog_item_id: int,
    color_id: int,
    condition: str,
) -> PriceOverrideRequest | None:
    stmt = (
        select(PriceOverrideRequest)
        .where(
            PriceOverrideRequest.store_id == store_id,
            PriceOverrideRequest.catalog_item_id == catalog_item_id,
            PriceOverrideRequest.color_id == color_id,
            PriceOverrideRequest.condition == condition,
            PriceOverrideRequest.status == "APPROVED",
        )
        .order_by(
            PriceOverrideRequest.reviewed_at.desc().nullslast(),
            PriceOverrideRequest.created_at.desc(),
        )
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def validate_lot_price(
    db: AsyncSession,
    catalog_item_id: int,
    color_id: int,
    condition: str,
    unit_price: Decimal,
    store_id: int,
) -> PriceValidationResult:
    """
    HARD RULE #1: Preco nao pode exceder 2x o avg 6 meses
    """
    price_guide_stmt = select(PriceGuide).where(
        PriceGuide.catalog_item_id == catalog_item_id,
        PriceGuide.color_id == color_id,
        PriceGuide.condition == condition,
    )
    price_guide_result = await db.execute(price_guide_stmt)
    price_guide = price_guide_result.scalars().first()

    if not price_guide or not price_guide.price_cap:
        # Sem dados suficientes, permitir (mas flag para review)
        return PriceValidationResult(valid=True)

    if unit_price > price_guide.price_cap:
        # Verificar se ha override aprovado
        override = await get_approved_override(
            db,
            store_id,
            catalog_item_id,
            color_id,
            condition,
        )
        if override and unit_price <= override.requested_price:
            return PriceValidationResult(valid=True)

        return PriceValidationResult(
            valid=False,
            error_code="PRICE_CAP_EXCEEDED",
            message=(
                f"Preco {unit_price} excede o cap de {price_guide.price_cap} "
                f"(2x avg 6m: {price_guide.avg_price_6m})"
            ),
            data={
                "your_price": float(unit_price),
                "avg_6m": float(price_guide.avg_price_6m),
                "price_cap": float(price_guide.price_cap),
                "max_allowed": float(price_guide.price_cap),
            },
            actions=["REQUEST_OVERRIDE", "ADJUST_PRICE"],
        )

    return PriceValidationResult(valid=True)
