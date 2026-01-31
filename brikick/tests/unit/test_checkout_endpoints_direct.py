from decimal import Decimal

import pytest

from api.v1 import checkout as checkout_module
from api.v1.checkout import (
    CheckoutPaymentRequest,
    CheckoutPrepareRequest,
    CheckoutShippingRequest,
)
from db.models.cart import Cart, CartItem, CartStore
from db.models.checkout import UserAddress
from db.models.stores import StorePaymentMethod, StoreShippingMethod
from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


@pytest.mark.asyncio
async def test_checkout_endpoints_direct_flow(db_session):
    buyer = await UserFactory.create(db_session)
    seller = await UserFactory.create(db_session, roles=["seller"])
    store = await StoreFactory.create(db_session, user_id=seller.id)
    item = await CatalogItemFactory.create(db_session)
    lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

    cart = Cart(user_id=buyer.id)
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

    shipping = StoreShippingMethod(
        store_id=store.id,
        name="Standard",
        cost_type="FIXED",
        base_cost=Decimal("3.00"),
        tracking_type="FULL_TRACKING",
        is_active=True,
    )
    payment = StorePaymentMethod(
        store_id=store.id,
        method_type="CARD",
        name="Card",
        is_on_site=True,
        is_active=True,
    )
    address = UserAddress(
        user_id=buyer.id,
        first_name="Test",
        last_name="Buyer",
        address_line1="Rua 1",
        address_line2=None,
        city="Porto",
        state_name="Porto",
        postal_code="4000-000",
        country_code="PT",
        phone="+351999999999",
        is_default=True,
    )
    db_session.add_all([shipping, payment, address])
    await db_session.commit()

    prepare_payload = CheckoutPrepareRequest(store_id=store.id)
    prepare_response = await checkout_module.prepare_checkout(
        prepare_payload, db_session, buyer
    )
    draft_id = prepare_response["draft"]["id"]

    methods = await checkout_module.get_shipping_methods(draft_id, db_session, buyer)
    assert len(methods["shipping_methods"]) == 1

    shipping_payload = CheckoutShippingRequest(
        shipping_method_id=shipping.id,
        address_id=address.id,
    )
    shipping_response = await checkout_module.update_shipping(
        draft_id, shipping_payload, db_session, buyer
    )
    assert shipping_response["draft"]["shipping_method_id"] == shipping.id

    payment_payload = CheckoutPaymentRequest(payment_method_id=payment.id)
    payment_response = await checkout_module.update_payment(
        draft_id, payment_payload, db_session, buyer
    )
    assert payment_response["draft"]["payment_method_id"] == payment.id

    submit_response = await checkout_module.submit_checkout(draft_id, db_session, buyer)
    assert submit_response["draft"]["status"] == "COMPLETED"
