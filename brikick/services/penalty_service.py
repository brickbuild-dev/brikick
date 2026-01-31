from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.penalties import UserIssue, UserPenalty, UserPenaltyConfig


DEFAULT_CONFIG = {
    "warning_threshold": 3,
    "cooldown_threshold": 5,
    "suspension_threshold": 8,
    "ban_threshold": 12,
    "evaluation_period_months": 6,
    "issue_decay_months": 12,
}

PENALTY_SEVERITY = {
    "WARNING": 1,
    "COOLDOWN": 2,
    "SUSPENSION": 3,
    "BAN": 4,
}


async def get_penalty_config(db: AsyncSession) -> UserPenaltyConfig:
    stmt = select(UserPenaltyConfig).order_by(UserPenaltyConfig.id).limit(1)
    result = await db.execute(stmt)
    config = result.scalars().first()
    if config:
        return config

    config = UserPenaltyConfig(**DEFAULT_CONFIG)
    db.add(config)
    await db.flush()
    return config


async def count_active_issues(
    db: AsyncSession,
    user_id: int,
    evaluation_period_months: int,
) -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=30 * evaluation_period_months)
    stmt = (
        select(func.count())
        .select_from(UserIssue)
        .where(
            UserIssue.user_id == user_id,
            UserIssue.created_at >= cutoff,
            UserIssue.expires_at >= now,
        )
    )
    result = await db.execute(stmt)
    return int(result.scalar() or 0)


async def get_active_issues(
    db: AsyncSession,
    user_id: int,
    months: int,
) -> int:
    return await count_active_issues(db, user_id, months)


async def get_current_penalty(
    db: AsyncSession,
    user_id: int,
) -> UserPenalty | None:
    now = datetime.now(timezone.utc)
    stmt = (
        select(UserPenalty)
        .where(
            UserPenalty.user_id == user_id,
            UserPenalty.starts_at <= now,
            or_(UserPenalty.ends_at.is_(None), UserPenalty.ends_at >= now),
        )
        .order_by(UserPenalty.starts_at.desc())
    )
    result = await db.execute(stmt)
    return result.scalars().first()


def should_escalate(
    current_penalty: UserPenalty | None,
    new_type: str,
) -> bool:
    if current_penalty is None:
        return True
    current_rank = PENALTY_SEVERITY.get(current_penalty.penalty_type, 0)
    new_rank = PENALTY_SEVERITY.get(new_type, 0)
    return new_rank > current_rank


def build_restrictions(penalty_type: str) -> dict:
    if penalty_type == "BAN":
        return {"can_sell": False, "can_buy": False, "api_disabled": True}
    if penalty_type == "SUSPENSION":
        return {"can_sell": False, "can_buy": False}
    if penalty_type == "COOLDOWN":
        return {"can_sell": False}
    return {}


async def apply_penalty(
    db: AsyncSession,
    user_id: int,
    penalty_type: str,
    duration: timedelta | None,
) -> UserPenalty:
    now = datetime.now(timezone.utc)
    ends_at = None if duration is None else now + duration
    penalty = UserPenalty(
        user_id=user_id,
        penalty_type=penalty_type,
        reason_code="AUTO_THRESHOLD",
        description="Automatic penalty based on active issues.",
        starts_at=now,
        ends_at=ends_at,
        restrictions=build_restrictions(penalty_type),
        created_by=None,
        created_at=now,
    )
    db.add(penalty)
    await db.flush()
    return penalty


async def evaluate_user_penalties(user_id: int, db: AsyncSession) -> None:
    """Called by daily job or after a new issue."""
    config = await get_penalty_config(db)

    active_issues = await count_active_issues(
        db,
        user_id,
        config.evaluation_period_months,
    )

    current_penalty = await get_current_penalty(db, user_id)

    if active_issues >= config.ban_threshold:
        new_type = "BAN"
        duration = None
    elif active_issues >= config.suspension_threshold:
        new_type = "SUSPENSION"
        duration = timedelta(days=30)
    elif active_issues >= config.cooldown_threshold:
        new_type = "COOLDOWN"
        duration = timedelta(days=7)
    elif active_issues >= config.warning_threshold:
        new_type = "WARNING"
        duration = timedelta(days=0)
    else:
        return

    if should_escalate(current_penalty, new_type):
        await apply_penalty(db, user_id, new_type, duration)
