from decimal import Decimal

import pytest
from fastapi import HTTPException

from api.v1.cart import (
    CartAddItemRequest,
    CartUpdateItemRequest,
    add_to_cart,
    delete_cart_item,
    delete_cart_store,
    get_cart,
    get_cart_count,
    update_cart_item,
)
from db.models.cart import Cart, CartItem, CartStore
from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_cart_endpoints_direct_flow(db_session):
    buyer = await UserFactory.create(db_session)
    seller = await UserFactory.create(db_session, roles=["seller"])
    store = await StoreFactory.create(db_session, user_id=seller.id)
    item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

    empty_cart = await get_cart(db=db_session, current_user=buyer)
    assert empty_cart["cart_id"] is None

    empty_count = await get_cart_count(db=db_session, current_user=buyer)
    assert empty_count == {"total_items": 0, "total_lots": 0}

    add_payload = CartAddItemRequest(lot_id=lot.id, quantity=1)
    add_response = await add_to_cart(add_payload, db_session, buyer)
    cart_id = add_response["cart_id"]
    item_id = add_response["stores"][0]["items"][0]["id"]

    update_payload = CartUpdateItemRequest(quantity=2)
    update_response = await update_cart_item(item_id, update_payload, db_session, buyer)
    assert update_response["stores"][0]["items"][0]["quantity"] == 2

    delete_response = await delete_cart_item(item_id, db_session, buyer)
    assert delete_response["stores"] == []

    cart = await db_session.get(Cart, cart_id)
    cart_store = CartStore(cart_id=cart.id, store_id=store.id)
    db_session.add(cart_store)
    await db_session.flush()
    cart_item = CartItem(
        cart_store_id=cart_store.id,
        lot_id=lot.id,
        quantity=1,
        unit_price_snapshot=Decimal("1.00"),
        sale_price_snapshot=None,
    )
    db_session.add(cart_item)
    await db_session.commit()

    response = await delete_cart_store(store.id, db_session, buyer)
    assert response["stores"] == []


@pytest.mark.asyncio
async def test_add_to_cart_direct_lot_not_found(db_session):
    buyer = await UserFactory.create(db_session)
    payload = CartAddItemRequest(lot_id=999999, quantity=1)
    with pytest.raises(HTTPException):
        await add_to_cart(payload, db_session, buyer)
