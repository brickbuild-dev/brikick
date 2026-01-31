from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class ItemType(Base):
    __tablename__ = "item_types"

    id: Mapped[str] = mapped_column(sa.CHAR(1), primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    name_plural: Mapped[str] = mapped_column(sa.String(50), nullable=False)


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        sa.ForeignKey("categories.id"),
    )
    allowed_item_types: Mapped[str | None] = mapped_column(sa.String(20))


class Color(Base):
    __tablename__ = "colors"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    rgb: Mapped[str | None] = mapped_column(sa.String(6))
    color_group: Mapped[int | None] = mapped_column(sa.Integer)


class CatalogItem(Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        sa.UniqueConstraint(
            "item_no",
            "item_type",
            "item_seq",
            name="uq_catalog_items_item_no_type_seq",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    item_no: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    item_seq: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        server_default=sa.text("1"),
    )
    item_type: Mapped[str] = mapped_column(
        sa.CHAR(1),
        sa.ForeignKey("item_types.id"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(sa.String(500), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        sa.Integer,
        sa.ForeignKey("categories.id"),
    )
    year_released: Mapped[int | None] = mapped_column(sa.SmallInteger)
    weight_grams: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2))
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'ACTIVE'"),
    )


class CatalogItemMapping(Base):
    __tablename__ = "catalog_item_mappings"
    __table_args__ = (
        sa.Index(
            "ix_catalog_item_mappings_source_external_id",
            "source",
            "external_id",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    catalog_item_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("catalog_items.id"),
        nullable=False,
    )
    source: Mapped[str] = mapped_column(sa.String(20), nullable=False)
    external_id: Mapped[str] = mapped_column(sa.String(100), nullable=False)


class PriceGuide(Base):
    __tablename__ = "price_guides"
    __table_args__ = (
        sa.UniqueConstraint(
            "catalog_item_id",
            "color_id",
            "condition",
            name="uq_price_guides_item_color_condition",
        ),
    )

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    catalog_item_id: Mapped[int] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("catalog_items.id"),
        nullable=False,
    )
    color_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("colors.id"),
        nullable=False,
    )
    condition: Mapped[str] = mapped_column(sa.CHAR(1), nullable=False)
    avg_price_6m: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    min_price_6m: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    max_price_6m: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    sales_count_6m: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
    )
    price_cap: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        sa.Computed("avg_price_6m * 2.0", persisted=True),
    )
    last_calculated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )


class PriceOverrideRequest(Base):
    __tablename__ = "price_override_requests"

    id: Mapped[int] = mapped_column(sa.BigInteger, primary_key=True)
    lot_id: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey(
            "lots.id",
            name="fk_price_override_requests_lot_id",
            use_alter=True,
        ),
    )
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
    color_id: Mapped[int] = mapped_column(
        sa.Integer,
        sa.ForeignKey("colors.id"),
        nullable=False,
    )
    condition: Mapped[str] = mapped_column(sa.CHAR(1), nullable=False)
    requested_price: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    price_cap: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 4),
        nullable=False,
    )
    justification: Mapped[str] = mapped_column(sa.Text, nullable=False)
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        server_default=sa.text("'PENDING'"),
    )
    reviewed_by: Mapped[int | None] = mapped_column(
        sa.BigInteger,
        sa.ForeignKey("users.id"),
    )
    review_notes: Mapped[str | None] = mapped_column(sa.Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.func.now(),
    )
