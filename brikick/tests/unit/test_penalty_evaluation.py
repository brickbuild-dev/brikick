import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.penalty_service import evaluate_user_penalties, get_active_issues
from db.models.penalties import UserIssue, UserPenalty
from tests.factories.user_factory import UserFactory


class TestPenaltyEvaluation:
    """Tests for automatic penalty evaluation"""

    @pytest.mark.asyncio
    async def test_no_issues_no_penalty(self, db_session: AsyncSession):
        """User with no issues should have no penalty"""
        user = await UserFactory.create(db_session)

        await evaluate_user_penalties(user.id, db_session)

        penalty = await db_session.execute(
            select(UserPenalty).where(UserPenalty.user_id == user.id)
        )
        assert penalty.scalar_one_or_none() is None

    @pytest.mark.asyncio
    async def test_3_issues_triggers_warning(self, db_session: AsyncSession):
        """3 issues should trigger WARNING"""
        user = await UserFactory.create(db_session)

        for _ in range(3):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db_session.add(issue)
        await db_session.commit()

        await evaluate_user_penalties(user.id, db_session)

        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "WARNING")
        )
        assert penalty.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_5_issues_triggers_cooldown(self, db_session: AsyncSession):
        """5 issues should trigger COOLDOWN"""
        user = await UserFactory.create(db_session)

        for _ in range(5):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db_session.add(issue)
        await db_session.commit()

        await evaluate_user_penalties(user.id, db_session)

        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "COOLDOWN")
        )
        result = penalty.scalar_one_or_none()
        assert result is not None
        assert result.ends_at is not None

    @pytest.mark.asyncio
    async def test_8_issues_triggers_suspension(self, db_session: AsyncSession):
        """8 issues should trigger SUSPENSION"""
        user = await UserFactory.create(db_session)

        for _ in range(8):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db_session.add(issue)
        await db_session.commit()

        await evaluate_user_penalties(user.id, db_session)

        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "SUSPENSION")
        )
        result = penalty.scalar_one_or_none()
        assert result is not None
        assert result.restrictions.get("can_sell") is False

    @pytest.mark.asyncio
    async def test_12_issues_triggers_ban(self, db_session: AsyncSession):
        """12 issues should trigger permanent BAN"""
        user = await UserFactory.create(db_session)

        for _ in range(12):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db_session.add(issue)
        await db_session.commit()

        await evaluate_user_penalties(user.id, db_session)

        penalty = await db_session.execute(
            select(UserPenalty)
            .where(UserPenalty.user_id == user.id)
            .where(UserPenalty.penalty_type == "BAN")
        )
        result = penalty.scalar_one_or_none()
        assert result is not None
        assert result.ends_at is None

    @pytest.mark.asyncio
    async def test_expired_issues_not_counted(self, db_session: AsyncSession):
        """Expired issues should not count towards penalties"""
        user = await UserFactory.create(db_session)

        for _ in range(5):
            issue = UserIssue(
                user_id=user.id,
                issue_type="DISPUTE_LOST",
                severity=2,
                created_at=datetime.now(timezone.utc) - timedelta(days=400),
                expires_at=datetime.now(timezone.utc) - timedelta(days=35),
            )
            db_session.add(issue)
        await db_session.commit()

        active = await get_active_issues(db_session, user.id, months=6)
        assert active == 0

        await evaluate_user_penalties(user.id, db_session)

        penalty = await db_session.execute(
            select(UserPenalty).where(UserPenalty.user_id == user.id)
        )
        assert penalty.scalar_one_or_none() is None
