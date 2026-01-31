import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.order_factory import OrderFactory
from tests.factories.store_factory import StoreFactory
from tests.factories.user_factory import UserFactory


class TestOrderEndpoints:
    @pytest.mark.asyncio
    async def test_list_orders_for_buyer(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_user,
    ):
        seller = await UserFactory.create(db_session, roles=["seller"])
        store = await StoreFactory.create(db_session, user_id=seller.id)
        order = await OrderFactory.create(
            db_session,
            buyer_id=test_user.id,
            store_id=store.id,
        )

        response = await authenticated_client.get("/api/v1/orders")
        assert response.status_code == 200
        data = response.json()
        assert any(entry["id"] == order.id for entry in data["orders"])

    @pytest.mark.asyncio
    async def test_orders_requires_auth(self, client: AsyncClient):
        response = await client.get("/api/v1/orders")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_orders_user_not_found(self, client: AsyncClient):
        response = await client.get(
            "/api/v1/orders",
            headers={"X-User-Id": "999999"},
        )
        assert response.status_code == 401
