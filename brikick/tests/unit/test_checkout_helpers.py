from decimal import Decimal

import pytest

from api.v1 import checkout as checkout_module
from db.models.cart import Cart, CartItem, CartStore
from db.models.checkout import CheckoutDraft, UserAddress
from db.models.stores import StoreShippingMethod
from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestCheckoutHelpers:
    @pytest.mark.asyncio
    async def test_get_cart_store_for_user(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        cart = Cart(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.commit()

        found = await checkout_module._get_cart_store_for_user(db_session, user.id, store.id)
        assert found.id == cart_store.id

    @pytest.mark.asyncio
    async def test_get_active_cart_items(self, db_session):
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
            quantity=2,
            unit_price_snapshot=Decimal("3.00"),
            sale_price_snapshot=Decimal("2.50"),
        )
        db_session.add(cart_item)
        await db_session.commit()

        items = await checkout_module._get_active_cart_items(db_session, cart_store.id)
        assert len(items) == 1
        total = await checkout_module._calculate_items_total(items)
        assert total == Decimal("5.00")

    @pytest.mark.asyncio
    async def test_get_draft_for_user(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        cart = Cart(user_id=user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.flush()
        draft = CheckoutDraft(
            cart_store_id=cart_store.id,
            user_id=user.id,
            store_id=store.id,
            payment_currency_id=978,
            items_total=Decimal("1.00"),
            shipping_total=Decimal("0.00"),
            tax_total=Decimal("0.00"),
            grand_total=Decimal("1.00"),
        )
        db_session.add(draft)
        await db_session.commit()

        found = await checkout_module._get_draft_for_user(db_session, user.id, draft.id)
        assert found.id == draft.id

    @pytest.mark.asyncio
    async def test_get_store_shipping_methods_filters_inactive(self, db_session):
        user = await UserFactory.create(db_session)
        store = await StoreFactory.create(db_session, user_id=user.id)
        active = StoreShippingMethod(
            store_id=store.id,
            name="Active",
            cost_type="FIXED",
            base_cost=Decimal("1.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        inactive = StoreShippingMethod(
            store_id=store.id,
            name="Inactive",
            cost_type="FIXED",
            base_cost=Decimal("1.00"),
            tracking_type="FULL_TRACKING",
            is_active=False,
        )
        unknown = StoreShippingMethod(
            store_id=store.id,
            name="Unknown",
            cost_type="FIXED",
            base_cost=Decimal("1.00"),
            tracking_type="FULL_TRACKING",
            is_active=None,
        )
        db_session.add_all([active, inactive, unknown])
        await db_session.commit()

        methods = await checkout_module._get_store_shipping_methods(db_session, store.id)
        ids = {method.id for method in methods}
        assert active.id in ids
        assert unknown.id in ids
        assert inactive.id not in ids

    def test_serialize_shipping_method(self):
        method = StoreShippingMethod(
            id=1,
            store_id=1,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("2.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        data = checkout_module._serialize_shipping_method(method)
        assert data["id"] == 1
        assert data["base_cost"] == 2.0

    def test_calculate_totals(self):
        shipping_total, grand_total = checkout_module._calculate_totals(
            items_total=Decimal("10.00"),
            shipping_cost=Decimal("2.00"),
            insurance_cost=Decimal("1.00"),
            tracking_fee=Decimal("0.50"),
            tax_total=Decimal("0.50"),
        )
        assert shipping_total == Decimal("3.50")
        assert grand_total == Decimal("14.00")

    def test_is_address_complete(self):
        address = UserAddress(
            first_name="A",
            last_name="B",
            address_line1="Rua 1",
            address_line2=None,
            city="Porto",
            state_name="Porto",
            postal_code="4000",
            country_code="PT",
            phone="+351",
            user_id=1,
            is_default=True,
        )
        assert checkout_module._is_address_complete(address) is True
        address.phone = ""
        assert checkout_module._is_address_complete(address) is False
