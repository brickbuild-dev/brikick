import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.catalog_factory import CatalogItemFactory


class TestCatalogEndpoints:
    @pytest.mark.asyncio
    async def test_list_catalog_items(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        item = await CatalogItemFactory.create(db_session)

        response = await client.get("/api/v1/catalog/items")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert any(entry["id"] == item.id for entry in data["items"])
