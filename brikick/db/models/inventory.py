from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Lot(Base):
    __tablename__ = "lots"
    __table_args__ = (
        sa.Index("ix_lots_store_id", "store_id"),
        sa.Index("ix_lots_catalog_item_id", "catalog_item_id"),
        sa.Index("ix_lots_color_id", "color_id"),
        sa.Index("ix_lots_condition", "condition"),
        sa.Index("ix_lots_unit_price", "unit_price"),
        sa.Index("ix_lots_status", "status"),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    store_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("stores.id"),
        nullable=False,
    )
    catalog_item_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("catalog_items.id"),
        nullable=False,
    )
    color_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        sa.ForeignKey("colors.id"),
    )
    condition: Mapped[str] = mapped_column(sa.CHAR(1), nullable=False)
    completeness: Mapped[str | None] = mapped_column(sa.CHAR(1))
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    bulk_quantity: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
    )
    unit_price: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    sale_percentage: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    )
    tier1_qty: Mapped[int | None] = mapped_column(sa.Integer)
    tier1_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 4))
    tier2_qty: Mapped[int | None] = mapped_column(sa.Integer)
    tier2_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 4))
    tier3_qty: Mapped[int | None] = mapped_column(sa.Integer)
    tier3_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 4))
    superlot_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("lots.id"),
    )
    description: Mapped[str | None] = mapped_column(sa.Text)
    extended_description: Mapped[str | None] = mapped_column(sa.Text)
    custom_image_url: Mapped[str | None] = mapped_column(sa.String(500))
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'AVAILABLE'"),
    )
    listed_at: Mapped[datetime] = mapped_column(
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
    price_override_approved: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        server_default=sa.text("false"),
    )
    price_override_request_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("price_override_requests.id"),
    )
