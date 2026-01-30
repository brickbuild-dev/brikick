from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from db.models.rating import UserRatingMetrics


class RatingFactory:
    @staticmethod
    async def create_user_metrics(
        db: AsyncSession,
        *,
        user_id: int,
        overall_score: Decimal | None = None,
        score_tier: str | None = None,
    ) -> UserRatingMetrics:
        metrics = UserRatingMetrics(
            user_id=user_id,
            period_start=date.today(),
            period_end=date.today(),
            metrics_json=None,
            factor_scores=None,
            overall_score=overall_score or Decimal("75.0"),
            score_tier=score_tier or "GOOD",
            calculated_at=datetime.now(timezone.utc),
        )
        db.add(metrics)
        await db.flush()
        return metrics
