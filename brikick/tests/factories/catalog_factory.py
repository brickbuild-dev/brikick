from __future__ import annotations

from decimal import Decimal

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.catalog import (
    CatalogItem,
    Category,
    Color,
    ItemType,
    PriceGuide,
)

faker = Faker()


class CatalogFactory:
    @staticmethod
    async def create_item_type(
        db: AsyncSession,
        *,
        item_type_id: str = "P",
        name: str = "Part",
        name_plural: str = "Parts",
    ) -> ItemType:
        existing = await db.get(ItemType, item_type_id)
        if existing:
            return existing
        item_type = ItemType(id=item_type_id, name=name, name_plural=name_plural)
        db.add(item_type)
        await db.flush()
        return item_type

    @staticmethod
    async def create_category(
        db: AsyncSession,
        *,
        name: str | None = None,
        parent_id: int | None = None,
        allowed_item_types: str | None = None,
    ) -> Category:
        category = Category(
            name=name or faker.word(),
            parent_id=parent_id,
            allowed_item_types=allowed_item_types,
        )
        db.add(category)
        await db.flush()
        return category

    @staticmethod
    async def create_color(
        db: AsyncSession,
        *,
        color_id: int | None = None,
        name: str | None = None,
    ) -> Color:
        if color_id is not None:
            existing = await db.get(Color, color_id)
            if existing:
                return existing
        color = Color(
            id=color_id or faker.unique.random_int(min=1, max=9999),
            name=name or faker.color_name(),
            rgb=faker.hex_color().lstrip("#"),
            color_group=faker.random_int(min=1, max=20),
        )
        db.add(color)
        await db.flush()
        return color

    @staticmethod
    async def create_catalog_item(
        db: AsyncSession,
        *,
        item_type_id: str = "P",
        item_no: str | None = None,
        item_seq: int = 1,
        name: str | None = None,
        category_id: int | None = None,
    ) -> CatalogItem:
        await CatalogFactory.create_item_type(db, item_type_id=item_type_id)
        if category_id is None:
            category = await CatalogFactory.create_category(db)
            category_id = category.id

        item = CatalogItem(
            item_no=item_no or faker.unique.bothify(text="BRK-#####"),
            item_seq=item_seq,
            item_type=item_type_id,
            name=name or faker.sentence(nb_words=3),
            category_id=category_id,
            year_released=faker.random_int(min=1970, max=2024),
            weight_grams=Decimal("1.00"),
            status="ACTIVE",
        )
        db.add(item)
        await db.flush()
        return item

    @staticmethod
    async def create_price_guide(
        db: AsyncSession,
        *,
        catalog_item_id: int,
        color_id: int,
        condition: str = "N",
        avg_price_6m: Decimal | None = None,
        min_price_6m: Decimal | None = None,
        max_price_6m: Decimal | None = None,
        sales_count_6m: int = 10,
    ) -> PriceGuide:
        price_guide = PriceGuide(
            catalog_item_id=catalog_item_id,
            color_id=color_id,
            condition=condition,
            avg_price_6m=avg_price_6m or Decimal("1.0000"),
            min_price_6m=min_price_6m or Decimal("0.8000"),
            max_price_6m=max_price_6m or Decimal("1.5000"),
            sales_count_6m=sales_count_6m,
        )
        db.add(price_guide)
        await db.flush()
        return price_guide
