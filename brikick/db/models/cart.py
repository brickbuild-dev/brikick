from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
        unique=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class CartStore(Base):
    __tablename__ = "cart_stores"
    __table_args__ = (
        sa.UniqueConstraint(
            "cart_id",
            "store_id",
            name="uq_cart_stores_cart_store",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    cart_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("carts.id"),
        nullable=False,
    )
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    total_items: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    total_lots: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    subtotal: Mapped[Decimal] = mapped_column(
        sa.Numeric(12, 2),
        nullable=False,
        server_default=sa.text("0"),
    )
    total_weight_grams: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
    )


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        sa.UniqueConstraint(
            "cart_store_id",
            "lot_id",
            name="uq_cart_items_cart_store_lot",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    cart_store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("cart_stores.id"),
        nullable=False,
    )
    lot_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("lots.id"),
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    sale_price_snapshot: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 4))
    warnings: Mapped[dict | None] = mapped_column(JSONB)
    added_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
