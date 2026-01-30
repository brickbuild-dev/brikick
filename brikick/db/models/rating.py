from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class RatingFactor(Base):
    __tablename__ = "rating_factors"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    factor_code: Mapped[str] = mapped_column(
        sa.String(50),
        unique=True,
        nullable=False,
    )
    factor_name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)
    applies_to: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    weight: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2),
        nullable=False,
    )
    higher_is_better: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("true"),
    )


class SlaConfig(Base):
    __tablename__ = "sla_configs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    shipping_excellent_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("24"),
    )
    shipping_good_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("48"),
    )
    shipping_acceptable_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("72"),
    )
    message_excellent_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("24"),
    )
    message_good_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("48"),
    )
    message_acceptable_hours: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("72"),
    )


class UserRatingMetrics(Base):
    __tablename__ = "user_rating_metrics"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date, nullable=False)
    metrics_json: Mapped[dict | None] = mapped_column(JSONB)
    factor_scores: Mapped[dict | None] = mapped_column(JSONB)
    overall_score: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    score_tier: Mapped[str | None] = mapped_column(sa.String(20))
    calculated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


class SlaMetrics(Base):
    __tablename__ = "sla_metrics"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    period_start: Mapped[date] = mapped_column(sa.Date, nullable=False)
    period_end: Mapped[date] = mapped_column(sa.Date, nullable=False)
    orders_shipped_total: Mapped[int | None] = mapped_column(sa.Integer)
    orders_shipped_24h: Mapped[int | None] = mapped_column(sa.Integer)
    orders_shipped_48h: Mapped[int | None] = mapped_column(sa.Integer)
    orders_shipped_72h: Mapped[int | None] = mapped_column(sa.Integer)
    orders_shipped_late: Mapped[int | None] = mapped_column(sa.Integer)
    avg_shipping_hours: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2))
    messages_received: Mapped[int | None] = mapped_column(sa.Integer)
    messages_replied_24h: Mapped[int | None] = mapped_column(sa.Integer)
    messages_replied_48h: Mapped[int | None] = mapped_column(sa.Integer)
    messages_replied_72h: Mapped[int | None] = mapped_column(sa.Integer)
    shipping_sla_score: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    message_sla_score: Mapped[Decimal | None] = mapped_column(sa.Numeric(5, 2))
    calculated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )


class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    code: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(sa.Text)
    icon_url: Mapped[str | None] = mapped_column(sa.String(500))
    badge_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    criteria: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)


class UserBadge(Base):
    __tablename__ = "user_badges"

    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        primary_key=True,
    )
    badge_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("badges.id"),
        primary_key=True,
    )
    awarded_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
