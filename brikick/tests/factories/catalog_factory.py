from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from db.models.catalog import CatalogItem, Color, Category, PriceGuide
from decimal import Decimal

fake = Faker()


class CatalogItemFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        item_no: str = None,
        item_type: str = "P",
        **kwargs,
    ) -> CatalogItem:
        item_id = kwargs.pop("id", fake.unique.random_int(min=1, max=10_000_000))
        item = CatalogItem(
            id=item_id,
            item_no=item_no or fake.bothify("####"),
            item_type=item_type,
            name=fake.sentence(nb_words=3),
            status="ACTIVE",
            **kwargs,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        return item


class PriceGuideFactory:
    @staticmethod
    async def create(
        db: AsyncSession,
        catalog_item_id: int,
        color_id: int = 0,
        condition: str = "N",
        avg_price: Decimal = Decimal("1.00"),
        **kwargs,
    ) -> PriceGuide:
        guide_id = kwargs.pop("id", fake.unique.random_int(min=1, max=10_000_000))
        price_guide = PriceGuide(
            id=guide_id,
            catalog_item_id=catalog_item_id,
            color_id=color_id,
            condition=condition,
            avg_price_6m=avg_price,
            min_price_6m=avg_price * Decimal("0.5"),
            max_price_6m=avg_price * Decimal("1.5"),
            sales_count_6m=100,
            **kwargs,
        )
        db.add(price_guide)
        await db.commit()
        await db.refresh(price_guide)
        return price_guide
