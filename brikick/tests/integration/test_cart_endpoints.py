import pytest

from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory


@pytest.mark.asyncio
async def test_get_cart_empty(authenticated_client):
    response = await authenticated_client.get("/api/v1/cart")
    assert response.status_code == 200
    data = response.json()
    assert data["items_total"] == 0.0
    assert data["stores"] == []


@pytest.mark.asyncio
async def test_add_to_cart(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items_total"] > 0
    assert data["stores"][0]["items"][0]["quantity"] == 1
