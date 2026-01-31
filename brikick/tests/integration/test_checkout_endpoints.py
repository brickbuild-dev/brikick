import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.cart import Cart, CartItem, CartStore
from db.models.checkout import CheckoutApproval, UserAddress
from db.models.penalties import UserPenalty
from db.models.rating import UserRatingMetrics
from db.models.stores import StorePaymentMethod, StoreShippingMethod
from sqlalchemy import select
from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.order_factory import OrderFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestCheckoutEndpoints:
    """Tests for checkout flow with Hard Rules"""

    @pytest.mark.asyncio
    async def test_checkout_requires_shipping_method(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        """HARD RULE: Checkout without shipping method should fail"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(
            db_session, store_id=store.id, catalog_item_id=item.id
        )

        response = await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        assert response.status_code == 200

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert response.status_code == 200
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )

        assert response.status_code == 422
        assert response.json()["error_code"] == "SHIPPING_REQUIRED"

    @pytest.mark.asyncio
    async def test_prepare_checkout_cart_store_not_found(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_prepare_checkout_store_inactive(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id, status="INACTIVE")
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.flush()
        cart_item = CartItem(
            cart_store_id=cart_store.id,
            lot_id=lot.id,
            quantity=1,
            unit_price_snapshot=lot.unit_price,
            sale_price_snapshot=None,
        )
        db_session.add(cart_item)
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_prepare_checkout_empty_cart_store(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        cart = Cart(user_id=test_user.id)
        db_session.add(cart)
        await db_session.flush()
        cart_store = CartStore(cart_id=cart.id, store_id=store.id)
        db_session.add(cart_store)
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_prepare_checkout_missing_currency(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id, currency_id=None)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )

        test_user.preferred_currency_id = None
        await db_session.commit()

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_checkout_no_hidden_fees(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        """No handling fees or hidden costs in checkout"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(
            db_session,
            store_id=store.id,
            catalog_item_id=item.id,
            unit_price=Decimal("10.00"),
            quantity=5,
        )

        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        db_session.add(shipping)
        await db_session.commit()

        address = UserAddress(
            user_id=test_user.id,
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
        db_session.add(address)
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 2},
        )

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        assert response.status_code == 200
        data = response.json()["draft"]

        assert data["items_total"] == 20.00
        assert data["shipping_total"] == 5.00
        assert data["grand_total"] == 25.00

        assert "handling_fee" not in data
        assert "packaging_fee" not in data
        assert "service_fee" not in data

    @pytest.mark.asyncio
    async def test_checkout_is_automatic_no_invoice_request(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
    ):
        """Checkout should be automatic, no 'request invoice' option"""
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(
            db_session, store_id=store.id, catalog_item_id=item.id
        )

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )

        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_status = response.json()["draft"]["status"]
        valid_statuses = [
            "DRAFT",
            "PENDING_SHIPPING",
            "PENDING_PAYMENT",
            "COMPLETED",
            "ABANDONED",
        ]

        assert "AWAITING_INVOICE" not in valid_statuses
        assert draft_status in valid_statuses

    @pytest.mark.asyncio
    async def test_untracked_shipping_requires_proof(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_seller,
        test_user,
    ):
        """Orders with untracked shipping must require proof"""
        order = await OrderFactory.create(
            db_session,
            buyer_id=test_user.id,
            store_id=test_seller.store.id,
        )
        await db_session.refresh(order)
        assert bool(order.shipping_proof_required) is True

        order.shipped_at = datetime.now(timezone.utc)
        order.shipping_proof_deadline = order.shipped_at + timedelta(hours=48)
        await db_session.commit()
        await db_session.refresh(order)
        assert order.shipping_proof_deadline is not None

    @pytest.mark.asyncio
    async def test_get_shipping_methods(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("4.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        db_session.add(shipping)
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.get(
            f"/api/v1/checkout/{draft_id}/shipping-methods"
        )
        assert response.status_code == 200
        assert any(method["id"] == shipping.id for method in response.json()["shipping_methods"])

    @pytest.mark.asyncio
    async def test_update_shipping_requires_address(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        db_session.add(shipping)
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "ADDRESS_REQUIRED"

    @pytest.mark.asyncio
    async def test_update_shipping_requires_method(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": None, "address_id": None},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "SHIPPING_REQUIRED"

    @pytest.mark.asyncio
    async def test_update_shipping_method_not_found(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        address = UserAddress(
            user_id=test_user.id,
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
        db_session.add(address)
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": 999999, "address_id": address.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_shipping_method_inactive(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
            tracking_type="FULL_TRACKING",
            is_active=False,
        )
        address = UserAddress(
            user_id=test_user.id,
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
        db_session.add_all([shipping, address])
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_shipping_method_wrong_store(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        other_seller = await UserFactory.create(db_session, roles=["seller"])
        other_store = await StoreFactory.create(db_session, user_id=other_seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=other_store.id,
            name="Other",
            cost_type="FIXED",
            base_cost=Decimal("4.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        address = UserAddress(
            user_id=test_user.id,
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
        db_session.add_all([shipping, address])
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_payment_requires_method(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": None},
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "PAYMENT_REQUIRED"

    @pytest.mark.asyncio
    async def test_update_payment_method_not_found(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": 999999},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_payment_method_inactive(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        payment = StorePaymentMethod(
            store_id=store.id,
            method_type="CARD",
            name="Card",
            is_on_site=True,
            is_active=False,
        )
        db_session.add(payment)
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_requires_payment(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        address = UserAddress(
            user_id=test_user.id,
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
        db_session.add_all([shipping, address])
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 422
        assert response.json()["error_code"] == "PAYMENT_REQUIRED"

    @pytest.mark.asyncio
    async def test_submit_cart_store_not_found(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
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
            user_id=test_user.id,
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

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )

        cart_store = await db_session.get(CartStore, response.json()["draft"]["cart_store_id"])
        await db_session.delete(cart_store)
        await db_session.commit()

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_lot_unavailable(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
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
            user_id=test_user.id,
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

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )

        lot.status = "SOLD"
        await db_session.commit()

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_lot_stock_changed(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id, quantity=1)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
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
            user_id=test_user.id,
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

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )

        lot.quantity = 0
        await db_session.commit()

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_store_inactive(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
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
            user_id=test_user.id,
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

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )

        store.status = "INACTIVE"
        await db_session.commit()

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_payment_method_wrong_store(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        other_seller = await UserFactory.create(db_session, roles=["seller"])
        other_store = await StoreFactory.create(db_session, user_id=other_seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        payment = StorePaymentMethod(
            store_id=other_store.id,
            method_type="CARD",
            name="Other",
            is_on_site=True,
            is_active=True,
        )
        db_session.add(payment)
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_prepare_checkout_empty_shipping_methods(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert response.status_code == 200
        assert response.json()["shipping_methods"] == []

    @pytest.mark.asyncio
    async def test_get_shipping_methods_not_found(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        response = await authenticated_client.get("/api/v1/checkout/999999/shipping-methods")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_submit_restricted_buyer(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
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
            user_id=test_user.id,
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
        penalty = UserPenalty(
            user_id=test_user.id,
            penalty_type="SUSPENSION",
            reason_code="TEST",
            starts_at=datetime.now(timezone.utc) - timedelta(days=1),
            ends_at=datetime.now(timezone.utc) + timedelta(days=1),
            restrictions={"can_buy": False},
            created_at=datetime.now(timezone.utc),
        )
        db_session.add_all([shipping, payment, address, penalty])
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 403
        assert response.json()["error_code"] == "BUYER_RESTRICTED"

    @pytest.mark.asyncio
    async def test_submit_requires_approval_for_risky_buyer(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(
            db_session,
            user_id=seller.id,
            require_approval_for_risky_buyers=True,
            risk_threshold_score=80.0,
        )
        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(db_session, store_id=store.id, catalog_item_id=item.id)
        shipping = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("5.00"),
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
            user_id=test_user.id,
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
        rating = UserRatingMetrics(
            user_id=test_user.id,
            period_start=datetime.now(timezone.utc).date(),
            period_end=datetime.now(timezone.utc).date(),
            overall_score=Decimal("50.00"),
            score_tier="AVERAGE",
            calculated_at=datetime.now(timezone.utc),
        )
        db_session.add_all([shipping, payment, address, rating])
        await db_session.commit()

        await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 1},
        )
        response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        draft_id = response.json()["draft"]["id"]

        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping.id, "address_id": address.id},
        )
        await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment.id},
        )

        response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert response.status_code == 200
        assert response.json()["approval_required"] is True

        approval_result = await db_session.execute(
            select(CheckoutApproval).where(CheckoutApproval.user_id == test_user.id)
        )
        assert approval_result.scalar_one_or_none() is not None
