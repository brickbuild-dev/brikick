from __future__ import annotations

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class UserPenaltyConfig(Base):
    __tablename__ = "user_penalty_configs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    warning_threshold: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("3"),
    )
    cooldown_threshold: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("5"),
    )
    suspension_threshold: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("8"),
    )
    ban_threshold: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("12"),
    )
    evaluation_period_months: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("6"),
    )
    issue_decay_months: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("12"),
    )


class UserIssue(Base):
    __tablename__ = "user_issues"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    issue_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    severity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    related_order_id: Mapped[int | None] = mapped_column(sa.BigInteger)
    related_dispute_id: Mapped[int | None] = mapped_column(sa.BigInteger)
    description: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )


class UserPenalty(Base):
    __tablename__ = "user_penalties"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    penalty_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    reason_code: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)
    starts_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
    )
    ends_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    restrictions: Mapped[dict | None] = mapped_column(JSONB)
    appeal_status: Mapped[str | None] = mapped_column(sa.String(20))
    appeal_text: Mapped[str | None] = mapped_column(sa.Text)
    appeal_reviewed_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    appeal_reviewed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    created_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
