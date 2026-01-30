from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ShippingFairnessConfig(Base):
    __tablename__ = "shipping_fairness_configs"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    max_markup_percentage: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2),
        nullable=False,
        server_default=sa.text("15.0"),
    )
    alert_threshold_percentage: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2),
        nullable=False,
        server_default=sa.text("25.0"),
    )
    auto_flag_threshold: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2),
        nullable=False,
        server_default=sa.text("50.0"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class ShippingCostBenchmark(Base):
    __tablename__ = "shipping_cost_benchmarks"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    origin_country: Mapped[str] = mapped_column(sa.CHAR(2), nullable=False)
    destination_country: Mapped[str] = mapped_column(sa.CHAR(2), nullable=False)
    destination_region: Mapped[str | None] = mapped_column(sa.String(50))
    carrier: Mapped[str | None] = mapped_column(sa.String(50))
    service_type: Mapped[str | None] = mapped_column(sa.String(50))
    weight_min_grams: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    weight_max_grams: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    benchmark_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
    )
    benchmark_currency: Mapped[str] = mapped_column(sa.CHAR(3), nullable=False)
    source: Mapped[str | None] = mapped_column(sa.String(50))
    last_updated: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )


class ShippingFairnessFlag(Base):
    __tablename__ = "shipping_fairness_flags"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("orders.id"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    charged_shipping: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
    )
    estimated_real_cost: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
    )
    markup_percentage: Mapped[Decimal] = mapped_column(
        sa.Numeric(5, 2),
        nullable=False,
    )
    flag_type: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'OPEN'"),
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    review_notes: Mapped[str | None] = mapped_column(sa.Text)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
