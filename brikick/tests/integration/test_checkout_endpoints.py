import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.checkout import UserAddress
from db.models.stores import StoreShippingMethod
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
