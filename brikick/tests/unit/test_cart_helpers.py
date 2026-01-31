from decimal import Decimal

import pytest

from api.v1 import cart as cart_module
from db.models.cart import Cart, CartItem, CartStore
from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestCartHelpers:
    @pytest.mark.asyncio
    async def test_get_or_create_cart_reuses(self, db_session):
        user = await UserFactory.create(db_session)
        cart = await cart_module._get_or_create_cart(db_session, user.id)
        cart_again = await cart_module._get_or_create_cart(db_session, user.id)
        assert cart_again.id == cart.id

    @pytest.mark.asyncio
    async def test_get_or_create_cart_store_reuses(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        cart = await cart_module._get_or_create_cart(db_session, user.id)
        cart_store = await cart_module._get_or_create_cart_store(db_session, cart.id, store.id)
        cart_store_again = await cart_module._get_or_create_cart_store(db_session, cart.id, store.id)
        assert cart_store_again.id == cart_store.id

    @pytest.mark.asyncio
    async def test_recalculate_cart_store_updates_totals(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        item = await CatalogItemFactory.create(db_session, weight_grams=Decimal("2.50"))
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        cart = Cart(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.flush()
        cart_item = CartItem(
            cart_store_id=cart_store.id,
            lot_id=lot.id,
            quantity=2,
            unit_price_snapshot=Decimal("3.00"),
            sale_price_snapshot=None,
        )
        db_session.add(cart_item)
        await db_session.commit()

        await cart_module._recalculate_cart_store(db_session, cart_store)
        await db_session.commit()
        await db_session.refresh(cart_store)

        assert cart_store.total_items == 2
        assert cart_store.total_lots == 1
        assert cart_store.subtotal == Decimal("6.00")
        assert cart_store.total_weight_grams == 5

    @pytest.mark.asyncio
    async def test_recalculate_cart_store_deletes_empty(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        cart = Cart(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.commit()

        await cart_module._recalculate_cart_store(db_session, cart_store)
        await db_session.flush()
        removed = await db_session.get(CartStore, cart_store.id)
        assert removed is None

    def test_compute_sale_price(self):
        assert cart_module._compute_sale_price(Decimal("10.00"), None) is None
        assert cart_module._compute_sale_price(Decimal("10.00"), 10) == Decimal("9.0000")

    @pytest.mark.asyncio
    async def test_build_cart_response_for_cart(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        cart = Cart(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.flush()
        cart_item = CartItem(
            cart_store_id=cart_store.id,
            lot_id=lot.id,
            quantity=1,
            unit_price_snapshot=Decimal("2.00"),
            sale_price_snapshot=None,
        )
        db_session.add(cart_item)
        await db_session.commit()

        await cart_module._recalculate_cart_store(db_session, cart_store)
        await db_session.commit()

        response = await cart_module._build_cart_response(db_session, cart)
        assert response["cart_id"] == cart.id
        assert response["items_total"] == 2.0

    @pytest.mark.asyncio
    async def test_build_cart_response_for_none(self, db_session):
        response = await cart_module._build_cart_response(db_session, None)
        assert response["stores"] == []
