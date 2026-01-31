import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.user_factory import UserFactory


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        user = await UserFactory.create(
            db_session,
            email="buyer@example.com",
            password="testpass123",
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "testpass123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ):
        user = await UserFactory.create(
            db_session,
            email="buyer2@example.com",
            password="correctpass",
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={"email": user.email, "password": "wrongpass"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_user(
        self,
        client: AsyncClient,
    ):
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "missing@example.com", "password": "testpass"},
        )
        assert response.status_code == 401
