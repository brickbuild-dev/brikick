from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.checkout import UserAddress
from db.models.stores import StorePaymentMethod, StoreShippingMethod
from tests.factories.catalog_factory import CatalogItemFactory
from tests.factories.lot_factory import LotFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestPurchaseFlow:
    @pytest.mark.asyncio
    async def test_purchase_flow_complete(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)

        shipping_method = StoreShippingMethod(
            store_id=store.id,
            name="Standard",
            cost_type="FIXED",
            base_cost=Decimal("3.00"),
            tracking_type="FULL_TRACKING",
            is_active=True,
        )
        payment_method = StorePaymentMethod(
            store_id=store.id,
            method_type="CARD",
            name="Card",
            is_on_site=True,
            is_active=True,
        )
        db_session.add_all([shipping_method, payment_method])
        await db_session.commit()

        address = UserAddress(
            user_id=test_user.id,
            first_name="Buyer",
            last_name="Test",
            address_line1="Rua 123",
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

        item = await CatalogItemFactory.create(db_session)
        lot = await LotFactory.create(
            db_session,
            store_id=store.id,
            catalog_item_id=item.id,
            unit_price=Decimal("2.00"),
            quantity=5,
        )

        add_response = await authenticated_client.post(
            "/api/v1/cart/add",
            json={"lot_id": lot.id, "quantity": 2},
        )
        assert add_response.status_code == 200

        prepare_response = await authenticated_client.post(
            "/api/v1/checkout/prepare",
            json={"store_id": store.id},
        )
        assert prepare_response.status_code == 200
        draft_id = prepare_response.json()["draft"]["id"]

        ship_response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/shipping",
            json={"shipping_method_id": shipping_method.id, "address_id": address.id},
        )
        assert ship_response.status_code == 200

        pay_response = await authenticated_client.put(
            f"/api/v1/checkout/{draft_id}/payment",
            json={"payment_method_id": payment_method.id},
        )
        assert pay_response.status_code == 200

        submit_response = await authenticated_client.post(
            f"/api/v1/checkout/{draft_id}/submit"
        )
        assert submit_response.status_code == 200
        draft = submit_response.json()["draft"]
        assert draft["status"] == "COMPLETED"
        assert draft["items_total"] == 4.00
        assert draft["shipping_total"] == 3.00
        assert draft["grand_total"] == 7.00
