import pytest
from decimal import Decimal

from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


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


@pytest.mark.asyncio
async def test_add_to_cart_lot_not_found(authenticated_client):
    response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": 999999, "quantity": 1},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_add_to_cart_inactive_store(authenticated_client, db_session):
    seller = await UserFactory.create(db_session, roles=["seller"])
    store = await StoreFactory.create(db_session, user_id=seller.id, status="INACTIVE")
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_to_cart_insufficient_stock(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=1,
    )

    response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 2},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_to_cart_unavailable_lot(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
        status="SOLD",
    )

    response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_to_cart_with_sale_price(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
        unit_price=Decimal("10.0000"),
    )
    lot.sale_percentage = 10
    await db_session.commit()

    response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    assert response.status_code == 200
    item = response.json()["stores"][0]["items"][0]
    assert item["sale_price_snapshot"] == 9.0


@pytest.mark.asyncio
async def test_cart_multiple_stores(authenticated_client, db_session, test_seller):
    other_seller = await UserFactory.create(db_session, roles=["seller"])
    other_store = await StoreFactory.create(db_session, user_id=other_seller.id)
    item_one = await CatalogItemFactory.create(db_session)
    item_two = await CatalogItemFactory.create(db_session)
    lot_one = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=item_one.id,
        quantity=5,
    )
    lot_two = await LotFactory.create(
        db_session,
        store_id=other_store.id,
        catalog_item_id=item_two.id,
        quantity=5,
    )

    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot_one.id, "quantity": 1},
    )
    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot_two.id, "quantity": 1},
    )

    response = await authenticated_client.get("/api/v1/cart")
    assert response.status_code == 200
    data = response.json()
    assert len(data["stores"]) == 2


@pytest.mark.asyncio
async def test_update_cart_item_quantity(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    add_response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    item_id = add_response.json()["stores"][0]["items"][0]["id"]

    update_response = await authenticated_client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 3},
    )
    assert update_response.status_code == 200
    updated = update_response.json()["stores"][0]["items"][0]["quantity"]
    assert updated == 3


@pytest.mark.asyncio
async def test_update_cart_item_exceeds_stock(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=1,
    )

    add_response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    item_id = add_response.json()["stores"][0]["items"][0]["id"]

    update_response = await authenticated_client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 2},
    )
    assert update_response.status_code == 400


@pytest.mark.asyncio
async def test_update_cart_item_lot_unavailable(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    add_response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    item_id = add_response.json()["stores"][0]["items"][0]["id"]
    lot.status = "SOLD"
    await db_session.commit()

    update_response = await authenticated_client.put(
        f"/api/v1/cart/items/{item_id}",
        json={"quantity": 1},
    )
    assert update_response.status_code == 400


@pytest.mark.asyncio
async def test_update_cart_item_not_found(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )
    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )

    update_response = await authenticated_client.put(
        "/api/v1/cart/items/999999",
        json={"quantity": 1},
    )
    assert update_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_cart_item(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    add_response = await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )
    item_id = add_response.json()["stores"][0]["items"][0]["id"]

    delete_response = await authenticated_client.delete(
        f"/api/v1/cart/items/{item_id}",
    )
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["stores"] == []


@pytest.mark.asyncio
async def test_delete_cart_item_not_found(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )
    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )

    delete_response = await authenticated_client.delete(
        "/api/v1/cart/items/999999",
    )
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_cart_store(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )

    delete_response = await authenticated_client.delete(
        f"/api/v1/cart/stores/{test_seller.store.id}",
    )
    assert delete_response.status_code == 200
    data = delete_response.json()
    assert data["stores"] == []


@pytest.mark.asyncio
async def test_delete_cart_store_not_found(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 1},
    )

    delete_response = await authenticated_client.delete(
        "/api/v1/cart/stores/999999",
    )
    assert delete_response.status_code == 404


@pytest.mark.asyncio
async def test_cart_count(authenticated_client, db_session, test_seller):
    catalog_item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(
        db_session,
        store_id=test_seller.store.id,
        catalog_item_id=catalog_item.id,
        quantity=5,
    )

    await authenticated_client.post(
        "/api/v1/cart/add",
        json={"lot_id": lot.id, "quantity": 2},
    )

    response = await authenticated_client.get("/api/v1/cart/count")
    assert response.status_code == 200
    data = response.json()
    assert data["total_items"] == 2
    assert data["total_lots"] == 1
