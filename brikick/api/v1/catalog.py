from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_db
from db.models.catalog import CatalogItem

catalog_router = APIRouter(prefix="/catalog", tags=["catalog"])


@catalog_router.get("/items")
async def list_catalog_items(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> dict:
    result = await db.execute(select(CatalogItem).limit(limit))
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": item.id,
                "item_no": item.item_no,
                "item_type": item.item_type,
                "name": item.name,
                "status": item.status,
            }
            for item in items
        ]
    }
